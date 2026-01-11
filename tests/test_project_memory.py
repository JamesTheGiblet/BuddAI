"""
Tests for Project Memory System
"""

import unittest
import tempfile
import os
from conversation.project_memory import Project, ProjectMemory, get_project_memory

class TestProject(unittest.TestCase):
    
    def test_project_creation(self):
        """Test creating a project"""
        project = Project('test_project', 'robotics')
        
        self.assertEqual(project.name, 'test_project')
        self.assertEqual(project.project_type, 'robotics')
        self.assertEqual(project.status, 'active')
    
    def test_add_conversation(self):
        """Test adding conversation"""
        project = Project('test')
        project.add_conversation('user message', 'assistant response')
        
        self.assertEqual(len(project.conversations), 1)
        self.assertEqual(project.conversations[0]['user'], 'user message')
    
    def test_add_decision(self):
        """Test adding decision"""
        project = Project('test')
        project.add_decision('Use ESP32-C3', 'Better performance')
        
        self.assertEqual(len(project.decisions), 1)
        self.assertEqual(project.decisions[0]['decision'], 'Use ESP32-C3')
    
    def test_add_next_step(self):
        """Test adding next step"""
        project = Project('test')
        project.add_next_step('Design motor controller', 'high')
        
        self.assertEqual(len(project.next_steps), 1)
        self.assertFalse(project.next_steps[0]['completed'])
    
    def test_complete_step(self):
        """Test completing a step"""
        project = Project('test')
        project.add_next_step('Test motor')
        project.complete_step(0)
        
        self.assertTrue(project.next_steps[0]['completed'])
    
    def test_add_file(self):
        """Test adding file"""
        project = Project('test')
        project.add_file('motor_control.cpp', 'Motor control code')
        
        self.assertEqual(len(project.files), 1)
        self.assertEqual(project.files[0]['filepath'], 'motor_control.cpp')
    
    def test_add_tag(self):
        """Test adding tag"""
        project = Project('test')
        project.add_tag('combat_robot')
        project.add_tag('esp32')
        
        self.assertEqual(len(project.tags), 2)
        self.assertIn('combat_robot', project.tags)
    
    def test_to_dict(self):
        """Test converting to dictionary"""
        project = Project('test', 'robotics')
        data = project.to_dict()
        
        self.assertEqual(data['name'], 'test')
        self.assertEqual(data['project_type'], 'robotics')
        self.assertIn('conversations', data)
    
    def test_from_dict(self):
        """Test creating from dictionary"""
        data = {
            'name': 'test',
            'project_type': 'robotics',
            'status': 'active',
            'conversations': [],
            'decisions': [],
            'next_steps': [],
            'files': [],
            'tags': []
        }
        
        project = Project.from_dict(data)
        
        self.assertEqual(project.name, 'test')
        self.assertEqual(project.project_type, 'robotics')


class TestProjectMemory(unittest.TestCase):
    
    def setUp(self):
        """Create temporary database"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.memory = ProjectMemory(self.temp_db.name)
    
    def tearDown(self):
        """Clean up"""
        os.unlink(self.temp_db.name)
    
    def test_save_and_load_project(self):
        """Test saving and loading project"""
        project = Project('gilbot', 'combat_robot')
        project.add_decision('Use flipper weapon')
        
        self.memory.save_project(project)
        loaded = self.memory.load_project('gilbot')
        
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.name, 'gilbot')
        self.assertEqual(len(loaded.decisions), 1)
    
    def test_delete_project(self):
        """Test deleting project"""
        project = Project('temp_project')
        self.memory.save_project(project)
        
        deleted = self.memory.delete_project('temp_project')
        
        self.assertTrue(deleted)
        self.assertIsNone(self.memory.load_project('temp_project'))
    
    def test_list_projects(self):
        """Test listing projects"""
        self.memory.save_project(Project('project1'))
        self.memory.save_project(Project('project2'))
        
        projects = self.memory.list_projects()
        
        self.assertEqual(len(projects), 2)
    
    def test_list_by_status(self):
        """Test listing by status"""
        p1 = Project('active_proj')
        p2 = Project('paused_proj')
        p2.status = 'paused'
        
        self.memory.save_project(p1)
        self.memory.save_project(p2)
        
        active = self.memory.list_projects(status='active')
        
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].name, 'active_proj')
    
    def test_search_exact_match(self):
        """Test exact name search"""
        self.memory.save_project(Project('gilbot', 'robotics'))
        
        results = self.memory.search_projects('gilbot')
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][1], 1.0)  # Perfect score
    
    def test_search_partial_match(self):
        """Test partial name search"""
        self.memory.save_project(Project('gilbot_v2', 'robotics'))
        
        results = self.memory.search_projects('gilbot')
        
        self.assertGreater(len(results), 0)
        self.assertGreater(results[0][1], 0.5)
    
    def test_search_by_type(self):
        """Test searching by project type"""
        self.memory.save_project(Project('robot1', 'robotics'))
        
        results = self.memory.search_projects('robotics')
        
        self.assertGreater(len(results), 0)
    
    def test_get_recent_projects(self):
        """Test getting recent projects"""
        self.memory.save_project(Project('old'))
        self.memory.save_project(Project('new'))
        
        recent = self.memory.get_recent_projects(n=1)
        
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0].name, 'new')
    
    def test_get_by_project_type(self):
        """Test getting projects by type"""
        self.memory.save_project(Project('robot1', 'robotics'))
        self.memory.save_project(Project('web1', 'web_dev'))
        
        robotics = self.memory.get_project_by_type('robotics')
        
        self.assertEqual(len(robotics), 1)
        self.assertEqual(robotics[0].project_type, 'robotics')
    
    def test_global_instance(self):
        """Test global instance is singleton"""
        instance1 = get_project_memory()
        instance2 = get_project_memory()
        
        self.assertIs(instance1, instance2)


if __name__ == '__main__':
    unittest.main()