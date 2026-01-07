#!/usr/bin/env python3
"""
Unit tests for BuddAI Fallback Prompts
Verifies that specific prompts are selected for fallback models.
"""

import unittest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

# Setup path
REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from buddai_executive import BuddAI

class TestFallbackPrompts(unittest.TestCase):
    @patch('buddai_executive.OllamaClient')
    @patch('buddai_executive.StorageManager')
    @patch('buddai_executive.RepoManager')
    def setUp(self, MockRepo, MockStorage, MockOllama):
        # Suppress prints
        with patch('builtins.print'):
            self.ai = BuddAI(user_id="test_prompts", server_mode=True)
        
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
        self.ai.hardware_profile.apply_hardware_rules.return_value = "mocked_code_response"
        self.ai.extract_code = MagicMock(return_value=["void setup() {}"])

    def test_specific_prompts_used(self):
        """Test that configured prompts are used for each model"""
        # Configure Personality
        self.ai.personality_manager.get_value.side_effect = lambda key, default=None: {
            "enabled": True,
            "confidence_threshold": 80,
            "fallback_models": ["claude", "gpt4"],
            "prompts": {
                "claude": "Claude Prompt: {context}",
                "gpt4": "GPT4 Prompt: {context}"
            }
        } if key == "ai_fallback" else default

        # Low confidence
        self.ai.confidence_scorer.calculate_confidence.return_value = 50
        self.ai.confidence_scorer.should_escalate.return_value = True

        # Mock LLM
        self.ai.llm.query.return_value = "Code: ```cpp\nvoid setup() {}\n```"
        
        # Run
        user_msg = "fix the motor"
        response = self.ai.chat(user_msg)
        
        # Verify
        self.assertIn("Claude Prompt: fix the motor", response)
        self.assertIn("GPT4 Prompt: fix the motor", response)

if __name__ == '__main__':
    unittest.main()