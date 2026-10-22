import base64
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from app.api.audio_routes import AudioWindow, AudioOrder
from app.services.sign_registry import ROOT, Registry
from app.services.live_pipeline import LivePipeline, EligibleProvider
from app.services.ollama_provider import LocalDecision, ConceptProposal
from app.services.speech import SpeechRecognizer

sys.path.insert(0, str(ROOT / 'preprocessing'))
from process_vocabulary import discover, source_id
from motion_validation import validate_motion


class AudioTests(unittest.TestCase):
    def test_recursive_case_insensitive_discovery_and_unique_ids(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            raw = Path(directory)
            (raw / 'sub').mkdir()
            for path in [raw / 'a.MP4', raw / 'sub/a.mp4', raw / 'skip.txt']:
                path.write_bytes(b'test')
            files = discover(raw)
            self.assertEqual(len(files), 2)
            self.assertNotEqual(source_id(files[0], raw), source_id(files[1], raw))

    def test_processed_inventory_preserves_originals_and_only_reviewed_mappings_play(self):
        inventory = json.loads((ROOT / 'datasets/metadata/dataset-vocabulary.json').read_text(encoding='utf-8'))
        self.assertEqual(inventory['discovered'], len(discover(ROOT / 'datasets/raw')))
        registry = Registry()
        self.assertEqual({e['signId'] for e in registry.available()},
                         {e['signId'] for e in inventory['records'] if e['reviewStatus'] == 'approved'})
        with self.assertRaises(ValueError):
            registry.resolve('NURSE')

    def test_body_face_counts_and_source_timing_are_validated(self):
        registry = Registry()
        entry = registry.details('CRY')
        animation = json.loads((registry.public / entry['animationFile']).read_text())
        stats = validate_motion(animation, 'CRY')
        self.assertGreater(stats['detections']['pose'], 0)
        animation['frames'][0]['pose'] = []
        with self.assertRaises(ValueError):
            validate_motion(animation, 'CRY')

    def test_audio_window_strict_bounds_and_extra_fields(self):
        packet = {'type': 'audio', 'seq': 0, 'startMs': 0, 'pcm16': base64.b64encode(b'\0' * 12800).decode()}
        self.assertEqual(len(AudioWindow.model_validate(packet).decode()), 12800)
        for bad in [{**packet, 'seq': True}, {**packet, 'path': '../file'}, {**packet, 'pcm16': '!!!!'}]:
            with self.assertRaises(ValueError):
                AudioWindow.model_validate(bad).decode()

    def test_silence_never_loads_model_or_invents_transcripts(self):
        recognizer = SpeechRecognizer()
        self.assertEqual(recognizer.transcribe(b'\0' * 32000)['segments'], [])
        self.assertIsNone(recognizer.model)

    def test_overlaps_duplicates_and_out_of_order_windows_cannot_repeat_playback(self):
        pcm = b'\0' * 32000
        packet = {'type': 'audio', 'seq': 0, 'startMs': 0, 'pcm16': base64.b64encode(pcm).decode()}
        order = AudioOrder()
        first = AudioWindow.model_validate(packet)
        self.assertTrue(order.accept(first, pcm))
        self.assertFalse(order.accept(first, pcm))
        with self.assertRaises(ValueError):
            order.accept(AudioWindow.model_validate({**packet, 'seq': 1, 'startMs': 500}), pcm)
        self.assertTrue(order.accept(AudioWindow.model_validate({**packet, 'seq': 1, 'startMs': 1000}), pcm))

    def test_unavailable_concepts_are_skipped_without_redirecting_to_other_signs(self):
        registry = Registry()
        provider = EligibleProvider(registry)
        missing = ConceptProposal(concept='NURSE', evidence='nurse', signId='NURSE', senseId='nursing-professional-person', support='clear', explanation='Nurse')
        valid = ConceptProposal(concept='CRY', evidence='crying', signId='CRY', senseId='person-weeping', support='clear', explanation='Weeping')
        with patch('app.services.ollama_provider.OllamaProvider.select', return_value=LocalDecision(concepts=[missing, valid])), patch.object(provider, 'verify_meaning', return_value=True):
            plan = provider.select('nurse crying', [], '')
        self.assertEqual([c.concept for c in plan.concepts], ['CRY'])
        self.assertEqual(len(provider.missing), 1)

    def test_semantic_cache_preserves_repeated_playback_intent(self):
        pipeline = LivePipeline()
        response = {'signs': ['CRY', 'CRY'], 'unsupported': [], 'concepts': [], 'manifest': Registry().manifest(['CRY'])}
        with patch('app.services.live_pipeline.SemanticAgent.process', return_value=response) as infer:
            first = pipeline.semantic('She is crying')
            second = pipeline.semantic('She is crying')
        self.assertEqual(infer.call_count, 1)
        self.assertTrue(second['cacheHit'])
        self.assertEqual(second['signs'], ['CRY', 'CRY'])

    def test_compact_model_proposals_are_individually_grounded_before_final_validation(self):
        registry = Registry()
        provider = EligibleProvider(registry)
        provider.transcript = 'Someone is crying.'
        vocabulary = [registry.details(sid) for sid in ['CRY', 'WALK', 'LOOK']]
        result = provider.parse_decision(json.dumps({'matches': [{'signId': 'CRY', 'evidence': 'crying'}, {'signId': 'WALK', 'evidence': 'walking'}], 'missing': []}), vocabulary)
        self.assertEqual([c.signId for c in result.concepts], ['CRY'])
        self.assertEqual(provider.missing[0]['discardedProposal']['signId'], 'WALK')

    def test_cancelled_session_does_not_start_another_recognition_or_model_call(self):
        import threading
        cancelled = threading.Event()
        cancelled.set()
        with patch('app.services.live_pipeline.recognizer.transcribe') as stt:
            result = LivePipeline().process(b'\0' * 32000, 0, 0, 'test', cancelled)
        stt.assert_not_called()
        self.assertTrue(result['cancelled'])
        self.assertEqual(result['signs'], [])

    def test_model_can_abstain_without_an_unregistered_playback_id(self):
        registry = Registry()
        provider = EligibleProvider(registry)
        provider.transcript = 'Ask a question, then look.'
        vocabulary = [registry.details('LOOK')]
        result = provider.parse_decision(json.dumps({'matches': [
            {'signId': None, 'evidence': 'Ask a question'},
            {'signId': 'LOOK', 'evidence': 'look'}], 'missing': []}), vocabulary)
        self.assertEqual([proposal.signId for proposal in result.concepts], ['LOOK'])
        self.assertIn('abstained', provider.missing[0]['reason'])
        schema = provider.output_schema(vocabulary)
        choice = schema['$defs']['CompactMatch']['properties']['signId']['anyOf']
        self.assertEqual(choice[0]['enum'], ['LOOK'])
        self.assertEqual(choice[1]['type'], 'null')
        provider.transcript = 'ask'
        with self.assertRaises(KeyError):
            provider.parse_decision('{"matches":[{"signId":"ASK","evidence":"ask"}],"missing":[]}', vocabulary)

    def test_meaning_verification_can_reject_but_never_redirect_a_proposal(self):
        provider = EligibleProvider(Registry())
        wrong = ConceptProposal(concept='LOOK', signId='LOOK', senseId='person-looking-with-eyes',
            evidence='The moon is luminous.', support='clear', explanation='Incorrect model proposal')
        response = {'model':provider.model,'done':True,'eval_count':5,
                    'message':{'content':'{"answer":"no"}'},'total_duration':100}
        with patch('app.services.ollama_provider.OllamaProvider.select', return_value=LocalDecision(concepts=[wrong])), patch.object(provider,'request',return_value=response):
            result = provider.select('The moon is luminous.',[provider.registry.details('LOOK')],'')
        self.assertEqual(result.concepts,[])
        self.assertIn('verification rejected',provider.missing[-1]['reason'])
        with patch.object(provider,'request',return_value={**response,'message':{'content':'{"answer":false}'}}),self.assertRaises(RuntimeError):
            provider.verify_meaning('Ask a question.','Ask a question.',0,'Looking with eyes')

    def test_a_known_vocabulary_word_does_not_create_a_model_selection(self):
        provider = EligibleProvider(Registry())
        provider.compact_proposals = [{'signId':None,'evidence':'Give'}]
        with patch('app.services.ollama_provider.OllamaProvider.select', return_value=LocalDecision(concepts=[])) as select, patch.object(provider,'request') as request:
            result = provider.select('Give me the book.',[provider.registry.details('GIVE')],'')
        self.assertEqual(result.concepts,[])
        request.assert_not_called()
        self.assertEqual(select.call_count,1, 'A valid abstention must not be retried into a forced choice')

    def test_negation_and_registered_exclusions_only_veto_matching_mentions(self):
        provider = EligibleProvider(Registry())
        text = 'Do not drink water or run.'
        for word, sid in [('drink','DRINK'),('run','RUN')]:
            self.assertIn('Negated',provider.excluded_context(text,text.index(word),text.index(word)+len(word),provider.registry.details(sid)))
        text = 'Do not drink, but run.'
        self.assertIsNone(provider.excluded_context(text,text.index('run'),text.index('run')+3,provider.registry.details('RUN')))
        text = 'Run a program, then run outside.'
        self.assertIn('excluded',provider.excluded_context(text,0,3,provider.registry.details('RUN')))
        self.assertIsNone(provider.excluded_context(text,text.rindex('run'),text.rindex('run')+3,provider.registry.details('RUN')))
        self.assertIn('excluded',provider.excluded_context('I see a bird.',2,5,provider.registry.details('LOOK')))
