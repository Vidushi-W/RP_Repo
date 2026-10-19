"""Dataset import, annotation, validation, and synthetic generation."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.ml.preprocessing import downsample_series, motion_magnitudes, validate_dataframe, validate_recording
from app.models.dataset import Dataset, DatasetVersion, ImportJob, Recording
from app.repositories.dataset import DatasetRepository
from app.services.manifest import map_manifest_columns, normalize_emotion, normalize_split
from app.services.split_service import assign_splits, save_split_manifest, validate_split_isolation
from app.services.synthetic_generator import SyntheticConfig, content_hash_for_file, generate_synthetic_package
from app.services.zip_utils import safe_extract_zip
from app.sensors.csv_source import CsvRecordingSource, load_csv_to_recording


class DatasetService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = DatasetRepository(db)

    def list_datasets(self) -> list[Dataset]:
        return self.repo.list_datasets()

    def get_dataset(self, dataset_id: int) -> Dataset | None:
        return self.repo.get_dataset(dataset_id)

    def create_dataset(self, name: str, description: str = "", provenance: str = "synthetic") -> Dataset:
        ds = Dataset(name=name, description=description, provenance=provenance, status="draft")
        self.db.add(ds)
        self.db.flush()
        version = DatasetVersion(dataset_id=ds.id, version="1.0.0", notes="Initial version")
        self.db.add(version)
        self.repo.add_activity("dataset_created", f"Created dataset '{name}'")
        self.db.commit()
        self.db.refresh(ds)
        return ds

    def _dataset_dir(self, dataset_id: int, version: str) -> Path:
        path = settings.datasets_dir / str(dataset_id) / version
        path.mkdir(parents=True, exist_ok=True)
        return path

    def preview_csv_files(self, files: list[UploadFile]) -> list[dict[str, Any]]:
        previews = []
        for f in files:
            content = f.file.read()
            f.file.seek(0)
            try:
                df = pd.read_csv(__import__("io").BytesIO(content))
                report = validate_dataframe(df)
                previews.append({
                    "filename": f.filename or "unknown.csv",
                    "valid": report.valid,
                    "errors": report.errors,
                    "warnings": report.warnings,
                    "frame_count": report.frame_count,
                    "duration_ms": report.duration_ms,
                })
            except Exception as exc:  # noqa: BLE001
                previews.append({"filename": f.filename or "unknown.csv", "valid": False, "errors": [str(exc)]})
        return previews

    def import_files(
        self,
        dataset_id: int,
        sensor_files: list[UploadFile],
        manifest_file: UploadFile | None = None,
        bump_version: bool = False,
    ) -> dict[str, Any]:
        ds = self.repo.get_dataset(dataset_id)
        if not ds:
            raise ValueError("Dataset not found")
        version = ds.current_version
        if bump_version:
            parts = version.split(".")
            version = f"{parts[0]}.{int(parts[1]) + 1}.0" if len(parts) >= 2 else "1.1.0"
            ds.current_version = version
            self.db.add(DatasetVersion(dataset_id=dataset_id, version=version, notes="Import version bump"))

        target_dir = self._dataset_dir(dataset_id, version) / "recordings"
        target_dir.mkdir(parents=True, exist_ok=True)
        manifest_df: pd.DataFrame | None = None
        if manifest_file:
            manifest_df = map_manifest_columns(pd.read_csv(manifest_file.file))

        imported = 0
        skipped = 0
        errors: list[str] = []
        for f in sensor_files:
            if not f.filename or not f.filename.lower().endswith(".csv"):
                continue
            content = f.file.read()
            rec_id = Path(f.filename).stem
            dest = target_dir / f"{rec_id}.csv"
            dest.write_bytes(content)
            chash = content_hash_for_file(dest)
            if self.repo.content_hash_exists(dataset_id, chash):
                skipped += 1
                dest.unlink(missing_ok=True)
                continue
            try:
                recording = load_csv_to_recording(dest, source_name=rec_id)
                report = validate_recording(recording)
                if not report.valid:
                    errors.append(f"{rec_id}: {report.errors}")
                    dest.unlink(missing_ok=True)
                    continue
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{rec_id}: {exc}")
                dest.unlink(missing_ok=True)
                continue

            meta = self._manifest_row(manifest_df, rec_id)
            rel_path = str(dest.relative_to(settings.data_dir)).replace("\\", "/")
            row = Recording(
                recording_id=rec_id,
                dataset_id=dataset_id,
                dataset_version=version,
                file_path=rel_path,
                signer_id=meta.get("signer_id", "UNKNOWN"),
                provenance=meta.get("provenance", ds.provenance),
                ordered_sign_labels=meta.get("ordered_sign_labels", ""),
                emotion_label=normalize_emotion(meta.get("emotion_label", "unknown")),
                reference_english_sentence=meta.get("reference_english_sentence", ""),
                split=normalize_split(meta.get("split", "unassigned")),
                collection_date=meta.get("collection_date"),
                group_id=meta.get("group_id", rec_id),
                content_hash=chash,
                duration_ms=report.duration_ms,
                frame_count=report.frame_count,
                sample_rate_hz=report.estimated_sample_rate_hz,
            )
            self.db.add(row)
            imported += 1

        ds.recording_count = len(self.repo.list_recordings(dataset_id))
        ds.status = "ready" if imported else ds.status
        job = ImportJob(dataset_id=dataset_id, status="completed", step="saved", source_name=f"{imported} files")
        job.report_json = json.dumps({"imported": imported, "skipped_duplicates": skipped, "errors": errors})
        self.db.add(job)
        self.repo.add_activity("dataset_import", f"Imported {imported} recordings into dataset '{ds.name}'")
        self.db.commit()
        return {"imported": imported, "skipped_duplicates": skipped, "errors": errors, "version": version}

    def import_zip(self, dataset_id: int, zip_file: UploadFile, bump_version: bool = False) -> dict[str, Any]:
        ds = self.repo.get_dataset(dataset_id)
        if not ds:
            raise ValueError("Dataset not found")
        with tempfile.TemporaryDirectory() as tmp:
            zpath = Path(tmp) / (zip_file.filename or "upload.zip")
            zpath.write_bytes(zip_file.file.read())
            extracted = safe_extract_zip(zpath, Path(tmp) / "extracted")
            csv_files = [p for p in extracted if p.suffix.lower() == ".csv" and p.name != "manifest.csv"]
            manifest = next((p for p in extracted if p.name.lower() in {"manifest.csv", "metadata.csv"}), None)
            uploads: list[UploadFile] = []
            for p in csv_files:
                uf = UploadFile(filename=p.name, file=open(p, "rb"))  # noqa: SIM115
                uploads.append(uf)
            manifest_upload = None
            if manifest:
                manifest_upload = UploadFile(filename=manifest.name, file=open(manifest, "rb"))  # noqa: SIM115
            result = self.import_files(dataset_id, uploads, manifest_upload, bump_version=bump_version)
            for uf in uploads:
                uf.file.close()
            if manifest_upload:
                manifest_upload.file.close()
            return result

    def _manifest_row(self, manifest_df: pd.DataFrame | None, recording_id: str) -> dict[str, str]:
        if manifest_df is None:
            return {}
        match = manifest_df[manifest_df["recording_id"].astype(str) == recording_id]
        if match.empty:
            return {}
        row = match.iloc[0]
        out: dict[str, str] = {}
        for col in manifest_df.columns:
            val = row[col]
            if pd.isna(val):
                continue
            out[col] = str(val)
        if "filepath" in out:
            out.pop("filepath", None)
        return out

    def get_recording_detail(self, dataset_id: int, recording_id: str) -> dict[str, Any]:
        rec = self.repo.get_recording(dataset_id, recording_id)
        if not rec:
            raise ValueError("Recording not found")
        path = settings.data_dir / rec.file_path
        recording = load_csv_to_recording(path, source_name=recording_id)
        report = validate_recording(recording)
        feats = recording.to_feature_matrix()
        ts = recording.timestamps()
        left, right = motion_magnitudes(feats)
        lts, lvals = downsample_series(ts, left)
        rts, rvals = downsample_series(ts, right)
        fts, flex_l = downsample_series(ts, feats[:, 0])
        _, flex_r = downsample_series(ts, feats[:, 11])
        return {
            "recording": rec,
            "validation": report.to_dict(),
            "visualization": {
                "left_motion": {"timestamps_ms": lts, "values": lvals},
                "right_motion": {"timestamps_ms": rts, "values": rvals},
                "left_flex_1": {"timestamps_ms": fts, "values": flex_l},
                "right_flex_1": {"timestamps_ms": fts, "values": flex_r},
            },
        }

    def update_recording(self, dataset_id: int, recording_id: str, payload: dict[str, Any]) -> Recording:
        rec = self.repo.get_recording(dataset_id, recording_id)
        if not rec:
            raise ValueError("Recording not found")
        rec.ordered_sign_labels = payload["ordered_sign_labels"]
        rec.emotion_label = normalize_emotion(payload["emotion_label"])
        rec.reference_english_sentence = payload.get("reference_english_sentence", "")
        rec.signer_id = payload["signer_id"]
        rec.provenance = payload["provenance"]
        rec.split = normalize_split(payload["split"])
        self.db.commit()
        self.db.refresh(rec)
        return rec

    def assign_dataset_splits(self, dataset_id: int, train_ratio: float, val_ratio: float, preserve: bool) -> dict[str, int]:
        recordings = self.repo.list_recordings(dataset_id)
        assign_splits(recordings, train_ratio=train_ratio, val_ratio=val_ratio, preserve_existing=preserve)
        ds = self.repo.get_dataset(dataset_id)
        if ds:
            manifest_path = self._dataset_dir(dataset_id, ds.current_version) / "split_manifest.json"
            save_split_manifest(recordings, manifest_path)
            ver = next((v for v in ds.versions if v.version == ds.current_version), None)
            if ver:
                ver.split_manifest_path = str(manifest_path.relative_to(settings.data_dir)).replace("\\", "/")
        self.db.commit()
        counts: dict[str, int] = {}
        for r in recordings:
            counts[r.split] = counts.get(r.split, 0) + 1
        return counts

    def validate_dataset(self, dataset_id: int) -> dict[str, Any]:
        recordings = self.repo.list_recordings(dataset_id)
        valid = 0
        invalid = 0
        issues: list[str] = []
        split_counts: dict[str, int] = {}
        for rec in recordings:
            split_counts[rec.split] = split_counts.get(rec.split, 0) + 1
            path = settings.data_dir / rec.file_path
            if not path.exists():
                invalid += 1
                issues.append(f"{rec.recording_id}: file missing")
                continue
            try:
                report = validate_recording(load_csv_to_recording(path))
                if report.valid:
                    valid += 1
                else:
                    invalid += 1
                    issues.append(f"{rec.recording_id}: {report.errors}")
            except Exception as exc:  # noqa: BLE001
                invalid += 1
                issues.append(f"{rec.recording_id}: {exc}")
        isolation = validate_split_isolation(recordings)
        return {
            "dataset_id": dataset_id,
            "recording_count": len(recordings),
            "valid_recordings": valid,
            "invalid_recordings": invalid,
            "split_counts": split_counts,
            "split_isolation_errors": isolation,
            "issues": issues[:50],
        }

    def generate_synthetic(self, req: dict[str, Any]) -> Dataset:
        ds = self.create_dataset(
            name=req["name"],
            description=req.get("description", ""),
            provenance="synthetic",
        )
        out_dir = self._dataset_dir(ds.id, ds.current_version)
        cfg = SyntheticConfig(seed=req.get("seed", 42), total_recordings=req.get("total_recordings", 400))
        generate_synthetic_package(out_dir, cfg)
        manifest = pd.read_csv(out_dir / "manifest.csv")
        recordings_dir = out_dir / "recordings"
        sensor_uploads: list[UploadFile] = []
        for p in sorted(recordings_dir.glob("*.csv")):
            sensor_uploads.append(UploadFile(filename=p.name, file=open(p, "rb")))  # noqa: SIM115
        manifest_upload = UploadFile(filename="manifest.csv", file=open(out_dir / "manifest.csv", "rb"))  # noqa: SIM115
        self.import_files(ds.id, sensor_uploads, manifest_upload)
        for uf in sensor_uploads:
            uf.file.close()
        manifest_upload.file.close()
        ds.status = "ready"
        self.db.commit()
        self.db.refresh(ds)
        return ds

    def list_import_jobs(self) -> list[ImportJob]:
        return self.repo.list_import_jobs()
