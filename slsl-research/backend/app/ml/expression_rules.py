"""User-configured expression annotation; not signer emotion recognition."""
from dataclasses import asdict, dataclass
import hashlib
import json
import re
import threading
import uuid

from app.core.config import settings

DEFAULT_ANGRY_WORDS = ['HATE', 'DIE', 'STOP', 'ENOUGH', 'ANNOYING', 'IDIOT', 'LOSER', 'DISGUST', 'STUPID']
RULE_SOURCE = 'configured_keyword_rule'
_LOCK = threading.RLock()


def normalize_word(word):
    return ' '.join(word.strip().upper().split())


def validate_rules(enabled, words):
    if not isinstance(enabled, bool) or not isinstance(words, list) or len(words) > 100:
        raise ValueError('Use an enabled flag and at most 100 trigger words.')
    normalized=[]
    for word in words:
        if not isinstance(word,str) or not 1 <= len(word.strip()) <= 80:
            raise ValueError('Each trigger must be a nonempty label, up to 80 characters.')
        word=normalize_word(word)
        if not re.fullmatch(r"[A-Z0-9]+(?:[ '\-][A-Z0-9]+)*",word):
            raise ValueError('Use label words or phrases; separate entries instead of using wildcards or punctuation.')
        if word not in normalized:normalized.append(word)
    return dict(enabled=enabled, words=normalized, emotion='angry', source=RULE_SOURCE)


def load_rules():
    path=settings.data_dir/'expression_rules.json'
    with _LOCK:
        if not path.exists():return validate_rules(True,DEFAULT_ANGRY_WORDS)
        try:
            data=json.loads(path.read_text(encoding='utf-8'))
            return validate_rules(data['enabled'],data['words'])
        except (OSError, ValueError, TypeError, KeyError) as exc:
            raise ValueError('Expression settings could not be read. Save the expression rule again to replace the invalid settings.') from exc


def save_rules(enabled,words):
    rules=validate_rules(enabled,words)
    path=settings.data_dir/'expression_rules.json'
    with _LOCK:
        path.parent.mkdir(parents=True,exist_ok=True)
        temporary=path.with_suffix('.'+uuid.uuid4().hex+'.tmp')
        try:
            temporary.write_text(json.dumps(rules,indent=2),encoding='utf-8')
            temporary.replace(path)
        finally:temporary.unlink(missing_ok=True)
    return rules


@dataclass(frozen=True)
class ExpressionResult:
    label: str | None
    matched_words: list[str]
    status: str
    message: str
    source: str = RULE_SOURCE
    rules_fingerprint: str = ''

    def to_dict(self):return asdict(self)


def analyze_expression(predicted_words):
    try:rules=load_rules()
    except ValueError as exc:return ExpressionResult(None,[],'unavailable',str(exc)).to_dict()
    fingerprint=hashlib.sha256(json.dumps(rules,sort_keys=True).encode()).hexdigest()[:16]
    if not rules['enabled']:
        return ExpressionResult(None,[],'disabled','Expression annotation is switched off.',rules_fingerprint=fingerprint).to_dict()
    matched=[]
    allowed=set(rules['words'])
    # Exact whole model-label matches. No substrings, stemming, or guesses from tone.
    for token in predicted_words:
        word=normalize_word(token)
        if word in allowed and word not in matched:matched.append(word)
    return ExpressionResult('angry' if matched else None,matched,'matched' if matched else 'not_matched',
        'Configured trigger words label this expression as angry; this is not measured signer emotion.' if matched else 'No configured angry trigger was recognized.',
        rules_fingerprint=fingerprint).to_dict()


def expression_text(sentence,expression):
    if not sentence:return ''
    return sentence.rstrip()+' [angry]' if expression.get('label')=='angry' else sentence


def annotate_sentence(suggestion,expression):
    # Keep plain English for model/content checks; suffix is presentation metadata.
    return {**suggestion,'display_text':expression_text(suggestion['text'],expression),'expression':expression}
