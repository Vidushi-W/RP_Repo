import io
import json
import zipfile
from pathlib import Path

import pandas as pd
import pytest

from app.core.config import FEATURE_COLUMNS, SENSOR_COLUMNS
from app.services.manifest import map_manifest_columns, normalize_split
from app.services.split_service import assign_splits, validate_split_isolation
from app.services.synthetic_generator import SyntheticConfig, generate_synthetic_package
from app.services.zip_utils import safe_extract_zip
from app.sensors.csv_source import CsvRecordingSource, load_csv_to_recording
from app.ml.preprocessing import validate_dataframe


def _sample_csv_rows(n: int = 30) -> pd.DataFrame:
    rows = []
    for i in range(n):
        row = {c: 0.0 for c in SENSOR_COLUMNS}
        row["timestamp_ms"] = i * 20.0
        row["left_flex_1"] = 0.5
        row["right_flex_1"] = 0.4
        row["left_acc_z_g"] = 1.0
        row["right_acc_z_g"] = 1.0
        rows.append(row)
    return pd.DataFrame(rows)


def test_import_sets_recording_count(client, tmp_path):
    df = _sample_csv_rows()
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    create = client.post("/api/datasets", json={"name": "Count DS", "provenance": "synthetic"})
    ds_id = create.json()["id"]
    client.post(
        f"/api/datasets/{ds_id}/import",
        files={"files": ("rec_count.csv", buf.getvalue(), "text/csv")},
    )
    ds = client.get(f"/api/datasets/{ds_id}").json()
    assert ds["recording_count"] == 1
    recs = client.get(f"/api/datasets/{ds_id}/recordings").json()
    assert len(recs) == 1


def test_valid_csv_import(client, tmp_path):
    df = _sample_csv_rows()
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    create = client.post("/api/datasets", json={"name": "Test DS", "provenance": "synthetic"})
    ds_id = create.json()["id"]
    res = client.post(
        "/api/datasets/{}/import".format(ds_id),
        files={"files": ("rec_001.csv", buf.getvalue(), "text/csv")},
    )
    assert res.status_code == 200
    assert res.json()["imported"] == 1
    recs = client.get(f"/api/datasets/{ds_id}/recordings")
    assert len(recs.json()) == 1


def test_import_requires_files(client):
    create = client.post("/api/datasets", json={"name": "Empty Import"})
    ds_id = create.json()["id"]
    res = client.post(f"/api/datasets/{ds_id}/import", data={"bump_version": "false"})
    assert res.status_code == 422 or res.status_code == 400


def test_invalid_csv_rejected(client):
    create = client.post("/api/datasets", json={"name": "Bad DS"})
    ds_id = create.json()["id"]
    bad = io.BytesIO(b"timestamp_ms\n0\n")
    res = client.post(f"/api/datasets/{ds_id}/import", files={"files": ("bad.csv", bad.getvalue(), "text/csv")})
    assert res.status_code == 200
    assert res.json()["imported"] == 0


def test_zip_path_traversal_blocked(tmp_path):
    zpath = tmp_path / "evil.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("../escape.csv", "bad")
    with pytest.raises(ValueError, match="Unsafe|traversal"):
        safe_extract_zip(zpath, tmp_path / "out")


def test_manifest_mapping():
    df = pd.DataFrame([{"sample_id": "r1", "labels": "I|WATER", "split": "train"}])
    mapped = map_manifest_columns(df)
    assert "recording_id" in mapped.columns
    assert mapped.iloc[0]["ordered_sign_labels"] == "I|WATER"


def test_timestamp_ordering():
    df = _sample_csv_rows()
    df = df.sort_values("timestamp_ms", ascending=False)
    report = validate_dataframe(df)
    assert report.valid


def test_annotation_update(client):
    df = _sample_csv_rows()
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    ds = client.post("/api/datasets", json={"name": "Annot DS"}).json()
    client.post(f"/api/datasets/{ds['id']}/import", files={"files": ("rec_a.csv", buf.getvalue(), "text/csv")})
    res = client.put(
        f"/api/datasets/{ds['id']}/recordings/rec_a",
        json={
            "ordered_sign_labels": "I|NEED|WATER",
            "emotion_label": "neutral",
            "reference_english_sentence": "I need water.",
            "signer_id": "SYNTHETIC_SIGNER_01",
            "provenance": "synthetic",
            "split": "train",
        },
    )
    assert res.status_code == 200
    assert res.json()["ordered_sign_labels"] == "I|NEED|WATER"


def test_split_isolation():
    class Rec:
        def __init__(self, gid, split):
            self.group_id = gid
            self.recording_id = gid
            self.split = split
            self.content_hash = ""

    recs = [Rec("g1", "train"), Rec("g1", "test")]
    errors = validate_split_isolation(recs)
    assert errors


def test_synthetic_reproducibility(tmp_path):
    out1 = tmp_path / "a"
    out2 = tmp_path / "b"
    generate_synthetic_package(out1, SyntheticConfig(seed=7, total_recordings=10))
    generate_synthetic_package(out2, SyntheticConfig(seed=7, total_recordings=10))
    m1 = (out1 / "manifest.csv").read_text()
    m2 = (out2 / "manifest.csv").read_text()
    assert m1 == m2


def test_sensor_csv_has_no_labels():
    df = _sample_csv_rows()
    for col in ["ordered_sign_labels", "emotion_label", "english_sentence"]:
        assert col not in df.columns
    rec = load_csv_to_recording(io.BytesIO(df.to_csv(index=False).encode()))
    assert CsvRecordingSource(io.BytesIO(df.to_csv(index=False).encode())).source_type() == "csv_recording"
