"""Load normalized hand-pose templates from the processed reference folder."""

from __future__ import annotations

import json
from pathlib import Path
from collections import Counter, defaultdict

import numpy as np


def _read_template(path: Path) -> tuple[np.ndarray, dict[str, list]]:
    """Read template arrays and per-pose metadata from either storage format."""
    metadata: dict[str, list] = {}
    if path.suffix.lower() == ".npy":
        poses = np.asarray(np.load(path), dtype=np.float32)
        metadata_path = path.with_suffix(".json")
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    elif path.suffix.lower() == ".npz":
        with np.load(path) as stored:
            if "landmarks" not in stored:
                raise ValueError(f"Missing 'landmarks' array in {path}")
            poses = np.asarray(stored["landmarks"], dtype=np.float32)
            for key in ("source_files", "frame_numbers", "hand_indices"):
                if key in stored:
                    metadata[key] = stored[key].tolist()
    else:
        raise ValueError(f"Unsupported reference template format: {path}")

    if poses.shape == (21, 3):
        poses = poses[None, :, :]
    if poses.ndim != 3 or poses.shape[1:] != (21, 3) or not len(poses):
        raise ValueError(f"Invalid reference template shape in {path}: {poses.shape}")
    if not np.isfinite(poses).all():
        raise ValueError(f"Reference template contains non-finite coordinates: {path}")
    return poses, metadata


def _sequence_groups(poses: np.ndarray, metadata: dict[str, list], fallback_name: str) -> list[list[np.ndarray]]:
    """Group hand rows into ordered frames and source-specific sequences."""
    source_files = metadata.get("source_files") or [fallback_name] * len(poses)
    frame_numbers = metadata.get("frame_numbers") or list(range(len(poses)))
    hand_indices = metadata.get("hand_indices") or [0] * len(poses)
    if not (len(source_files) == len(frame_numbers) == len(hand_indices) == len(poses)):
        raise ValueError(f"Reference metadata row counts do not match {fallback_name}")

    groups: dict[str, dict[int, dict[int, np.ndarray]]] = defaultdict(lambda: defaultdict(dict))
    for pose, source, frame_number, hand_index in zip(poses, source_files, frame_numbers, hand_indices):
        groups[str(source)][int(frame_number)][int(hand_index)] = pose

    sequences: list[list[np.ndarray]] = []
    for frames in groups.values():
        hand_counts = Counter(len(hands) for hands in frames.values())
        if not hand_counts:
            continue
        # Keep the dominant hand count per source. Prefer 2 hands on ties,
        # which avoids silently reducing an intended two-hand sign to one.
        expected_hands = max(hand_counts, key=lambda count: (hand_counts[count], count))
        sequence = [
            np.stack([hands[index] for index in sorted(hands)])
            for _, hands in sorted(frames.items())
            if len(hands) == expected_hands
        ]
        if sequence:
            sequences.append(sequence)
    return sequences


def load_reference_sequences(
    reference_dir: str | Path | None = None,
) -> dict[str, list[list[np.ndarray]]]:
    """Load each sign as its source-specific temporal pose sequences.

    Each sequence contains frames shaped ``(hands, 21, 3)``. Video source
    files remain separate sequences; a still image becomes a one-frame sequence.
    """
    directory = (
        Path(reference_dir)
        if reference_dir is not None
        else Path(__file__).resolve().parents[1] / "references" / "processed"
    )
    if not directory.exists():
        return {}

    library: dict[str, list[list[np.ndarray]]] = {}
    for path in sorted(directory.iterdir()):
        if path.suffix.lower() not in {".npy", ".npz"}:
            continue
        if path.suffix.lower() == ".npz":
            # Prefer the simpler .npy template when both formats exist.
            if path.with_suffix(".npy").exists():
                continue
        poses, metadata = _read_template(path)
        sequences = _sequence_groups(poses, metadata, path.name)
        if sequences:
            library[path.stem] = sequences
    return library


def load_reference_library(
    reference_dir: str | Path | None = None,
) -> dict[str, np.ndarray]:
    """Load all templates by label as flattened ``(N, 21, 3)`` arrays.

    Kept for simple callers; live sequence scoring should use
    :func:`load_reference_sequences` to preserve video frame order.
    """
    return {
        label: np.concatenate([np.concatenate(sequence, axis=0) for sequence in sequences])
        for label, sequences in load_reference_sequences(reference_dir).items()
    }
