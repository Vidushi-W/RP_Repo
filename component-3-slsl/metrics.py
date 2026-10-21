"""Similarity scores and basic hand joint-angle measurements."""

from __future__ import annotations

from itertools import permutations

import numpy as np


def _landmark_array(values: np.ndarray | list, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=np.float32)
    if array.shape != (21, 3):
        raise ValueError(f"{name} must have shape (21, 3), got {array.shape}")
    if not np.isfinite(array).all():
        raise ValueError(f"{name} must contain only finite coordinates")
    return array


def euclidean_distance(live: np.ndarray | list, target: np.ndarray | list) -> float:
    """Return mean per-landmark Euclidean error for two normalized hands."""
    live_points = _landmark_array(live, "live landmarks")
    target_points = _landmark_array(target, "target landmarks")
    per_landmark = np.linalg.norm(live_points - target_points, axis=1)
    return float(np.mean(per_landmark))


def cosine_similarity(live: np.ndarray | list, target: np.ndarray | list) -> float:
    """Return cosine similarity of flattened normalized landmark vectors."""
    live_vector = _landmark_array(live, "live landmarks").ravel()
    target_vector = _landmark_array(target, "target landmarks").ravel()
    denominator = float(np.linalg.norm(live_vector) * np.linalg.norm(target_vector))
    if denominator <= np.finfo(np.float32).eps:
        return 1.0 if np.allclose(live_vector, target_vector) else 0.0
    return float(np.clip(np.dot(live_vector, target_vector) / denominator, -1.0, 1.0))


def accuracy_percentage(live: np.ndarray | list, target: np.ndarray | list) -> float:
    """Map mean landmark distance to the project's pose-similarity percentage.

    The factor of two follows the provided prototype formula. This is a
    similarity score, not a calibrated probability or sign accuracy.
    """
    distance = euclidean_distance(live, target)
    return max(0.0, (1.0 - (distance * 2.0)) * 100.0)


def _frame_distance_and_pairs(
    live_frame: np.ndarray, reference_frame: np.ndarray
) -> tuple[float, tuple[tuple[int, int], ...]]:
    """Compare two one- or two-hand frames, pairing hands by lowest error."""
    live = np.asarray(live_frame, dtype=np.float32)
    reference = np.asarray(reference_frame, dtype=np.float32)
    if live.ndim == 2:
        live = live[None, :, :]
    if reference.ndim == 2:
        reference = reference[None, :, :]
    if live.ndim != 3 or reference.ndim != 3 or live.shape[1:] != (21, 3) or reference.shape[1:] != (21, 3):
        raise ValueError("Each sequence frame must have shape (21, 3) or (hands, 21, 3)")
    if len(live) != len(reference) or not len(live):
        return float("inf"), ()

    best_distance = float("inf")
    best_pairs: tuple[tuple[int, int], ...] = ()
    for reference_order in permutations(range(len(reference))):
        pairs = tuple((live_index, reference_index) for live_index, reference_index in enumerate(reference_order))
        distance = float(np.mean([euclidean_distance(live[i], reference[j]) for i, j in pairs]))
        if distance < best_distance:
            best_distance, best_pairs = distance, pairs
    return best_distance, best_pairs


def compare_pose_sequences(
    live_sequence: list[np.ndarray], reference_sequence: list[np.ndarray]
) -> dict[str, object] | None:
    """Align live and reference pose sequences with dynamic time warping.

    Returns the prototype similarity from the mean per-frame aligned
    landmark distance, along with aligned frame and hand index pairs used for
    kinematic comparisons. Frames with different hand counts cannot align.
    """
    if not live_sequence or not reference_sequence:
        return None
    live_count = np.asarray(live_sequence[0]).reshape(-1, 21, 3).shape[0]
    reference_count = np.asarray(reference_sequence[0]).reshape(-1, 21, 3).shape[0]
    if live_count != reference_count:
        return None

    live_length, reference_length = len(live_sequence), len(reference_sequence)
    if reference_length == 1:
        aligned = []
        for live_index, live_frame in enumerate(live_sequence):
            distance, hand_pairs = _frame_distance_and_pairs(live_frame, reference_sequence[0])
            if not np.isfinite(distance):
                return None
            aligned.append((live_index, 0, hand_pairs))
        mean_distance = float(np.mean([
            _frame_distance_and_pairs(live_sequence[i], reference_sequence[0])[0]
            for i, _, _ in aligned
        ]))
        return {
            "distance": mean_distance,
            "similarity": max(0.0, (1.0 - (mean_distance * 2.0)) * 100.0),
            "alignment": aligned,
        }

    costs = np.full((live_length, reference_length), np.inf, dtype=np.float64)
    pairings: dict[tuple[int, int], tuple[tuple[int, int], ...]] = {}
    for i, live_frame in enumerate(live_sequence):
        for j, reference_frame in enumerate(reference_sequence):
            distance, hands = _frame_distance_and_pairs(live_frame, reference_frame)
            costs[i, j] = distance
            pairings[(i, j)] = hands

    accumulated = np.full((live_length + 1, reference_length + 1), np.inf, dtype=np.float64)
    predecessor = np.zeros((live_length + 1, reference_length + 1), dtype=np.uint8)
    accumulated[0, 0] = 0.0
    # Allow leading idle frames before the learner begins the sign.
    accumulated[1:, 0] = 0.0
    # 0 = diagonal, 1 = consume live frame, 2 = consume reference frame.
    for i in range(1, live_length + 1):
        for j in range(1, reference_length + 1):
            choices = (accumulated[i - 1, j - 1], accumulated[i - 1, j], accumulated[i, j - 1])
            direction = int(np.argmin(choices))
            accumulated[i, j] = costs[i - 1, j - 1] + choices[direction]
            predecessor[i, j] = direction
    # End at the least-cost point that has consumed the complete reference,
    # allowing trailing idle frames after the learner finishes the sign.
    live_end = int(np.argmin(accumulated[1:, reference_length])) + 1
    if not np.isfinite(accumulated[live_end, reference_length]):
        return None

    aligned: list[tuple[int, int, tuple[tuple[int, int], ...]]] = []
    i, j = live_end, reference_length
    while j > 0 and i > 0:
        aligned.append((i - 1, j - 1, pairings[(i - 1, j - 1)]))
        direction = predecessor[i, j]
        if direction == 0:
            i -= 1
            j -= 1
        elif direction == 1:
            i -= 1
        else:
            j -= 1
    aligned.reverse()
    if not aligned:
        return None
    mean_distance = float(np.mean([costs[live_i, ref_i] for live_i, ref_i, _ in aligned]))
    similarity = max(0.0, (1.0 - (mean_distance * 2.0)) * 100.0)
    return {
        "distance": mean_distance,
        "similarity": similarity,
        "alignment": aligned,
    }


def joint_angle_degrees(
    landmarks: np.ndarray | list, first: int, joint: int, last: int
) -> float:
    """Measure the angle at ``joint`` from three landmark indices."""
    points = _landmark_array(landmarks, "landmarks")
    if any(index < 0 or index >= 21 for index in (first, joint, last)):
        raise IndexError("Landmark indices must be between 0 and 20")
    vector_a = points[first] - points[joint]
    vector_b = points[last] - points[joint]
    lengths = float(np.linalg.norm(vector_a) * np.linalg.norm(vector_b))
    if lengths <= np.finfo(np.float32).eps:
        return float("nan")
    cosine = float(np.clip(np.dot(vector_a, vector_b) / lengths, -1.0, 1.0))
    return float(np.degrees(np.arccos(cosine)))
