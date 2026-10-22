import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.evaluation import (
    CompareEvaluationsResponse,
    EvalCompatibilityPreview,
    EvaluationResultsResponse,
    EvaluationRunResponse,
    StartEvaluationRequest,
)
from app.services.evaluation_service import EvaluationService

router = APIRouter(tags=["evaluation"])


def _run_response(run) -> EvaluationRunResponse:
    return EvaluationRunResponse(
        id=run.id,
        name=run.name,
        status=run.status,
        model_id=run.model_id,
        dataset_id=run.dataset_id,
        dataset_version=run.dataset_version,
        split_used=run.split_used,
        provenance=run.provenance,
        summary=run.summary,
        message=run.message,
        sequence_accuracy=run.sequence_accuracy,
        word_error_rate=run.word_error_rate,
        metrics=json.loads(run.metrics_json or "{}"),
        config=json.loads(run.config_json or "{}"),
        created_at=run.created_at,
        completed_at=run.completed_at,
    )


@router.get("/evaluation/preview", response_model=EvalCompatibilityPreview)
def preview_evaluation(
    model_id: int,
    dataset_id: int,
    split: str = "test",
    db: Session = Depends(get_db),
) -> EvalCompatibilityPreview:
    try:
        return EvalCompatibilityPreview(**EvaluationService(db).preview_compatibility(model_id, dataset_id, split))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/evaluation/run", response_model=EvaluationRunResponse)
def run_evaluation(payload: StartEvaluationRequest, db: Session = Depends(get_db)) -> EvaluationRunResponse:
    try:
        run = EvaluationService(db).run_evaluation(payload.model_dump())
        return _run_response(run)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/evaluation/runs", response_model=list[EvaluationRunResponse])
def list_runs(provenance: str | None = None, db: Session = Depends(get_db)) -> list[EvaluationRunResponse]:
    return [_run_response(r) for r in EvaluationService(db).list_runs(provenance)]


@router.get("/evaluation/runs/{run_id}", response_model=EvaluationRunResponse)
def get_run(run_id: int, db: Session = Depends(get_db)) -> EvaluationRunResponse:
    run = EvaluationService(db).get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Evaluation run not found")
    return _run_response(run)


@router.get("/evaluation/runs/{run_id}/results", response_model=EvaluationResultsResponse)
def get_results(run_id: int, db: Session = Depends(get_db)) -> EvaluationResultsResponse:
    svc = EvaluationService(db)
    run = svc.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Evaluation run not found")
    try:
        data = svc.get_results(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return EvaluationResultsResponse(
        run=_run_response(run),
        aggregate=data.get("aggregate", {}),
        emotion=data.get("emotion", {}),
        predictions=data.get("predictions", []),
        limitations=data.get("limitations", []),
    )


@router.get("/evaluation/compare", response_model=CompareEvaluationsResponse)
def compare_runs(ids: str = Query(..., description="Comma-separated evaluation run IDs"), db: Session = Depends(get_db)):
    try:
        run_ids = [int(x.strip()) for x in ids.split(",") if x.strip()]
        result = EvaluationService(db).compare_runs(run_ids)
        return CompareEvaluationsResponse(
            runs=[_run_response(r) for r in result["runs"]],
            comparison=result["comparison"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
