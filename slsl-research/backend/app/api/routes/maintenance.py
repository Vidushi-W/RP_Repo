from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.maintenance import DeleteDatasetRequest, DeleteModelRequest, ResetDatabaseRequest
from app.services.maintenance_service import MaintenanceService

router = APIRouter(prefix="/maintenance", tags=["maintenance"])


@router.get("/storage")
def storage_summary(db: Session = Depends(get_db)) -> dict:
    return MaintenanceService(db).storage_summary()


@router.delete("/datasets/{dataset_id}")
def delete_dataset(dataset_id: int, payload: DeleteDatasetRequest, db: Session = Depends(get_db)) -> dict:
    try:
        return MaintenanceService(db).delete_dataset(dataset_id, payload.confirmation, payload.force)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/datasets/{dataset_id}/recordings/{recording_id}")
def delete_recording(dataset_id: int, recording_id: str, db: Session = Depends(get_db)) -> dict:
    try:
        return MaintenanceService(db).delete_recording(dataset_id, recording_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/training/jobs/{job_id}")
def delete_training_job(job_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        return MaintenanceService(db).delete_training_job(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/evaluations/{run_id}")
def delete_evaluation(run_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        return MaintenanceService(db).delete_evaluation(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/models/{model_id}")
def delete_model(model_id: int, payload: DeleteModelRequest, db: Session = Depends(get_db)) -> dict:
    try:
        return MaintenanceService(db).delete_model(model_id, payload.confirmation)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/recognition-history")
def clear_recognition_history(db: Session = Depends(get_db)) -> dict:
    return MaintenanceService(db).clear_recognition_history()


@router.delete("/evaluations")
def clear_evaluations(db: Session = Depends(get_db)) -> dict:
    return MaintenanceService(db).clear_evaluations()


@router.post("/reset-database")
def reset_database(payload: ResetDatabaseRequest, db: Session = Depends(get_db)) -> dict:
    try:
        return MaintenanceService(db).reset_database(payload.scope, payload.confirmation, payload.delete_files)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
