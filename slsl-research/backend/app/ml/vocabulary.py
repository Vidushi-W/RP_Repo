"""Vocabulary and label encoding for CTC training."""

from __future__ import annotations

import json
from pathlib import Path

from app.core.config import VOCABULARY

BLANK_TOKEN = "<blank>"


def build_vocabulary(signs: list[str] | None = None) -> dict:
    labels = [BLANK_TOKEN] + sorted(set(signs or VOCABULARY))
    label_to_id = {label: idx for idx, label in enumerate(labels)}
    id_to_label = {idx: label for label, idx in label_to_id.items()}
    return {
        "blank_index": 0,
        "blank_token": BLANK_TOKEN,
        "labels": labels,
        "label_to_id": label_to_id,
        "id_to_label": {str(k): v for k, v in id_to_label.items()},
    }


def save_vocabulary(vocab: dict, path: Path) -> None:
    path.write_text(json.dumps(vocab, indent=2), encoding="utf-8")


def load_vocabulary(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def encode_labels(gloss: str, label_to_id: dict[str, int]) -> list[int]:
    if not gloss:
        return []
    tokens = [t.strip() for t in gloss.split("|") if t.strip()]
    unknown = [t for t in tokens if t not in label_to_id]
    if unknown:
        raise ValueError(f"Unknown gloss tokens: {unknown}")
    return [label_to_id[t] for t in tokens]
