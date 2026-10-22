from sqlalchemy import select

from app.core.config import settings
from app.models.dataset import Dataset
from app.models.job import TrainingJob
from app.models.ml_model import MLModel
from app.services.dataset_service import DatasetService
from app.services.maintenance_service import MaintenanceService


def test_storage_summary(client):
    res = client.get("/api/maintenance/storage")
    assert res.status_code == 200
    body = res.json()
    assert "counts" in body
    assert "database_size_bytes" in body


def test_delete_synthetic_dataset(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", tmp_path / "data")
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    ds = DatasetService(db_session).generate_synthetic({"name": "Delete Me", "total_recordings": 10, "seed": 1})
    ds_id = ds.id

    bad = client.request("DELETE", f"/api/maintenance/datasets/{ds_id}", json={"confirmation": "wrong"})
    assert bad.status_code == 400

    good = client.request("DELETE", f"/api/maintenance/datasets/{ds_id}", json={"confirmation": f"DELETE {ds_id}"})
    assert good.status_code == 200
    db_session.expire_all()
    assert db_session.get(Dataset, ds_id) is None


def test_reset_training_scope(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "artifacts_dir", tmp_path / "artifacts")
    ds = DatasetService(db_session).generate_synthetic({"name": "Keep DS", "total_recordings": 10, "seed": 2})

    model = MLModel(
        name="M1",
        version="1.0.0",
        status="inactive",
        architecture="ctc_cnn_bilstm",
        dataset_id=ds.id,
        bundle_path="models/job_1",
    )
    job = TrainingJob(name="J1", status="completed", dataset_id=ds.id, total_epochs=1)
    db_session.add_all([model, job])
    db_session.commit()

    res = client.post(
        "/api/maintenance/reset-database",
        json={"scope": "training", "confirmation": "RESET TRAINING", "delete_files": False},
    )
    assert res.status_code == 200
    assert db_session.scalar(select(MLModel)) is None
    assert db_session.scalar(select(TrainingJob)) is None
    assert db_session.get(Dataset, ds.id) is not None


def test_delete_active_model_blocked(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "artifacts_dir", tmp_path / "artifacts")
    ds = DatasetService(db_session).generate_synthetic({"name": "Model DS", "total_recordings": 10, "seed": 3})
    model = MLModel(
        name="Active",
        version="1.0.0",
        status="active",
        architecture="ctc_cnn_bilstm",
        dataset_id=ds.id,
        bundle_path="models/job_x",
    )
    db_session.add(model)
    db_session.commit()

    try:
        MaintenanceService(db_session).delete_model(model.id, f"DELETE MODEL {model.id}")
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "Deactivate" in str(exc)


def test_reset_synthetic_datasets(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", tmp_path / "data")
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    ds = DatasetService(db_session).generate_synthetic({"name": "Synth", "total_recordings": 10, "seed": 4})
    ds_id = ds.id

    res = client.post(
        "/api/maintenance/reset-database",
        json={"scope": "synthetic", "confirmation": "RESET SYNTHETIC", "delete_files": False},
    )
    assert res.status_code == 200
    db_session.expire_all()
    assert db_session.get(Dataset, ds_id) is None
