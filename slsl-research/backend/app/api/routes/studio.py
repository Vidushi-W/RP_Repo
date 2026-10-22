"""Simple local train/test workspace; inference never receives reference labels."""
import csv
import hashlib
import io
import json
import random
import threading
import uuid
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import SENSOR_COLUMNS, settings
from app.core.database import get_db
from app.ml.inference import load_bundle, recognize_from_csv
from app.ml.metrics import sequence_metrics
from app.ml import sinhala_speech
from app.ml.local_sentence import generate_spoken_sentence
from app.ml.expression_rules import load_rules, save_rules, analyze_expression, expression_text, annotate_sentence
from app.ml.preprocessing import validate_dataframe
from app.ml.sentence_generator import generate_english_sentence
from app.models.dataset import Recording
from app.models.ml_model import MLModel
from app.services.dataset_service import DatasetService
from app.services.reset_service import ResetService
from app.services.training_service import TrainingService

router = APIRouter(prefix="/studio", tags=["studio"])
_TEST_RECORD_LOCK = threading.RLock()


def save_test_record(row):
    """Readers see either the old complete JSON or the new complete JSON."""
    with _TEST_RECORD_LOCK:
        destination = test_dir() / (row['id'] + '.json')
        temporary = destination.with_suffix('.' + uuid.uuid4().hex + '.tmp')
        try:
            temporary.write_text(json.dumps(row), encoding='utf-8')
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)


def current_model(db):
    models = list(db.scalars(select(MLModel).where(MLModel.is_archived == False).order_by(MLModel.id.desc())))
    return next((m for m in models if m.status == "active"), models[0] if models else None)


def test_dir():
    path = settings.data_dir / "studio_tests"
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_records():
    with _TEST_RECORD_LOCK:
        return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(test_dir().glob("*.json"))]


@lru_cache(maxsize=32768)
def canonical_training_hash(path_string, mtime_ns, size):
    path = Path(path_string)
    return motion_fingerprint(sensor_dataframe(path.read_bytes()))


def motion_fingerprint(df):
    # Compare numerical motion, independent of CSV formatting or clock start.
    values = df[SENSOR_COLUMNS].to_numpy(dtype=np.float64).copy()
    values[:, 0] -= values[0, 0]
    values = np.round(values, 7)
    values[values == 0] = 0  # canonicalize negative zero
    return hashlib.sha256(values.astype('<f8').tobytes()).hexdigest()


def exposed_recording_ids(db, model):
    """Train AND validation exposure, including continued-training ancestors."""
    seen, exposed = set(), set()
    bundle = (settings.artifacts_dir / model.bundle_path).resolve()
    root = settings.artifacts_dir.resolve()
    while bundle not in seen and bundle.is_relative_to(root):
        seen.add(bundle)
        source_file = bundle / 'training_sources.json'
        if not source_file.exists():
            # Older bundles lack provenance: exclude known library exposure conservatively.
            exposed.update(db.scalars(select(Recording.id).where(Recording.split.in_(['train', 'val']))))
            break
        sources = json.loads(source_file.read_text())
        exposed.update(r['id'] for r in sources if r.get('split') in {'train', 'val'})
        config_file = bundle / 'training_settings.json'
        config = json.loads(config_file.read_text()) if config_file.exists() else {}
        source = config.get('source_bundle_path')
        if not source:
            break
        candidate = Path(source)
        bundle = (candidate if candidate.is_absolute() else Path.cwd() / candidate).resolve()
    return exposed


def evaluation_summary(tests, model_id):
    labelled = [t for t in tests if t.get('expected_signs')]
    scored, excluded, words = [], 0, 0
    seen = set()
    for row in labelled:
        result = row.get('result') or {}
        if result.get('model_id') != model_id or result.get('evaluation_version') != 2:
            continue
        if result.get('accuracy_excluded_reason'):
            excluded += 1
            continue
        identity = result.get('motion_fingerprint', row['id'])
        if identity in seen:
            excluded += 1
            continue
        seen.add(identity)
        # Recompute from raw words, never cached percentage, AI prose or confidence.
        scored.append(sequence_metrics(row['expected_signs'], result.get('predicted_signs', [])))
        words += len(row['expected_signs'])
    matches = sum(m.exact_match for m in scored)
    n = len(scored)
    errors = sum(m.insertions + m.deletions + m.substitutions for m in scored)
    interval = None
    if n:
        p = matches / n
        z = 1.96
        center = (p + z*z/(2*n))/(1 + z*z/n)
        half = z*((p*(1-p)/n + z*z/(4*n*n))**.5)/(1 + z*z/n)
        interval = [max(0., center-half), min(1., center+half)]
    return dict(accuracy=matches/n if n else None, evaluated_recordings=n,
        exact_matches=matches, labelled_test_recordings=len(labelled),
        pending_evaluations=len(labelled)-n-excluded, excluded_evaluations=excluded,
        unlabelled_test_recordings=len(tests)-len(labelled),
        sign_error_rate=errors/words if words else None, accuracy_interval=interval)


def error(exc):
    return HTTPException(status_code=400, detail=str(exc))


def sensor_dataframe(data):
    df = pd.read_csv(io.BytesIO(data))
    report = validate_dataframe(df)
    if not report.valid:
        raise ValueError("; ".join(report.errors))
    df = df[SENSOR_COLUMNS].copy()
    if not np.isfinite(df.to_numpy(dtype=float)).all():
        raise ValueError("Timestamps and sensor values must be finite numbers.")
    if len(df) < 4 or (np.diff(df.timestamp_ms.to_numpy()) <= 0).any():
        raise ValueError("Use at least four frames with strictly increasing timestamps.")
    return df


def collection_ids():
    path = settings.data_dir / "studio_collections.json"
    return json.loads(path.read_text()) if path.exists() else None


def prepare_recordings(db):
    recordings = list(db.scalars(select(Recording).order_by(Recording.id)))
    included = collection_ids()
    if included is not None:
        recordings = [r for r in recordings if r.dataset_id in included]
    labelled = [r for r in recordings if r.ordered_sign_labels.strip()]
    groups = {}
    for r in labelled:
        groups.setdefault(r.content_hash or f"recording:{r.id}", []).append(r)
    keys = sorted(groups)
    random.Random(42).shuffle(keys)
    for index, key in enumerate(keys):
        group = groups[key]
        existing = {r.split for r in group if r.split in {"train", "val", "test"}}
        if len(existing) > 1:
            raise ValueError("Identical recordings occur across training and held-out sets. Resolve their splits before training.")
        split = next(iter(existing)) if existing else ("val" if index % 10 == 0 else "test" if index % 10 == 1 else "train")
        for r in group:
            r.split = split
    db.commit()
    # Replay all previous training datasets, deduplicating identical source bytes.
    return [group[0] for group in groups.values()]


@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    model = current_model(db)
    vocabulary = json.loads(model.vocabulary_json or "{}") if model else {}
    labels = vocabulary.get("labels", []) if isinstance(vocabulary, dict) else vocabulary
    tests = test_records()
    evaluation = evaluation_summary(tests, model.id if model else None)
    jobs = TrainingService(db).list_jobs()
    included = collection_ids()
    if included is not None:
        # Deleted collections may remain in older saved selections.
        from app.models.dataset import Dataset
        known = set(db.scalars(select(Dataset.id)))
        included = sorted(set(included) & known)
    return dict(model=dict(id=model.id, name="SLSL Model", version=model.version) if model else None,
        vocabulary=[s for s in labels if s != "<blank>"],
        included_dataset_ids=included,
        training_recordings=len([r for r in db.scalars(select(Recording)) if included is None or r.dataset_id in included]), test_recordings=len(tests),
        **evaluation, jobs=[dict(id=j.id,status=j.status,epoch=j.current_epoch,
            epochs=j.total_epochs,message=j.message,loss=j.train_loss) for j in jobs[:8]])


@router.get("/tests")
def tests():
    return test_records()


@router.delete('/tests/{test_id}')
def delete_test(test_id: str):
    with _TEST_RECORD_LOCK:
        row = next((r for r in test_records() if r['id'] == test_id), None)
        if row is None:
            raise HTTPException(404, 'Test recording not found')
        directory = test_dir().resolve()
        paths = [directory / (test_id + suffix) for suffix in ('.csv', '.json')]
        if any(p.resolve().parent != directory for p in paths):
            raise HTTPException(400, 'Invalid test recording ID')
        paths += list(sinhala_speech.audio_directory(test_id).glob('*.wav'))
        backups = {p: p.read_bytes() for p in paths if p.exists()}
        try:
            for path in paths:
                path.unlink(missing_ok=True)
        except OSError as exc:
            for path, content in backups.items():
                path.write_bytes(content)
            raise HTTPException(500, 'Could not delete the recording. Please try again.') from exc
    return dict(deleted=test_id)


class ExpressionRuleRequest(BaseModel):
    enabled: bool = True
    words: list[str] = Field(default_factory=list, max_length=100)


@router.get("/expression-rules")
def expression_rules():
    try:return load_rules()
    except ValueError as exc:raise HTTPException(503,str(exc)) from exc


@router.put("/expression-rules")
def update_expression_rules(payload: ExpressionRuleRequest):
    try:return save_rules(payload.enabled,payload.words)
    except ValueError as exc:raise error(exc) from exc


@router.post("/data/training")
async def upload_training(files: list[UploadFile] = File(...), name: str = Form("Training recordings"),
                          manifest: UploadFile | None = File(None), db: Session = Depends(get_db)):
    """Accept inline sequence labels or the existing manifest workflow."""
    parsed = []
    source_records = []
    manifest_rows = {}
    try:
        if manifest:
            for row in csv.DictReader(io.StringIO((await manifest.read()).decode("utf-8-sig"))):
                manifest_rows[str(row.get("recording_id", ""))] = row
        for file in files:
            content = await file.read(settings.max_upload_bytes + 1)
            if len(content) > settings.max_upload_bytes:
                raise ValueError("Each recording must be smaller than 50 MB.")
            raw = pd.read_csv(io.BytesIO(content), dtype={"recording_id": str})
            if "recording_id" in raw:
                parts = raw.groupby("recording_id", sort=False)
            else:
                parts = [(Path(file.filename or "recording.csv").stem, raw)]
            for source_id, part in parts:
                metadata = manifest_rows.get(str(source_id), {})
                label_column = next((c for c in ("ordered_sign_labels", "sign_labels", "meaning") if c in part), None)
                labels = part[label_column].dropna().astype(str).str.strip().unique().tolist() if label_column else []
                labels = [s for s in labels if s]
                label = metadata.get("ordered_sign_labels", "").strip() or (labels[0] if len(labels) == 1 else "")
                if not label or len(labels) > 1:
                    raise ValueError(f"{source_id}: supply one ordered sequence per recording, such as I|NEED|WATER.")
                data = sensor_dataframe(part.to_csv(index=False).encode())
                rid = uuid.uuid4().hex
                source_records.append(dict(stored_recording_id=rid, source_file=file.filename,
                    source_recording_id=str(source_id), source_sha256=hashlib.sha256(content).hexdigest(),
                    supplied_metadata=dict(metadata), ordered_sign_labels=label))
                parsed.append((rid, data.to_csv(index=False).encode(), dict(recording_id=rid,
                    ordered_sign_labels=label, signer_id=metadata.get("signer_id", "UNKNOWN"),
                    provenance=metadata.get("provenance", "imported"), group_id=metadata.get("group_id", rid))))
        if not parsed:
            raise ValueError("No labelled recordings found.")
        service = DatasetService(db)
        dataset = service.create_dataset(name, provenance="imported")
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=list(parsed[0][2]))
        writer.writeheader(); writer.writerows(p[2] for p in parsed)
        uploads = [UploadFile(filename=rid+".csv", file=io.BytesIO(data)) for rid,data,_ in parsed]
        result = service.import_files(dataset.id, uploads,
            UploadFile(filename="manifest.csv", file=io.BytesIO(buffer.getvalue().encode())))
        source_path = settings.datasets_dir / str(dataset.id) / dataset.current_version / "studio_sources.json"
        source_path.write_text(json.dumps(source_records, indent=2), encoding="utf-8")
        included = collection_ids()
        if included is not None:
            included.append(dataset.id)
            (settings.data_dir / "studio_collections.json").write_text(json.dumps(sorted(set(included))))
        return dict(dataset_id=dataset.id, **result)
    except (ValueError, KeyError, pd.errors.ParserError) as exc:
        raise error(exc) from exc


@router.post("/data/tests")
async def upload_tests(files: list[UploadFile] = File(...), answer_key: UploadFile | None = File(None)):
    answers = {}
    prepared = []
    try:
        if answer_key:
            reader = csv.DictReader(io.StringIO((await answer_key.read()).decode("utf-8-sig")))
            if not {"recording_id", "ordered_sign_labels"}.issubset(reader.fieldnames or []):
                raise ValueError("Answer key requires recording_id and ordered_sign_labels columns.")
            answers = {r["recording_id"]: r["ordered_sign_labels"] for r in reader}
        for file in files:
            data = await file.read(settings.max_upload_bytes + 1)
            if len(data) > settings.max_upload_bytes:
                raise ValueError("Each test must be smaller than 50 MB.")
            df = sensor_dataframe(data)
            rid = uuid.uuid4().hex
            filename = Path(file.filename or "test.csv").name
            expected = answers.get(Path(filename).stem, "")
            content_hash = hashlib.sha256(df.to_csv(index=False).encode()).hexdigest()
            existing = next((r for r in test_records() if r.get("content_hash") == content_hash), None)
            if existing:
                rid = existing["id"]
                if not expected:
                    expected = "|".join(existing["expected_signs"])
            row = dict(id=rid, content_hash=content_hash, filename=filename, frames=len(df),
                duration_ms=float(df.timestamp_ms.iloc[-1]-df.timestamp_ms.iloc[0]),
                expected_signs=[s.strip() for s in expected.split("|") if s.strip()], result=None)
            prepared.append((row, df))
        for row, df in prepared:
            df.to_csv(test_dir() / (row["id"]+".csv"), index=False)
            (test_dir() / (row["id"]+".json")).write_text(json.dumps(row), encoding="utf-8")
        return dict(imported=len(prepared))
    except (ValueError, KeyError, pd.errors.ParserError) as exc:
        raise error(exc) from exc


class TrainRequest(BaseModel):
    epochs: int = Field(20, ge=1, le=100)
    learning_rate: float = Field(.001, gt=0, le=.1)


@router.post("/train")
def train(payload: TrainRequest, db: Session = Depends(get_db)):
    try:
        if TrainingService(db)._active_job():
            raise ValueError("Training is already running.")
        recordings = prepare_recordings(db)
        train_rows = [r for r in recordings if r.split == "train"]
        val_rows = [r for r in recordings if r.split == "val"]
        if not train_rows or not val_rows:
            raise ValueError("Add more labelled recordings so training and validation both contain examples.")
        model = current_model(db)
        source = settings.artifacts_dir / model.bundle_path if model else None
        known = set(t.strip() for r in train_rows for t in r.ordered_sign_labels.split("|") if t.strip())
        if source:
            known.update(json.loads((source/"vocabulary.json").read_text())["labels"])
        unknown = {t.strip() for r in val_rows for t in r.ordered_sign_labels.split("|") if t.strip()} - known
        if unknown:
            raise ValueError("Add training examples for these held-out signs: " + ", ".join(sorted(unknown)))
        ids = sorted({r.dataset_id for r in recordings})
        architecture = json.loads((source/"model_config.json").read_text()) if source else {}
        service = TrainingService(db)
        job = service.start_training(dict(dataset_id=train_rows[0].dataset_id,
            studio_recording_ids=[r.id for r in recordings], dataset_ids=ids,
            training_mode="finetune" if model else "fresh", source_model_id=model.id if model else None,
            epochs=payload.epochs, batch_size=1, learning_rate=payload.learning_rate,
            cnn_channels=architecture.get("cnn_channels",32), hidden_size=architecture.get("hidden_size",32),
            model_name="SLSL Model", studio=True))
        return dict(job_id=job.id)
    except (ValueError, OSError) as exc:
        raise error(exc) from exc


@router.post("/tests/{test_id}/run")
def run_test(test_id: str, db: Session = Depends(get_db)):
    row = next((r for r in test_records() if r["id"] == test_id), None)
    if not row:
        raise HTTPException(404, "Test recording not found")
    model = current_model(db)
    if not model:
        raise HTTPException(400, "Train the model first")
    bundle = load_bundle(settings.artifacts_dir / model.bundle_path)
    try:
        fingerprint = motion_fingerprint(sensor_dataframe((test_dir() / (test_id+'.csv')).read_bytes()))
        prediction = recognize_from_csv(test_dir() / (test_id+".csv"), bundle)
    except FileNotFoundError as exc:
        raise HTTPException(404, 'Test recording was deleted during recognition') from exc
    sentence = generate_english_sentence(prediction.predicted_signs, prediction.decoder_score)
    result = dict(recognition_id=uuid.uuid4().hex, model_id=model.id, predicted_signs=prediction.predicted_signs, english=sentence.english,
        text_status=sentence.status, inference_ms=prediction.inference_ms,
        uncertain=prediction.decoder_score < .25, metrics=None)
    expression = analyze_expression(prediction.predicted_signs)
    result['expression'] = expression
    result['english_display'] = expression_text(sentence.english, expression)
    # Reference labels are read only AFTER sensor-only recognition has returned.
    if row["expected_signs"]:
        metrics = sequence_metrics(row["expected_signs"], prediction.predicted_signs)
        result["metrics"] = dict(exact_match=metrics.exact_match, word_error_rate=metrics.word_error_rate,
            insertions=metrics.insertions,deletions=metrics.deletions,substitutions=metrics.substitutions)
    result['evaluation_version'] = 2
    result['motion_fingerprint'] = fingerprint
    result["accuracy_excluded_reason"] = None
    exposed = exposed_recording_ids(db, model)
    for training_row in db.scalars(select(Recording).where(Recording.id.in_(exposed))):
        path = settings.data_dir / training_row.file_path
        if not path.exists():
            continue
        stat = path.stat()
        canonical_hash = canonical_training_hash(str(path.resolve()), stat.st_mtime_ns, stat.st_size)
        if result['motion_fingerprint'] == canonical_hash:
            result["metrics"] = None
            result["accuracy_excluded_reason"] = "This motion was used for training or validation in this model's learning history. Excluded from independent test accuracy."
            break
    with _TEST_RECORD_LOCK:
        latest = next((r for r in test_records() if r['id'] == test_id), None)
        if latest is None:
            raise HTTPException(404, 'Test recording was deleted during recognition')
        latest['result'] = result
        save_test_record(latest)
        return latest


class SentenceRequest(BaseModel):
    recognition_id: str = Field(min_length=1, max_length=64)


@router.post("/tests/{test_id}/sentence")
def form_test_sentence(test_id: str, payload: SentenceRequest, db: Session = Depends(get_db)):
    row = next((r for r in test_records() if r["id"] == test_id), None)
    if not row:
        raise HTTPException(404, "Test recording not found")
    result = row.get("result")
    if not result or result.get("recognition_id") != payload.recognition_id:
        raise HTTPException(409, "Motion prediction changed. Recognize this recording again.")
    model = current_model(db)
    if not model or result.get("model_id") != model.id:
        raise HTTPException(409, "The active model changed. Recognize this recording again.")
    # Only predictions enter the language model. Never pass row metadata or answers.
    suggestion = generate_spoken_sentence(result["predicted_signs"], uncertain=bool(result.get("uncertain")))
    with _TEST_RECORD_LOCK:
        latest = next((r for r in test_records() if r["id"] == test_id), None)
        latest_result = latest.get("result") if latest else None
        current = current_model(db)
        if (not latest_result or latest_result.get("recognition_id") != payload.recognition_id
                or not current or current.id != result["model_id"]):
            raise HTTPException(409, "Motion prediction or model changed while forming the sentence. Recognize again.")
        expression = analyze_expression(latest_result['predicted_signs'])
        latest_result['expression'] = expression
        latest_result['english_display'] = expression_text(latest_result['english'], expression)
        sinhala_speech.clear_audio(test_id)
        latest_result.pop('sinhala', None)
        latest_result["spoken_sentence"] = annotate_sentence(suggestion.to_dict(), expression)
        save_test_record(latest)
        return latest_result["spoken_sentence"]


class SpeechRequest(SentenceRequest):
    translation_id: str = Field(min_length=1, max_length=64)


def speech_context(test_id, recognition_id, db, translation_id=None):
    row = next((r for r in test_records() if r['id'] == test_id), None)
    if row is None:
        raise HTTPException(404, 'Test recording not found')
    result = row.get('result') or {}
    model = current_model(db)
    if (result.get('recognition_id') != recognition_id or not model or result.get('model_id') != model.id):
        raise HTTPException(409, 'Recognition or active model changed. Recognize again.')
    spoken = result.get('spoken_sentence') or {}
    if not spoken.get('text'):
        raise HTTPException(400, 'Form a sentence from recognized words first')
    if translation_id and (result.get('sinhala') or {}).get('translation_id') != translation_id:
        raise HTTPException(409, 'The translation changed. Generate speech again.')
    return row, result


@router.post('/tests/{test_id}/translate')
def translate_test_sentence(test_id: str, payload: SentenceRequest, db: Session = Depends(get_db)):
    row, result = speech_context(test_id, payload.recognition_id, db)
    english = result['spoken_sentence']['text']  # Never display_text, answers or [angry].
    try:
        text = sinhala_speech.translate_sentence(english)
    except sinhala_speech.SpeechUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    except ValueError as exc:
        raise error(exc) from exc
    with _TEST_RECORD_LOCK:
        latest, current = speech_context(test_id, payload.recognition_id, db)
        if current['spoken_sentence']['text'] != english:
            raise HTTPException(409, 'The English sentence changed. Translate again.')
        sinhala_speech.clear_audio(test_id)
        expression = current['spoken_sentence'].get('expression') or current.get('expression') or {}
        translated = dict(translation_id=uuid.uuid4().hex, text=text, english=english,
            emotion=expression.get('label'), status='translated', model_name=sinhala_speech.TRANSLATOR,
            message='Machine-translated Sinhala. Check the wording and pronunciation; correctness is not guaranteed.',
            speech=None)
        current['sinhala'] = translated
        save_test_record(latest)
        return translated


class TranslationEditRequest(SpeechRequest):
    text: str = Field(min_length=1, max_length=1500)


@router.patch('/tests/{test_id}/translation')
def edit_test_translation(test_id: str, payload: TranslationEditRequest, db: Session = Depends(get_db)):
    text = payload.text.strip()
    if not text or not any('\u0d80' <= c <= '\u0dff' for c in text):
        raise HTTPException(400, 'Enter Sinhala text before generating speech')
    with _TEST_RECORD_LOCK:
        row, result = speech_context(test_id, payload.recognition_id, db, payload.translation_id)
        previous = result['sinhala']
        sinhala_speech.clear_audio(test_id)
        result['sinhala'] = dict(previous, text=text, translation_id=uuid.uuid4().hex,
            machine_text=previous.get('machine_text', previous['text']), status='edited',
            message='Sinhala wording edited by the user. Check it against the recognized meaning.', speech=None)
        save_test_record(row)
        return result['sinhala']


@router.post('/tests/{test_id}/speech')
def speak_test_sentence(test_id: str, payload: SpeechRequest, db: Session = Depends(get_db)):
    row, result = speech_context(test_id, payload.recognition_id, db, payload.translation_id)
    translation = result['sinhala']
    text, emotion = translation['text'], translation.get('emotion')
    try:
        audio = sinhala_speech.synthesize_sinhala(text, emotion)
    except sinhala_speech.SpeechUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    except ValueError as exc:
        raise error(exc) from exc
    with _TEST_RECORD_LOCK:
        latest, current = speech_context(test_id, payload.recognition_id, db, payload.translation_id)
        if current['sinhala']['text'] != text or current['sinhala'].get('emotion') != emotion:
            raise HTTPException(409, 'The speech input changed. Generate speech again.')
        directory = sinhala_speech.audio_directory(test_id)
        directory.mkdir(parents=True, exist_ok=True)
        filename = sinhala_speech.audio_filename(payload.recognition_id, payload.translation_id, text, emotion)
        destination = directory / filename
        temporary = destination.with_suffix('.'+uuid.uuid4().hex+'.tmp')
        try:
            temporary.write_bytes(audio)
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
        current['sinhala']['speech'] = dict(status='ready', voice=sinhala_speech.VOICE,
            emotion=emotion, style_method='prosody_preset' if emotion else 'default_voice',
            filename=filename, audio_url=f'/api/studio/tests/{test_id}/audio?recognition_id={payload.recognition_id}&translation_id={payload.translation_id}')
        save_test_record(latest)
        return current['sinhala']


@router.get('/tests/{test_id}/audio')
def test_sentence_audio(test_id: str, recognition_id: str, translation_id: str, db: Session = Depends(get_db)):
    row, result = speech_context(test_id, recognition_id, db, translation_id)
    speech = result['sinhala'].get('speech') or {}
    filename = speech.get('filename', '')
    if not filename or Path(filename).name != filename or not filename.endswith('.wav'):
        raise HTTPException(404, 'Generate Sinhala audio first')
    path = sinhala_speech.audio_directory(test_id) / filename
    if not path.is_file():
        raise HTTPException(404, 'Audio is unavailable. Generate it again.')
    return FileResponse(path, media_type='audio/wav', filename='sinhala-speech.wav', headers={'Cache-Control':'no-store'})


class ResetRequest(BaseModel):
    confirmation: str


@router.post("/reset")
def reset(payload: ResetRequest, db: Session = Depends(get_db)):
    try:
        if TrainingService(db)._active_job():
            raise ValueError("Stop training before resetting the model.")
        return ResetService(db).execute_reset(dict(archive_models=True), payload.confirmation)
    except ValueError as exc:
        raise error(exc) from exc


@router.get("/tests/{test_id}/file")
def test_file(test_id: str):
    row = next((r for r in test_records() if r["id"] == test_id), None)
    if not row:
        raise HTTPException(404, "Test recording not found")
    return FileResponse(test_dir() / (test_id + ".csv"), filename=row["filename"], media_type="text/csv")


class CollectionRequest(BaseModel):
    dataset_ids: list[int]


@router.post("/collections")
def set_collections(payload: CollectionRequest, db: Session = Depends(get_db)):
    if TrainingService(db)._active_job():
        raise HTTPException(400, "Wait for training to finish before changing its collections.")
    from app.models.dataset import Dataset
    known = set(db.scalars(select(Dataset.id)))
    if set(payload.dataset_ids) - known:
        raise HTTPException(400, "Unknown training collection")
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    (settings.data_dir / "studio_collections.json").write_text(json.dumps(sorted(set(payload.dataset_ids))))
    return {"dataset_ids": payload.dataset_ids}
