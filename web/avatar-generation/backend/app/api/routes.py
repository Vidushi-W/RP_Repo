from fastapi import APIRouter
router = APIRouter()
@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "pipeline": "not_implemented"}
