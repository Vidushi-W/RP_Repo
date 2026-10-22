"""Read and repair versioned CSV headers for collected kinematic features."""

from __future__ import annotations

import csv
import os
import shutil
import tempfile
from pathlib import Path

import numpy as np

from backend.ml_features import FEATURE_NAMES


METADATA_FIELDS = ["label", "sign_id", "signer_id", "session_id", "frame_index"]
CURRENT_FIELDS = [*METADATA_FIELDS, *FEATURE_NAMES]
LEGACY_FIELDS = [*METADATA_FIELDS, *FEATURE_NAMES[:-3]]


def _derive_palm_normal(row: list[str], columns: dict[str, int]) -> list[str]:
    """Reconstruct appended palm-normal values for rows from the old schema."""
    points = np.asarray(
        [float(row[columns[f"lm_{index}_{axis}"]]) for index in range(21) for axis in "xyz"],
        dtype=np.float32,
    ).reshape(21, 3)
    normal = np.cross(points[5] - points[0], points[17] - points[0])
    length = float(np.linalg.norm(normal))
    if not np.isfinite(length) or length <= np.finfo(np.float32).eps:
        raise ValueError("Cannot derive palm-normal features from this CSV row's landmarks")
    normal /= length
    return [format(float(value), ".9g") for value in normal]


def ensure_current_dataset_schema(path: Path) -> None:
    """Repair the old header/row-width mismatch without losing original data.

    Earlier captures can have 78 features while newer captures already contain
    81. The CSV schema always has 81 columns after metadata; missing palm-normal
    values are reconstructed from the normalized landmark coordinates.
    """
    if not path.exists() or path.stat().st_size == 0:
        return
    with path.open("r", newline="", encoding="utf-8") as source:
        reader = csv.reader(source)
        header = next(reader, [])
        rows = [row for row in reader if row]

    if header not in (CURRENT_FIELDS, LEGACY_FIELDS):
        raise ValueError(
            "Unrecognized dataset columns. Back up the CSV and check that it was "
            "created by this Component 3 data collector."
        )
    legacy_index = {name: index for index, name in enumerate(LEGACY_FIELDS)}
    migrated_rows: list[list[str]] = []
    for row_number, row in enumerate(rows, start=2):
        if len(row) == len(CURRENT_FIELDS):
            migrated_rows.append(row)
        elif len(row) == len(LEGACY_FIELDS):
            normal = _derive_palm_normal(row, legacy_index)
            migrated_rows.append([*row, *normal])
        else:
            raise ValueError(
                f"Dataset row {row_number} has {len(row)} values; expected "
                f"{len(LEGACY_FIELDS)} or {len(CURRENT_FIELDS)}. No changes were made."
            )

    if header == CURRENT_FIELDS and all(len(row) == len(CURRENT_FIELDS) for row in rows):
        return

    backup = path.with_name(path.name + ".pre_schema_migration.bak")
    if backup.exists():
        backup = path.with_name(path.name + ".pre_schema_migration_2.bak")
    shutil.copy2(path, backup)
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", newline="", encoding="utf-8", dir=path.parent,
            prefix=path.stem + ".", suffix=".tmp", delete=False,
        ) as destination:
            temporary_path = destination.name
            writer = csv.writer(destination)
            writer.writerow(CURRENT_FIELDS)
            writer.writerows(migrated_rows)
        os.replace(temporary_path, path)
    except Exception:
        if temporary_path and os.path.exists(temporary_path):
            os.unlink(temporary_path)
        raise
    print(
        f"Updated dataset schema for {len(migrated_rows)} rows. "
        f"Original backed up to {backup.name}."
    )
