import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app.services.semantic_agent import AgentUnavailable, Decision, SemanticAgent, TOOLS
from app.services.sign_registry import REGISTRY, PUBLIC, Registry
from app.services.ollama_provider import LocalDecision


class FakeProvider:
    def __init__(self, decision):
        self.decision = decision
        self.calls = 0

    def respond(self, history, tools, instructions):
        self.calls += 1
        if self.calls == 1:
            name, args = 'getSignDetails', {'signId': 'NURSE'}
        else:
            name, args = 'submitSelection', self.decision
        return {'output': [{'type': 'function_call', 'name': name, 'arguments': json.dumps(args), 'call_id': str(self.calls)}]}


def selection(text, evidence='nursing professional', sign='NURSE', sense='nursing-professional-person'):
    start = text.index(evidence)
    return {'matches': [{'signId': sign, 'senseId': sense, 'start': start, 'end': start + len(evidence), 'evidence': evidence, 'explanation': 'This phrase describes the registered nursing occupation.'}], 'unsupported': []}


class SemanticTests(unittest.TestCase):
    def setUp(self):
        self.registry = Registry(preview=True)

    def test_pending_recording_is_not_promoted_to_approved(self):
        self.assertNotIn('NURSE', [entry['signId'] for entry in Registry().available()])
        with patch('app.services.ollama_provider.OllamaProvider.select', return_value=LocalDecision(concepts=[])):
            result = SemanticAgent().process('The nurse has a smartphone')
        self.assertEqual(result['signs'], [])
        self.assertEqual(result['status'], 'unsupported')

    def test_existing_recording_hash_and_manual_label_provenance(self):
        entry = self.registry.details('NURSE')
        self.assertEqual(entry['reviewStatus'], 'pending')
        self.assertEqual(entry['verifiedSynonyms'], [])
        self.assertEqual(self.registry.resolve('NURSE')['animationFile'], 'hand-animations/recorded/nurse.json')
        self.assertEqual(SemanticAgent(self.registry).process(' NURSE ')['signs'], ['NURSE'])

    def test_contextual_paraphrase_uses_real_tool_protocol_and_validator(self):
        text = 'She is a nursing professional.'
        provider = FakeProvider(selection(text))
        result = SemanticAgent(self.registry, provider).process(text)
        self.assertEqual(provider.calls, 2)
        self.assertEqual(result['signs'], ['NURSE'])
        self.assertEqual(result['matches'][0]['method'], 'AI semantic interpretation')
        self.assertFalse(result['manifest']['signs'][0]['reviewed'])

    def test_unsupported_model_decision_queues_nothing(self):
        result = SemanticAgent(self.registry, FakeProvider({'matches': [], 'unsupported': ['phone (verb)']})).process('He will phone his mother.')
        self.assertEqual(result['signs'], [])

    def test_multi_mentions_keep_source_order_without_overlap(self):
        text = 'A nurse greeted another nurse.'
        decision = selection(text, 'nurse')
        second = copy.deepcopy(decision['matches'][0])
        second['start'] = text.rindex('nurse')
        second['end'] = second['start'] + 5
        decision['matches'].append(second)
        result = SemanticAgent(self.registry, FakeProvider(decision)).process(text)
        self.assertEqual(result['signs'], ['NURSE', 'NURSE'])
        self.assertEqual(len(result['manifest']['signs']), 1)

    def test_invalid_ids_senses_evidence_and_overlaps_fail_closed(self):
        text = 'She is a nursing professional.'
        for field, value in [('signId', 'PHONE'), ('senseId', 'breastfeeding'), ('end', 9999), ('evidence', 'nurse'), ('start', True)]:
            bad = selection(text)
            bad['matches'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                SemanticAgent(self.registry).validate(text, Decision.model_validate(bad))
        bad = selection(text)
        bad['matches'] *= 2
        with self.assertRaises(ValueError):
            SemanticAgent(self.registry).validate(text, Decision.model_validate(bad))

    def test_unknown_tools_and_arbitrary_arguments_rejected(self):
        agent = SemanticAgent(self.registry)
        for name, args in [('readFile', {'path': '../secret'}), ('queueAnimation', {'animationId': '../secret'}), ('getSignDetails', {'signId': 'NURSE', 'path': 'secret'}), ('getSignDetails', {'signId': 4})]:
            with self.assertRaises(ValueError):
                agent.tool(name, args)

    def test_traversal_missing_assets_and_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'registry.json'
            data = json.loads(REGISTRY.read_text(encoding='utf-8'))
            data['signs'] = [entry for entry in data['signs'] if entry['signId'] == 'NURSE']
            for filename in ['../secret.json', 'hand-animations/missing.json']:
                data['signs'][0]['animationFile'] = filename
                path.write_text(json.dumps(data))
                self.assertEqual(Registry(path, PUBLIC, preview=True).available(), [])
            data['signs'][0]['animationFile'] = 'hand-animations/recorded/nurse.json'
            data['signs'][0]['sha256'] = '0' * 64
            path.write_text(json.dumps(data))
            self.assertEqual(Registry(path, PUBLIC, preview=True).available(), [])

    def test_contextual_requests_do_not_silently_fallback_when_ollama_is_unavailable(self):
        with patch('app.services.ollama_provider.OllamaProvider.select', side_effect=AgentUnavailable('Ollama unavailable')), self.assertRaises(AgentUnavailable):
            SemanticAgent(self.registry).process('The nurse is working.')

    def test_tool_schemas_do_not_leave_unresolved_references(self):
        self.assertNotIn('$ref', json.dumps(TOOLS))


if __name__ == '__main__':
    unittest.main()
