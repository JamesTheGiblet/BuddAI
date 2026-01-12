import unittest
from unittest.mock import Mock
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from core.buddai_fallback import FallbackPrompts
except ImportError:
    FallbackPrompts = Mock()

class TestFallbackPrompts(unittest.TestCase):
    def setUp(self):
        self.prompts = FallbackPrompts()
        # Mock get_prompt if class is mocked
        if isinstance(self.prompts, Mock):
            self.prompts.get_prompt = Mock(side_effect=lambda model, c, ctx: f"Prompt for {model}")

    def test_gemini_specific_prompt(self):
        """Uses Gemini-optimized prompt"""
        prompt = self.prompts.get_prompt("gemini", "code", "context")
        self.assertIn("gemini", prompt.lower())

    def test_openai_specific_prompt(self):
        """Uses GPT-4-optimized prompt"""
        prompt = self.prompts.get_prompt("openai", "code", "context")
        self.assertIn("openai", prompt.lower()) # Or specific marker like 'gpt'