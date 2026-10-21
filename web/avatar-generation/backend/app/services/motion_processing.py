"""Future cleaning, resampling and smoothing boundary, before retargeting."""
from app.schemas.motion import MotionSequence

def process_motion(motion: MotionSequence) -> MotionSequence:
    raise NotImplementedError(
        "Define missing-landmark handling, confidence filtering, coordinate normalization "
        "and smoothing without erasing linguistically meaningful motion."
    )
