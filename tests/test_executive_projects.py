"""
Tests for Executive Project Commands
Verifies /projects, /new, /open, /close commands work correctly
"""

import unittest
import tempfile
import os
from unittest.mock import patch, MagicMock
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from buddai_executive import BuddAI
from conversation.project_memory import ProjectMemory, Project

class TestExecutiveProjects(unittest.TestCase):
    """Test project management commands in BuddAI Executive"""
    
    def setUp(self):
        """Create isolated test environment"""
        # Create temp database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # Suppress print output
        self.print_patcher = patch('builtins.print')
        self.print_patcher.start()
        
        # Create BuddAI instance with temp database
        self.buddai = BuddAI(user_id="test_projects", server_mode=True, db_path=self.temp_db.name)
        
        # Override project memory to use temp database
        self.buddai.project_memory = ProjectMemory(self.temp_db.name)
        
    def tearDown(self):
        """Cleanup"""
        self.print_patcher.stop()
        
        # Clean up temp database
        try:
            os.unlink(self.temp_db.name)
        except:
            pass
    
    def test_projects_new_command(self):
        """Test creating a new project"""
        # Mock user input for interactive prompts
        with patch('builtins.input', side_effect=['1', 'Test robot project']):
            self.buddai._cmd_new_project('/new TestProject')
        
        # Verify project was created
        project = self.buddai.project_memory.load_project('TestProject')
        self.assertIsNotNone(project)
        self.assertEqual(project.name, 'TestProject')
        self.assertEqual(project.project_type, 'robotics')
    
    def test_projects_list_empty(self):
        """Test listing projects when none exist"""
        # Capture output
        output = []
        def capture_print(*args, **kwargs):
            output.append(' '.join(map(str, args)))
        
        self.buddai._print = capture_print
        self.buddai._cmd_list_projects()
        
        result = '\n'.join(output)
        self.assertIn("No projects yet", result)
    
    def test_projects_list_populated(self):
        """Test listing projects with existing data"""
        # Create test projects
        proj1 = Project('ProjectA', 'robotics')
        proj1.status = 'active'
        self.buddai.project_memory.save_project(proj1)
        
        proj2 = Project('ProjectB', '3d_printing')
        proj2.status = 'paused'
        self.buddai.project_memory.save_project(proj2)
        
        # Capture output
        output = []
        def capture_print(*args, **kwargs):
            output.append(' '.join(map(str, args)))
        
        self.buddai._print = capture_print
        self.buddai._cmd_list_projects()
        
        result = '\n'.join(output)
        self.assertIn("ProjectA", result)
        self.assertIn("ProjectB", result)
        self.assertIn("robotics", result)
        self.assertIn("3d_printing", result)
    
    def test_projects_usage_errors(self):
        """Test invalid command usage"""
        # Test opening non-existent project
        output = []
        def capture_print(*args, **kwargs):
            output.append(' '.join(map(str, args)))
        
        self.buddai._print = capture_print
        self.buddai._cmd_open_project('/open NonExistent')
        
        result = '\n'.join(output)
        self.assertIn("not found", result)

if __name__ == '__main__':
    unittest.main()