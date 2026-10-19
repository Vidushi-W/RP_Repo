from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.playground import (
    DictionaryResponse,
    LiveFinalizeResponse,
    LiveSessionCreate,
    LiveSessionResponse,
    LiveSpeedRequest,
    PlaygroundStatus,
    RecognitionMessage,
)
from app.services.live_session_service import live_session_store
from app.services.playground_service import PlaygroundService

router = APIRouter(tags=["playground"])


@router.get("/playground/status", response_model=PlaygroundStatus)
def playground_status(db: Session = Depends(get_db)) -> PlaygroundStatus:
    return PlaygroundStatus(**PlaygroundService(db).get_status())


@router.get("/playground/history")
def recognition_history(limit: int = 50, db: Session = Depends(get_db)) -> list[dict]:
    return PlaygroundService(db).list_history(limit)


@router.delete("/playground/history")
def clear_history(db: Session = Depends(get_db)) -> dict:
    return {"cleared": PlaygroundService(db).clear_history()}


@router.post("/playground/recognize", response_model=RecognitionMessage)
async def recognize_upload(
    file: UploadFile = File(...),
    model_id: int | None = Form(default=None),
    uncertainty_threshold: float = Form(default=0.25),
    db: Session = Depends(get_db),
) -> RecognitionMessage:
    try:
        data = await file.read()
        result = PlaygroundService(db).recognize_upload(
            data, file.filename or "upload.csv", model_id, uncertainty_threshold
        )
        if not result["validation"]["valid"]:
            raise ValueError(f"Invalid sensor CSV: {result['validation']['errors']}")
        return RecognitionMessage(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/playground/dictionary", response_model=DictionaryResponse)
def get_dictionary(model_id: int | None = None, db: Session = Depends(get_db)) -> DictionaryResponse:
    try:
        return DictionaryResponse(**PlaygroundService(db).get_dictionary(model_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/playground/live/session", response_model=LiveSessionResponse)
def create_live_session(payload: LiveSessionCreate, db: Session = Depends(get_db)) -> LiveSessionResponse:
    session = live_session_store.create(payload.source_type)
    try:
        model_id = None
        svc = PlaygroundService(db)
        _, bundle_dir = svc._resolve_model(model_id)
        live_session_store.attach_bundle(session.id, bundle_dir)
    except ValueError:
        pass
    return LiveSessionResponse(session_id=session.id, source_type=session.source_type)


@router.post("/playground/live/session/{session_id}/upload")
async def live_upload(session_id: str, file: UploadFile = File(...)) -> dict:
    try:
        data = await file.read()
        return live_session_store.upload_csv(session_id, data, file.filename or "playback.csv")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/playground/live/session/{session_id}/start")
def live_start(session_id: str, db: Session = Depends(get_db)) -> dict:
    try:
        svc = PlaygroundService(db)
        _, bundle_dir = svc._resolve_model(None)
        live_session_store.attach_bundle(session_id, bundle_dir)
        live_session_store.start(session_id)
        return {"status": "playing"}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/playground/live/session/{session_id}/pause")
def live_pause(session_id: str) -> dict:
    try:
        live_session_store.pause(session_id)
        return {"status": "paused"}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/playground/live/session/{session_id}/resume")
def live_resume(session_id: str) -> dict:
    try:
        live_session_store.resume(session_id)
        return {"status": "playing"}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/playground/live/session/{session_id}/stop")
def live_stop(session_id: str) -> dict:
    try:
        live_session_store.stop(session_id)
        return {"status": "stopped"}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/playground/live/session/{session_id}/reset")
def live_reset(session_id: str) -> dict:
    try:
        live_session_store.reset(session_id)
        return {"status": "idle"}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/playground/live/session/{session_id}/speed")
def live_speed(session_id: str, payload: LiveSpeedRequest) -> dict:
    try:
        live_session_store.set_speed(session_id, payload.speed)
        return {"speed": payload.speed}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/playground/live/session/{session_id}/tick")
def live_tick(session_id: str) -> dict:
    try:
        return live_session_store.tick(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/playground/live/session/{session_id}/finalize", response_model=LiveFinalizeResponse)
def live_finalize(session_id: str) -> LiveFinalizeResponse:
    try:
        message = live_session_store.finalize(session_id)
        return LiveFinalizeResponse(message=message)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
