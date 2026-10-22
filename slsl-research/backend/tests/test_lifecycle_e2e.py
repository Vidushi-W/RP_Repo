"""Reproducible synthetic end-to-end lifecycle experiment."""

import io

import pytest

from app.core.config import settings
from app.ml.trainer import TrainingConfig, run_training
from app.models.ml_model import MLModel
from app.services.dataset_service import DatasetService
from app.services.evaluation_service import EvaluationService
from app.services.model_registry import ModelRegistryService
from app.services.playground_service import PlaygroundService
from app.services.reset_service import ResetService
from tests.test_playground import _sample_csv


@pytest.mark.e2e
def test_full_synthetic_lifecycle(db_session, tmp_path, monkeypatch):
    """Generate → train → evaluate → activate → recognize → reset (archive)."""
    monkeypatch.setattr(settings, "artifacts_dir", tmp_path / "artifacts")

    ds_svc = DatasetService(db_session)
    ds = ds_svc.generate_synthetic({"name": "Lifecycle DS", "total_recordings": 50, "seed": 42})
    recs = ds_svc.repo.list_recordings(ds.id)
    train = [r for r in recs if r.split == "train"]
    val = [r for r in recs if r.split == "val"]
    test = [r for r in recs if r.split == "test"]
    assert train and val and test

    bundle_dir = tmp_path / "artifacts" / "models" / "lifecycle"
    result = run_training(
        train, val,
        TrainingConfig(dataset_id=ds.id, dataset_version="1.0.0", provenance="synthetic", epochs=1, patience=1),
        bundle_dir,
    )
    assert result["status"] == "completed"
    assert (bundle_dir / "model.pt").exists()

    model = MLModel(
        name="Lifecycle Model",
        version="1.0.0",
        status="inactive",
        architecture="ctc_cnn_bilstm",
        dataset_id=ds.id,
        bundle_path="models/lifecycle",
        vocabulary_json=(bundle_dir / "vocabulary.json").read_text(encoding="utf-8"),
        emotion_available=(bundle_dir / "emotion_model.pkl").exists(),
    )
    db_session.add(model)
    db_session.commit()
    db_session.refresh(model)

    eval_run = EvaluationService(db_session).run_evaluation({
        "model_id": model.id, "dataset_id": ds.id, "split": "test", "name": "Lifecycle Eval",
    })
    assert eval_run.status == "completed"
    assert eval_run.word_error_rate is not None
    measured_wer = eval_run.word_error_rate

    activated = ModelRegistryService(db_session).activate_model(model.id)
    assert activated.status == "active"

    pg = PlaygroundService(db_session)
    rec = pg.recognize_upload(_sample_csv(80), "unknown_lifecycle.csv", model.id)
    assert rec["no_ground_truth_used"] is True
    assert rec["english"] is not None
    history = pg.list_history()
    assert len(history) >= 1

    reset = ResetService(db_session).execute_reset({"archive_models": True, "clear_jobs": False}, confirmation="RESET")
    assert reset["archived_models"] >= 1
    db_session.refresh(model)
    assert model.is_archived

    # Document measured results — no hardcoded accuracy requirement
    assert 0.0 <= measured_wer <= 1.0
