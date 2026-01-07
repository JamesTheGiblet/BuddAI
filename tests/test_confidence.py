#!/usr/bin/env python3
"""
Unit tests for Confidence Scoring
"""
import unittest
import sys
from pathlib import Path

# Setup path
REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.buddai_confidence import ConfidenceScorer

class TestConfidence(unittest.TestCase):
    def setUp(self):
        self.scorer = ConfidenceScorer()

    def test_confidence_high(self):
        """Known good code → should score >70%"""
        # A perfect scenario: Valid code, matches hardware, matches rules
        code = "void setup() { Serial.begin(115200); }"
        context = {
            'hardware': 'ESP32',
            'learned_rules': ['Serial.begin(115200)'],
            'user_message': 'setup serial'
        }
        validation_results = (True, []) # Valid, no issues
        
        score = self.scorer.calculate_confidence(code, context, validation_results)
        self.assertGreater(score, 70, f"Score {score} should be > 70")

    def test_confidence_low(self):
        """Edge case code → should score <70%"""
        # A failure scenario: Invalid code
        code = "broken code"
        context = {'hardware': 'ESP32'}
        validation_results = (False, ['Syntax Error'])
        
        score = self.scorer.calculate_confidence(code, context, validation_results)
        self.assertLess(score, 70, f"Score {score} should be < 70")

    def test_threshold_detection(self):
        """Verify escalation trigger logic"""
        # Default threshold 70
        self.assertTrue(self.scorer.should_escalate(69))
        self.assertFalse(self.scorer.should_escalate(71))
        
        # Custom threshold
        self.assertTrue(self.scorer.should_escalate(80, threshold=85))

if __name__ == '__main__':
    unittest.main()