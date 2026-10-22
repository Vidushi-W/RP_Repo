"""Offline CPU speech recognition; PCM is held only in memory."""
import os
import threading
from time import perf_counter
from app.services.sign_registry import ROOT


class SpeechUnavailable(RuntimeError):
    pass


class SpeechRecognizer:
    def __init__(self):
        self.model = None
        self.lock = threading.Lock()

    def transcribe(self, pcm, start_ms=0):
        import numpy as np
        audio = np.frombuffer(pcm, dtype='<i2').astype('float32') / 32768
        if not 6400 <= len(audio) <= 128000:
            raise ValueError('Speech windows must contain 0.4 to 8 seconds of mono 16 kHz PCM')
        if float(np.sqrt(np.mean(audio * audio))) < 0.003:
            return {'segments': [], 'latencyMs': 0, 'language': None, 'languageProbability': None}
        started = perf_counter()
        with self.lock:
            if self.model is None:
                from pathlib import Path
                path = Path(os.getenv('STT_MODEL_PATH', str(ROOT / 'preprocessing/models/faster-whisper-base'))).resolve()
                if not path.is_relative_to(ROOT) or not (path / 'model.bin').is_file():
                    raise SpeechUnavailable('Local speech model is missing. Run backend/scripts/setup_speech.py first.')
                try:
                    from faster_whisper import WhisperModel
                    self.model = WhisperModel(str(path), device='cpu', compute_type='int8', cpu_threads=2,
                                              num_workers=1, local_files_only=True)
                except Exception as error:
                    raise SpeechUnavailable('The local speech engine could not load. Check requirements-speech.txt and model files.') from error
            # Multilingual Whisper translates supported speech to English for Qwen.
            # Sinhala is supported by the model, but its reliability needs local evaluation.
            segments, info = self.model.transcribe(audio, task='translate', beam_size=1, best_of=1,
                vad_filter=True, vad_parameters={'min_silence_duration_ms': 500},
                condition_on_previous_text=False, word_timestamps=False)
            result = []
            for segment in segments:
                if segment.no_speech_prob > 0.6 or segment.avg_logprob < -1.0 or not segment.text.strip():
                    continue
                result.append({'text': segment.text.strip(), 'startMs': start_ms + round(segment.start * 1000),
                               'endMs': start_ms + round(segment.end * 1000), 'avgLogProbability': segment.avg_logprob,
                               'noSpeechProbability': segment.no_speech_prob})
            language = info.language
            probability = info.language_probability
        if language not in ('en', 'si'):
            result = []
        return {'segments': result, 'latencyMs': round((perf_counter() - started) * 1000, 2),
                'language': language, 'languageProbability': probability, 'task': 'offline speech-to-English'}


recognizer = SpeechRecognizer()
