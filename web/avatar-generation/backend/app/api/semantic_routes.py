from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from app.services.semantic_agent import AgentUnavailable, SemanticAgent
from app.services.sign_registry import Registry
from app.services.ollama_provider import OllamaProvider

router = APIRouter()


class Transcript(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    text: str = Field(min_length=1, max_length=4000)
    researchPreview: bool = False


@router.post('/agent/process')
def process_transcript(request: Transcript):
    try:
        return SemanticAgent(Registry(preview=request.researchPreview)).process(request.text)
    except AgentUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except (ValueError, OSError) as error:
        raise HTTPException(status_code=422, detail='Registry, recording or transcript validation failed. No playback was requested.') from error


@router.get('/agent/vocabulary')
def vocabulary():
    provider = OllamaProvider()
    return {'signs': Registry().available(), 'configured': True, 'provider': 'ollama', 'model': provider.model}


@router.get('/agent/status')
def agent_status():
    try:
        return OllamaProvider().status()
    except AgentUnavailable as error:
        return {'provider': 'ollama', 'reachable': False, 'modelAvailable': False, 'error': str(error)}
