"""
Tests for Executive Project Commands
"""
import unittest
import sqlite3
import os
import tempfile
import sys
from unittest.mock import MagicMock, patch

from buddai_executive import BuddAI

# Ensure we can import from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestExecutiveProjects(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment with mocked DB and dependencies"""
        # Create temporary database
        self.db_fd, self.db_path = tempfile.mkstemp()
        os.close(self.db_fd)
        
        # Patch DB_PATH in buddai_executive to use our temp db
        self.db_patcher = patch('buddai_executive.DB_PATH', self.db_path)
        self.db_patcher.start()
        
        # Mock heavy dependencies to allow lightweight BuddAI instantiation
        self.patches = [
            patch('buddai_executive.StorageManager'),
            patch('buddai_executive.PersonalityManager'),
            patch('buddai_executive.ShadowSuggestionEngine'),
            patch('buddai_executive.SmartLearner'),
            patch('buddai_executive.HardwareProfile'),
            patch('buddai_executive.ValidatorRegistry'),
            patch('buddai_executive.ConfidenceScorer'),
            patch('buddai_executive.FallbackClient'),
            patch('buddai_executive.ConversationProtocol'),
            patch('buddai_executive.RepoManager'),
            patch('buddai_executive.OllamaClient'),
            patch('buddai_executive.PromptEngine'),
            patch('buddai_executive.load_registry', return_value={}),
            patch('buddai_executive.get_language_registry'),
            patch('buddai_executive.WorkflowDetector'),
            patch('buddai_executive.ModelFineTuner'),
            patch('buddai_executive.LearningMetrics'),
            patch('buddai_executive.AdaptiveLearner'),
            patch('builtins.print')  # Suppress startup prints
        ]
        
        for p in self.patches:
            p.start()
            
        # Initialize BuddAI
        self.ai = BuddAI(server_mode=False)

    def tearDown(self):
        """Clean up"""
        self.db_patcher.stop()
        for p in self.patches:
            p.stop()
        os.unlink(self.db_path)

    def test_projects_new_command(self):
        """Test creating a new project"""
        cmd = "/projects new GilBot"
        response = self.ai._handle_projects_command(cmd)
        
        self.assertIn("Project 'GilBot' created", response)
        
        # Verify in DB
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT name, status FROM projects WHERE name=?", ('GilBot',))
        row = c.fetchone()
        conn.close()
        
        self.assertIsNotNone(row)
        self.assertEqual(row[0], 'GilBot')
        self.assertEqual(row[1], 'active')

    def test_projects_list_empty(self):
        """Test listing projects when none exist"""
        cmd = "/projects list"
        response = self.ai._handle_projects_command(cmd)
        
        self.assertIn("No active projects", response)
        self.assertIn("Use /projects new", response)

    def test_projects_list_populated(self):
        """Test listing projects with existing data"""
        # Pre-populate DB
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY, name TEXT, status TEXT, created_at TEXT)")
        c.execute("INSERT INTO projects (name, status, created_at) VALUES (?, ?, ?)", ('ProjectA', 'active', '2023-01-01'))
        c.execute("INSERT INTO projects (name, status, created_at) VALUES (?, ?, ?)", ('ProjectB', 'active', '2023-01-02'))
        conn.commit()
        conn.close()
        
        cmd = "/projects list"
        response = self.ai._handle_projects_command(cmd)
        
        self.assertIn("Projects:", response)
        self.assertIn("- ProjectA (active)", response)
        self.assertIn("- ProjectB (active)", response)

    def test_projects_usage_errors(self):
        """Test invalid command usage"""
        # Missing name
        cmd = "/projects new"
        response = self.ai._handle_projects_command(cmd)
        self.assertIn("Usage:", response)
        
        # Unknown action
        cmd = "/projects delete"
        response = self.ai._handle_projects_command(cmd)
        self.assertIn("Usage:", response)

if __name__ == '__main__':
    unittest.main()