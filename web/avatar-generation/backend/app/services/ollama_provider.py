"""Local-only, CPU-oriented structured inference. No cloud or mock fallback."""
import ipaddress
import json
import os
import re
import threading
from typing import Literal
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from pydantic import BaseModel, ConfigDict, Field


class AgentUnavailable(RuntimeError):
    pass


class ConceptProposal(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    concept: str = Field(pattern=r'^[A-Z0-9_]{1,64}$')
    evidence: str = Field(min_length=1, max_length=1000)
    signId: str | None
    senseId: str | None
    support: Literal['clear', 'ambiguous', 'unsupported']
    explanation: str = Field(min_length=1, max_length=500)


class LocalDecision(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    concepts: list[ConceptProposal] = Field(max_length=24)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise AgentUnavailable('Ollama redirects are disabled; inference must remain local.')


INFERENCE_SLOT = threading.BoundedSemaphore(1)


def integer_setting(name, default, minimum, maximum):
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError as error:
        raise AgentUnavailable(f'{name} must be an integer.') from error
    if not minimum <= value <= maximum:
        raise AgentUnavailable(f'{name} must be between {minimum} and {maximum}.')
    return value


class OllamaProvider:
    def __init__(self):
        if os.getenv('AI_PROVIDER', 'ollama').lower() != 'ollama':
            raise AgentUnavailable('Only AI_PROVIDER=ollama is enabled. Cloud inference is disabled.')
        self.base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434').rstrip('/')
        try:
            url = urlsplit(self.base_url)
            local = url.hostname == 'localhost' or ipaddress.ip_address(url.hostname or '').is_loopback
        except ValueError as error:
            raise AgentUnavailable('OLLAMA_BASE_URL must be a loopback HTTP address.') from error
        if url.scheme != 'http' or not local or url.username or url.password or url.path or url.query or url.fragment:
            raise AgentUnavailable('OLLAMA_BASE_URL must be a loopback HTTP address without credentials or a path.')
        self.model = os.getenv('OLLAMA_MODEL', 'qwen3:1.7b')
        if not re.fullmatch(r'[A-Za-z0-9_.:-]{1,100}', self.model) or self.model.lower().endswith('cloud'):
            raise AgentUnavailable('Set OLLAMA_MODEL to an installed local model tag, such as qwen3:1.7b.')
        self.num_ctx = integer_setting('OLLAMA_NUM_CTX', 4096, 2048, 8192)
        self.num_predict = integer_setting('OLLAMA_NUM_PREDICT', 1024, 256, 2048)
        self.num_thread = integer_setting('OLLAMA_NUM_THREAD', min(4, os.cpu_count() or 2), 1, 16)
        self.timeout = integer_setting('OLLAMA_TIMEOUT_SECONDS', 120, 5, 300)
        # Ignore system HTTP proxies and do not follow redirects away from loopback.
        self.opener = build_opener(ProxyHandler({}), NoRedirect())
        self.last_inference = None

    def request(self, path, payload=None, timeout=None):
        data = None if payload is None else json.dumps(payload).encode('utf-8')
        request = Request(self.base_url + path, data=data, headers={'Content-Type': 'application/json'})
        try:
            with self.opener.open(request, timeout=timeout or self.timeout) as response:
                raw = response.read(2 * 1024 * 1024 + 1)
            if len(raw) > 2 * 1024 * 1024:
                raise AgentUnavailable('Ollama response exceeded the size limit.')
            result = json.loads(raw)
            if not isinstance(result, dict) or result.get('error'):
                raise AgentUnavailable('Ollama returned an invalid response. Check the installed model and server logs.')
            return result
        except HTTPError as error:
            if error.code == 404:
                raise AgentUnavailable(f'Ollama model {self.model} is unavailable. Run: ollama pull {self.model}') from error
            raise AgentUnavailable(f'Ollama returned HTTP {error.code}. Check the local model/server.') from error
        except AgentUnavailable:
            raise
        except Exception as error:
            raise AgentUnavailable(f'Cannot reach Ollama at {self.base_url}, or inference timed out. Start Ollama and run: ollama pull {self.model}') from error

    def status(self):
        data = self.request('/api/tags', timeout=3)
        installed = any(item.get('name') == self.model or item.get('model') == self.model for item in data.get('models', []))
        return {'provider': 'ollama', 'model': self.model, 'reachable': True, 'modelAvailable': installed,
                'mode': 'structured-output orchestration', 'cpuOnly': True,
                'error': None if installed else f'Model is not installed. Run: ollama pull {self.model}'}

    def output_schema(self, vocabulary):
        return LocalDecision.model_json_schema()

    def parse_decision(self, content, vocabulary):
        return LocalDecision.model_validate_json(content)

    def input_vocabulary(self, vocabulary, text):
        return vocabulary

    def select(self, text, vocabulary, instructions):
        self.last_inference = None
        if len(text) > 1000:
            raise AgentUnavailable('Use a short transcript of up to 1000 characters for the local CPU prototype.')
        schema = self.output_schema(vocabulary)
        payload_text = json.dumps({'transcript': text, 'availableSigns': self.input_vocabulary(vocabulary, text)}, ensure_ascii=False)
        # Refuse oversized knowledge rather than silently truncating meanings or context.
        if len(payload_text) + len(instructions) + len(json.dumps(schema)) > self.num_ctx * 3:
            raise AgentUnavailable('Vocabulary and transcript exceed the local context budget. Shorten the input or curate a smaller vocabulary.')
        payload = {'model': self.model, 'stream': False, 'think': False, 'keep_alive': '5m',
                   'format': schema, 'messages': [{'role': 'system', 'content': instructions},
                                                {'role': 'user', 'content': payload_text}],
                   'options': {'num_ctx': self.num_ctx, 'num_predict': self.num_predict, 'num_thread': self.num_thread,
                               'num_gpu': 0, 'temperature': 0, 'seed': 42}}
        if not INFERENCE_SLOT.acquire(blocking=False):
            raise AgentUnavailable('The local model is busy. Wait for the current inference request to finish and retry.')
        try:
            response = self.request('/api/chat', payload)
            if response.get('done') is not True or response.get('done_reason') == 'length' or response.get('model') != self.model or type(response.get('eval_count')) is not int or response['eval_count'] <= 0:
                raise AgentUnavailable('Ollama returned incomplete inference or a different model. No animation was queued.')
            self.last_inference = {'provider': 'ollama', 'model': self.model, 'performed': True,
                                   'mode': 'structured-output orchestration', 'evalCount': response['eval_count'],
                                   'totalDurationNs': response.get('total_duration'), 'cpuOnly': True}
            try:
                decision = self.parse_decision(response['message']['content'], vocabulary)
            except (ValueError, KeyError, TypeError) as error:
                raise AgentUnavailable('Qwen returned invalid structured JSON. No animation was queued; try a shorter, clearer sentence.') from error
            return decision
        finally:
            INFERENCE_SLOT.release()
