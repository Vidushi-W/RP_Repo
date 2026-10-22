"""Training job orchestration with subprocess worker."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.ml.trainer import TrainingConfig, validate_time_resolution
from app.ml.vocabulary import build_vocabulary
from app.models.job import TrainingJob
from app.models.ml_model import MLModel
from app.models.dataset import Recording
from app.repositories.dataset import DatasetRepository


class TrainingService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.dataset_repo = DatasetRepository(db)

    def _active_job(self) -> TrainingJob | None:
        return self.db.scalars(
            select(TrainingJob).where(TrainingJob.status.in_(["queued", "running"])).limit(1)
        ).first()

    def preview_training(self, dataset_id: int) -> dict[str, Any]:
        ds = self.dataset_repo.get_dataset(dataset_id)
        if not ds:
            raise ValueError("Dataset not found")
        recordings = self.dataset_repo.list_recordings(dataset_id)
        train = [r for r in recordings if r.split == "train"]
        val = [r for r in recordings if r.split == "val"]
        test = [r for r in recordings if r.split == "test"]
        signs = set()
        for r in recordings:
            signs.update(t.strip() for t in r.ordered_sign_labels.split("|") if t.strip())
        vocab = build_vocabulary(sorted(signs))
        warnings = validate_time_resolution(train + val)
        if not train:
            warnings.append("No training recordings — assign splits first.")
        if not val:
            warnings.append("No validation recordings — assign splits first.")
        if test:
            warnings.append(f"Test split ({len(test)} recordings) will NOT be used for training.")
        return {
            "dataset_id": dataset_id,
            "dataset_name": ds.name,
            "provenance": ds.provenance,
            "dataset_version": ds.current_version,
            "train_count": len(train),
            "val_count": len(val),
            "test_count": len(test),
            "vocabulary_size": len(vocab["labels"]) - 1,
            "schema_compatible": True,
            "warnings": warnings,
            "estimated_params": len(vocab["labels"]) * 32 * 64,
        }

    def start_training(self, payload: dict[str, Any]) -> TrainingJob:
        if self._active_job():
            raise ValueError("Another training job is already active. Wait for it to finish or cancel it.")
        dataset_id = payload["dataset_id"]
        if payload.get("studio"):
            replay = list(self.db.scalars(select(Recording).where(Recording.id.in_(payload["studio_recording_ids"]))))
            preview = {"train_count": sum(r.split == "train" for r in replay),
                       "val_count": sum(r.split == "val" for r in replay), "warnings": []}
        else:
            preview = self.preview_training(dataset_id)
        if preview["train_count"] == 0 or preview["val_count"] == 0:
            raise ValueError("Dataset must have train and validation splits before training.")
        if preview["warnings"] and any("No training" in w or "No validation" in w for w in preview["warnings"]):
            raise ValueError("Cannot start training without train and validation splits.")

        job = TrainingJob(
            name=payload.get("name", f"Training {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}"),
            status="queued",
            dataset_id=dataset_id,
            training_mode=payload.get("training_mode", "fresh"),
            source_model_id=payload.get("source_model_id"),
            config_json=json.dumps(payload),
            total_epochs=payload.get("epochs", 20),
            message="Queued for training.",
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)

        if payload.get("training_mode") == "finetune" and payload.get("source_model_id"):
            src = self.db.get(MLModel, payload["source_model_id"])
            if src and src.bundle_path:
                cfg = json.loads(job.config_json)
                cfg["source_bundle_path"] = str(settings.artifacts_dir / src.bundle_path)
                job.config_json = json.dumps(cfg)

        worker = BACKEND_ROOT / "scripts" / "train_worker.py"
        python = sys.executable
        self.db.commit()
        proc = subprocess.Popen([python, str(worker), str(job.id)], cwd=str(BACKEND_ROOT))
        job.pid = proc.pid
        job.status = "running"
        job.message = "Training subprocess started."
        self.db.commit()
        self.db.refresh(job)
        return job

    def cancel_job(self, job_id: int) -> TrainingJob:
        job = self.db.get(TrainingJob, job_id)
        if not job:
            raise ValueError("Job not found")
        if job.status not in {"queued", "running"}:
            raise ValueError(f"Cannot cancel job in status {job.status}")
        job.status = "cancelled"
        job.message = "Cancellation requested."
        if job.pid:
            try:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/PID", str(job.pid), "/F"], check=False, capture_output=True)
                else:
                    os.kill(job.pid, signal.SIGTERM)
            except (ProcessLookupError, OSError):
                pass
        job.completed_at = datetime.now(timezone.utc)
        self.db.commit()
        return job

    def list_jobs(self) -> list[TrainingJob]:
        return list(self.db.scalars(select(TrainingJob).order_by(TrainingJob.created_at.desc()).limit(50)))

    def get_job(self, job_id: int) -> TrainingJob | None:
        return self.db.get(TrainingJob, job_id)

    def mark_interrupted_jobs(self) -> int:
        count = 0
        for job in self.db.scalars(select(TrainingJob).where(TrainingJob.status == "running")):
            job.status = "interrupted"
            job.message = "Training interrupted by backend restart."
            job.completed_at = datetime.now(timezone.utc)
            count += 1
        self.db.commit()
        return count


BACKEND_ROOT = Path(__file__).resolve().parents[2]
