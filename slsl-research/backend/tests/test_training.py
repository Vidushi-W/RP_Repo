import io
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import torch

from app.core.config import SENSOR_COLUMNS, settings
from app.ml.decoder import greedy_ctc_decode, torch_greedy_decode
from app.ml.models import CtcSignModel
from app.ml.preprocessing import NormalizationConfig
from app.ml.trainer import TrainingConfig, run_training
from app.ml.vocabulary import build_vocabulary, encode_labels, load_vocabulary
from app.models.job import TrainingJob
from app.services.dataset_service import DatasetService
from app.services.model_registry import ModelRegistryService
from app.services.reset_service import ResetService


def _sample_csv(n=40):
    rows = []
    for i in range(n):
        row = {c: 0.0 for c in SENSOR_COLUMNS}
        row["timestamp_ms"] = i * 20.0
        row["left_flex_1"] = 0.5
        row["right_flex_1"] = 0.4
        row["left_acc_z_g"] = 1.0
        row["right_acc_z_g"] = 1.0
        rows.append(row)
    return pd.DataFrame(rows)


def test_ctc_decoder_blanks_and_repeats():
    log_probs = np.array([
        [0.9, 0.05, 0.05],
        [0.9, 0.05, 0.05],
        [0.05, 0.9, 0.05],
        [0.9, 0.05, 0.05],
        [0.05, 0.05, 0.9],
        [0.05, 0.9, 0.05],
    ], dtype=np.float32)
    log_probs = np.log(log_probs)
    decoded, conf = greedy_ctc_decode(log_probs, blank_index=0, id_to_label={1: "A", 2: "B"})
    assert decoded == ["A", "B", "A"]
    assert conf > 0


def test_ctc_model_output_lengths():
    model = CtcSignModel(num_classes=5, cnn_channels=32, hidden_size=32)
    x = torch.randn(2, 50, 22)
    in_lens = torch.tensor([50, 40])
    logits, out_lens = model(x, input_lengths=in_lens)
    assert logits.shape[0] == 2
    assert int(out_lens[0]) == 25
    assert int(out_lens[1]) == 20


def test_vocabulary_encoding():
    vocab = build_vocabulary(["I", "NEED", "WATER"])
    ids = encode_labels("I|NEED|WATER", vocab["label_to_id"])
    assert len(ids) == 3


def test_training_preview_requires_splits(client):
    create = client.post("/api/datasets", json={"name": "No Split DS"}).json()
    ds_id = create["id"]
    buf = io.BytesIO()
    _sample_csv().to_csv(buf, index=False)
    client.post(f"/api/datasets/{ds_id}/import", files={"files": ("r1.csv", buf.getvalue(), "text/csv")})
    preview = client.get(f"/api/training/preview/{ds_id}")
    assert preview.status_code == 200
    body = preview.json()
    assert body["train_count"] == 0
    assert any("training" in w.lower() for w in body["warnings"])


def test_start_training_rejects_without_splits(client):
    create = client.post("/api/datasets", json={"name": "Train Fail"}).json()
    ds_id = create["id"]
    buf = io.BytesIO()
    _sample_csv().to_csv(buf, index=False)
    client.post(f"/api/datasets/{ds_id}/import", files={"files": ("r1.csv", buf.getvalue(), "text/csv")})
    res = client.post("/api/training/start", json={"dataset_id": ds_id, "epochs": 1})
    assert res.status_code == 400


def test_model_activation_requires_bundle(client, tmp_path):
    res = client.get("/api/models")
    assert res.status_code == 200


def test_run_training_weights_checkpoint_and_inference(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "artifacts_dir", tmp_path / "artifacts")
    svc = DatasetService(db_session)
    ds = svc.generate_synthetic({"name": "E2E Train", "total_recordings": 50, "seed": 42})
    recordings = svc.repo.list_recordings(ds.id)
    train_recs = [r for r in recordings if r.split == "train"]
    val_recs = [r for r in recordings if r.split == "val"]
    test_recs = [r for r in recordings if r.split == "test"]
    assert train_recs and val_recs and test_recs

    bundle_dir = tmp_path / "artifacts" / "models" / "e2e_run"
    config = TrainingConfig(
        dataset_id=ds.id,
        dataset_version=ds.current_version,
        provenance=ds.provenance,
        epochs=2,
        batch_size=4,
        patience=2,
    )
    signs = set()
    for rec in train_recs + val_recs:
        signs.update(t.strip() for t in rec.ordered_sign_labels.split("|") if t.strip())
    vocab_size = len(build_vocabulary(sorted(signs))["labels"])
    before = CtcSignModel(num_classes=vocab_size, cnn_channels=32, hidden_size=32)
    before_state = {k: v.clone() for k, v in before.state_dict().items()}

    result = run_training(train_recs, val_recs, config, bundle_dir)
    assert result["status"] == "completed"
    assert (bundle_dir / "model.pt").exists()
    assert (bundle_dir / "vocabulary.json").exists()
    assert (bundle_dir / "preprocessing.json").exists()

    vocab = load_vocabulary(bundle_dir / "vocabulary.json")
    norm = NormalizationConfig.load(bundle_dir / "preprocessing.json")
    model = CtcSignModel(num_classes=len(vocab["labels"]), cnn_channels=32, hidden_size=32)
    state = torch.load(bundle_dir / "model.pt", map_location="cpu", weights_only=True)
    model.load_state_dict(state)
    after_state = model.state_dict()
    assert any(not torch.allclose(before_state[k], after_state[k]) for k in before_state)

    from app.sensors.csv_source import load_csv_to_recording
    from app.ml.preprocessing import resample_recording, smooth_features

    sample = train_recs[0]
    sensor = load_csv_to_recording(settings.data_dir / sample.file_path)
    x = smooth_features(resample_recording(sensor, norm.target_sample_rate_hz).to_feature_matrix())
    x = norm.normalize(x)
    tensor = torch.from_numpy(x.astype(np.float32)).unsqueeze(0)
    in_len = torch.tensor([x.shape[0]])
    with torch.no_grad():
        logits, out_lens = model(tensor, input_lengths=in_len)
    id_to_label = {int(k): v for k, v in vocab["id_to_label"].items() if v != "<blank>"}
    pred, conf = torch_greedy_decode(logits[0, : int(out_lens[0])], blank_index=0, id_to_label=id_to_label)
    assert isinstance(pred, list)
    assert conf >= 0


def test_training_excludes_test_split(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "artifacts_dir", tmp_path / "artifacts")
    svc = DatasetService(db_session)
    ds = svc.generate_synthetic({"name": "Split Guard", "total_recordings": 50, "seed": 7})
    recordings = svc.repo.list_recordings(ds.id)
    test_ids = {r.recording_id for r in recordings if r.split == "test"}
    used_ids = {r.recording_id for r in recordings if r.split in {"train", "val"}}
    assert test_ids.isdisjoint(used_ids)

    from app.services.training_service import TrainingService

    body = TrainingService(db_session).preview_training(ds.id)
    assert body["test_count"] > 0
    assert any("will NOT be used" in w for w in body["warnings"])


def test_train_worker_registers_model(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "artifacts_dir", tmp_path / "artifacts")
    svc = DatasetService(db_session)
    ds = svc.generate_synthetic({"name": "Worker DS", "total_recordings": 50, "seed": 11})
    job = TrainingJob(
        name="Worker test",
        status="queued",
        dataset_id=ds.id,
        training_mode="fresh",
        config_json=json.dumps({"epochs": 2, "batch_size": 4, "learning_rate": 0.001}),
        total_epochs=2,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    import scripts.train_worker as worker

    monkeypatch.setattr(worker, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    worker.main(job.id)

    db_session.refresh(job)
    assert job.status == "completed"
    assert job.model_id is not None
    model = ModelRegistryService(db_session).get_model(job.model_id)
    assert model is not None
    bundle = tmp_path / "artifacts" / model.bundle_path
    assert (bundle / "model.pt").exists()
    activated = ModelRegistryService(db_session).activate_model(model.id)
    assert activated.status == "active"


def test_reset_workspace_archives_models(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "artifacts_dir", tmp_path / "artifacts")
    svc = DatasetService(db_session)
    ds = svc.generate_synthetic({"name": "Reset DS", "total_recordings": 50, "seed": 3})
    bundle_dir = tmp_path / "artifacts" / "models" / "job_99"
    bundle_dir.mkdir(parents=True)
    (bundle_dir / "model.pt").write_bytes(b"x")
    (bundle_dir / "vocabulary.json").write_text('{"labels":["<blank>","I"]}', encoding="utf-8")
    (bundle_dir / "preprocessing.json").write_text(
        '{"feature_mean":[0.0],"feature_std":[1.0],"target_sample_rate_hz":50}',
        encoding="utf-8",
    )
    (bundle_dir / "model_config.json").write_text("{}", encoding="utf-8")

    from app.models.ml_model import MLModel

    model = MLModel(
        name="Reset Test",
        version="1.0.0",
        status="active",
        architecture="ctc_cnn_bilstm",
        dataset_id=ds.id,
        bundle_path="models/job_99",
        checkpoint_path="models/job_99/model.pt",
    )
    db_session.add(model)
    db_session.commit()

    result = ResetService(db_session).execute_reset(
        {"archive_models": True, "clear_jobs": False},
        confirmation="RESET",
    )
    assert result["deactivated_models"] == 1
    assert result["archived_models"] == 1
    db_session.refresh(model)
    assert model.is_archived
    assert model.status == "inactive"
