"""Training subprocess worker — run separately from FastAPI."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings
from app.core.database import SessionLocal
from app.ml.trainer import TrainingConfig, run_training
from app.models.job import TrainingJob
from app.models.ml_model import MLModel
from app.models.dataset import Recording
from sqlalchemy import select
from app.repositories.dataset import DatasetRepository


def main(job_id: int) -> None:
    db = SessionLocal()
    job = db.get(TrainingJob, job_id)
    if not job:
        sys.exit(1)

    config_data = json.loads(job.config_json)
    repo = DatasetRepository(db)
    dataset = repo.get_dataset(job.dataset_id)
    if not dataset:
        job.status = "failed"
        job.message = "Dataset not found"
        db.commit()
        sys.exit(1)

    recordings = (list(db.scalars(select(Recording).where(Recording.id.in_(config_data["studio_recording_ids"]))))
                  if config_data.get("studio") else repo.list_recordings(job.dataset_id))
    train_recs = [r for r in recordings if r.split == "train"]
    val_recs = [r for r in recordings if r.split == "val"]
    if not train_recs or not val_recs:
        job.status = "failed"
        job.message = "Dataset needs train and validation splits before training."
        db.commit()
        sys.exit(1)

    bundle_dir = settings.artifacts_dir / "models" / f"job_{job_id}"
    config = TrainingConfig(
        dataset_id=job.dataset_id,
        dataset_version=dataset.current_version,
        provenance=dataset.provenance,
        epochs=config_data.get("epochs", 20),
        batch_size=config_data.get("batch_size", 4),
        learning_rate=config_data.get("learning_rate", 0.001),
        cnn_channels=config_data.get("cnn_channels", 32),
        hidden_size=config_data.get("hidden_size", 32),
        training_mode=job.training_mode,
        source_bundle_path=config_data.get("source_bundle_path"),
    )

    job.status = "running"
    job.started_at = datetime.now(timezone.utc)
    db.commit()

    cancel_flag = {"cancelled": False}

    def on_progress(entry: dict) -> None:
        j = db.get(TrainingJob, job_id)
        if j and j.status == "cancelled":
            cancel_flag["cancelled"] = True
            return
        if j:
            j.current_epoch = entry["epoch"]
            j.train_loss = entry["train_loss"]
            j.val_loss = entry["val_loss"]
            j.val_wer = entry["val_wer"]
            j.progress_json = json.dumps({"history": [entry]})
            j.message = f"Epoch {entry['epoch']}: train={entry['train_loss']:.4f} val={entry['val_loss']:.4f} WER={entry['val_wer']:.3f}"
            db.commit()

    try:
        (bundle_dir).mkdir(parents=True, exist_ok=True)
        (bundle_dir / "training_sources.json").write_text(json.dumps([dict(id=r.id, dataset_id=r.dataset_id, source_hash=r.content_hash, labels=r.ordered_sign_labels, split=r.split) for r in recordings], indent=2))
        result = run_training(
            train_recs, val_recs, config, bundle_dir,
            progress_callback=on_progress,
            cancel_check=lambda: cancel_flag["cancelled"],
        )
        job = db.get(TrainingJob, job_id)
        db.refresh(job)
        if result.get("status") == "cancelled" or job.status == "cancelled":
            job.status = "cancelled"
            job.message = "Training cancelled by user."
        else:
            model = MLModel(
                name=config_data.get("model_name", f"Model {job_id}"),
                version=str(job_id),
                status="inactive",
                architecture="ctc_cnn_bilstm",
                dataset_id=job.dataset_id,
                dataset_version=dataset.current_version,
                provenance=dataset.provenance,
                training_job_id=job_id,
                bundle_path=str(bundle_dir.relative_to(settings.artifacts_dir)).replace("\\", "/"),
                checkpoint_path=str((bundle_dir / "model.pt").relative_to(settings.artifacts_dir)).replace("\\", "/"),
                vocabulary_json=(bundle_dir / "vocabulary.json").read_text(encoding="utf-8"),
                feature_schema_json=(bundle_dir / "feature_schema.json").read_text(encoding="utf-8"),
                validation_metrics_json=json.dumps(result.get("metrics", {})),
                emotion_available=result.get("emotion", {}).get("trained", False),
                emotion_model_path="emotion_model.pkl" if result.get("emotion", {}).get("trained") else None,
            )
            if config_data.get("studio"):
                for previous in db.scalars(select(MLModel).where(MLModel.status == "active")):
                    previous.status = "inactive"
                model.status = "active"
            db.add(model)
            db.flush()
            job.status = "completed"
            job.model_id = model.id
            job.completed_at = datetime.now(timezone.utc)
            job.message = "Training completed successfully."
        db.commit()
    except Exception as exc:  # noqa: BLE001
        job = db.get(TrainingJob, job_id)
        job.status = "failed"
        job.message = str(exc)
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main(int(sys.argv[1]))
