"""Recognition and emotion evaluation metrics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class AlignmentStep:
    op: str  # match | substitution | insertion | deletion
    ref: str | None
    pred: str | None


@dataclass
class SequenceMetrics:
    word_error_rate: float
    exact_match: bool
    insertions: int
    deletions: int
    substitutions: int
    alignment: list[AlignmentStep]


def _edit_table(ref: list[str], pred: list[str]) -> tuple[int, int, int, int, list[AlignmentStep]]:
    r, p = ref, pred
    d = np.zeros((len(r) + 1, len(p) + 1), dtype=int)
    for i in range(len(r) + 1):
        d[i, 0] = i
    for j in range(len(p) + 1):
        d[0, j] = j
    for i in range(1, len(r) + 1):
        for j in range(1, len(p) + 1):
            cost = 0 if r[i - 1] == p[j - 1] else 1
            d[i, j] = min(d[i - 1, j] + 1, d[i, j - 1] + 1, d[i - 1, j - 1] + cost)

    alignment: list[AlignmentStep] = []
    insertions = deletions = substitutions = 0
    i, j = len(r), len(p)
    while i > 0 or j > 0:
        if i > 0 and j > 0 and d[i, j] == d[i - 1, j - 1] and r[i - 1] == p[j - 1]:
            alignment.append(AlignmentStep("match", r[i - 1], p[j - 1]))
            i -= 1
            j -= 1
        elif i > 0 and j > 0 and d[i, j] == d[i - 1, j - 1] + 1:
            alignment.append(AlignmentStep("substitution", r[i - 1], p[j - 1]))
            substitutions += 1
            i -= 1
            j -= 1
        elif i > 0 and d[i, j] == d[i - 1, j] + 1:
            alignment.append(AlignmentStep("deletion", r[i - 1], None))
            deletions += 1
            i -= 1
        else:
            alignment.append(AlignmentStep("insertion", None, p[j - 1]))
            insertions += 1
            j -= 1
    alignment.reverse()
    edits = insertions + deletions + substitutions
    return edits, insertions, deletions, substitutions, alignment


def word_error_rate(ref: list[str], pred: list[str]) -> float:
    if not ref and not pred:
        return 0.0
    if not ref:
        return float(len(pred))
    edits, _, _, _, _ = _edit_table(ref, pred)
    return float(edits / len(ref))


def sequence_metrics(ref: list[str], pred: list[str]) -> SequenceMetrics:
    edits, ins, dels, subs, alignment = _edit_table(ref, pred)
    wer = 0.0 if not ref and not pred else (float(edits / len(ref)) if ref else float(len(pred)))
    return SequenceMetrics(
        word_error_rate=wer,
        exact_match=ref == pred,
        insertions=ins,
        deletions=dels,
        substitutions=subs,
        alignment=alignment,
    )


def aggregate_wer(per_recording_wer: list[float]) -> float:
    return float(np.mean(per_recording_wer)) if per_recording_wer else 0.0


def exact_sequence_accuracy(exact_flags: list[bool]) -> float:
    return float(np.mean(exact_flags)) if exact_flags else 0.0


def emotion_classification_metrics(y_true: list[str], y_pred: list[str]) -> dict[str, Any]:
    from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score

    labels = sorted(set(y_true) | set(y_pred))
    if not y_true:
        return {"available": False, "reason": "No ground-truth emotion labels in evaluation split."}
    acc = float(accuracy_score(y_true, y_pred))
    prec = float(precision_score(y_true, y_pred, labels=labels, average="macro", zero_division=0))
    rec = float(recall_score(y_true, y_pred, labels=labels, average="macro", zero_division=0))
    f1 = float(f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0))
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    return {
        "available": True,
        "accuracy": acc,
        "precision": prec,
        "recall": rec,
        "f1": f1,
        "labels": labels,
        "confusion_matrix": cm.tolist(),
    }
