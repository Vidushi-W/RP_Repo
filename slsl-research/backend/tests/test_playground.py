import io
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from app.core.config import SENSOR_COLUMNS, settings
from app.ml.sentence_generator import generate_english_sentence
from app.ml.trainer import TrainingConfig, run_training
from app.models.ml_model import MLModel
from app.services.dataset_service import DatasetService
from app.services.live_session_service import LiveSessionStore
from app.services.playground_service import PlaygroundService


def _sample_csv(n=60):
    rows = []
    for i in range(n):
        row = {c: 0.0 for c in SENSOR_COLUMNS}
        row["timestamp_ms"] = i * 20.0
        row["left_flex_1"] = 0.5 + 0.1 * (i % 10)
        row["right_flex_1"] = 0.4
        row["left_acc_z_g"] = 1.0
        row["right_acc_z_g"] = 1.0
        rows.append(row)
    buf = io.BytesIO()
    pd.DataFrame(rows).to_csv(buf, index=False)
    return buf.getvalue()


def _train_model(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "artifacts_dir", tmp_path / "artifacts")
    svc = DatasetService(db_session)
    ds = svc.generate_synthetic({"name": "PG DS", "total_recordings": 50, "seed": 5})
    recs = svc.repo.list_recordings(ds.id)
    train = [r for r in recs if r.split == "train"]
    val = [r for r in recs if r.split == "val"]
    bundle_dir = tmp_path / "artifacts" / "models" / "pg_model"
    run_training(train, val, TrainingConfig(dataset_id=ds.id, dataset_version="1.0.0", provenance="synthetic", epochs=1, patience=1), bundle_dir)
    model = MLModel(
        name="PG Model",
        version="1.0.0",
        status="active",
        architecture="ctc_cnn_bilstm",
        dataset_id=ds.id,
        bundle_path="models/pg_model",
        vocabulary_json=(bundle_dir / "vocabulary.json").read_text(encoding="utf-8"),
        emotion_available=(bundle_dir / "emotion_model.pkl").exists(),
    )
    db_session.add(model)
    db_session.commit()
    db_session.refresh(model)
    return model, ds


def test_sentence_generator_patterns():
    r = generate_english_sentence(["I", "NEED", "WATER"], decoder_score=0.9)
    assert r.english == "I need water."
    assert r.status == "supported"
    u = generate_english_sentence(["I", "NEED", "WATER"], decoder_score=0.1, uncertainty_threshold=0.25)
    assert u.status == "uncertain"


def test_playground_recognize_no_labels(db_session, tmp_path, monkeypatch):
    model, _ = _train_model(db_session, tmp_path, monkeypatch)
    svc = PlaygroundService(db_session)
    with patch("app.services.playground_service.load_csv_to_recording") as mock_load:
        from app.sensors.csv_source import load_csv_to_recording
        mock_load.side_effect = load_csv_to_recording
        result = svc.recognize_upload(_sample_csv(), "unknown.csv", model.id)
        assert result["no_ground_truth_used"] is True
        assert "english" in result
        assert result["model_version"] == "1.0.0"
        assert mock_load.call_count == 1


def test_playground_no_model(db_session):
    svc = PlaygroundService(db_session)
    with pytest.raises(ValueError, match="No model available"):
        svc.recognize_upload(_sample_csv(), "x.csv")


def test_dictionary_consistency(db_session, tmp_path, monkeypatch):
    model, _ = _train_model(db_session, tmp_path, monkeypatch)
    d = PlaygroundService(db_session).get_dictionary(model.id)
    assert d["model_id"] == model.id
    assert len(d["entries"]) > 0
    assert d["disclaimer"]


def test_live_session_pause_resume_finalize(db_session, tmp_path, monkeypatch):
    model, _ = _train_model(db_session, tmp_path, monkeypatch)
    store = LiveSessionStore()
    session = store.create("csv_playback")
    store.attach_bundle(session.id, tmp_path / "artifacts" / model.bundle_path)
    meta = store.upload_csv(session.id, _sample_csv(80), "live.csv")
    assert meta["frame_count"] == 80
    store.start(session.id)
    store.pause(session.id)
    assert store.get(session.id).status == "paused"
    store.resume(session.id)
    for _ in range(20):
        store.tick(session.id)
    store.stop(session.id)
    store.reset(session.id)
    assert store.get(session.id).buffer == []


def test_playground_api(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "artifacts_dir", tmp_path / "artifacts")
    model, _ = _train_model(db_session, tmp_path, monkeypatch)

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    from app.core.database import get_db
    from app.main import app

    app.dependency_overrides[get_db] = override_get_db

    status = client.get("/api/playground/status")
    assert status.status_code == 200
    assert status.json()["active_model"]["id"] == model.id

    res = client.post(
        "/api/playground/recognize",
        files={"file": ("test.csv", _sample_csv(), "text/csv")},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["gloss_sequence"] is not None
    assert body["no_ground_truth_used"] is True

    dict_res = client.get("/api/playground/dictionary")
    assert dict_res.status_code == 200

    app.dependency_overrides.clear()
