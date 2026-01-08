#!/usr/bin/env python3
"""
Unit tests for BuddAI Fallback Logic
Verifies that low confidence scores trigger fallback when enabled in personality.
"""

import unittest
from unittest.mock import MagicMock, patch
import sys
import os
from pathlib import Path

# Setup path
REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from buddai_executive import BuddAI

class TestFallbackLogic(unittest.TestCase):
    @patch('buddai_executive.OllamaClient')
    @patch('buddai_executive.StorageManager')
    @patch('buddai_executive.RepoManager')
    def setUp(self, MockRepo, MockStorage, MockOllama):
        # Suppress prints during initialization
        with patch('builtins.print'):
            self.ai = BuddAI(user_id="test_fallback", server_mode=True)
        
        # Mock dependencies
        self.ai.llm = MockOllama()
        self.ai.storage = MockStorage()
        self.ai.confidence_scorer = MagicMock()
        self.ai.personality_manager = MagicMock()
        self.ai.validator = MagicMock()
        self.ai.hardware_profile = MagicMock()
        self.ai.shadow_engine = MagicMock()
        self.ai.shadow_engine.get_all_suggestions.return_value = []
        
        # Mock FallbackClient to avoid AttributeError and simulate responses
        self.ai.fallback_client = MagicMock()
        self.ai.fallback_client.is_available.return_value = True
        self.ai.fallback_client.escalate.side_effect = lambda model, *args, **kwargs: f"Fallback Triggered: {model} response"
        
        # Setup default mocks
        self.ai.validator.validate.return_value = (True, [])
        self.ai.hardware_profile.detect_hardware.return_value = "ESP32"
        # FIX: Ensure apply_hardware_rules returns a string, not a Mock
        self.ai.hardware_profile.apply_hardware_rules.return_value = "mocked_code_response"
        self.ai.extract_code = MagicMock(return_value=["void setup() {}"])

    def test_fallback_triggered(self):
        """Test that fallback triggers when enabled and confidence is low"""
        # Configure Personality to enable fallback
        self.ai.personality_manager.get_value.side_effect = lambda key, default=None: {
            "enabled": True,
            "confidence_threshold": 80,
            "fallback_models": ["claude", "gpt4"]
        } if key == "ai_fallback" else default

        # Configure Scorer to return low confidence (50 < 80)
        self.ai.confidence_scorer.calculate_confidence.return_value = 50
        self.ai.confidence_scorer.should_escalate.return_value = True

        # Mock LLM response
        self.ai.llm.query.return_value = "Here is code:\n```cpp\nvoid setup() {}\n```"
        
        # Run chat
        response = self.ai.chat("generate code")
        
        # Verify Fallback Message
        self.assertIn("Fallback Triggered", response)
        self.assertIn("claude", response)
        self.assertIn("gpt4", response)

    def test_fallback_disabled(self):
        """Test that standard warning appears when fallback is disabled"""
        # Configure Personality to disable fallback
        self.ai.personality_manager.get_value.side_effect = lambda key, default=None: {
            "enabled": False,
            "confidence_threshold": 80
        } if key == "ai_fallback" else default

        # Configure Scorer to return low confidence
        self.ai.confidence_scorer.calculate_confidence.return_value = 50
        self.ai.confidence_scorer.should_escalate.return_value = True

        # Mock LLM response
        self.ai.llm.query.return_value = "Here is code:\n```cpp\nvoid setup() {}\n```"
        
        # Run chat
        response = self.ai.chat("generate code")
        
        # Verify Standard Warning
        self.assertIn("Low Confidence", response)
        self.assertNotIn("Fallback Triggered", response)

    def test_fallback_learning(self):
        """Test that successful fallback triggers learning"""
        # Configure Personality to enable fallback
        self.ai.personality_manager.get_value.side_effect = lambda key, default=None: {
            "enabled": True,
            "confidence_threshold": 80,
            "fallback_models": ["claude"]
        } if key == "ai_fallback" else default

        # Configure Scorer to return low confidence
        self.ai.confidence_scorer.calculate_confidence.return_value = 50
        self.ai.confidence_scorer.should_escalate.return_value = True

        # Mock LLM response
        self.ai.llm.query.return_value = "Bad Code: ```cpp\nvoid setup() { delay(1000); }\n```"
        
        # Ensure hardware profile doesn't swallow the code
        self.ai.hardware_profile.apply_hardware_rules.side_effect = lambda code, *args: code
        
        # Mock Fallback Client Success
        self.ai.fallback_client.escalate.side_effect = None
        self.ai.fallback_client.escalate.return_value = "Here is fixed code:\n```cpp\nvoid setup() { millis(); }\n```"
        self.ai.fallback_client.extract_learning_patterns.return_value = ["Use millis()"]
        
        # Mock Learner
        self.ai.learner = MagicMock()
        
        # Mock extract_code to handle multiple calls
        def extract_side_effect(text):
            if "Bad Code" in text:
                return ["void setup() { delay(1000); }"]
            if "fixed code" in text:
                return ["void setup() { millis(); }"]
            return []
        self.ai.extract_code.side_effect = extract_side_effect
        
        # Run chat
        with patch('builtins.print'):
            self.ai.chat("fix code")
            
        # Verify store_rule called
        self.ai.learner.store_rule.assert_called_with("Use millis()", 0.6, "fallback_claude")

if __name__ == '__main__':
    unittest.main()
