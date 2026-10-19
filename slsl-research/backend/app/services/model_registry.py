"""Model registry: activate, export, import, archive."""

from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.ml_model import MLModel


class ModelRegistryService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_models(self, include_archived: bool = False) -> list[MLModel]:
        q = select(MLModel).order_by(MLModel.created_at.desc())
        if not include_archived:
            q = q.where(MLModel.is_archived == False)  # noqa: E712
        return list(self.db.scalars(q))

    def get_model(self, model_id: int) -> MLModel | None:
        return self.db.get(MLModel, model_id)

    def activate_model(self, model_id: int) -> MLModel:
        model = self.db.get(MLModel, model_id)
        if not model or model.is_archived:
            raise ValueError("Model not found or archived")
        bundle = settings.artifacts_dir / (model.bundle_path or "")
        required = ["model.pt", "vocabulary.json", "preprocessing.json", "model_config.json"]
        for f in required:
            if not (bundle / f).exists():
                raise ValueError(f"Model bundle incomplete: missing {f}")
        for m in self.db.scalars(select(MLModel).where(MLModel.status == "active")):
            m.status = "inactive"
        model.status = "active"
        self.db.commit()
        self.db.refresh(model)
        return model

    def archive_model(self, model_id: int) -> MLModel:
        model = self.db.get(MLModel, model_id)
        if not model:
            raise ValueError("Model not found")
        if model.status == "active":
            model.status = "inactive"
        model.is_archived = True
        self.db.commit()
        return model

    def export_bundle(self, model_id: int, dest: Path) -> Path:
        model = self.db.get(MLModel, model_id)
        if not model or not model.bundle_path:
            raise ValueError("Model bundle not found")
        src = settings.artifacts_dir / model.bundle_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in src.rglob("*"):
                if f.is_file():
                    zf.write(f, f.relative_to(src))
        return dest

    def import_bundle(self, zip_path: Path, name: str) -> MLModel:
        import_dir = settings.artifacts_dir / "models" / f"imported_{zip_path.stem}"
        import_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zf:
            for member in zf.infolist():
                if ".." in member.filename:
                    raise ValueError("Unsafe path in bundle")
                zf.extract(member, import_dir)
        required = ["model.pt", "vocabulary.json", "preprocessing.json"]
        for f in required:
            if not (import_dir / f).exists():
                raise ValueError(f"Invalid bundle: missing {f}")
        metrics = {}
        if (import_dir / "validation_results.json").exists():
            metrics = json.loads((import_dir / "validation_results.json").read_text())
        model = MLModel(
            name=name,
            version="imported",
            status="inactive",
            bundle_path=str(import_dir.relative_to(settings.artifacts_dir)).replace("\\", "/"),
            checkpoint_path=str((import_dir / "model.pt").relative_to(settings.artifacts_dir)).replace("\\", "/"),
            vocabulary_json=(import_dir / "vocabulary.json").read_text(encoding="utf-8"),
            feature_schema_json=(import_dir / "feature_schema.json").read_text(encoding="utf-8") if (import_dir / "feature_schema.json").exists() else "{}",
            validation_metrics_json=json.dumps(metrics),
            emotion_available=(import_dir / "emotion_model.pkl").exists(),
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return model
