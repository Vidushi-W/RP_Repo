from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class DatasetSummary(BaseModel):
    id: int
    name: str
    description: str
    provenance: str
    status: str
    current_version: str
    recording_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None


class RecordingSummary(BaseModel):
    id: int
    recording_id: str
    signer_id: str
    provenance: str
    ordered_sign_labels: str
    emotion_label: str
    reference_english_sentence: str
    split: str
    duration_ms: float
    frame_count: int
    sample_rate_hz: float


class RecordingDetail(RecordingSummary):
    file_path: str
    collection_date: Optional[str] = None
    group_id: str
    validation: dict[str, Any] = Field(default_factory=dict)
    visualization: dict[str, Any] = Field(default_factory=dict)


class RecordingUpdate(BaseModel):
    ordered_sign_labels: str
    emotion_label: str
    reference_english_sentence: str = ""
    signer_id: str
    provenance: str
    split: str


class ValidationReportSchema(BaseModel):
    valid: bool
    errors: list[str]
    warnings: list[str]
    frame_count: int = 0
    duration_ms: float = 0.0
    estimated_sample_rate_hz: float = 0.0


class ImportPreviewItem(BaseModel):
    filename: str
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    frame_count: int = 0
    duration_ms: float = 0.0


class ImportJobSchema(BaseModel):
    id: int
    dataset_id: Optional[int]
    status: str
    step: str
    source_name: str
    report: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class DatasetValidationReport(BaseModel):
    dataset_id: int
    recording_count: int
    valid_recordings: int
    invalid_recordings: int
    split_counts: dict[str, int]
    split_isolation_errors: list[str]
    issues: list[str]


class SyntheticGenerateRequest(BaseModel):
    name: str = "Synthetic Prototype Dataset"
    description: str = "Artificial sensor patterns for pipeline development."
    total_recordings: int = Field(default=400, ge=50, le=600)
    seed: int = 42


class SplitAssignRequest(BaseModel):
    train_ratio: float = Field(default=0.7, ge=0.1, le=0.9)
    val_ratio: float = Field(default=0.15, ge=0.05, le=0.5)
    preserve_existing: bool = True


class DatasetCreateRequest(BaseModel):
    name: str
    description: str = ""
    provenance: str = "synthetic"
