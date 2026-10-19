from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MLModel(Base):
    __tablename__ = "ml_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False, default="1.0.0")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="inactive")
    architecture: Mapped[str] = mapped_column(String(64), nullable=False, default="ctc_cnn_bilstm")
    dataset_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dataset_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    provenance: Mapped[str] = mapped_column(String(32), nullable=False, default="synthetic")
    training_job_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checkpoint_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    bundle_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    vocabulary_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    feature_schema_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    validation_metrics_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    emotion_available: Mapped[bool] = mapped_column(Boolean, default=False)
    emotion_model_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
