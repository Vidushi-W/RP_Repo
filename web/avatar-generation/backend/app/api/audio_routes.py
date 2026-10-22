"""Bounded non-overlapping PCM speech windows over a local WebSocket."""
import asyncio
import base64
import hashlib
import json
import uuid
import threading
from collections import OrderedDict
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ConfigDict, Field, StrictInt
from app.services.live_pipeline import pipeline
from app.services.ollama_provider import AgentUnavailable
from app.services.speech import SpeechUnavailable

router = APIRouter()
PROCESS_SLOT = asyncio.Semaphore(1)
SESSIONS = set()


class AudioWindow(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    type: str = Field(pattern='^audio$')
    seq: StrictInt = Field(ge=0)
    startMs: StrictInt = Field(ge=0, le=86_400_000)
    pcm16: str = Field(max_length=350000)

    def decode(self):
        pcm = base64.b64decode(self.pcm16, validate=True)
        if len(pcm) % 2 or not 12800 <= len(pcm) <= 256000:
            raise ValueError('Invalid PCM window')
        return pcm


class AudioOrder:
    def __init__(self):
        self.previous_seq = -1
        self.previous_end = 0
        self.seen = OrderedDict()

    def accept(self, window, pcm):
        digest = hashlib.sha256(pcm).hexdigest()
        if window.seq in self.seen:
            if self.seen[window.seq] != digest:
                raise ValueError('Changed duplicate audio window')
            return False
        if window.seq <= self.previous_seq or window.startMs < self.previous_end:
            raise ValueError('Speech windows must be ordered and non-overlapping')
        self.previous_seq, self.previous_end = window.seq, window.startMs + len(pcm) / 32
        self.seen[window.seq] = digest
        while len(self.seen) > 32:
            self.seen.popitem(last=False)
        return True


@router.websocket('/audio/live')
async def live_audio(ws: WebSocket):
    # A browser on another site must not use this localhost speech service.
    if ws.headers.get('origin') not in ('http://127.0.0.1:5173', 'http://localhost:5173', 'http://127.0.0.1:8000', 'http://localhost:8000'):
        await ws.close(code=1008)
        return
    if len(SESSIONS) >= 2:
        await ws.close(code=1013)
        return
    await ws.accept()
    session = uuid.uuid4().hex
    SESSIONS.add(session)
    pending = asyncio.Queue(maxsize=3)
    cancel = threading.Event()

    async def worker():
        order = AudioOrder()
        while True:
            window = await pending.get()
            pcm = window.decode()
            if not order.accept(window, pcm):
                await ws.send_json({'type': 'ack', 'seq': window.seq, 'duplicate': True})
                continue
            async with PROCESS_SLOT:
                try:
                    work = asyncio.create_task(asyncio.to_thread(pipeline.process, pcm, window.startMs, window.seq, session, cancel))
                    try:
                        result = await asyncio.shield(work)
                    except asyncio.CancelledError:
                        # Keep the global slot until native work releases its CPU/model
                        # resources; the cancel flag prevents starting another stage.
                        await work
                        raise
                    result['session'] = session
                    await ws.send_json(result)
                except (AgentUnavailable, SpeechUnavailable) as error:
                    pipeline.log({'type': 'service-unavailable', 'session': session, 'seq': window.seq, 'error': str(error)})
                    await ws.send_json({'type': 'error', 'message': 'The local speech or sign service is not ready. Please restart it and try again.', 'fatal': True})
                    await ws.close(code=1011)
                    return
                except (ValueError, OSError):
                    pipeline.log({'type': 'selection-rejected', 'session': session, 'seq': window.seq})
                    await ws.send_json({'type': 'error', 'message': 'This speech could not be matched safely. Please try a shorter phrase.', 'fatal': False, 'seq': window.seq})

    task = asyncio.create_task(worker())
    receive = None
    try:
        await ws.send_json({'type': 'ready'})
        while not task.done():
            receive = asyncio.create_task(ws.receive_text())
            done, _ = await asyncio.wait([receive, task], return_when=asyncio.FIRST_COMPLETED)
            if task in done:
                receive.cancel()
                task.result()
                break
            raw = receive.result()
            if len(raw) > 350500:
                raise ValueError('Audio window too large')
            window = AudioWindow.model_validate_json(raw)
            window.decode()
            if pending.full():
                await ws.send_json({'type': 'error', 'message': 'Speech is arriving too quickly. Stop and try shorter phrases with pauses.', 'fatal': True})
                await ws.close(code=1013)
                break
            pending.put_nowait(window)
    except (WebSocketDisconnect, RuntimeError):
        pass
    except (ValueError, json.JSONDecodeError):
        await ws.close(code=1008)
    finally:
        cancel.set()
        task.cancel()
        if receive is not None:
            receive.cancel()
        await asyncio.gather(*([task, receive] if receive is not None else [task]), return_exceptions=True)
        SESSIONS.discard(session)
        # In-flight native inference can finish, but cannot enqueue after disconnect.


class PlaybackMetrics(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    session: str = Field(pattern='^[a-f0-9]{32}$')
    seq: StrictInt = Field(ge=0)
    signId: str = Field(pattern='^[A-Z0-9_]{1,64}$')
    captureWindowMs: float = Field(ge=0, le=8000, allow_inf_nan=False)
    preparationMs: float = Field(ge=0, le=300000, allow_inf_nan=False)
    firstRecordedHandMs: float = Field(ge=0, le=3600000, allow_inf_nan=False)
    animationDurationMs: float = Field(gt=0, le=300000, allow_inf_nan=False)


@router.post('/audio/metrics')
def playback_metrics(metrics: PlaybackMetrics):
    pipeline.log({'type': 'playback-metrics', **metrics.model_dump(),
                  'clock': 'client monotonic; delay measured from estimated speech-window start'})
    return {'status': 'recorded'}
