"""Shared feature extraction for the kinematic error classifier."""

from __future__ import annotations

import numpy as np

from backend.metrics import hand_kinematic_features


ANGLE_NAMES = (
    "thumb_mcp", "thumb_ip", "thumb_abduction",
    "index_mcp", "index_pip", "index_dip",
    "middle_mcp", "middle_pip", "middle_dip",
    "ring_mcp", "ring_pip", "ring_dip",
    "pinky_mcp", "pinky_pip", "pinky_dip",
)
FEATURE_NAMES = tuple(
    [f"lm_{index}_{axis}" for index in range(21) for axis in "xyz"]
    + [f"angle_{name}" for name in ANGLE_NAMES]
    + ["palm_normal_x", "palm_normal_y", "palm_normal_z"]
)


def extract_features(normalized_landmarks: np.ndarray | list) -> np.ndarray:
    """Return one finite, fixed-length feature vector for a normalized hand."""
    points = np.asarray(normalized_landmarks, dtype=np.float32)
    if points.shape != (21, 3) or not np.isfinite(points).all():
        raise ValueError("Expected 21 finite, normalized XYZ hand landmarks")
    angles = hand_kinematic_features(points)
    palm_normal = np.cross(points[5] - points[0], points[17] - points[0])
    normal_length = float(np.linalg.norm(palm_normal))
    if normal_length <= np.finfo(np.float32).eps:
        raise ValueError("Cannot calculate palm orientation from degenerate landmarks")
    palm_normal /= normal_length
    values = [
        *points.reshape(-1).tolist(),
        *(angles[name] for name in ANGLE_NAMES),
        *palm_normal.tolist(),
    ]
    result = np.asarray(values, dtype=np.float32)
    if not np.isfinite(result).all():
        raise ValueError("Landmark feature extraction produced non-finite values")
    return result
