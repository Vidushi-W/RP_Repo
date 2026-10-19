"""CTC decoding utilities."""

from __future__ import annotations

import numpy as np
import torch


def greedy_ctc_decode(
    log_probs: np.ndarray,
    blank_index: int = 0,
    id_to_label: dict[int, str] | None = None,
) -> tuple[list[str], float]:
    probs = np.exp(log_probs - log_probs.max(axis=1, keepdims=True))
    probs = probs / probs.sum(axis=1, keepdims=True)
    best_path = probs.argmax(axis=1)
    max_probs = probs.max(axis=1)
    decoded: list[str] = []
    confidences: list[float] = []
    prev = blank_index
    for idx, token in enumerate(best_path):
        if token == blank_index:
            prev = blank_index
            continue
        if token != prev:
            label = id_to_label[token] if id_to_label else str(token)
            if label != "<blank>":
                decoded.append(label)
                confidences.append(float(max_probs[idx]))
        prev = token
    seq_conf = float(np.mean(confidences)) if confidences else 0.0
    return decoded, seq_conf


def torch_greedy_decode(
    logits: torch.Tensor,
    blank_index: int,
    id_to_label: dict[int, str],
) -> tuple[list[str], float]:
    log_probs = torch.log_softmax(logits, dim=-1).detach().cpu().numpy()
    return greedy_ctc_decode(log_probs, blank_index=blank_index, id_to_label=id_to_label)
