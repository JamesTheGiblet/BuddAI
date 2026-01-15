import sys
import os
import unittest
from pathlib import Path
import tempfile
import json
from datetime import datetime
from unittest.mock import patch

# Add parent directory to path so we can import buddai modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from buddai_executive import BuddAI
from conversation.personality import BuddAIPersonality

class TestPersonalityManager(unittest.TestCase):
    def setUp(self):
        # Create temp DB
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.db_fd)
        self.db_path_obj = Path(self.db_path)

        # Patch DB paths to use temp DB
        self.patches = [
            patch('core.buddai_shared.DB_PATH', self.db_path_obj),
            patch('core.buddai_storage.DB_PATH', self.db_path_obj),
            patch('buddai_executive.DB_PATH', self.db_path_obj),
            patch('builtins.print')
        ]
        for p in self.patches:
            p.start()

        self.ai = BuddAI(user_id="test_user", server_mode=True)

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        if os.path.exists(self.db_path):
            try:
                os.unlink(self.db_path)
            except PermissionError:
                pass

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

class TestBuddAIPersonality(unittest.TestCase):
    
    def setUp(self):
        """Create personality instance"""
        self.personality = BuddAIPersonality()
    
    def test_initialization(self):
        """Test personality initializes"""
        self.assertIsNotNone(self.personality)
        self.assertEqual(self.personality.traits['name'], 'BuddAI')
    
    def test_understand_intent_greeting(self):
        """Test detecting greetings"""
        intent = self.personality.understand_intent("hi")
        self.assertEqual(intent['type'], 'greeting')
        self.assertGreater(intent['confidence'], 0.9)

    def test_understand_intent_how_are_you(self):
        """Test detecting personal status questions"""
        intent = self.personality.understand_intent("hi how are you?")
        self.assertEqual(intent['type'], 'greeting')
        self.assertGreater(intent['confidence'], 0.9)

    def test_greet_generates_message(self):
        """Test greeting generation"""
        greeting = self.personality.greet()
        
        self.assertIn('James', greeting)
        self.assertGreater(len(greeting), 10)
    
    def test_understand_intent_idea_exploration(self):
        """Test detecting idea exploration"""
        intent = self.personality.understand_intent("I was thinking about a robot that spins")
        
        self.assertEqual(intent['type'], 'idea_exploration')
        self.assertGreater(intent['confidence'], 0.5)
        self.assertTrue(intent['requires_clarification'])
    
    def test_understand_intent_continue_project(self):
        """Test detecting continuation intent"""
        intent = self.personality.understand_intent("continue where we left off")
        
        self.assertEqual(intent['type'], 'continue_project')
        self.assertGreater(intent['confidence'], 0.8)
    
    def test_understand_intent_new_project(self):
        """Test detecting new project intent"""
        intent = self.personality.understand_intent("start a new project")
        
        self.assertEqual(intent['type'], 'new_project')
        self.assertGreater(intent['confidence'], 0.8)
    
    def test_understand_intent_new_one(self):
        """Test detecting new project from 'new one'"""
        intent = self.personality.understand_intent("new one")
        self.assertEqual(intent['type'], 'new_project')
        self.assertGreater(intent['confidence'], 0.8)

    def test_understand_intent_question(self):
        """Test detecting questions"""
        intent = self.personality.understand_intent("how does this work?")
        
        self.assertEqual(intent['type'], 'question')
        self.assertGreater(intent['confidence'], 0.8)
    
    def test_generate_clarifying_questions_robotics(self):
        """Test generating questions for robotics"""
        intent = {
            'type': 'idea_exploration',
            'entities': [{'type': 'domain', 'value': 'robotics'}]
        }
        
        questions = self.personality.generate_clarifying_questions(intent)
        
        self.assertGreater(len(questions), 0)
        self.assertTrue(any('GilBot' in q or 'ESP32' in q for q in questions))
    
    def test_respond_naturally_idea_exploration(self):
        """Test natural response to idea"""
        intent = {
            'type': 'idea_exploration',
            'entities': [{'type': 'domain', 'value': 'robotics'}]
        }
        
        response = self.personality.respond_naturally("thinking about a spinner", intent)
        
        self.assertIn('robot', response.lower())
        self.assertGreater(len(response), 20)

    def test_respond_naturally_greeting(self):
        """Test natural response to greeting"""
        intent = {'type': 'greeting'}
        response = self.personality.respond_naturally("hi", intent)
        
        self.assertIn('James', response)
        self.assertIn('?', response) # Should ask a question
    
    def test_remember_conversation(self):
        """Test conversation memory"""
        self.personality.remember_conversation(
            "test message",
            "test response",
            {'context': 'test'}
        )
        
        self.assertEqual(len(self.personality.conversation_history), 1)
        self.assertEqual(self.personality.conversation_history[0]['user'], 'test message')
    
    def test_conversation_summary(self):
        """Test getting conversation summary"""
        self.personality.remember_conversation("msg1", "resp1")
        self.personality.remember_conversation("msg2", "resp2")
        
        summary = self.personality.get_conversation_summary(last_n=2)
        
        self.assertIn('msg1', summary)
        self.assertIn('msg2', summary)
    
    def test_detect_robotics_domain(self):
        """Test detecting robotics domain"""
        intent = self.personality.understand_intent("thinking about a battle bot")
        
        entities = intent.get('entities', [])
        domains = [e['value'] for e in entities if e['type'] == 'domain']
        
        self.assertIn('robotics', domains)
    
    def test_detect_3d_printing_domain(self):
        """Test detecting 3D printing domain"""
        intent = self.personality.understand_intent("idea for 3d printer optimization")
        
        entities = intent.get('entities', [])
        domains = [e['value'] for e in entities if e['type'] == 'domain']
        
        self.assertIn('3d_printing', domains)
        
if __name__ == "__main__":
    unittest.main()
