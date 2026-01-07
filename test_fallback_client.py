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
                client.client = mock_model
                
                result = client.escalate_to_gemini("prompt", "bad code", 50)
                
                self.assertIn("Gemini Fallback", result)
                self.assertIn("Fixed Code", result)

    def test_escalate_no_key(self):
        """Test behavior when API key is missing"""
        with patch.dict('os.environ', {}, clear=True):
            client = FallbackClient()
            result = client.escalate_to_gemini("prompt", "bad code", 50)
            self.assertIn("Fallback unavailable", result)

if __name__ == '__main__':
    unittest.main()