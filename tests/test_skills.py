import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add parent directory to path so we can import 'skills'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skills import load_registry

class TestSkills(unittest.TestCase):
    
    def setUp(self):
        self.registry = load_registry()

    def test_registry_loading(self):
        """Ensure skills are discovered and loaded"""
        self.assertGreater(len(self.registry), 0, "No skills loaded")
        # Check for core skills
        self.assertIn("calculator", self.registry)
        self.assertIn("weather", self.registry)
        self.assertIn("timer", self.registry)
        self.assertIn("system_info", self.registry)
        self.assertIn("test_all", self.registry)

    def test_calculator_logic(self):
        """Verify calculator skill math"""
        calc = self.registry["calculator"]["run"]
        self.assertIn("4", calc("Calculate 2 + 2"))
        self.assertIn("25", calc("5 * 5"))
        self.assertIsNone(calc("No math here"))

    def test_timer_parsing(self):
        """Verify timer parses duration correctly"""
        timer = self.registry["timer"]["run"]
        # We use 0 seconds to avoid waiting during tests
        response = timer("Set a timer for 0 seconds")
        self.assertIn("Timer started", response)

    @patch('urllib.request.urlopen')
    def test_weather_mock(self, mock_urlopen):
        """Verify weather skill with mocked network"""
        # Mock the API response so tests work offline
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b"London: +15C"
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        weather = self.registry["weather"]["run"]
        result = weather("Weather in London")
        
        self.assertIn("London: +15C", result)

if __name__ == '__main__':
    unittest.main()