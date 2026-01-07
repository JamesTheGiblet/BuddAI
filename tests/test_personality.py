import sys
import os
import unittest
from pathlib import Path
import json
from datetime import datetime
from unittest.mock import patch

# Add parent directory to path so we can import buddai modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from buddai_executive import BuddAI

class TestPersonality(unittest.TestCase):
    def setUp(self):
        # Suppress prints
        self.print_patcher = patch("builtins.print")
        self.print_patcher.start()
        self.ai = BuddAI(user_id="test_user", server_mode=True)

    def tearDown(self):
        self.print_patcher.stop()

    def test_identity_meta(self):
        """Verify Identity & Meta"""
        user_name = self.ai.personality_manager.get_value("identity.user_name")
        ai_name = self.ai.personality_manager.get_value("identity.ai_name")
        self.assertEqual(user_name, "James")
        self.assertEqual(ai_name, "BuddAI")

    def test_communication_style(self):
        """Verify Communication & Phrases"""
        welcome = self.ai.personality_manager.get_value("communication.welcome_message")
        phrases = self.ai.personality_manager.get_value("identity.signature_phrases")
        self.assertIn("{rule_count}", welcome)
        self.assertGreater(len(phrases), 0)

    def test_schedule_logic(self):
        """Test Schedule & Work Cycles"""
        morning_mode = self.ai.personality_manager.get_value(["work_cycles", "schedule", "weekdays", "0-4", "5.5-6.5", "mode"])
        self.assertEqual(morning_mode, "morning_build_peak")

    def test_forge_theory(self):
        """Verify Forge Theory Configuration"""
        forge_enabled = self.ai.personality_manager.get_value("forge_theory.enabled")
        k_balanced = self.ai.personality_manager.get_value("forge_theory.constants.balanced.value")
        self.assertTrue(forge_enabled)
        self.assertEqual(k_balanced, 0.1)

    def test_technical_preferences(self):
        """Verify Technical Preferences"""
        baud = self.ai.personality_manager.get_value("technical_preferences.james_patterns.serial_baud")
        self.assertIn("115200", str(baud))

    def test_interaction_modes(self):
        """Verify Interaction Modes"""
        modes = self.ai.personality_manager.get_value("interaction_modes")
        self.assertIn("morning_build", modes)
        self.assertIn("evening_build", modes)

    def test_advanced_features(self):
        """Verify Deep Key Access"""
        shadow_enabled = self.ai.personality_manager.get_value("advanced_features.shadow_suggestions.enabled")
        self.assertTrue(shadow_enabled)
        
if __name__ == "__main__":
    unittest.main()
