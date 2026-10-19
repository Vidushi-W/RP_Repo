"""Evaluation orchestration — sensor-only inference, labels compared after."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.ml.evaluator import EvalConfig, evaluate_recordings
from app.models.evaluation import EvaluationRun
from app.models.ml_model import MLModel
from app.repositories.dataset import DatasetRepository


class EvaluationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.dataset_repo = DatasetRepository(db)

    def _get_model(self, model_id: int) -> MLModel:
        model = self.db.get(MLModel, model_id)
        if not model or model.is_archived:
            raise ValueError("Model not found or archived")
        if not model.bundle_path:
            raise ValueError("Model has no saved bundle")
        bundle = settings.artifacts_dir / model.bundle_path
        for req in ("model.pt", "vocabulary.json", "preprocessing.json"):
            if not (bundle / req).exists():
                raise ValueError(f"Model bundle incomplete: missing {req}")
        return model

    def preview_compatibility(self, model_id: int, dataset_id: int, split: str = "test") -> dict[str, Any]:
        model = self._get_model(model_id)
        ds = self.dataset_repo.get_dataset(dataset_id)
        if not ds:
            raise ValueError("Dataset not found")

        recordings = self.dataset_repo.list_recordings(dataset_id)
        split_counts = {"train": 0, "val": 0, "test": 0, "unassigned": 0}
        for r in recordings:
            split_counts[r.split] = split_counts.get(r.split, 0) + 1

        vocab_data = json.loads(model.vocabulary_json or "{}")
        model_signs = set(vocab_data.get("label_to_id", {}).keys()) - {"<blank>"}
        dataset_signs: set[str] = set()
        for r in recordings:
            dataset_signs.update(t.strip() for t in r.ordered_sign_labels.split("|") if t.strip())
        unknown = sorted(dataset_signs - model_signs)
        vocab_warnings = []
        if unknown:
            vocab_warnings.append(f"Dataset contains {len(unknown)} gloss(es) outside model vocabulary: {unknown[:5]}")

        training_signers: set[str] = set()
        if model.dataset_id:
            for r in self.dataset_repo.list_recordings(model.dataset_id):
                if r.split in {"train", "val"}:
                    training_signers.add(r.signer_id)

        eval_recs = [r for r in recordings if r.split == split]
        eval_signers = {r.signer_id for r in eval_recs}
        unseen_signers = sorted(eval_signers - training_signers) if training_signers else sorted(eval_signers)

        warnings: list[str] = []
        recommended = "test"
        if split_counts.get("test", 0) > 0:
            recommended = "test"
        elif split_counts.get("val", 0) > 0:
            recommended = "val"
            warnings.append("No test split available; validation split is recommended only for diagnostics.")
        else:
            warnings.append("No held-out test or validation recordings found.")

        if split == "train":
            warnings.append("Training split must not be used for final reporting — results will be marked as diagnostic only.")
        elif split == "val":
            warnings.append("Validation split was used during training hyperparameter selection; prefer test split for final metrics.")
        if split_counts.get(split, 0) == 0:
            warnings.append(f"No recordings in '{split}' split.")

        signer_analysis = {
            "training_signer_count": len(training_signers),
            "evaluation_signer_count": len(eval_signers),
            "unseen_signers": unseen_signers,
            "supports_unseen_signer_eval": bool(unseen_signers) and bool(training_signers),
            "note": (
                "Signer-grouped held-out evaluation available."
                if unseen_signers and training_signers
                else "All evaluation signers were seen during training, or signer metadata is insufficient."
            ),
        }

        return {
            "model_id": model.id,
            "model_name": model.name,
            "model_version": model.version,
            "model_provenance": model.provenance,
            "training_dataset_id": model.dataset_id,
            "training_dataset_version": model.dataset_version,
            "dataset_id": ds.id,
            "dataset_name": ds.name,
            "dataset_version": ds.current_version,
            "dataset_provenance": ds.provenance,
            "split": split,
            "split_counts": split_counts,
            "recommended_split": recommended,
            "compatible": split_counts.get(split, 0) > 0 and len(vocab_warnings) == 0,
            "schema_compatible": True,
            "vocabulary_warnings": vocab_warnings,
            "signer_analysis": signer_analysis,
            "warnings": warnings,
        }

    def run_evaluation(self, payload: dict[str, Any]) -> EvaluationRun:
        model_id = payload["model_id"]
        dataset_id = payload["dataset_id"]
        split = payload.get("split", "test")
        preview = self.preview_compatibility(model_id, dataset_id, split)
        if preview["split_counts"].get(split, 0) == 0:
            raise ValueError(f"No recordings in '{split}' split for evaluation.")

        model = self._get_model(model_id)
        ds = self.dataset_repo.get_dataset(dataset_id)
        if not ds:
            raise ValueError("Dataset not found")

        run = EvaluationRun(
            name=payload.get("name", f"Eval {model.name} on {ds.name}"),
            model_id=model_id,
            dataset_id=dataset_id,
            dataset_version=ds.current_version,
            split_used=split,
            provenance=ds.provenance,
            status="running",
            config_json=json.dumps(payload),
            message="Evaluation in progress.",
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)

        try:
            recordings = [r for r in self.dataset_repo.list_recordings(dataset_id) if r.split == split]
            bundle_dir = settings.artifacts_dir / model.bundle_path
            output_dir = settings.artifacts_dir / "evaluations" / f"eval_{run.id}"
            config = EvalConfig(
                model_id=model_id,
                dataset_id=dataset_id,
                dataset_version=ds.current_version,
                split=split,
                uncertainty_threshold=payload.get("uncertainty_threshold", 0.25),
            )
            results = evaluate_recordings(bundle_dir, recordings, config, output_dir)

            agg = results["aggregate"]
            run.status = "completed"
            run.word_error_rate = agg["word_error_rate"]
            run.sequence_accuracy = agg["exact_sequence_accuracy"]
            run.summary = (
                f"WER {agg['word_error_rate']:.3f} · "
                f"Exact accuracy {agg['exact_sequence_accuracy']:.1%} · "
                f"{agg['recording_count']} recordings ({split})"
            )
            run.message = "Evaluation completed."
            run.metrics_json = json.dumps({"aggregate": agg, "emotion": results["emotion"]})
            run.results_path = str(output_dir.relative_to(settings.artifacts_dir)).replace("\\", "/")
            run.completed_at = datetime.now(timezone.utc)
            self.dataset_repo.add_activity(
                "evaluation_completed",
                f"Evaluation '{run.name}' — WER {agg['word_error_rate']:.3f}",
            )
            self.db.commit()
            self.db.refresh(run)
            return run
        except Exception as exc:  # noqa: BLE001
            run.status = "failed"
            run.message = str(exc)
            run.completed_at = datetime.now(timezone.utc)
            self.db.commit()
            raise

    def list_runs(self, provenance: str | None = None) -> list[EvaluationRun]:
        q = select(EvaluationRun).order_by(EvaluationRun.created_at.desc()).limit(50)
        if provenance:
            q = q.where(EvaluationRun.provenance == provenance)
        return list(self.db.scalars(q))

    def get_run(self, run_id: int) -> EvaluationRun | None:
        return self.db.get(EvaluationRun, run_id)

    def get_results(self, run_id: int) -> dict[str, Any]:
        run = self.get_run(run_id)
        if not run or not run.results_path:
            raise ValueError("Evaluation results not found")
        path = settings.artifacts_dir / run.results_path / "results.json"
        if not path.exists():
            raise ValueError("Results file missing")
        data = json.loads(path.read_text(encoding="utf-8"))
        return data

    def compare_runs(self, run_ids: list[int]) -> dict[str, Any]:
        runs = [self.get_run(rid) for rid in run_ids]
        if any(r is None for r in runs):
            raise ValueError("One or more evaluation runs not found")
        comparison = {
            "word_error_rate": {r.id: r.word_error_rate for r in runs if r},
            "sequence_accuracy": {r.id: r.sequence_accuracy for r in runs if r},
            "recording_count": {
                r.id: json.loads(r.metrics_json or "{}").get("aggregate", {}).get("recording_count")
                for r in runs if r
            },
        }
        return {"runs": runs, "comparison": comparison}
