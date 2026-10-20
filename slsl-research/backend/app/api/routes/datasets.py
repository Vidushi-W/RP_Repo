from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.dataset import (
    DatasetCreateRequest,
    DatasetSummary,
    DatasetValidationReport,
    ImportJobSchema,
    ImportPreviewItem,
    RecordingDetail,
    RecordingSummary,
    RecordingUpdate,
    SplitAssignRequest,
    SyntheticGenerateRequest,
)
from app.services.dataset_service import DatasetService

router = APIRouter(prefix="/datasets", tags=["datasets"])


def _to_summary(ds) -> DatasetSummary:
    return DatasetSummary(
        id=ds.id,
        name=ds.name,
        description=ds.description,
        provenance=ds.provenance,
        status=ds.status,
        current_version=ds.current_version,
        recording_count=ds.recording_count,
        created_at=ds.created_at,
        updated_at=ds.updated_at,
    )


@router.get("", response_model=list[DatasetSummary])
def list_datasets(db: Session = Depends(get_db)) -> list[DatasetSummary]:
    return [_to_summary(d) for d in DatasetService(db).list_datasets()]


@router.post("", response_model=DatasetSummary)
def create_dataset(payload: DatasetCreateRequest, db: Session = Depends(get_db)) -> DatasetSummary:
    ds = DatasetService(db).create_dataset(payload.name, payload.description, payload.provenance)
    return _to_summary(ds)


@router.get("/imports", response_model=list[ImportJobSchema])
def list_imports(db: Session = Depends(get_db)) -> list[ImportJobSchema]:
    jobs = DatasetService(db).list_import_jobs()
    return [
        ImportJobSchema(
            id=j.id,
            dataset_id=j.dataset_id,
            status=j.status,
            step=j.step,
            source_name=j.source_name,
            report=__import__("json").loads(j.report_json or "{}"),
            created_at=j.created_at,
        )
        for j in jobs
    ]


@router.post("/preview", response_model=list[ImportPreviewItem])
async def preview_files(files: list[UploadFile] = File(...), db: Session = Depends(get_db)) -> list[ImportPreviewItem]:
    previews = DatasetService(db).preview_csv_files(files)
    if not previews:
        raise HTTPException(status_code=400, detail="No previewable sensor CSV or ZIP files received.")
    return [ImportPreviewItem(**p) for p in previews]


@router.post("/generate-synthetic", response_model=DatasetSummary)
def generate_synthetic(payload: SyntheticGenerateRequest, db: Session = Depends(get_db)) -> DatasetSummary:
    try:
        ds = DatasetService(db).generate_synthetic(payload.model_dump())
        return _to_summary(ds)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{dataset_id}", response_model=DatasetSummary)
def get_dataset(dataset_id: int, db: Session = Depends(get_db)) -> DatasetSummary:
    ds = DatasetService(db).get_dataset(dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return _to_summary(ds)


@router.get("/{dataset_id}/recordings", response_model=list[RecordingSummary])
def list_recordings(dataset_id: int, db: Session = Depends(get_db)) -> list[RecordingSummary]:
    svc = DatasetService(db)
    if not svc.get_dataset(dataset_id):
        raise HTTPException(status_code=404, detail="Dataset not found")
    return [
        RecordingSummary(
            id=r.id,
            recording_id=r.recording_id,
            signer_id=r.signer_id,
            provenance=r.provenance,
            ordered_sign_labels=r.ordered_sign_labels,
            emotion_label=r.emotion_label,
            reference_english_sentence=r.reference_english_sentence,
            split=r.split,
            duration_ms=r.duration_ms,
            frame_count=r.frame_count,
            sample_rate_hz=r.sample_rate_hz,
        )
        for r in svc.repo.list_recordings(dataset_id)
    ]


@router.get("/{dataset_id}/recordings/{recording_id}", response_model=RecordingDetail)
def get_recording(dataset_id: int, recording_id: str, db: Session = Depends(get_db)) -> RecordingDetail:
    try:
        detail = DatasetService(db).get_recording_detail(dataset_id, recording_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    rec = detail["recording"]
    return RecordingDetail(
        id=rec.id,
        recording_id=rec.recording_id,
        signer_id=rec.signer_id,
        provenance=rec.provenance,
        ordered_sign_labels=rec.ordered_sign_labels,
        emotion_label=rec.emotion_label,
        reference_english_sentence=rec.reference_english_sentence,
        split=rec.split,
        duration_ms=rec.duration_ms,
        frame_count=rec.frame_count,
        sample_rate_hz=rec.sample_rate_hz,
        file_path=rec.file_path,
        collection_date=rec.collection_date,
        group_id=rec.group_id,
        validation=detail["validation"],
        visualization=detail["visualization"],
    )


@router.put("/{dataset_id}/recordings/{recording_id}", response_model=RecordingSummary)
def update_recording(
    dataset_id: int,
    recording_id: str,
    payload: RecordingUpdate,
    db: Session = Depends(get_db),
) -> RecordingSummary:
    try:
        rec = DatasetService(db).update_recording(dataset_id, recording_id, payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return RecordingSummary(
        id=rec.id,
        recording_id=rec.recording_id,
        signer_id=rec.signer_id,
        provenance=rec.provenance,
        ordered_sign_labels=rec.ordered_sign_labels,
        emotion_label=rec.emotion_label,
        reference_english_sentence=rec.reference_english_sentence,
        split=rec.split,
        duration_ms=rec.duration_ms,
        frame_count=rec.frame_count,
        sample_rate_hz=rec.sample_rate_hz,
    )


@router.post("/{dataset_id}/import")
async def import_dataset(
    dataset_id: int,
    files: list[UploadFile] = File(...),
    manifest: UploadFile | None = File(None),
    bump_version: bool = Form(False),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    svc = DatasetService(db)
    zip_files = [f for f in files if f.filename and f.filename.lower().endswith(".zip")]
    csv_files = [f for f in files if f.filename and f.filename.lower().endswith(".csv") and f.filename.lower() != "manifest.csv"]
    if not zip_files and not csv_files:
        raise HTTPException(status_code=400, detail="No importable files received. Upload sensor CSV files or a dataset ZIP.")
    try:
        if zip_files:
            return svc.import_zip(dataset_id, zip_files[0], bump_version=bump_version)
        return svc.import_files(dataset_id, csv_files, manifest, bump_version=bump_version)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{dataset_id}/splits", response_model=dict[str, int])
def assign_splits(dataset_id: int, payload: SplitAssignRequest, db: Session = Depends(get_db)) -> dict[str, int]:
    return DatasetService(db).assign_dataset_splits(
        dataset_id, payload.train_ratio, payload.val_ratio, payload.preserve_existing
    )


@router.post("/{dataset_id}/sync-count")
def sync_dataset_count(dataset_id: int, db: Session = Depends(get_db)) -> dict[str, int]:
    try:
        count = DatasetService(db).sync_recording_count(dataset_id)
        return {"recording_count": count}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{dataset_id}/repair-labels")
def repair_dataset_labels(dataset_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        return DatasetService(db).repair_syn_simulation_labels(dataset_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{dataset_id}/validation", response_model=DatasetValidationReport)
def validate_dataset(dataset_id: int, db: Session = Depends(get_db)) -> DatasetValidationReport:
    if not DatasetService(db).get_dataset(dataset_id):
        raise HTTPException(status_code=404, detail="Dataset not found")
    report = DatasetService(db).validate_dataset(dataset_id)
    return DatasetValidationReport(**report)
