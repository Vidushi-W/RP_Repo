from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    provenance: Mapped[str] = mapped_column(String(32), nullable=False, default="synthetic")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    current_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0.0")
    recording_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    versions: Mapped[list["DatasetVersion"]] = relationship(back_populates="dataset", cascade="all, delete-orphan")
    recordings: Mapped[list["Recording"]] = relationship(back_populates="dataset", cascade="all, delete-orphan")


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    split_manifest_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_locked: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    dataset: Mapped["Dataset"] = relationship(back_populates="versions")


class Recording(Base):
    __tablename__ = "recordings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recording_id: Mapped[str] = mapped_column(String(128), nullable=False)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"), nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0.0")
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    signer_id: Mapped[str] = mapped_column(String(128), nullable=False, default="UNKNOWN")
    provenance: Mapped[str] = mapped_column(String(32), nullable=False, default="synthetic")
    ordered_sign_labels: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    emotion_label: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    reference_english_sentence: Mapped[str] = mapped_column(Text, nullable=False, default="")
    split: Mapped[str] = mapped_column(String(16), nullable=False, default="unassigned")
    collection_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    group_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    duration_ms: Mapped[float] = mapped_column(default=0.0)
    frame_count: Mapped[int] = mapped_column(Integer, default=0)
    sample_rate_hz: Mapped[float] = mapped_column(default=0.0)
    is_protected: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    dataset: Mapped["Dataset"] = relationship(back_populates="recordings")


class ImportJob(Base):
    __tablename__ = "import_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[int | None] = mapped_column(ForeignKey("datasets.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    step: Mapped[str] = mapped_column(String(64), nullable=False, default="select_files")
    source_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    report_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
