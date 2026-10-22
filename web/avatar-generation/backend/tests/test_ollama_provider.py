"""Mocked transport/contract tests, NOT evidence of real Qwen inference."""
import json
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError
from app.services.ollama_provider import AgentUnavailable, ConceptProposal, INFERENCE_SLOT, LocalDecision, OllamaProvider
from app.services.semantic_agent import SemanticAgent
from app.services.sign_registry import Registry


def concept(label, evidence, available=False, support='clear'):
    return ConceptProposal(concept=label, evidence=evidence, signId=label if available else None,
                           senseId='nursing-professional-person' if available else None,
                           support=support, explanation='Equivalent English concept in context.')


class StructuredProvider:
    def __init__(self, concepts):
        self.plan = LocalDecision(concepts=concepts)
        self.last_inference = {'performed': False, 'mode': 'unit-test fake, not real inference'}
        self.calls = 0

    def select(self, text, vocabulary, instructions):
        self.calls += 1
        return self.plan


class OllamaTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict('os.environ', {'AI_PROVIDER': 'ollama', 'OLLAMA_MODEL': 'qwen3:1.7b', 'OLLAMA_BASE_URL': 'http://localhost:11434'}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def test_no_key_required_and_no_remote_endpoints_or_cloud_provider(self):
        self.assertEqual(OllamaProvider().model, 'qwen3:1.7b')
        for url in ['https://api.openai.com', 'http://example.com:11434', 'http://localhost:11434@evil.com', 'http://localhost:11434/path', 'http://localhost:11434?redirect=evil']:
            with patch.dict('os.environ', {'OLLAMA_BASE_URL': url}), self.assertRaises(AgentUnavailable):
                OllamaProvider()
        with patch.dict('os.environ', {'AI_PROVIDER': 'openai'}), self.assertRaises(AgentUnavailable):
            OllamaProvider()

    def test_local_request_uses_cpu_small_context_and_validates_actual_response(self):
        provider = OllamaProvider()
        content = {'concepts': [concept('PHONE', 'smartphone').model_dump()]}
        response = {'model': 'qwen3:1.7b', 'done': True, 'done_reason': 'stop', 'eval_count': 40,
                    'message': {'content': json.dumps(content)}}
        with patch.object(provider, 'request', return_value=response) as request:
            result = provider.select('smartphone', [], 'Return concepts.')
        self.assertEqual(result.concepts[0].concept, 'PHONE')
        payload = request.call_args.args[1]
        self.assertEqual(payload['options']['num_gpu'], 0)
        self.assertEqual(payload['options']['num_ctx'], 4096)
        self.assertFalse(payload['think'])
        self.assertFalse(payload['stream'])
        self.assertIn('concepts', payload['format']['properties'])
        self.assertNotIn('Authorization', str(payload))

    def test_unavailable_device_label_normalization_cannot_grant_playback(self):
        provider = StructuredProvider([concept('CELLPHONE', 'cellphone')])
        result = SemanticAgent(Registry(preview=True), provider).process('cellphone')
        self.assertEqual(result['concepts'][0]['concept'], 'PHONE')
        self.assertEqual(result['concepts'][0]['modelConcept'], 'CELLPHONE')
        self.assertFalse(result['concepts'][0]['animationAvailable'])
        self.assertEqual(result['signs'], [])
        self.assertEqual(provider.calls, 1)

    def test_invalid_truncated_or_wrong_model_responses_never_become_predictions(self):
        provider = OllamaProvider()
        base = {'model': provider.model, 'done': True, 'eval_count': 10, 'message': {'content': '{invalid'}}
        for response in [base, {**base, 'done_reason': 'length'}, {**base, 'model': 'other'}, {**base, 'eval_count': 0}]:
            with patch.object(provider, 'request', return_value=response), self.assertRaises(AgentUnavailable):
                provider.select('nurse', [], 'instructions')
        self.assertIsNone(provider.last_inference)

    def test_connection_and_missing_model_errors_are_actionable(self):
        provider = OllamaProvider()
        for error, message in [(URLError('connection refused'), 'Start Ollama'), (HTTPError('local', 404, 'not found', {}, None), 'ollama pull')]:
            provider.opener = Mock()
            provider.opener.open.side_effect = error
            with self.assertRaisesRegex(AgentUnavailable, message):
                provider.request('/api/chat', {})

    def test_busy_inference_is_rejected_without_starting_another_request(self):
        provider = OllamaProvider()
        INFERENCE_SLOT.acquire()
        try:
            with patch.object(provider, 'request') as request, self.assertRaisesRegex(AgentUnavailable, 'busy'):
                provider.select('nurse', [], 'instructions')
            request.assert_not_called()
        finally:
            INFERENCE_SLOT.release()

    def test_real_generated_tokens_are_recorded_even_if_semantic_json_is_invalid(self):
        provider = OllamaProvider()
        with patch.object(provider, 'request', return_value={'model': provider.model, 'done': True, 'eval_count': 7, 'message': {'content': 'invalid JSON'}}), self.assertRaises(AgentUnavailable):
            provider.select('nurse', [], 'instructions')
        self.assertTrue(provider.last_inference['performed'])
        self.assertEqual(provider.last_inference['evalCount'], 7)

    def test_model_status_distinguishes_reachable_server_from_missing_model(self):
        provider = OllamaProvider()
        with patch.object(provider, 'request', return_value={'models': []}):
            self.assertFalse(provider.status()['modelAvailable'])
        with patch.object(provider, 'request', return_value={'models': [{'name': 'qwen3:1.7b'}]}):
            self.assertTrue(provider.status()['modelAvailable'])

    def test_phone_concept_recognition_does_not_fabricate_phone_animation(self):
        for phrase in ['cellphone', 'smartphone']:
            provider = StructuredProvider([concept('PHONE', phrase)])
            result = SemanticAgent(Registry(), provider).process(phrase)
            self.assertEqual(result['concepts'][0]['concept'], 'PHONE')
            self.assertFalse(result['concepts'][0]['animationAvailable'])
            self.assertEqual(result['signs'], [])
            self.assertEqual(provider.calls, 1)

    def test_paraphrases_call_existing_tools_and_require_preview(self):
        for phrase in ['nursing professional', 'hospital nurse']:
            provider = StructuredProvider([concept('NURSE', phrase, available=True)])
            result = SemanticAgent(Registry(preview=True), provider).process(phrase)
            self.assertEqual(result['signs'], ['NURSE'])
            tools = [item['tool'] for item in result['trace']]
            self.assertEqual(tools[:2], ['listAvailableSigns', 'findMatchingSign'])
            self.assertGreaterEqual(tools.count('getSignDetails'), 1)
            self.assertEqual(tools[-2:], ['resolveAnimation', 'queueAnimation'])
            with self.assertRaises(ValueError):
                SemanticAgent(Registry(), provider).process(phrase)

    def test_multiple_concepts_and_mentions_keep_order(self):
        provider = StructuredProvider([concept('NURSE', 'nurse', True), concept('PHONE', 'smartphone')])
        result = SemanticAgent(Registry(preview=True), provider).process('The nurse has a smartphone')
        self.assertEqual([c['concept'] for c in result['concepts']], ['NURSE', 'PHONE'])
        self.assertEqual(result['signs'], ['NURSE'])
        provider = StructuredProvider([concept('NURSE', 'nurse', True), concept('NURSE', 'nurse', True)])
        result = SemanticAgent(Registry(preview=True), provider).process('A nurse greeted another nurse')
        self.assertEqual(result['signs'], ['NURSE', 'NURSE'])

    def test_unsupported_ambiguous_and_invalid_evidence_never_play(self):
        provider = StructuredProvider([concept('NURSE', 'nurse', True, 'ambiguous')])
        self.assertEqual(SemanticAgent(Registry(preview=True), provider).process('Is she a nurse?')['signs'], [])
        provider = StructuredProvider([concept('PHONE', 'invented substring')])
        with self.assertRaises(ValueError):
            SemanticAgent(Registry(preview=True), provider).process('smartphone')
        provider = StructuredProvider([concept('PHONE', 'smartphone', True)])
        with self.assertRaises(ValueError):
            SemanticAgent(Registry(preview=True), provider).process('smartphone')

    def test_missing_json_does_not_allow_structured_selection(self):
        registry = Registry(preview=True)
        registry.entries['NURSE']['animationFile'] = 'hand-animations/recorded/missing.json'
        provider = StructuredProvider([concept('NURSE', 'nursing professional', True)])
        with self.assertRaises(ValueError):
            SemanticAgent(registry, provider).process('nursing professional')
