"""Coordinate normalization for MediaPipe Hands landmarks."""

from __future__ import annotations

import numpy as np


def normalize_landmarks(landmarks: np.ndarray | list) -> np.ndarray:
    """Center 21 XYZ landmarks at the wrist and scale to unit max radius.

    Args:
        landmarks: Array-like data with shape ``(21, 3)``.

    Returns:
        Float32 normalized landmarks with the wrist at the origin. If all
        points coincide, returns a zero array rather than dividing by zero.

    Raises:
        ValueError: If the input does not have shape ``(21, 3)`` or has
            non-finite values.
    """
    points = np.asarray(landmarks, dtype=np.float32)
    if points.shape != (21, 3):
        raise ValueError(f"Expected landmark shape (21, 3), got {points.shape}")
    if not np.isfinite(points).all():
        raise ValueError("Landmarks must contain only finite coordinates")

    centered = points - points[0]
    max_distance = float(np.linalg.norm(centered, axis=1).max())
    if max_distance <= np.finfo(np.float32).eps:
        return np.zeros_like(centered)
    return centered / max_distance
