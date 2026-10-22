from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    model_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dataset_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dataset_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    split_used: Mapped[str] = mapped_column(String(16), nullable=False, default="test")
    provenance: Mapped[str] = mapped_column(String(32), nullable=False, default="synthetic")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    sequence_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    word_error_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    config_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    results_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    metrics_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
