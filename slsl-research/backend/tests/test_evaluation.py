import json
from pathlib import Path
from unittest.mock import patch

import pytest

from app.core.config import settings
from app.ml.evaluator import evaluate_recordings, parse_gloss_labels
from app.ml.inference import gloss_to_english, load_bundle, recognize_from_csv
from app.ml.metrics import sequence_metrics, word_error_rate
from app.ml.trainer import TrainingConfig, run_training
from app.models.ml_model import MLModel
from app.services.dataset_service import DatasetService
from app.services.evaluation_service import EvaluationService


def test_wer_exact_and_empty_cases():
    assert word_error_rate(["A", "B"], ["A", "B"]) == 0.0
    assert word_error_rate([], []) == 0.0
    assert word_error_rate(["A"], []) == 1.0
    assert word_error_rate([], ["A"]) == 1.0
    m = sequence_metrics(["I", "NEED", "WATER"], ["I", "WANT", "WATER"])
    assert m.substitutions == 1
    assert m.insertions == 0
    assert m.deletions == 0
    assert abs(m.word_error_rate - 1 / 3) < 1e-6


def test_inference_never_receives_labels(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "artifacts_dir", tmp_path / "artifacts")
    svc = DatasetService(db_session)
    ds = svc.generate_synthetic({"name": "Leak Test", "total_recordings": 50, "seed": 1})
    recordings = svc.repo.list_recordings(ds.id)
    train = [r for r in recordings if r.split == "train"]
    val = [r for r in recordings if r.split == "val"]
    test = [r for r in recordings if r.split == "test"]
    bundle_dir = tmp_path / "artifacts" / "models" / "leak_test"
    run_training(train, val, TrainingConfig(dataset_id=ds.id, dataset_version="1.0.0", provenance="synthetic", epochs=1, patience=1), bundle_dir)

    bundle = load_bundle(bundle_dir)
    sample = test[0]
    csv_path = settings.data_dir / sample.file_path

    with patch("app.ml.inference.load_csv_to_recording") as mock_load:
        from app.sensors.csv_source import load_csv_to_recording
        mock_load.side_effect = load_csv_to_recording
        result = recognize_from_csv(csv_path, bundle)
        assert mock_load.call_args[0][0] == csv_path
        assert "ordered_sign_labels" not in str(mock_load.call_args)

    ref = parse_gloss_labels(sample.ordered_sign_labels)
    assert isinstance(result.predicted_signs, list)
    assert result.predicted_signs != sample.reference_english_sentence.split()


def test_evaluation_uses_test_split_only(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "artifacts_dir", tmp_path / "artifacts")
    svc = DatasetService(db_session)
    ds = svc.generate_synthetic({"name": "Eval DS", "total_recordings": 50, "seed": 2})
    recordings = svc.repo.list_recordings(ds.id)
    train = [r for r in recordings if r.split == "train"]
    val = [r for r in recordings if r.split == "val"]
    bundle_dir = tmp_path / "artifacts" / "models" / "eval_model"
    run_training(train, val, TrainingConfig(dataset_id=ds.id, dataset_version="1.0.0", provenance="synthetic", epochs=1, patience=1), bundle_dir)

    model = MLModel(
        name="Eval Model",
        version="1.0.0",
        status="inactive",
        architecture="ctc_cnn_bilstm",
        dataset_id=ds.id,
        dataset_version="1.0.0",
        provenance="synthetic",
        bundle_path="models/eval_model",
        checkpoint_path="models/eval_model/model.pt",
        vocabulary_json=(bundle_dir / "vocabulary.json").read_text(encoding="utf-8"),
        feature_schema_json="{}",
        emotion_available=(bundle_dir / "emotion_model.pkl").exists(),
    )
    db_session.add(model)
    db_session.commit()
    db_session.refresh(model)

    eval_svc = EvaluationService(db_session)
    preview = eval_svc.preview_compatibility(model.id, ds.id, "test")
    assert preview["split_counts"]["test"] > 0
    assert preview["recommended_split"] == "test"

    run = eval_svc.run_evaluation({"model_id": model.id, "dataset_id": ds.id, "split": "test"})
    assert run.status == "completed"
    assert run.word_error_rate is not None
    assert run.sequence_accuracy is not None

    results = eval_svc.get_results(run.id)
    assert len(results["predictions"]) == preview["split_counts"]["test"]
    pred_ids = {p["recording_id"] for p in results["predictions"]}
    test_ids = {r.recording_id for r in recordings if r.split == "test"}
    assert pred_ids == test_ids
    for p in results["predictions"]:
        assert "reference_signs" in p
        assert "predicted_signs" in p
        assert p["decoder_score_label"] == "uncalibrated_decoder_score"


def test_evaluation_api(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "artifacts_dir", tmp_path / "artifacts")

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    from app.core.database import get_db
    from app.main import app

    app.dependency_overrides[get_db] = override_get_db

    svc = DatasetService(db_session)
    ds = svc.generate_synthetic({"name": "API Eval", "total_recordings": 50, "seed": 3})
    recordings = svc.repo.list_recordings(ds.id)
    train = [r for r in recordings if r.split == "train"]
    val = [r for r in recordings if r.split == "val"]
    bundle_dir = tmp_path / "artifacts" / "models" / "api_model"
    run_training(train, val, TrainingConfig(dataset_id=ds.id, dataset_version="1.0.0", provenance="synthetic", epochs=1, patience=1), bundle_dir)
    model = MLModel(
        name="API Model",
        version="1.0.0",
        status="inactive",
        architecture="ctc_cnn_bilstm",
        dataset_id=ds.id,
        bundle_path="models/api_model",
        vocabulary_json=(bundle_dir / "vocabulary.json").read_text(encoding="utf-8"),
    )
    db_session.add(model)
    db_session.commit()

    preview = client.get(f"/api/evaluation/preview?model_id={model.id}&dataset_id={ds.id}&split=test")
    assert preview.status_code == 200
    assert preview.json()["compatible"] is True

    run_res = client.post("/api/evaluation/run", json={"model_id": model.id, "dataset_id": ds.id, "split": "test"})
    assert run_res.status_code == 200
    body = run_res.json()
    assert body["status"] == "completed"
    assert body["word_error_rate"] is not None

    results = client.get(f"/api/evaluation/runs/{body['id']}/results")
    assert results.status_code == 200
    assert len(results.json()["predictions"]) > 0

    app.dependency_overrides.clear()


def test_gloss_to_english_from_prediction_only():
    assert gloss_to_english(["I", "NEED", "WATER"]) == "I need water."
