"""Local Sinhala translation/speech, separate from sensor recognition and scoring."""
from functools import lru_cache
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading

from app.core.config import settings
from app.ml.speech_styles import SPEECH_STYLES

LOGGER = logging.getLogger(__name__)
_WORKER_LOCK = threading.Lock()
TRANSLATOR = 'M2M100-418M (offline)'
VOICE = 'Dilu Sinhala / Piper (offline)'
SUPPORTED_EMOTIONS = {None, *(set(SPEECH_STYLES) - {'normal'})}


class SpeechUnavailable(ValueError):
    pass


def audio_directory(test_id):
    if not re.fullmatch(r'[a-zA-Z0-9_-]{1,128}', test_id):
        raise ValueError('Invalid test recording ID')
    return settings.data_dir / 'studio_speech' / test_id


def clear_audio(test_id):
    directory = audio_directory(test_id)
    if directory.exists():
        for file in directory.glob('*.wav'):
            file.unlink(missing_ok=True)


def _worker(request):
    if not _WORKER_LOCK.acquire(timeout=5):
        raise SpeechUnavailable('Local speech processing is busy. Please retry shortly.')
    try:
        env = os.environ.copy()
        env.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1',
            TOKENIZERS_PARALLELISM='false', OMP_NUM_THREADS='2', MKL_NUM_THREADS='2')
        kwargs = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
        result = subprocess.run([sys.executable, '-B', str(Path(__file__).with_name('sinhala_worker.py'))],
            input=json.dumps(request, ensure_ascii=True), capture_output=True, text=True,
            encoding='utf-8', timeout=settings.speech_timeout_seconds, env=env, **kwargs)
        if result.returncode:
            LOGGER.error('Sinhala worker failed: %s', result.stderr[-1800:])
            raise SpeechUnavailable('Local Sinhala processing failed. Please retry or check the installed models.')
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired as exc:
        raise SpeechUnavailable('Local Sinhala processing took too long. Please retry.') from exc
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        raise SpeechUnavailable('Local Sinhala processing is unavailable. Please check the installed models.') from exc
    finally:
        _WORKER_LOCK.release()


def _model_stamp(path):
    if not path.is_file():
        raise SpeechUnavailable('Sinhala models are not installed. Run backend/scripts/setup_sinhala_models.py.')
    return (path.stat().st_mtime_ns, path.stat().st_size)


@lru_cache(maxsize=256)
def _translate(text, model_dir, stamp):
    result = _worker(dict(action='translate', text=text, model_dir=model_dir))
    translated = result['text'].strip()
    if not translated or len(translated) > 1500 or not re.search(r'[\u0d80-\u0dff]', translated):
        raise SpeechUnavailable('The translator did not return Sinhala. Please retry.')
    return translated


def translate_sentence(text):
    if not isinstance(text, str) or not text.strip() or len(text) > 600:
        raise ValueError('A nonempty English sentence of at most 600 characters is required')
    directory = settings.translation_model_dir.resolve()
    return _translate(text.strip(), str(directory), _model_stamp(directory/'pytorch_model.bin'))


@lru_cache(maxsize=32)
def _speak(text, emotion, voice_dir, stamp):
    with tempfile.TemporaryDirectory(prefix='slsl-speech-') as temp:
        output = Path(temp)/'speech.wav'
        _worker(dict(action='speak', text=text, emotion=emotion, voice_dir=voice_dir, output_file=str(output)))
        audio = output.read_bytes()
    if len(audio) < 44 or audio[:4] != b'RIFF' or audio[8:12] != b'WAVE':
        raise SpeechUnavailable('Speech synthesis did not return valid WAV audio')
    return audio


def synthesize_sinhala(text, emotion=None):
    if emotion not in SUPPORTED_EMOTIONS:
        raise ValueError('This speaking emotion is not supported yet')
    if not isinstance(text, str) or not text.strip() or len(text) > 1500:
        raise ValueError('A Sinhala sentence is required')
    directory = settings.sinhala_voice_dir.resolve()
    stamp = _model_stamp(directory/'onnx'/'si_LK-dilu-medium.onnx')
    return _speak(text.strip(), emotion, str(directory), stamp)


def audio_filename(recognition_id, translation_id, text, emotion):
    key = json.dumps([recognition_id, translation_id, text, emotion, VOICE, 'style-v1'], ensure_ascii=True)
    return hashlib.sha256(key.encode()).hexdigest() + '.wav'
