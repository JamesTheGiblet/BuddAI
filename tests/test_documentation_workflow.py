"""
Tests for Documentation Workflow
"""

import unittest
import tempfile
import os
from workflows.documentation_workflow import DocumentationWorkflow

class TestDocumentationWorkflow(unittest.TestCase):
    
    def setUp(self):
        """Create workflow instance"""
        self.workflow = DocumentationWorkflow()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up temp directory"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initialization(self):
        """Test workflow initializes"""
        self.assertEqual(self.workflow.name, 'generate_documentation')
        self.assertIsNotNone(self.workflow.description)
    
    def test_detect_high_confidence(self):
        """Test high confidence detection"""
        confidence = self.workflow.detect('generate documentation for this project')
        self.assertGreater(confidence, 0.8)
    
    def test_detect_medium_confidence(self):
        """Test medium confidence detection"""
        confidence = self.workflow.detect('create docs please')
        self.assertGreater(confidence, 0.5)
    
    def test_detect_low_confidence(self):
        """Test low confidence detection"""
        confidence = self.workflow.detect('fix the bug')
        self.assertLess(confidence, 0.3)
    
    def test_plan_creates_steps(self):
        """Test plan creates workflow steps"""
        steps = self.workflow.plan('generate documentation')
        
        self.assertGreater(len(steps), 0)
        self.assertTrue(any('readme' in s.name.lower() for s in steps))
    
    def test_detect_project_type_python(self):
        """Test Python project detection"""
        # Create requirements.txt
        req_file = os.path.join(self.temp_dir, 'requirements.txt')
        with open(req_file, 'w') as f:
            f.write('pytest\n')
        
        project_type = self.workflow._detect_project_type(self.temp_dir)
        self.assertEqual(project_type, 'python')
    
    def test_detect_project_type_javascript(self):
        """Test JavaScript project detection"""
        # Create package.json
        pkg_file = os.path.join(self.temp_dir, 'package.json')
        with open(pkg_file, 'w') as f:
            f.write('{}')
        
        project_type = self.workflow._detect_project_type(self.temp_dir)
        self.assertEqual(project_type, 'javascript')
    
    def test_find_source_files(self):
        """Test finding source files"""
        # Create test files
        test_file = os.path.join(self.temp_dir, 'test.py')
        with open(test_file, 'w') as f:
            f.write('# test')
        
        files = self.workflow._find_source_files(self.temp_dir)
        
        self.assertGreater(len(files), 0)
        self.assertTrue(any('test.py' in f for f in files))
    
    def test_generate_readme(self):
        """Test README generation"""
        context = {'project_info': {'type': 'python', 'has_tests': True, 'test_framework': 'pytest'}}
        
        result = self.workflow._generate_readme({}, context)
        
        self.assertIn('file', result)
        self.assertEqual(result['file'], 'README.md')
        self.assertIn('content', result)
        self.assertIn('# ', result['content'])
    
    def test_generate_architecture(self):
        """Test architecture doc generation"""
        context = {'project_info': {}}
        
        result = self.workflow._generate_architecture({}, context)
        
        self.assertEqual(result['file'], 'ARCHITECTURE.md')
        self.assertIn('Architecture', result['content'])
    
    def test_generate_contributing(self):
        """Test contributing guide generation"""
        result = self.workflow._generate_contributing({}, {})
        
        self.assertEqual(result['file'], 'CONTRIBUTING.md')
        self.assertIn('Contributing', result['content'])
    
    def test_analyze_project(self):
        """Test project analysis"""
        params = {'path': self.temp_dir}
        context = {}
        
        result = self.workflow._analyze_project(params, context)
        
        self.assertIn('type', result)
        self.assertIn('source_files', result)

if __name__ == '__main__':
    unittest.main()