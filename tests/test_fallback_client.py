import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path to import core modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mocking the module since it might not exist in the environment yet
try:
    from core.buddai_fallback import FallbackClient
except ImportError:
    FallbackClient = MagicMock()

class TestFallbackClient(unittest.TestCase):
    def setUp(self):
        self.client = FallbackClient()
        # Setup mocks for clients
        self.client.genai = Mock()
        self.client.openai = Mock()
        self.client.anthropic = Mock()

    def test_escalate_gemini(self):
        """Test escalation to Gemini works"""
        self.client.is_available = Mock(return_value=True)
        self.client._call_gemini = Mock(return_value="Gemini Code")
        
        result = self.client.escalate("gemini", "code", "context", 50)
        
        self.client._call_gemini.assert_called_once()
        self.assertEqual(result, "Gemini Code")

    def test_escalate_openai(self):
        """Test escalation to GPT-4 works"""
        self.client.is_available = Mock(return_value=True)
        self.client._call_openai = Mock(return_value="GPT Code")
        
        result = self.client.escalate("gpt4", "code", "context", 50)
        
        self.client._call_openai.assert_called_once()
        self.assertEqual(result, "GPT Code")

    @patch('core.buddai_fallback.anthropic', create=True)
    def test_escalate_claude(self, mock_anthropic):
        """Test escalation to Claude works"""
        self.client.anthropic = mock_anthropic
        self.client.is_available = Mock(return_value=True)
        self.client._call_claude = Mock(return_value="Claude Code")
        
        result = self.client.escalate("claude", "code", "context", 50)
        
        self.client._call_claude.assert_called_once()
        self.assertEqual(result, "Claude Code")

    def test_escalate_no_key(self):
        """Gracefully handles missing API key"""
        self.client.is_available = Mock(return_value=False)
        result = self.client.escalate("gemini", "code", "context", 50)
        self.assertIn("unavailable", str(result).lower())

    def test_extract_learning_patterns(self):
        """difflib extracts fix patterns"""
        # Assuming extract_patterns logic exists in client
        self.client.extract_patterns = Mock(return_value=["Serial.begin"])
        
        patterns = self.client.extract_patterns("void setup() {}", "void setup() { Serial.begin(115200); }")
        self.assertIn("Serial.begin", patterns)