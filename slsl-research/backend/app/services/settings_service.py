"""Local studio settings persisted alongside artifacts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.dataset import Dataset
from app.models.evaluation import EvaluationRun
from app.models.job import TrainingJob
from app.models.ml_model import MLModel
from app.repositories.system import SystemRepository


class SettingsService:
    DEFAULTS = {
        "default_model_id": None,
        "torch_threads": 2,
        "max_upload_mb": 50,
        "training_concurrency": 1,
        "uncertainty_threshold": 0.25,
        "theme": "light",
    }

    def __init__(self, db: Session) -> None:
        self.db = db
        self.path = settings.artifacts_dir / "studio_settings.json"

    def _ensure_dir(self) -> None:
        settings.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def get_settings(self) -> dict[str, Any]:
        data = dict(self.DEFAULTS)
        if self.path.exists():
            stored = json.loads(self.path.read_text(encoding="utf-8"))
            data.update({k: stored[k] for k in self.DEFAULTS if k in stored})
        return {
            **data,
            "data_dir": str(settings.data_dir),
            "artifacts_dir": str(settings.artifacts_dir),
            "database_url": settings.database_url,
            "max_upload_bytes": settings.max_upload_bytes,
            "paths_readonly": True,
        }

    def update_settings(self, patch: dict[str, Any]) -> dict[str, Any]:
        current = self.get_settings()
        allowed = {k: patch[k] for k in self.DEFAULTS if k in patch}
        if "default_model_id" in allowed and allowed["default_model_id"] is not None:
            model = self.db.get(MLModel, allowed["default_model_id"])
            if not model or model.is_archived:
                raise ValueError("Default model not found or archived")
        merged = {**{k: current[k] for k in self.DEFAULTS}, **allowed}
        self._ensure_dir()
        self.path.write_text(json.dumps(merged, indent=2), encoding="utf-8")
        return self.get_settings()

    def export_metadata(self) -> dict[str, Any]:
        repo = SystemRepository(self.db)
        return {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "app": settings.app_name,
            "datasets": [
                {"id": d.id, "name": d.name, "provenance": d.provenance, "recording_count": d.recording_count}
                for d in self.db.scalars(select(Dataset).order_by(Dataset.id))
            ],
            "models": [
                {
                    "id": m.id,
                    "name": m.name,
                    "version": m.version,
                    "status": m.status,
                    "provenance": m.provenance,
                    "is_archived": m.is_archived,
                }
                for m in self.db.scalars(select(MLModel).order_by(MLModel.id))
            ],
            "training_jobs": [
                {"id": j.id, "name": j.name, "status": j.status, "model_id": j.model_id}
                for j in self.db.scalars(select(TrainingJob).order_by(TrainingJob.id))
            ],
            "evaluations": [
                {"id": e.id, "name": e.name, "wer": e.word_error_rate, "status": e.status}
                for e in self.db.scalars(select(EvaluationRun).order_by(EvaluationRun.id))
            ],
            "active_model_id": repo.active_model().id if repo.active_model() else None,
            "settings": self.get_settings(),
        }
