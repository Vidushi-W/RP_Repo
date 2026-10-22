"""Regression checks against the preserved expansion audit and real assets."""
import hashlib
import json
import unittest
from app.services.sign_registry import ROOT, Registry


class VocabularyExpansionTests(unittest.TestCase):
    def test_approved_assets_reuse_exact_motion_and_preserve_baseline(self):
        audit = json.loads((ROOT/'research/evaluation/vocabulary-expansion/motion-audit.json').read_text(encoding='utf-8'))
        registry = Registry()
        self.assertEqual({e['signId'] for e in registry.available()}, {'CRY','WALK','LOOK','DRINK','RUN','GIVE','TAKE','SEE','DRAW','EAT'})
        for sid, expected in audit['baselineApprovedAssets'].items():
            self.assertEqual(registry.details(sid)['sha256'], expected)
        for sid, candidate in audit['candidates'].items():
            if sid == 'ASK':
                continue
            entry = registry.details(sid)
            original = ROOT/'frontend/public'/candidate['originalMotionFile']
            self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(), candidate['originalMotionSha256'])
            old = json.loads(original.read_text(encoding='utf-8'))
            new = json.loads((ROOT/'frontend/public'/entry['animationFile']).read_text(encoding='utf-8'))
            old['signId'] = sid
            self.assertEqual(new, old, 'Only the concept identity may change; motion and metadata must be reused')
            registry.resolve(sid)
            self.assertFalse(entry['linguisticallyCertified'])
            self.assertTrue(entry['reviewSources'])

    def test_ambiguous_ask_source_stays_blocked_even_in_preview(self):
        for preview in (False, True):
            registry = Registry(preview=preview)
            source = next(e for e in registry.entries.values() if e.get('sourceFile') == 'ahanawa.mp4')
            self.assertEqual(source['reviewStatus'], 'pending')
            with self.assertRaises(ValueError):
                registry.resolve(source['signId'])
            with self.assertRaises(ValueError):
                registry.resolve('ASK')
        registry = Registry()
        with self.assertRaises(ValueError):
            registry.resolve('NURSE')
        self.assertNotEqual(registry.details('LOOK')['senseId'],registry.details('SEE')['senseId'])

    def test_all_original_source_hashes_are_unchanged(self):
        audit = json.loads((ROOT/'research/evaluation/vocabulary-expansion/motion-audit.json').read_text(encoding='utf-8'))
        for filename, expected in audit['allSourceHashes'].items():
            self.assertEqual(hashlib.sha256((ROOT/'datasets/raw'/filename).read_bytes()).hexdigest(),expected)
