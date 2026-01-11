"""
Tests for Conversational Integration
"""

import unittest
import tempfile
import os
from unittest.mock import patch, MagicMock
from buddai_executive import BuddAI
from conversation.project_memory import Project

class TestConversationalIntegration(unittest.TestCase):
    
    def setUp(self):
        """Create BuddAI instance with temp database"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # Mock print to suppress output
        self.print_patcher = patch('builtins.print')
        self.print_patcher.start()
        
        # Create instance
        self.ai = BuddAI(user_id="test_user", server_mode=True)
        
        # Override project memory database
        from conversation.project_memory import ProjectMemory
        self.ai.project_memory = ProjectMemory(self.temp_db.name)
    
    def tearDown(self):
        """Cleanup"""
        self.print_patcher.stop()
        os.unlink(self.temp_db.name)
    
    def test_personality_initialized(self):
        """Test personality is initialized"""
        self.assertIsNotNone(self.ai.personality)
    
    def test_project_memory_initialized(self):
        """Test project memory is initialized"""
        self.assertIsNotNone(self.ai.project_memory)
    
    def test_greet_uses_personality(self):
        """Test greeting uses personality"""
        greeting = self.ai.personality.greet()
        
        self.assertIn('James', greeting)
        self.assertGreater(len(greeting), 10)
    
    def test_detect_new_project_intent(self):
        """Test detecting new project intent"""
        intent = self.ai.personality.understand_intent("create a new project")
        
        self.assertEqual(intent['type'], 'new_project')
        self.assertGreater(intent['confidence'], 0.7)
    
    def test_detect_idea_exploration(self):
        """Test detecting idea exploration"""
        intent = self.ai.personality.understand_intent("thinking about a robot")
        
        self.assertEqual(intent['type'], 'idea_exploration')
        self.assertTrue(intent['requires_clarification'])
    
    def test_create_project_programmatically(self):
        """Test creating project programmatically"""
        project = Project('test_robot', 'robotics')
        self.ai.project_memory.save_project(project)
        
        loaded = self.ai.project_memory.load_project('test_robot')
        
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.name, 'test_robot')
    
    def test_current_project_tracking(self):
        """Test tracking current project"""
        project = Project('active_proj', 'robotics')
        self.ai.current_project = project
        
        self.assertEqual(self.ai.current_project.name, 'active_proj')
    
    def test_save_conversation_to_project(self):
        """Test saving conversation to project"""
        project = Project('conv_test', 'general')
        project.add_conversation("test message", "test response")
        
        self.assertEqual(len(project.conversations), 1)
        self.assertEqual(project.conversations[0]['user'], 'test message')
    
    def test_intent_detection_robotics_domain(self):
        """Test detecting robotics domain"""
        intent = self.ai.personality.understand_intent("I want to build a combat robot")
        
        entities = intent.get('entities', [])
        domains = [e['value'] for e in entities if e['type'] == 'domain']
        
        self.assertIn('robotics', domains)
    
    def test_search_projects(self):
        """Test searching projects"""
        self.ai.project_memory.save_project(Project('robot_alpha', 'robotics'))
        self.ai.project_memory.save_project(Project('robot_beta', 'robotics'))
        
        results = self.ai.project_memory.search_projects('robot')
        
        self.assertGreater(len(results), 0)

if __name__ == '__main__':
    unittest.main()