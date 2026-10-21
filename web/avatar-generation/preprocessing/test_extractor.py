"""Dependency-free helper tests; run with python -m unittest discover -s preprocessing."""
import math
import unittest
from pathlib import Path
from types import SimpleNamespace
from extract_hand_landmarks import normalized_hand, within_component, COMPONENT_ROOT

class ExtractorTests(unittest.TestCase):
    def test_missing_or_partial_hand(self):
        self.assertIsNone(normalized_hand([]))
        self.assertIsNone(normalized_hand([SimpleNamespace(x=0.2, y=0.3)] * 20))
    def test_coordinates_are_normalized_and_nonfinite_hands_are_missing(self):
        points = [SimpleNamespace(x=0.2, y=0.3)] * 21
        self.assertEqual(len(normalized_hand(points)), 21)
        self.assertIsNone(normalized_hand([SimpleNamespace(x=math.nan, y=0.3)] * 21))
    def test_paths_cannot_escape_component(self):
        self.assertEqual(within_component(COMPONENT_ROOT / "preprocessing"), COMPONENT_ROOT / "preprocessing")
        with self.assertRaises(ValueError):
            within_component(COMPONENT_ROOT.parent / "outside.mp4")
if __name__ == "__main__":
    unittest.main()
