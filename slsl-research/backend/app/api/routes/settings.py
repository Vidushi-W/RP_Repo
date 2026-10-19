from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.settings import SettingsUpdate, StudioSettings
from app.services.settings_service import SettingsService

router = APIRouter(tags=["settings"])


@router.get("/settings", response_model=StudioSettings)
def get_settings(db: Session = Depends(get_db)) -> StudioSettings:
    return StudioSettings(**SettingsService(db).get_settings())


@router.patch("/settings", response_model=StudioSettings)
def update_settings(payload: SettingsUpdate, db: Session = Depends(get_db)) -> StudioSettings:
    try:
        patch = {k: v for k, v in payload.model_dump().items() if v is not None}
        return StudioSettings(**SettingsService(db).update_settings(patch))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/settings/export")
def export_metadata(db: Session = Depends(get_db)) -> JSONResponse:
    data = SettingsService(db).export_metadata()
    return JSONResponse(content=data)
