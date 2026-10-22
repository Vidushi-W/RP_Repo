"""Summarize manually annotated diagnostic and fast/slow evaluation trials.

Complete research_evaluation/trials.csv after collecting real learner trials,
then run ``python -m backend.evaluate_trials``. This script never fabricates trials.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean, median


TRIALS_PATH = Path(__file__).resolve().parents[1] / "research_evaluation" / "trials.csv"


def evaluate_trials(path: str | Path = TRIALS_PATH) -> dict[str, float | int | None]:
    """Compute diagnosis rates, latency, and fast/slow score consistency."""
    rows: list[dict[str, str]] = []
    with Path(path).open(newline="", encoding="utf-8-sig") as stream:
        rows = [row for row in csv.DictReader(stream) if row.get("trial_id", "").strip()]

    intentional = [row for row in rows if row.get("expected_error_code", "").strip()]
    true_positives = 0
    total_detected = 0
    for row in rows:
        detected = {
            code.strip() for code in row.get("detected_errors", "").split(";")
            if code.strip()
        }
        total_detected += len(detected)
        expected = row.get("expected_error_code", "").strip()
        if expected and expected in detected:
            true_positives += 1

    latencies = [
        float(row["analysis_latency_ms"])
        for row in rows if row.get("analysis_latency_ms", "").strip()
    ]
    speed_scores: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in rows:
        speed = row.get("speed", "").strip().lower()
        sign_id = row.get("sign_id", "").strip()
        score = row.get("similarity_score", "").strip()
        if speed in {"fast", "slow"} and sign_id and score:
            speed_scores[(sign_id, speed)].append(float(score))
    paired_score_deltas = [
        abs(mean(speed_scores[(sign, "fast")]) - mean(speed_scores[(sign, "slow")]))
        for sign in {sign for sign, _ in speed_scores}
        if speed_scores[(sign, "fast")] and speed_scores[(sign, "slow")]
    ]

    return {
        "trials": len(rows),
        "intentional_error_trials": len(intentional),
        # This is the attachment's metric (correct tags / introduced errors).
        "intentional_error_detection_rate_pct": (
            100.0 * true_positives / len(intentional) if intentional else None
        ),
        # Conventional precision uses all predicted error tags as the denominator.
        "diagnostic_precision_pct": (
            100.0 * true_positives / total_detected if total_detected else None
        ),
        "mean_analysis_latency_ms": mean(latencies) if latencies else None,
        "median_analysis_latency_ms": median(latencies) if latencies else None,
        "fast_slow_paired_signs": len(paired_score_deltas),
        "mean_fast_slow_score_delta_points": mean(paired_score_deltas) if paired_score_deltas else None,
    }


def main() -> None:
    results = evaluate_trials()
    print("Empirical trial summary (only completed, human-recorded rows are used):")
    for label, value in results.items():
        formatted = "not available" if value is None else f"{value:.2f}" if isinstance(value, float) else str(value)
        print(f"  {label}: {formatted}")
    if results["intentional_error_trials"] < 20:
        print("  note: collect at least 20 intentional-error trials for the planned evaluation.")
    if not results["fast_slow_paired_signs"]:
        print("  note: collect both fast and slow attempts for the same sign to assess score consistency.")


if __name__ == "__main__":
    main()
