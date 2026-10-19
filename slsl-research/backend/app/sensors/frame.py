"""Common synchronized two-glove sensor frame (22 features)."""

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from app.core.config import FEATURE_COLUMNS

NUM_FEATURES = 22


@dataclass(frozen=True)
class SensorFrame:
    timestamp_ms: float
    features: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.features) != NUM_FEATURES:
            raise ValueError(f"Expected {NUM_FEATURES} features, got {len(self.features)}")

    def as_dict(self) -> dict[str, float]:
        return {"timestamp_ms": float(self.timestamp_ms), **{n: float(self.features[i]) for i, n in enumerate(FEATURE_COLUMNS)}}


@dataclass
class SensorRecording:
    frames: list[SensorFrame] = field(default_factory=list)
    source_name: str = "unknown"
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        if not self.frames:
            return 0.0
        return self.frames[-1].timestamp_ms - self.frames[0].timestamp_ms

    @property
    def frame_count(self) -> int:
        return len(self.frames)

    def timestamps(self) -> np.ndarray:
        if not self.frames:
            return np.zeros(0, dtype=np.float64)
        return np.array([f.timestamp_ms for f in self.frames], dtype=np.float64)

    def to_feature_matrix(self) -> np.ndarray:
        if not self.frames:
            return np.zeros((0, NUM_FEATURES), dtype=np.float32)
        return np.array([f.features for f in self.frames], dtype=np.float32)
