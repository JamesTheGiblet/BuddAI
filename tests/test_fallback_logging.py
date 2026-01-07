#!/usr/bin/env python3
"""
Unit tests for BuddAI Fallback Logging
Verifies that fallback prompts are logged to file.
"""

import unittest
from unittest.mock import MagicMock, patch, mock_open
import sys
from pathlib import Path

# Setup path
REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from buddai_executive import BuddAI
from core.buddai_shared import DATA_DIR

class TestFallbackLogging(unittest.TestCase):
    @patch('buddai_executive.OllamaClient')
    @patch('buddai_executive.StorageManager')
    @patch('buddai_executive.RepoManager')
    def setUp(self, MockRepo, MockStorage, MockOllama):
        # Suppress prints
        with patch('builtins.print'):
            self.ai = BuddAI(user_id="test_logging", server_mode=True)
        
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

    def test_fallback_logging(self):
        """Test that fallback prompts are written to log file"""
        # Configure Personality
        self.ai.personality_manager.get_value.side_effect = lambda key, default=None: {
            "enabled": True,
            "confidence_threshold": 80,
            "fallback_models": ["claude"],
            "prompts": {
                "claude": "Claude Prompt: {context}"
            }
        } if key == "ai_fallback" else default

        # Low confidence
        self.ai.confidence_scorer.calculate_confidence.return_value = 50
        self.ai.confidence_scorer.should_escalate.return_value = True

        # Mock LLM
        self.ai.llm.query.return_value = "Code: ```cpp\nvoid setup() {}\n```"
        
        # Mock file opening
        m = mock_open()
        with patch('builtins.open', m):
            self.ai.chat("fix logic")
            
        # Verify file write
        log_path = DATA_DIR / "external_prompts.log"
        m.assert_called_with(log_path, "a", encoding="utf-8")
        handle = m()
        
        # Check if any write call contained the prompt
        written_content = "".join(call.args[0] for call in handle.write.call_args_list)
        self.assertIn("Claude Prompt: fix logic", written_content)
        self.assertIn("MODEL: CLAUDE", written_content)

    def test_logs_command(self):
        """Test /logs command retrieves content"""
        # Mock file existence and content
        m = mock_open(read_data="Log Entry 1\nLog Entry 2")
        
        # We need to patch Path.exists as well since the code checks it
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', m):
            
            response = self.ai.handle_slash_command("/logs")
            
            self.assertIn("Log Entry 2", response)
            self.assertIn("External Prompts Log", response)

if __name__ == '__main__':
    unittest.main()