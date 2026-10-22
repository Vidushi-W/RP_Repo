"""Train the kinematic classifier and evaluate on held-out recording groups."""

from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from backend.dataset_schema import ensure_current_dataset_schema
from backend.ml_features import FEATURE_NAMES


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "data" / "kinematic_dataset.csv"
DEFAULT_MODEL = ROOT / "kinematic_error_classifier.pkl"
METADATA_COLUMNS = {"label", "sign_id", "signer_id", "session_id", "frame_index"}
MIN_SESSION_ACCURACY = 0.45
MIN_SESSIONS_PER_CLASS = 3
MIN_SIGNERS = 1


def _make_pipeline(seed: int) -> Pipeline:
    preprocessor = ColumnTransformer(
        [
            ("numeric", "passthrough", list(FEATURE_NAMES)),
            ("sign", OneHotEncoder(handle_unknown="ignore"), ["sign_id"]),
        ],
        remainder="drop",
    )
    return Pipeline([
        ("features", preprocessor),
        ("classifier", RandomForestClassifier(
            n_estimators=400,
            class_weight="balanced_subsample",
            min_samples_leaf=2,
            max_features="sqrt",
            random_state=seed,
            n_jobs=-1,
        )),
    ])


def _session_summary(data: pd.DataFrame, predictions: np.ndarray) -> pd.DataFrame:
    evaluated = data[["session_id", "label"]].copy()
    evaluated["prediction"] = predictions
    rows = []
    for session_id, group in evaluated.groupby("session_id", sort=False):
        labels = group["label"].astype(str).unique()
        if len(labels) != 1:
            raise ValueError(f"Session {session_id!r} contains multiple labels; split captures by label.")
        counts = group["prediction"].value_counts()
        rows.append({
            "session_id": str(session_id),
            "label": labels[0],
            "prediction": str(counts.index[0]),
            "frames": int(len(group)),
        })
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if not args.data.exists():
        raise FileNotFoundError(f"Dataset not found: {args.data}. Run python -m frontend.collect_data first.")
    ensure_current_dataset_schema(args.data)
    data = pd.read_csv(args.data)
    required = METADATA_COLUMNS | set(FEATURE_NAMES)
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"Dataset is missing required columns: {', '.join(sorted(missing))}")
    data = data.dropna(subset=["label", "sign_id", "signer_id", "session_id", *FEATURE_NAMES]).reset_index(drop=True)
    data["label"] = data["label"].astype(str)
    data["sign_id"] = data["sign_id"].astype(str)
    data["signer_id"] = data["signer_id"].astype(str)
    data["session_id"] = data["session_id"].astype(str)
    labels = data["label"]

    session_label_counts = data.groupby("session_id")["label"].nunique()
    if (session_label_counts != 1).any():
        raise ValueError("Each capture session must contain a single label. Re-collect mixed-label sessions separately.")
    class_sessions = data.groupby("label")["session_id"].nunique().sort_index()
    if class_sessions.min() < 2:
        raise ValueError("Each label needs at least two separate capture sessions for group-held-out evaluation.")

    # With multiple signers, test generalization to unseen people. With one
    # signer, keep whole capture sessions together and report that limitation.
    group_column = "signer_id" if data["signer_id"].nunique() > 1 else "session_id"
    groups = data[group_column].astype(str)
    n_splits = min(3, int(groups.nunique()))
    if n_splits < 2:
        raise ValueError("Need at least two independent evaluation groups.")
    splitter = GroupKFold(n_splits=n_splits)
    feature_frame = data[[*FEATURE_NAMES, "sign_id"]]
    oof_predictions = np.empty(len(data), dtype=object)
    fold_accuracies: list[float] = []
    for fold, (train_index, test_index) in enumerate(splitter.split(feature_frame, labels, groups), start=1):
        train_labels = set(labels.iloc[train_index])
        missing_train_labels = set(labels.unique()) - train_labels
        if missing_train_labels:
            raise ValueError(
                f"Fold {fold} training data misses labels {sorted(missing_train_labels)}. "
                "Collect those labels in more independent groups before training."
            )
        fold_model = _make_pipeline(args.seed)
        fold_model.fit(feature_frame.iloc[train_index], labels.iloc[train_index])
        fold_prediction = fold_model.predict(feature_frame.iloc[test_index])
        oof_predictions[test_index] = fold_prediction
        fold_accuracies.append(float(accuracy_score(labels.iloc[test_index], fold_prediction)))

    frame_accuracy = float(accuracy_score(labels, oof_predictions))
    session_results = _session_summary(data, oof_predictions)
    session_accuracy = float(accuracy_score(session_results["label"], session_results["prediction"]))
    session_report = classification_report(
        session_results["label"], session_results["prediction"],
        labels=sorted(labels.unique()), output_dict=True, zero_division=0,
    )
    per_class_session_recall = {
        label: float(session_report.get(label, {}).get("recall", 0.0))
        for label in sorted(labels.unique())
    }
    signer_count = int(data["signer_id"].nunique())
    approved = (
        session_accuracy >= MIN_SESSION_ACCURACY
        and int(class_sessions.min()) >= MIN_SESSIONS_PER_CLASS
        and signer_count >= MIN_SIGNERS
        and all(recall >= MIN_SESSION_ACCURACY for recall in per_class_session_recall.values())
    )

    print(f"Grouped cross-validation: {n_splits} folds, grouped by {group_column}")
    print(f"Out-of-fold frame accuracy: {frame_accuracy * 100:.2f}%")
    print(f"Mean fold frame accuracy: {np.mean(fold_accuracies) * 100:.2f}%")
    print(f"Whole-session majority accuracy: {session_accuracy * 100:.2f}% ({len(session_results)} sessions)")
    print("Session-level classification report:")
    print(classification_report(
        session_results["label"], session_results["prediction"],
        labels=sorted(labels.unique()), zero_division=0,
    ))
    print("Session confusion matrix (rows=true, columns=predicted):")
    print(confusion_matrix(
        session_results["label"], session_results["prediction"],
        labels=sorted(labels.unique()),
    ))
    print("Sessions per class:")
    print(class_sessions.to_string())
    print(f"Unique signers: {signer_count}")

    final_model = _make_pipeline(args.seed)
    final_model.fit(feature_frame, labels)
    evaluation = {
        "split": f"group_kfold_{group_column}_holdout",
        "folds": n_splits,
        "held_out_groups": int(groups.nunique()),
        "oof_frame_accuracy": frame_accuracy,
        "mean_fold_frame_accuracy": float(np.mean(fold_accuracies)),
        "session_accuracy": session_accuracy,
        "session_macro_f1": float(session_report["macro avg"]["f1-score"]),
        "session_count": int(len(session_results)),
        "sessions_per_class": {key: int(value) for key, value in class_sessions.items()},
        "session_class_recall": per_class_session_recall,
        "signer_count": signer_count,
        "deployment_approved": bool(approved),
        "approval_requirements": {
            "session_accuracy": MIN_SESSION_ACCURACY,
            "per_class_session_recall": MIN_SESSION_ACCURACY,
            "sessions_per_class": MIN_SESSIONS_PER_CLASS,
            "signers": MIN_SIGNERS,
        },
    }
    bundle = {
        "pipeline": final_model,
        "sign_ids": sorted(data["sign_id"].unique().tolist()),
        "labels": sorted(labels.unique().tolist()),
        "feature_names": FEATURE_NAMES,
        "evaluation": evaluation,
    }
    args.model.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, args.model)
    print(f"Saved full-data research model: {args.model}")
    if not approved:
        print("Live inference remains disabled: validation/data coverage does not meet approval requirements.")


if __name__ == "__main__":
    main()
