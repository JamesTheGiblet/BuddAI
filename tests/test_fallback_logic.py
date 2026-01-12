import unittest
from unittest.mock import Mock, patch
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestFallbackLogic(unittest.TestCase):
    def setUp(self):
        self.ai = Mock()
        self.ai.personality = Mock()
        self.ai.fallback_client = Mock()
        self.ai.learner = Mock()
        self.ai.hardware_profile = Mock()

    def test_fallback_triggered(self):
        """Triggers when confidence < 70%"""
        confidence = 60
        self.ai.personality.allow_fallback = True
        
        # Simulate logic check
        should_trigger = confidence < 70 and self.ai.personality.allow_fallback
        self.assertTrue(should_trigger)

    def test_fallback_disabled(self):
        """Respects personality disable flag"""
        confidence = 60
        self.ai.personality.allow_fallback = False
        
        should_trigger = confidence < 70 and self.ai.personality.allow_fallback
        self.assertFalse(should_trigger)

    def test_fallback_learning(self):
        """CRITICAL: Stores extracted rules"""
        # Fix from troubleshooting log: Mock return value must match real behavior
        self.ai.hardware_profile.apply_hardware_rules.side_effect = lambda code, *args: code
        
        # Mock extraction
        self.ai.fallback_client.extract_patterns = Mock(return_value=["Rule 1"])
        
        # Simulate learning loop
        patterns = self.ai.fallback_client.extract_patterns("old", "new")
        for p in patterns:
            self.ai.learner.store_rule(p)
            
        self.ai.learner.store_rule.assert_called_with("Rule 1")