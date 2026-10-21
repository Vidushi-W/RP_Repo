"""Stable hand-off shapes for future offline modules."""
from pydantic import BaseModel, Field
class LandmarkFrame(BaseModel):
    timestamp_seconds: float = Field(ge=0)
    # Coordinates and landmark topology must be documented before retargeting.
    landmarks: list[list[float]]
class MotionSequence(BaseModel):
    source_id: str
    coordinate_system: str
    frames: list[LandmarkFrame]
