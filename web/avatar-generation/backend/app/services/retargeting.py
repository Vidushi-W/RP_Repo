"""Future landmark-to-Blender/GLTF skeleton retargeting boundary."""
from pathlib import Path
from app.schemas.motion import MotionSequence
def retarget_motion(motion: MotionSequence, rig: Path) -> Path:
    raise NotImplementedError("Define rest pose, bone mapping, scale, hand/finger constraints, and smoothing before exporting clips.")
