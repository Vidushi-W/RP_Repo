import unittest
from unittest.mock import patch
from fastapi import HTTPException
from pydantic import ValidationError
from app.api.semantic_routes import Transcript, process_transcript, vocabulary, agent_status
from app.services.ollama_provider import LocalDecision, AgentUnavailable


class SemanticRouteTests(unittest.TestCase):
    def test_transcript_schema_rejects_extra_fields_and_implicit_preview_coercion(self):
        for data in [{'text': 'nurse', 'researchPreview': 'false'}, {'text': 'nurse', 'path': '../secret'}, {'text': ''}, {'text': 'x' * 4001}]:
            with self.assertRaises(ValidationError):
                Transcript.model_validate(data)

    def test_default_request_never_enables_pending_recordings(self):
        with patch('app.services.ollama_provider.OllamaProvider.select', return_value=LocalDecision(concepts=[])):
            result = process_transcript(Transcript(text='nurse'))
        self.assertEqual(result['signs'], [])
        self.assertFalse(result['researchPreview'])

    def test_preview_request_resolves_existing_recording(self):
        result = process_transcript(Transcript(text='nurse', researchPreview=True))
        self.assertEqual(result['signs'], ['NURSE'])
        self.assertEqual(result['manifest']['signs'][0]['sha256'], result['matches'][0]['sha256'])

    def test_unavailable_ollama_surfaces_as_service_unavailable(self):
        with patch('app.services.ollama_provider.OllamaProvider.select', side_effect=AgentUnavailable('Ollama unavailable')), self.assertRaises(HTTPException) as error:
            process_transcript(Transcript(text='The nurse is working.', researchPreview=True))
        self.assertEqual(error.exception.status_code, 503)

    def test_configuration_endpoint_does_not_expose_secrets(self):
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'secret-example', 'OPENAI_MODEL': 'test-model'}):
            result = vocabulary()
        self.assertTrue(result['configured'])
        self.assertEqual(result['provider'], 'ollama')
        self.assertEqual(result['model'], 'qwen3:1.7b')
        self.assertNotIn('secret-example', str(result))

    def test_status_surfaces_unavailable_model_without_claiming_inference(self):
        with patch('app.services.ollama_provider.OllamaProvider.status', side_effect=AgentUnavailable('Start Ollama')):
            result = agent_status()
        self.assertFalse(result['reachable'])
        self.assertFalse(result['modelAvailable'])
        self.assertEqual(result['error'], 'Start Ollama')
