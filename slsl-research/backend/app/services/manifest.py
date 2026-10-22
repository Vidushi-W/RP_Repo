"""Manifest parsing and column mapping."""

from __future__ import annotations

import pandas as pd

from app.core.config import MANIFEST_CANONICAL_COLUMNS


def map_manifest_columns(df: pd.DataFrame, custom_mapping: dict[str, str] | None = None) -> pd.DataFrame:
    mapping = custom_mapping or {}
    rename: dict[str, str] = {}
    lower_cols = {c.lower(): c for c in df.columns}
    for canonical, aliases in MANIFEST_CANONICAL_COLUMNS.items():
        if canonical in mapping and mapping[canonical] in df.columns:
            rename[mapping[canonical]] = canonical
            continue
        for alias in aliases:
            if alias in df.columns:
                rename[alias] = canonical
                break
            if alias.lower() in lower_cols:
                rename[lower_cols[alias.lower()]] = canonical
                break
    out = df.rename(columns=rename)
    if "recording_id" not in out.columns:
        raise ValueError("Manifest must include a recording identifier column (recording_id, id, or sample_id).")
    return out


def normalize_split(value: str) -> str:
    v = str(value).strip().lower()
    if v in {"train", "training", "tr"}:
        return "train"
    if v in {"val", "validation", "dev"}:
        return "val"
    if v in {"test", "testing", "held_out", "held-out"}:
        return "test"
    return "unassigned"


def normalize_emotion(value: str) -> str:
    v = str(value).strip().lower()
    if v in {"neutral", "angry", "unknown"}:
        return v
    return "unknown"
