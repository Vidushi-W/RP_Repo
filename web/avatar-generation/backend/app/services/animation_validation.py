"""Human review must precede an animation's available status."""
from pathlib import Path
def validate_animation(asset: Path, vocabulary_id: str) -> dict:
    raise NotImplementedError("Check rig integrity and timing, then obtain SLSL reviewer approval; never mark unreviewed output as valid.")
