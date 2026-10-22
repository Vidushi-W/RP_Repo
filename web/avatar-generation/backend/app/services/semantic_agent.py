"""Registry-constrained selection with a local structured-output provider."""
import json
from pydantic import BaseModel, ConfigDict, Field, StrictInt
from app.services.sign_registry import ROOT, Registry, normalize
from app.services.ollama_provider import AgentUnavailable, OllamaProvider


class Match(BaseModel):
    model_config = ConfigDict(extra='forbid')
    signId: str = Field(max_length=64)
    senseId: str = Field(max_length=100)
    start: StrictInt = Field(ge=0)
    end: StrictInt = Field(gt=0)
    evidence: str = Field(min_length=1, max_length=2000)
    explanation: str = Field(min_length=1, max_length=1000)


class Decision(BaseModel):
    model_config = ConfigDict(extra='forbid')
    matches: list[Match] = Field(max_length=40)
    unsupported: list[str] = Field(max_length=80)


def function(name, description, properties):
    return {'type': 'function', 'name': name, 'description': description, 'strict': True,
            'parameters': {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}}


STRING = {'type': 'string'}
TOOLS = [
    function('listAvailableSigns', 'List only existing vocabulary available in this request mode.', {}),
    function('getSignDetails', 'Read approved meaning, exclusions, synonyms and review provenance.', {'signId': STRING}),
    function('findMatchingSign', 'Retrieve phrase hits and all available meaning descriptions; assess semantic similarity in context, never equate related concepts.', {'text': STRING}),
    function('resolveAnimation', 'Validate the registered animation, checksum and sign identifier.', {'signId': STRING}),
    function('queueAnimation', 'Validate eligibility for later playback. Does not commit playback; the final decision must pass validation.', {'animationId': STRING}),
    function('submitSelection', 'Submit ordered grounded selections. Use empty matches when unsupported or ambiguous.', Decision.model_json_schema()['properties']),
]
# Pydantic emits references for nested models; inline the small match schema for strict tools.
TOOLS[-1]['parameters']['properties']['matches']['items'] = Match.model_json_schema()


class SemanticAgent:
    def __init__(self, registry=None, provider=None):
        self.registry = registry or Registry()
        self.provider = provider

    def tool(self, name, args):
        expected = {'listAvailableSigns': set(), 'getSignDetails': {'signId'}, 'findMatchingSign': {'text'},
                    'resolveAnimation': {'signId'}, 'queueAnimation': {'animationId'}}
        if name not in expected or not isinstance(args, dict) or set(args) != expected[name] or any(not isinstance(v, str) or len(v) > 4000 for v in args.values()):
            raise ValueError('Invalid tool arguments')
        if name == 'listAvailableSigns':
            return self.registry.available()
        if name == 'getSignDetails':
            return self.registry.details(args['signId'])
        if name == 'findMatchingSign':
            return self.registry.candidates(args['text'])
        return self.registry.resolve(args.get('signId', args.get('animationId')))

    def validate(self, text, decision):
        selected = []
        previous = 0
        for match in decision.matches:
            entry = self.registry.details(match.signId)
            if match.senseId != entry['senseId'] or match.start < previous or match.end > len(text) or text[match.start:match.end] != match.evidence:
                raise ValueError('Invalid, overlapping or ungrounded semantic selection')
            previous = match.end
            resolved = self.registry.resolve(match.signId)
            phrase = normalize(match.evidence)
            method = 'registered canonical label' if phrase == normalize(entry['canonicalLabel']) else 'verified synonym' if phrase in [normalize(a) for a in entry['verifiedSynonyms']] else 'AI semantic interpretation'
            selected.append({**match.model_dump(), **resolved, 'canonicalLabel': entry['canonicalLabel'],
                             'method': method, 'reviewStatus': entry['reviewStatus']})
        return selected

    def process_structured(self, text, provider):
        trace = []
        def call(name, args):
            value = self.tool(name, args)
            trace.append({'tool': name, 'arguments': args, 'orchestrator': 'backend'})
            return value
        available = call('listAvailableSigns', {})
        candidates = call('findMatchingSign', {'text': text})
        vocabulary = []
        for candidate in candidates:
            entry = call('getSignDetails', {'signId': candidate['signId']})
            vocabulary.append({**{key: entry[key] for key in ('signId', 'canonicalLabel', 'senseId', 'description', 'verifiedSynonyms', 'reviewStatus')},
                               'sinhalaLabel': entry.get('sinhalaLabel'),
                               'excludedPhrases': entry.get('excludedPhrases', [])})
        instructions = (ROOT / 'backend/app/services/local_semantic_instructions.txt').read_text(encoding='utf-8')
        plan = provider.select(text, vocabulary, instructions)
        concepts, matches, unsupported = [], [], []
        previous = 0
        eligible = {entry['signId'] for entry in available}
        for proposal in plan.concepts:
            # Normalize equivalent ENGLISH labels emitted by the model only for
            # concepts that have no selected sign. This never grants playback.
            concept_label = proposal.concept
            if proposal.signId is None:
                concept_label = {'CELLPHONE': 'PHONE', 'CELL_PHONE': 'PHONE', 'MOBILE_PHONE': 'PHONE',
                                 'SMARTPHONE': 'PHONE'}.get(concept_label, concept_label)
            start = text.find(proposal.evidence, previous)
            if start < 0:
                raise ValueError('Concept evidence is missing or not in transcript order')
            end = start + len(proposal.evidence)
            previous = end
            playable = False
            if proposal.signId is not None:
                if proposal.signId not in eligible or proposal.concept != proposal.signId:
                    raise ValueError('The model proposed an unavailable or inconsistent sign ID')
                entry = self.registry.details(proposal.signId)
                if proposal.senseId != entry['senseId']:
                    raise ValueError('The proposed sense is not registered')
                if proposal.support == 'clear':
                    match = Match(signId=proposal.signId, senseId=proposal.senseId, start=start, end=end,
                                  evidence=proposal.evidence, explanation=proposal.explanation)
                    matches.append(match)
                    call('resolveAnimation', {'signId': proposal.signId})
                    call('queueAnimation', {'animationId': proposal.signId})
                    playable = True
            elif proposal.senseId is not None:
                raise ValueError('Unregistered concepts cannot assert a registered sense')
            concepts.append({**proposal.model_dump(), 'modelConcept': proposal.concept, 'concept': concept_label,
                             'start': start, 'end': end, 'animationAvailable': playable})
            if not playable:
                unsupported.append(f'{proposal.evidence}: {concept_label} — no eligible animation or meaning is ambiguous')
        selected = self.validate(text, Decision(matches=matches, unsupported=unsupported))
        result = self.result(text, selected, unsupported, trace)
        result['concepts'] = concepts
        result['inference'] = provider.last_inference
        return result

    def process(self, text, force_inference=False):
        if not isinstance(text, str) or not text.strip() or len(text) > 4000:
            raise ValueError('Provide 1 to 4000 characters of English text')
        candidates = self.registry.candidates(text)
        if not candidates and self.provider is not None and not hasattr(self.provider, 'select'):
            return self.result(text, [], ['Unsupported sign: no reviewed, intact animations available in this mode.'], [])
        # Only standalone, single-meaning registry labels/synonyms bypass contextual inference.
        exact = [c for c in candidates if normalize(text) in [normalize(a) for a in [self.registry.details(c['signId'])['canonicalLabel'], *self.registry.details(c['signId'])['verifiedSynonyms']]]]
        if len(exact) == 1 and not force_inference:
            entry = self.registry.details(exact[0]['signId'])
            start = len(text) - len(text.lstrip())
            decision = Decision(matches=[Match(signId=entry['signId'], senseId=entry['senseId'], start=start, end=len(text.rstrip()), evidence=text.strip(), explanation='Standalone registry vocabulary match.')], unsupported=[])
            return self.result(text, self.validate(text, decision), [], [])
        provider = self.provider or OllamaProvider()
        self.provider = provider
        if hasattr(provider, 'select'):
            return self.process_structured(text, provider)
        # Retain the existing injected tool-call adapter contract. Production uses
        # the local structured provider above; no native calls are simulated.
        instructions = (ROOT / 'backend/app/services/semantic_instructions.txt').read_text(encoding='utf-8')
        history = [{'role': 'user', 'content': json.dumps({'transcript': text, 'candidates': candidates}, ensure_ascii=False)}]
        trace = []
        inspected = set()
        for _ in range(10):
            response = provider.respond(history, TOOLS, instructions)
            output = response.get('output', [])
            history.extend(output)
            calls = [item for item in output if item.get('type') == 'function_call']
            if len(calls) != 1:
                raise AgentUnavailable('Agent did not produce one valid tool call')
            call = calls[0]
            name = call['name']
            args = {}
            try:
                args = json.loads(call['arguments'])
                if name == 'submitSelection':
                    decision = Decision.model_validate(args)
                    if any(m.signId not in inspected for m in decision.matches):
                        raise ValueError('Inspect getSignDetails for each chosen sign before submitting')
                    matches = self.validate(text, decision)
                    return self.result(text, matches, decision.unsupported, trace)
                data = self.tool(name, args)
                if name == 'getSignDetails':
                    inspected.add(args['signId'])
            except (ValueError, OSError):
                data = {'error': 'Invalid selection or unavailable animation. Recheck tool arguments, evidence, sense and vocabulary.'}
            trace.append({'tool': name, 'arguments': args if isinstance(args, dict) else {}})
            history.append({'type': 'function_call_output', 'call_id': call['call_id'], 'output': json.dumps(data, ensure_ascii=False)})
        raise AgentUnavailable('Agent exceeded the tool-call limit. No animation was queued.')

    def result(self, text, matches, unsupported, trace):
        signs = [m['signId'] for m in matches]
        return {'englishText': text, 'signs': signs, 'matches': matches, 'unsupported': unsupported,
                'status': 'matched' if matches else 'unsupported', 'researchPreview': self.registry.preview,
                'manifest': self.registry.manifest(signs), 'trace': trace,
                'concepts': [{'concept': m['signId'], 'evidence': m['evidence'], 'animationAvailable': True, 'support': 'clear', 'explanation': m['explanation']} for m in matches],
                'inference': {'performed': False, 'mode': 'deterministic registry match'},
                'confidencePolicy': 'Closed vocabulary, grounded spans and sense validation; no calibrated probability is claimed.'}
