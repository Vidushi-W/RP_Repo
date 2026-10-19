"""Safe training workspace reset."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.dataset import Dataset
from app.models.job import TrainingJob
from app.models.ml_model import MLModel


class ResetService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def preview_reset(self, options: dict) -> dict:
        affected = {
            "active_models": [],
            "models_to_archive": [],
            "jobs_to_clear": [],
            "datasets_to_remove": [],
            "warnings": [],
            "safe_defaults": {
                "archive_models": True,
                "clear_jobs": False,
                "delete_checkpoints": False,
                "remove_synthetic_datasets": False,
            },
        }
        for m in self.db.scalars(select(MLModel).where(MLModel.status == "active")):
            affected["active_models"].append({"id": m.id, "name": m.name})
        if options.get("archive_models"):
            for m in self.db.scalars(select(MLModel).where(MLModel.is_archived == False)):  # noqa: E712
                affected["models_to_archive"].append({"id": m.id, "name": m.name})
        if options.get("clear_jobs"):
            for j in self.db.scalars(select(TrainingJob)):
                affected["jobs_to_clear"].append({"id": j.id, "name": j.name, "status": j.status})
        if options.get("remove_synthetic_datasets"):
            for d in self.db.scalars(select(Dataset).where(Dataset.provenance == "synthetic")):
                affected["datasets_to_remove"].append({"id": d.id, "name": d.name})
        return affected

    def execute_reset(self, options: dict, confirmation: str) -> dict:
        if confirmation != "RESET":
            raise ValueError("Typed confirmation must be RESET for irreversible actions.")
        result = {"deactivated_models": 0, "archived_models": 0, "cleared_jobs": 0}
        for m in self.db.scalars(select(MLModel).where(MLModel.status == "active")):
            m.status = "inactive"
            result["deactivated_models"] += 1
        if options.get("archive_models"):
            for m in self.db.scalars(select(MLModel).where(MLModel.is_archived == False)):  # noqa: E712
                m.is_archived = True
                m.status = "inactive"
                result["archived_models"] += 1
        if options.get("clear_jobs"):
            for j in self.db.scalars(select(TrainingJob)):
                self.db.delete(j)
                result["cleared_jobs"] += 1
        if options.get("delete_checkpoints") and options.get("confirmation_delete") == "DELETE":
            models_dir = settings.artifacts_dir / "models"
            if models_dir.exists():
                for p in models_dir.iterdir():
                    if p.is_dir() and p.name.startswith("job_"):
                        import shutil
                        shutil.rmtree(p, ignore_errors=True)
        from app.repositories.dataset import DatasetRepository

        DatasetRepository(self.db).add_activity(
            "workspace_reset",
            f"Reset workspace — deactivated {result['deactivated_models']}, archived {result['archived_models']}",
        )
        self.db.commit()
        return result
