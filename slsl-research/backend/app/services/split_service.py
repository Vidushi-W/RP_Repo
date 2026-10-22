"""Train/validation/test split management with group isolation."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.dataset import Recording


def assign_splits(
    recordings: list[Recording],
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
    preserve_existing: bool = True,
) -> None:
    groups: dict[str, list[Recording]] = defaultdict(list)
    for rec in recordings:
        if preserve_existing and rec.split in {"train", "val", "test"}:
            continue
        key = rec.group_id or rec.recording_id
        groups[key].append(rec)

    group_keys = sorted(groups.keys())
    n = len(group_keys)
    train_end = int(n * train_ratio)
    val_end = train_end + int(n * val_ratio)
    for idx, gkey in enumerate(group_keys):
        split = "train" if idx < train_end else ("val" if idx < val_end else "test")
        for rec in groups[gkey]:
            if preserve_existing and rec.split in {"train", "val", "test"}:
                continue
            rec.split = split


def validate_split_isolation(recordings: list[Recording]) -> list[str]:
    errors: list[str] = []
    group_splits: dict[str, set[str]] = defaultdict(set)
    hash_splits: dict[str, set[str]] = defaultdict(set)
    for rec in recordings:
        gkey = rec.group_id or rec.recording_id
        group_splits[gkey].add(rec.split)
        if rec.content_hash:
            hash_splits[rec.content_hash].add(rec.split)
    for gkey, splits in group_splits.items():
        if len(splits) > 1:
            errors.append(f"Group {gkey} appears in multiple splits: {sorted(splits)}")
    for h, splits in hash_splits.items():
        if len(splits) > 1:
            errors.append(f"Duplicate content hash {h[:12]}… spans splits: {sorted(splits)}")
    return errors


def save_split_manifest(recordings: list[Recording], path: Path) -> None:
    rows = [{"recording_id": r.recording_id, "split": r.split, "group_id": r.group_id} for r in recordings]
    path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
