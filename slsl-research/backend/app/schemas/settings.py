from typing import Any, Optional

from pydantic import BaseModel, Field


class StudioSettings(BaseModel):
    default_model_id: Optional[int] = None
    torch_threads: int = Field(ge=1, le=8, default=2)
    max_upload_mb: int = Field(ge=1, le=500, default=50)
    training_concurrency: int = Field(ge=1, le=1, default=1)
    uncertainty_threshold: float = Field(ge=0.0, le=1.0, default=0.25)
    theme: str = Field(default="light", pattern="^(light|dark)$")
    data_dir: str = ""
    artifacts_dir: str = ""
    database_url: str = ""
    max_upload_bytes: int = 0
    paths_readonly: bool = True


class SettingsUpdate(BaseModel):
    default_model_id: Optional[int] = None
    torch_threads: Optional[int] = Field(default=None, ge=1, le=8)
    max_upload_mb: Optional[int] = Field(default=None, ge=1, le=500)
    uncertainty_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    theme: Optional[str] = Field(default=None, pattern="^(light|dark)$")
