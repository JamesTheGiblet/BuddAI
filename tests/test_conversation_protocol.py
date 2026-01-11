#!/usr/bin/env python3
"""
Tests for Conversation Protocol (Abilities)
"""
import unittest
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Setup path
REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.buddai_abilities import ConversationProtocol

class TestConversationProtocol(unittest.TestCase):
    def setUp(self):
        self.mock_personality = MagicMock()
        self.protocol = ConversationProtocol(self.mock_personality)

    def test_detect_gratitude(self):
        self.assertTrue(self.protocol.is_conversational("i am well thank you"))
        self.assertTrue(self.protocol.is_conversational("thanks for the help"))

    def test_detect_greetings(self):
        self.assertTrue(self.protocol.is_conversational("Hi BuddAI"))
        self.assertTrue(self.protocol.is_conversational("Good morning"))

    def test_ignore_technical_requests(self):
        # Should return False because it contains technical keywords
        self.assertFalse(self.protocol.is_conversational("generate code for servo"))
        self.assertFalse(self.protocol.is_conversational("fix this compilation error"))
        self.assertFalse(self.protocol.is_conversational("thank you, now write a loop"))
        self.assertTrue(self.protocol.is_conversational("thank you how can we apply this to a battle bot"))
        self.assertTrue(self.protocol.is_conversational("great i am thinking something to do with my forge theory"))

if __name__ == '__main__':
    unittest.main()