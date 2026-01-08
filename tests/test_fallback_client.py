import unittest
from unittest.mock import MagicMock, patch
import sys
import os
from pathlib import Path

# Setup path
REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.buddai_fallback import FallbackClient

class TestFallbackClient(unittest.TestCase):
    @patch('core.buddai_fallback.genai')
    def test_escalate_success(self, mock_genai):
        """Test successful escalation to Gemini"""
        # Setup mocks
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Fixed Code"
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        # Force HAS_GEMINI to True for this test
        with patch('core.buddai_fallback.HAS_GEMINI', True):
            with patch.dict('os.environ', {'GEMINI_API_KEY': 'fake_key'}):
                client = FallbackClient()
                # Inject mock client since __init__ might fail if real genai not installed
                client.gemini_client = mock_model
                client.build_fallback_prompt = MagicMock(return_value="Prompt")
                
                result = client.escalate("gemini", "prompt", "bad code", 50)
                
                self.assertIn("Gemini Fallback", result)
                self.assertIn("Fixed Code", result)

    def test_escalate_no_key(self):
        """Test behavior when API key is missing"""
        with patch.dict('os.environ', {}, clear=True):
            client = FallbackClient()
            result = client.escalate("gemini", "prompt", "bad code", 50)
            self.assertIn("fallback unavailable", result)

    @patch('core.buddai_fallback.OpenAI')
    def test_escalate_openai(self, mock_openai):
        """Test successful escalation to OpenAI"""
        # Setup mocks
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "GPT Code"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        with patch('core.buddai_fallback.HAS_OPENAI', True):
            with patch.dict('os.environ', {'OPENAI_API_KEY': 'fake_key'}):
                client = FallbackClient()
                client.openai_client = mock_client
                client.build_fallback_prompt = MagicMock(return_value="Prompt")
                
                result = client.escalate("gpt4", "prompt", "bad code", 50)
                
                self.assertIn("GPT4 Fallback", result)
                self.assertIn("GPT Code", result)

    @patch('core.buddai_fallback.anthropic', create=True)
    def test_escalate_claude(self, mock_anthropic):
        """Test successful escalation to Claude"""
        # Setup mocks
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text="Claude Code")]
        mock_client.messages.create.return_value = mock_message
        mock_anthropic.Anthropic.return_value = mock_client

        with patch('core.buddai_fallback.HAS_CLAUDE', True, create=True):
            with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'fake_key'}):
                client = FallbackClient()
                client.claude_client = mock_client
                
                result = client.escalate("claude", "prompt", "bad code", 50)
                
                self.assertIn("Claude Fallback", result)
                self.assertIn("Claude Code", result)

    def test_extract_learning_patterns(self):
        """Test extraction of patterns from code diffs"""
        with patch.dict('os.environ', {}, clear=True):
            client = FallbackClient()
            
            buddai_code = "void setup() {\n  pinMode(13, OUTPUT);\n}"
            fallback_code = "void setup() {\n  pinMode(13, OUTPUT);\n  Serial.begin(115200);\n}"
            
            patterns = client.extract_learning_patterns(buddai_code, fallback_code)
            
            self.assertIn("Serial.begin(115200);", patterns)
            self.assertNotIn("pinMode(13, OUTPUT);", patterns)

if __name__ == '__main__':
    unittest.main()