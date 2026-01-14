import unittest
import sys
import os
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add repo root to path
REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import buddai_executive
from conversation.project_memory import Project
import conversation.project_memory

class TestExecutiveProjects(unittest.TestCase):
    def setUp(self):
        # Create temp DB
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.db_fd)
        self.db_path_obj = Path(self.db_path)
        
        # Reset ProjectMemory singleton and initialize with temp DB
        self.original_project_memory = conversation.project_memory._project_memory
        conversation.project_memory._project_memory = conversation.project_memory.ProjectMemory(self.db_path)
        
        # Patch DB paths
        self.patches = [
            patch('buddai_executive.DB_PATH', self.db_path_obj),
            patch('builtins.print')
        ]
        for p in self.patches:
            p.start()
            
        self.buddai = buddai_executive.BuddAI(server_mode=False, db_path=self.db_path_obj)

    def tearDown(self):
        if self.buddai:
            self.buddai.close()
        
        for p in reversed(self.patches):
            p.stop()
            
        # Restore original ProjectMemory
        conversation.project_memory._project_memory = self.original_project_memory
            
        if os.path.exists(self.db_path):
            try:
                os.unlink(self.db_path)
            except PermissionError:
                pass

    def test_projects_list_empty(self):
        """Test listing projects when none exist"""
        with patch('builtins.print') as mock_print:
            self.buddai.handle_slash_command("/projects")
            # Check if any print call contained the expected message
            found = False
            for call in mock_print.call_args_list:
                if "No projects yet" in str(call):
                    found = True
                    break
            # If handle_slash_command returns string instead of printing
            res = self.buddai.handle_slash_command("/projects")
            if "No projects yet" in str(res):
                found = True
            self.assertTrue(found)

    def test_projects_new_command(self):
        """Test creating a new project"""
        with patch('builtins.input', side_effect=["1", "Test Description"]):
            self.buddai.handle_slash_command("/new GilBot")
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name, status FROM projects WHERE name=?", ('GilBot',))
        row = cursor.fetchone()
        conn.close()
        
        self.assertIsNotNone(row)
        self.assertEqual(row[0], 'GilBot')
        self.assertEqual(row[1], 'active')

    def test_projects_list_populated(self):
        """Test listing projects with existing data"""
        # Create a project first
        project = Project("ExistingBot", "robotics")
        project.status = "active"
        self.buddai.project_memory.save_project(project)
        
        res = self.buddai.handle_slash_command("/projects")
        self.assertIn("ExistingBot", str(res))

    def test_projects_usage_errors(self):
        """Test invalid command usage"""
        res = self.buddai.handle_slash_command("/open")
        self.assertIn("Usage:", str(res))

if __name__ == '__main__':
    unittest.main()