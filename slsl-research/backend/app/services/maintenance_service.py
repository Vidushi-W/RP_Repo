"""Data management: delete, reset, and storage overview."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.activity import ActivityLog
from app.models.dataset import Dataset, DatasetVersion, ImportJob, Recording
from app.models.evaluation import EvaluationRun
from app.models.job import TrainingJob
from app.models.ml_model import MLModel
from app.models.recognition import RecognitionMessage
from app.repositories.dataset import DatasetRepository


class MaintenanceService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = DatasetRepository(db)

    def storage_summary(self) -> dict[str, Any]:
        def count(model) -> int:
            return self.db.scalar(select(func.count()).select_from(model)) or 0

        db_path = settings.database_url.replace("sqlite:///", "")
        db_size = Path(db_path).stat().st_size if Path(db_path).exists() else 0

        def dir_size(path: Path) -> int:
            if not path.exists():
                return 0
            return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())

        return {
            "database_path": db_path,
            "database_size_bytes": db_size,
            "data_dir": str(settings.data_dir),
            "data_dir_size_bytes": dir_size(settings.data_dir),
            "artifacts_dir": str(settings.artifacts_dir),
            "artifacts_dir_size_bytes": dir_size(settings.artifacts_dir),
            "counts": {
                "datasets": count(Dataset),
                "recordings": count(Recording),
                "models": count(MLModel),
                "training_jobs": count(TrainingJob),
                "evaluations": count(EvaluationRun),
                "recognition_messages": count(RecognitionMessage),
                "activity_logs": count(ActivityLog),
            },
        }

    def delete_dataset(self, dataset_id: int, confirmation: str, force: bool = False) -> dict[str, Any]:
        ds = self.repo.get_dataset(dataset_id)
        if not ds:
            raise ValueError("Dataset not found")
        expected = f"DELETE {ds.name}" if ds.provenance == "real" else f"DELETE {ds.id}"
        if confirmation != expected:
            raise ValueError(f"Type '{expected}' to confirm deletion.")

        linked_models = list(
            self.db.scalars(select(MLModel).where(MLModel.dataset_id == dataset_id, MLModel.is_archived == False))
        )
        if linked_models and not force:
            names = ", ".join(m.name for m in linked_models)
            raise ValueError(f"Archive or reassign models first: {names}")

        for m in linked_models:
            m.status = "inactive"
            m.is_archived = True

        recordings = self.repo.list_recordings(dataset_id)
        files_removed = 0
        for rec in recordings:
            fpath = settings.data_dir / rec.file_path
            if fpath.exists():
                fpath.unlink()
                files_removed += 1

        dataset_dir = settings.datasets_dir / str(dataset_id)
        if dataset_dir.exists():
            shutil.rmtree(dataset_dir, ignore_errors=True)

        self.db.execute(delete(Recording).where(Recording.dataset_id == dataset_id))
        self.db.execute(delete(DatasetVersion).where(DatasetVersion.dataset_id == dataset_id))
        self.db.execute(delete(ImportJob).where(ImportJob.dataset_id == dataset_id))
        self.db.delete(ds)
        self.repo.add_activity("dataset_deleted", f"Deleted dataset '{ds.name}' (id={dataset_id})")
        self.db.commit()
        return {"dataset_id": dataset_id, "recordings_removed": len(recordings), "files_removed": files_removed}

    def delete_recording(self, dataset_id: int, recording_id: str) -> dict[str, Any]:
        rec = self.repo.get_recording(dataset_id, recording_id)
        if not rec:
            raise ValueError("Recording not found")
        if rec.provenance == "real" and rec.is_protected:
            raise ValueError("Real protected recordings cannot be deleted from the UI. Contact admin or use dataset delete with confirmation.")

        fpath = settings.data_dir / rec.file_path
        if fpath.exists():
            fpath.unlink()
        ds = self.repo.get_dataset(dataset_id)
        self.db.delete(rec)
        if ds:
            ds.recording_count = max(0, ds.recording_count - 1)
        self.repo.add_activity("recording_deleted", f"Deleted recording {recording_id} from dataset {dataset_id}")
        self.db.commit()
        return {"recording_id": recording_id, "deleted": True}

    def delete_training_job(self, job_id: int) -> dict[str, Any]:
        job = self.db.get(TrainingJob, job_id)
        if not job:
            raise ValueError("Training job not found")
        if job.status in {"running", "queued"}:
            raise ValueError("Cancel the job before deleting it.")
        self.db.delete(job)
        self.repo.add_activity("job_deleted", f"Deleted training job {job_id}")
        self.db.commit()
        return {"job_id": job_id, "deleted": True}

    def delete_evaluation(self, run_id: int) -> dict[str, Any]:
        run = self.db.get(EvaluationRun, run_id)
        if not run:
            raise ValueError("Evaluation run not found")
        if run.results_path:
            results_dir = settings.artifacts_dir / run.results_path
            if results_dir.exists():
                shutil.rmtree(results_dir, ignore_errors=True)
        self.db.delete(run)
        self.repo.add_activity("evaluation_deleted", f"Deleted evaluation run {run_id}")
        self.db.commit()
        return {"run_id": run_id, "deleted": True}

    def delete_model(self, model_id: int, confirmation: str) -> dict[str, Any]:
        model = self.db.get(MLModel, model_id)
        if not model:
            raise ValueError("Model not found")
        if model.status == "active":
            raise ValueError("Deactivate the model before deleting it.")
        expected = f"DELETE MODEL {model_id}"
        if confirmation != expected:
            raise ValueError(f"Type '{expected}' to confirm permanent model deletion.")
        if model.bundle_path:
            bundle = settings.artifacts_dir / model.bundle_path
            if bundle.exists():
                shutil.rmtree(bundle, ignore_errors=True)
        self.db.delete(model)
        self.repo.add_activity("model_deleted", f"Permanently deleted model '{model.name}' (id={model_id})")
        self.db.commit()
        return {"model_id": model_id, "deleted": True}

    def clear_recognition_history(self) -> dict[str, int]:
        count = self.db.scalar(select(func.count()).select_from(RecognitionMessage)) or 0
        self.db.execute(delete(RecognitionMessage))
        self.repo.add_activity("history_cleared", f"Cleared {count} recognition messages")
        self.db.commit()
        return {"cleared": count}

    def clear_evaluations(self) -> dict[str, int]:
        runs = list(self.db.scalars(select(EvaluationRun)))
        for run in runs:
            if run.results_path:
                path = settings.artifacts_dir / run.results_path
                if path.exists():
                    shutil.rmtree(path, ignore_errors=True)
        count = len(runs)
        self.db.execute(delete(EvaluationRun))
        self.repo.add_activity("evaluations_cleared", f"Cleared {count} evaluation runs")
        self.db.commit()
        return {"cleared": count}

    def reset_database(self, scope: str, confirmation: str, delete_files: bool = False) -> dict[str, Any]:
        scopes = {
            "training": "RESET TRAINING",
            "synthetic": "RESET SYNTHETIC",
            "all": "RESET DATABASE",
        }
        if confirmation != scopes.get(scope):
            raise ValueError(f"Type '{scopes[scope]}' to confirm this operation.")

        result: dict[str, Any] = {"scope": scope, "deleted": {}}

        if scope == "training":
            for j in self.db.scalars(select(TrainingJob)):
                self.db.delete(j)
            for m in self.db.scalars(select(MLModel)):
                if m.bundle_path and delete_files:
                    shutil.rmtree(settings.artifacts_dir / m.bundle_path, ignore_errors=True)
                self.db.delete(m)
            result["deleted"] = {"training_jobs": "all", "models": "all"}
            if delete_files:
                eval_dir = settings.artifacts_dir / "evaluations"
                if eval_dir.exists():
                    shutil.rmtree(eval_dir, ignore_errors=True)
                    eval_dir.mkdir(parents=True, exist_ok=True)

        elif scope == "synthetic":
            synth_ids = [d.id for d in self.db.scalars(select(Dataset).where(Dataset.provenance == "synthetic"))]
            for ds_id in synth_ids:
                self.delete_dataset(ds_id, confirmation=f"DELETE {ds_id}", force=True)
            result["deleted"]["synthetic_datasets"] = len(synth_ids)

        elif scope == "all":
            if delete_files:
                for sub in ("datasets", "imports"):
                    p = settings.data_dir / sub
                    if p.exists():
                        shutil.rmtree(p, ignore_errors=True)
                        p.mkdir(parents=True, exist_ok=True)
                models_dir = settings.artifacts_dir / "models"
                if models_dir.exists():
                    shutil.rmtree(models_dir, ignore_errors=True)
                    models_dir.mkdir(parents=True, exist_ok=True)
                eval_dir = settings.artifacts_dir / "evaluations"
                if eval_dir.exists():
                    shutil.rmtree(eval_dir, ignore_errors=True)
                    eval_dir.mkdir(parents=True, exist_ok=True)

            for table in (
                RecognitionMessage,
                EvaluationRun,
                TrainingJob,
                MLModel,
                Recording,
                DatasetVersion,
                ImportJob,
                Dataset,
                ActivityLog,
            ):
                self.db.execute(delete(table))
            result["deleted"]["tables"] = "all research data"

        self.repo.add_activity("database_reset", f"Database reset scope={scope} delete_files={delete_files}")
        self.db.commit()
        return result
