#!/usr/bin/env python3
"""
Unit tests for BuddAI Confidence Scorer
Verifies scoring logic, penalties, and escalation flags.
"""

import unittest
import sys
import os
from pathlib import Path

# Dynamic import setup
REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.buddai_confidence import ConfidenceScorer

class TestConfidenceScorer(unittest.TestCase):
    def setUp(self):
        self.scorer = ConfidenceScorer()

    def test_calculate_confidence_high(self):
        """Test a high confidence scenario (Success + Matches)"""
        code = "void setup() { Serial.begin(115200); }"
        context = {
            'hardware': 'ESP32',
            'learned_rules': ['Serial.begin(115200)'],
            'user_message': 'setup serial',
            'history': []
        }
        # Success, no issues
        validation_results = (True, [])
        
        score = self.scorer.calculate_confidence(code, context, validation_results)
        
        # Expected Score Breakdown:
        # Validation: 40 (Perfect)
        # Patterns: ~30 (1 match / 1 rule = 100% * 1.5 boost, capped at 30)
        # Hardware: 10 (ESP32 not explicitly in code string, generic fallback)
        # Context: 10 (Hardware + Message + Rules present)
        # Total ~90
        self.assertGreaterEqual(score, 80)
        self.assertFalse(self.scorer.should_escalate(score))

    def test_calculate_confidence_low(self):
        """Test a low confidence scenario (Validation Failure)"""
        code = "broken code"
        context = {'hardware': 'ESP32'}
        validation_results = (False, ['Syntax Error'])
        
        score = self.scorer.calculate_confidence(code, context, validation_results)
        
        # Expected Score Breakdown:
        # Validation: 0 (Failed)
        # Patterns: 15 (Default baseline when no rules)
        # Hardware: 10 (Generic)
        # Context: 3 (Hardware only)
        # Total: 28
        self.assertLess(score, 50)
        self.assertTrue(self.scorer.should_escalate(score))

    def test_should_escalate_thresholds(self):
        """Test flagging logic at specific boundaries"""
        # Default threshold is 70
        self.assertTrue(self.scorer.should_escalate(69))
        self.assertFalse(self.scorer.should_escalate(70))
        self.assertFalse(self.scorer.should_escalate(71))
        
        # Custom threshold
        self.assertTrue(self.scorer.should_escalate(80, threshold=85))

    def test_validation_scoring_penalties(self):
        """Test that warnings reduce score but don't zero it"""
        # 2 warnings -> -10 points (5 per warning)
        validation_results = (True, [{'message': 'W1'}, {'message': 'W2'}])
        score = self.scorer._score_validation(validation_results)
        self.assertEqual(score, 30.0) # 40 - 10

        # Many warnings -> Min score 10
        many_issues = [{'message': 'W'}] * 10
        score_min = self.scorer._score_validation((True, many_issues))
        self.assertEqual(score_min, 10.0)

    def test_pattern_familiarity(self):
        """Test pattern matching logic"""
        code = "ledcSetup(0, 5000, 8);"
        
        # Match
        context_match = {'learned_rules': ['Use ledcSetup']}
        score_match = self.scorer._score_patterns(code, context_match)
        self.assertEqual(score_match, 30.0) # Capped max
        
        # No Match
        context_miss = {'learned_rules': ['Use analogRead']}
        score_miss = self.scorer._score_patterns(code, context_miss)
        self.assertEqual(score_miss, 0.0)
        
        # No Rules Provided (Neutral Baseline)
        score_empty = self.scorer._score_patterns(code, {})
        self.assertEqual(score_empty, 15.0)

if __name__ == '__main__':
    unittest.main()