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
        
        # Setup default mocks
        self.ai.validator.validate.return_value = (True, [])
        self.ai.hardware_profile.detect_hardware.return_value = "ESP32"
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

if __name__ == '__main__':
    unittest.main()