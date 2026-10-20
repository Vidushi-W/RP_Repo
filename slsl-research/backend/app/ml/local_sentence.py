"""Offline spoken-English suggestions from model predictions only."""
from collections import Counter
from dataclasses import asdict, dataclass
from functools import lru_cache
import json
import logging
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time

from app.core.config import settings

LOGGER = logging.getLogger(__name__)
MODEL_NAME = 'Qwen2.5-0.5B-Instruct (local CPU)'
_LOCK = threading.Lock()
GRAMMAR_WORDS = set('a an the am is are be been being to of at in on for with by and as'.split())
CONTRACTIONS = {"i'm": 'i am', "you're": 'you are', "we're": 'we are', "they're": 'they are',
    "it's": 'it is', "isn't": 'is not', "aren't": 'are not', "don't": 'do not',
    "doesn't": 'does not', "can't": 'can not', "cannot": 'can not', "won't": 'will not'}
INFLECTIONS = {'goes': 'go', 'has': 'have', 'does': 'do', 'wants': 'want', 'needs': 'need',
    'likes': 'like', 'drinks': 'drink', 'eats': 'eat', 'walks': 'walk', 'works': 'work', 'studies': 'study'}


@dataclass(frozen=True)
class SpokenSentence:
    text: str
    status: str
    message: str
    model_name: str = MODEL_NAME
    generation_ms: float = 0.

    def to_dict(self):
        return asdict(self)


def _content_words(text):
    text = text.lower().replace('\u2019', "'")
    for contraction, expanded in CONTRACTIONS.items():
        text = re.sub(r'\b' + re.escape(contraction) + r'\b', expanded, text)
    words = re.findall(r"[a-z]+(?:'[a-z]+)?|\d+(?:\.\d+)?", text)
    return Counter(INFLECTIONS.get(word, word) for word in words if word not in GRAMMAR_WORDS)


def validate_suggestion(tokens, sentence):
    """Reject added/dropped content, changed pronouns/numbers/negation, and commentary.

    This is a lexical safeguard, not proof of semantic or SLSL equivalence.
    """
    sentence = sentence.strip().strip('"\u201c\u201d')
    if not sentence or len(sentence) > 400 or '\n' in sentence or ':' in sentence:
        return None
    if not re.fullmatch(r"[A-Za-z0-9\s.,!?;'\u2019\-]+", sentence):
        return None
    original = _content_words(' '.join(tokens))
    proposed = _content_words(sentence)
    # English negation needs an auxiliary: I NOT WANT FOOD -> I do not want food.
    normalized = sentence.lower().replace("don't", 'do not').replace("doesn't", 'does not')
    if (original['not'] and proposed['do'] == original['do'] + 1
            and re.search(r'\b(?:do|does)\s+not\b', normalized)):
        proposed['do'] -= 1
        if not proposed['do']:
            del proposed['do']
    if original != proposed:
        return None
    if not sentence.endswith(('.', '!', '?')):
        sentence += '.'
    return sentence[0].upper() + sentence[1:]


@lru_cache(maxsize=128)
def _run_local_model(tokens, model_dir, model_stamp):
    env = os.environ.copy()
    env.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1',
        TOKENIZERS_PARALLELISM='false', OMP_NUM_THREADS='2', MKL_NUM_THREADS='2')
    kwargs = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
    result = subprocess.run([sys.executable, '-B', str(Path(__file__).with_name('local_sentence_worker.py'))],
        input=json.dumps(dict(tokens=list(tokens), model_dir=model_dir)),
        capture_output=True, text=True, encoding='utf-8', env=env,
        timeout=settings.sentence_timeout_seconds, **kwargs)
    if result.returncode:
        LOGGER.error('Local sentence worker failed: %s', result.stderr[-1500:])
        raise RuntimeError('Local sentence worker failed')
    return json.loads(result.stdout)['sentence']


def generate_spoken_sentence(tokens: list[str], uncertain: bool = False) -> SpokenSentence:
    if not tokens:
        return SpokenSentence('', 'empty', 'No words were recognized. Try another motion recording.')
    if uncertain:
        return SpokenSentence('', 'uncertain', 'Motion recognition is uncertain. Repeat the motion before forming a sentence.')
    if len(tokens) > 64 or any(not isinstance(token, str) or not token.strip() or len(token) > 80 for token in tokens):
        return SpokenSentence('', 'unsupported', 'The recognized word sequence is too long or invalid.')
    if any(token.upper().startswith('SOURCE1 ') or not re.fullmatch(r"[A-Za-z0-9 '\-.,]+", token) for token in tokens):
        return SpokenSentence('', 'unsupported', 'These labels do not have verified English meanings. Showing the recognized labels without guessing a translation.')
    directory = settings.sentence_model_dir.resolve()
    weights = directory/'model.safetensors'
    if not weights.is_file() or not (directory/'config.json').is_file():
        return SpokenSentence('', 'unavailable', 'The local sentence model is not installed. Run scripts/setup_sentence_model.py; recognized words are still available.')
    if not _LOCK.acquire(blocking=False):
        return SpokenSentence('', 'busy', 'The local sentence model is processing another request. Try again shortly.')
    started = time.perf_counter()
    try:
        text = _run_local_model(tuple(tokens), str(directory), weights.stat().st_mtime_ns)
        validated = validate_suggestion(tokens, text)
        elapsed = (time.perf_counter()-started)*1000
        if not validated:
            return SpokenSentence('', 'unsupported', 'The AI suggestion changed or omitted recognized content, so it was not used. The original words are preserved.', generation_ms=elapsed)
        return SpokenSentence(validated, 'suggested', 'AI-generated phrasing. Check it against the recognized words; this is not a verified SLSL translation.', generation_ms=elapsed)
    except subprocess.TimeoutExpired:
        return SpokenSentence('', 'timeout', 'Sentence generation took too long. The recognized words are preserved; you can try again.')
    except (OSError, RuntimeError, ValueError, KeyError, json.JSONDecodeError):
        LOGGER.exception('Unable to form a local sentence')
        return SpokenSentence('', 'unavailable', 'The local AI could not form a sentence. The recognized words are preserved; you can try again.')
    finally:
        _LOCK.release()
