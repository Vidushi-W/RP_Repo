"""Controlled English sentence generation from predicted gloss sequences."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Configurable gloss-pattern → English mappings (no LLM, no external API).
SENTENCE_PATTERNS: dict[tuple[str, ...], str] = {
    ("I", "NEED", "WATER"): "I need water.",
    ("I", "WANT", "FOOD"): "I want food.",
    ("YOU", "GO", "HOME"): "You go home.",
    ("I", "NEED", "HELP"): "I need help.",
    ("YOU", "STOP"): "You stop.",
}


@dataclass
class SentenceResult:
    english: str
    status: str  # supported | fallback | uncertain | empty
    gloss_sequence: list[str]
    pattern_matched: bool
    message: str


def _simple_fallback(gloss_tokens: list[str]) -> str:
    if not gloss_tokens:
        return ""
    words = [t.lower() if t.isupper() and len(t) > 1 else t for t in gloss_tokens]
    sentence = " ".join(words)
    if sentence:
        sentence = sentence[0].upper() + sentence[1:]
    if sentence and sentence[-1] not in ".!?":
        sentence += "."
    return sentence


def generate_english_sentence(
    gloss_tokens: list[str],
    decoder_score: float = 1.0,
    uncertainty_threshold: float = 0.25,
) -> SentenceResult:
    """Generate English from predicted glosses only — never from filenames or reference text."""
    if not gloss_tokens:
        return SentenceResult(
            english="",
            status="empty",
            gloss_sequence=[],
            pattern_matched=False,
            message="No signs decoded.",
        )

    key = tuple(gloss_tokens)
    if decoder_score < uncertainty_threshold:
        return SentenceResult(
            english=_simple_fallback(gloss_tokens),
            status="uncertain",
            gloss_sequence=gloss_tokens,
            pattern_matched=key in SENTENCE_PATTERNS,
            message="Low decoder confidence — showing gloss-based fallback instead of a fluent sentence.",
        )

    if key in SENTENCE_PATTERNS:
        return SentenceResult(
            english=SENTENCE_PATTERNS[key],
            status="supported",
            gloss_sequence=gloss_tokens,
            pattern_matched=True,
            message="Matched supported gloss pattern.",
        )

    # Partial pattern support: try without repeated tokens collapsed
    collapsed = [gloss_tokens[0]]
    for t in gloss_tokens[1:]:
        if t != collapsed[-1]:
            collapsed.append(t)
    collapsed_key = tuple(collapsed)
    if collapsed_key in SENTENCE_PATTERNS and collapsed_key != key:
        return SentenceResult(
            english=SENTENCE_PATTERNS[collapsed_key],
            status="supported",
            gloss_sequence=gloss_tokens,
            pattern_matched=True,
            message="Matched pattern after collapsing repeated glosses.",
        )

    return SentenceResult(
        english=_simple_fallback(gloss_tokens),
        status="fallback",
        gloss_sequence=gloss_tokens,
        pattern_matched=False,
        message="Unsupported gloss pattern — literal gloss concatenation shown.",
    )


def list_sentence_patterns() -> list[dict[str, Any]]:
    return [
        {"gloss_sequence": list(k), "english": v, "supported": True}
        for k, v in SENTENCE_PATTERNS.items()
    ]
