"""Train and evaluate a Random Forest with whole capture sessions held out."""

from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from backend.ml_features import FEATURE_NAMES
from backend.dataset_schema import ensure_current_dataset_schema


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "data" / "kinematic_dataset.csv"
DEFAULT_MODEL = ROOT / "kinematic_error_classifier.pkl"
METADATA_COLUMNS = {"label", "sign_id", "signer_id", "session_id", "frame_index"}


def choose_session_split(data: pd.DataFrame, labels: pd.Series, groups: pd.Series, seed: int):
    """Find a group-disjoint split containing every class on both sides."""
    all_labels = set(labels.unique())
    splitter = GroupShuffleSplit(n_splits=100, test_size=0.25, random_state=seed)
    indices = np.arange(len(data))
    for train_index, test_index in splitter.split(data, labels, groups):
        if set(labels.iloc[train_index].unique()) == all_labels and set(labels.iloc[test_index].unique()) == all_labels:
            return train_index, test_index
    raise ValueError(
        "Could not form the selected group-independent split containing every label. "
        "Collect each class in at least two distinct captures (sessions); "
        "frames within one capture cannot count as independent train/test examples."
    )


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
    data = data.dropna(subset=["label", "sign_id", "session_id", *FEATURE_NAMES]).reset_index(drop=True)
    class_sessions = data.groupby("label")["session_id"].nunique().sort_index()
    print("Capture sessions per class:")
    print(class_sessions.to_string())
    labels = data["label"].astype(str)
    groups = data["session_id"].astype(str)
    group_column = "signer_id" if data["signer_id"].nunique() > 1 else "session_id"
    evaluation_groups = data[group_column].astype(str)
    train_index, test_index = choose_session_split(data, labels, evaluation_groups, args.seed)

    numeric = list(FEATURE_NAMES)
    preprocessor = ColumnTransformer(
        [("numeric", "passthrough", numeric), ("sign", OneHotEncoder(handle_unknown="ignore"), ["sign_id"])],
        remainder="drop",
    )
    model = Pipeline([
        ("features", preprocessor),
        ("classifier", RandomForestClassifier(
            n_estimators=300, class_weight="balanced", random_state=args.seed,
            min_samples_leaf=2, n_jobs=-1,
        )),
    ])
    feature_frame = data[[*numeric, "sign_id"]]
    model.fit(feature_frame.iloc[train_index], labels.iloc[train_index])
    predicted = model.predict(feature_frame.iloc[test_index])
    truth = labels.iloc[test_index]
    score = accuracy_score(truth, predicted)
    split_description = "signer-independent" if group_column == "signer_id" else "capture-session-held-out"
    print(f"\n{split_description} evaluation:")
    print(f"Held-out {group_column} groups: {evaluation_groups.iloc[test_index].nunique()}")
    qualifier = "" if group_column == "signer_id" else " (same signer may occur in train and test)"
    print(f"Test frame accuracy: {score * 100:.2f}%{qualifier}")
    print(classification_report(truth, predicted, labels=sorted(labels.unique()), zero_division=0))
    print("Confusion matrix (rows=true, columns=predicted):")
    print(confusion_matrix(truth, predicted, labels=sorted(labels.unique())))
    args.model.parent.mkdir(parents=True, exist_ok=True)
    bundle = {
        "pipeline": model,
        "sign_ids": sorted(data["sign_id"].astype(str).unique().tolist()),
        "labels": sorted(labels.unique().tolist()),
        "feature_names": FEATURE_NAMES,
        "evaluation": {
            "split": f"{group_column}_holdout",
            "test_frame_accuracy": float(score),
            "held_out_groups": int(evaluation_groups.iloc[test_index].nunique()),
        },
    }
    joblib.dump(bundle, args.model)
    print(f"Saved model: {args.model}")
    print("For a signer-independent result, collect multiple signers and hold out entire signer IDs.")


if __name__ == "__main__":
    main()
