import json
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.training import (
    ModelResponse,
    ResetExecuteRequest,
    ResetPreviewRequest,
    StartTrainingRequest,
    TrainingJobResponse,
    TrainingPreview,
)
from app.services.model_registry import ModelRegistryService
from app.services.reset_service import ResetService
from app.services.training_service import TrainingService

router = APIRouter(tags=["training"])


def _job_response(job) -> TrainingJobResponse:
    return TrainingJobResponse(
        id=job.id,
        name=job.name,
        status=job.status,
        dataset_id=job.dataset_id,
        model_id=job.model_id,
        training_mode=job.training_mode,
        current_epoch=job.current_epoch,
        total_epochs=job.total_epochs,
        train_loss=job.train_loss,
        val_loss=job.val_loss,
        val_wer=job.val_wer,
        message=job.message,
        pid=job.pid,
        started_at=job.started_at,
        completed_at=job.completed_at,
        created_at=job.created_at,
        config=json.loads(job.config_json or "{}"),
    )


def _model_response(m) -> ModelResponse:
    vocab = json.loads(m.vocabulary_json or "[]")
    if isinstance(vocab, dict):
        vocab = [v for v in vocab.get("labels", []) if v != "<blank>"]
    return ModelResponse(
        id=m.id,
        name=m.name,
        version=m.version,
        status=m.status,
        architecture=m.architecture,
        dataset_id=m.dataset_id,
        dataset_version=m.dataset_version,
        provenance=m.provenance,
        training_job_id=m.training_job_id,
        validation_metrics=json.loads(m.validation_metrics_json or "{}"),
        vocabulary=vocab if isinstance(vocab, list) else [],
        emotion_available=m.emotion_available,
        is_archived=m.is_archived,
        created_at=m.created_at,
        notes=m.notes,
    )


@router.get("/training/preview/{dataset_id}", response_model=TrainingPreview)
def preview_training(dataset_id: int, db: Session = Depends(get_db)) -> TrainingPreview:
    try:
        return TrainingPreview(**TrainingService(db).preview_training(dataset_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/training/start", response_model=TrainingJobResponse)
def start_training(payload: StartTrainingRequest, db: Session = Depends(get_db)) -> TrainingJobResponse:
    try:
        job = TrainingService(db).start_training(payload.model_dump())
        return _job_response(job)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/training/jobs", response_model=list[TrainingJobResponse])
def list_jobs(db: Session = Depends(get_db)) -> list[TrainingJobResponse]:
    return [_job_response(j) for j in TrainingService(db).list_jobs()]


@router.get("/training/jobs/{job_id}", response_model=TrainingJobResponse)
def get_job(job_id: int, db: Session = Depends(get_db)) -> TrainingJobResponse:
    job = TrainingService(db).get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_response(job)


@router.post("/training/jobs/{job_id}/cancel", response_model=TrainingJobResponse)
def cancel_job(job_id: int, db: Session = Depends(get_db)) -> TrainingJobResponse:
    try:
        return _job_response(TrainingService(db).cancel_job(job_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/models", response_model=list[ModelResponse])
def list_models(include_archived: bool = False, db: Session = Depends(get_db)) -> list[ModelResponse]:
    return [_model_response(m) for m in ModelRegistryService(db).list_models(include_archived)]


@router.get("/models/{model_id}", response_model=ModelResponse)
def get_model(model_id: int, db: Session = Depends(get_db)) -> ModelResponse:
    m = ModelRegistryService(db).get_model(model_id)
    if not m:
        raise HTTPException(status_code=404, detail="Model not found")
    return _model_response(m)


@router.post("/models/{model_id}/activate", response_model=ModelResponse)
def activate_model(model_id: int, db: Session = Depends(get_db)) -> ModelResponse:
    try:
        return _model_response(ModelRegistryService(db).activate_model(model_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/models/{model_id}/export")
def export_model(model_id: int, db: Session = Depends(get_db)) -> FileResponse:
    try:
        dest = Path(tempfile.gettempdir()) / f"slsl_model_{model_id}.zip"
        path = ModelRegistryService(db).export_bundle(model_id, dest)
        return FileResponse(path, filename=path.name, media_type="application/zip")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/models/{model_id}/archive", response_model=ModelResponse)
def archive_model(model_id: int, db: Session = Depends(get_db)) -> ModelResponse:
    try:
        return _model_response(ModelRegistryService(db).archive_model(model_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/training/reset/preview")
def reset_preview(payload: ResetPreviewRequest, db: Session = Depends(get_db)) -> dict:
    return ResetService(db).preview_reset(payload.model_dump())


@router.post("/training/reset/execute")
def reset_execute(payload: ResetExecuteRequest, db: Session = Depends(get_db)) -> dict:
    try:
        return ResetService(db).execute_reset(payload.model_dump(), payload.confirmation)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
