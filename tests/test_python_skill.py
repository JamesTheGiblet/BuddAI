#!/usr/bin/env python3
"""
Tests for Python Language Skill
"""

import unittest
import sys
from pathlib import Path

from languages.python_skill import PythonSkill

# Setup path
REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


class TestPythonSkill(unittest.TestCase):
    
    def setUp(self):
        """Create Python skill instance"""
        self.python = PythonSkill()
    
    def test_initialization(self):
        """Test Python skill initializes correctly"""
        self.assertEqual(self.python.name, "Python")
        self.assertIn('.py', self.python.file_extensions)
    
    def test_supports_file(self):
        """Test file extension detection"""
        self.assertTrue(self.python.supports_file('script.py'))
        self.assertTrue(self.python.supports_file('test.py'))
        self.assertFalse(self.python.supports_file('script.js'))
    
    def test_patterns_loaded(self):
        """Test that patterns are loaded"""
        self.assertGreater(len(self.python.patterns), 0)
        self.assertIn('list_comprehension', self.python.patterns)
        self.assertIn('context_managers', self.python.patterns)
    
    def test_anti_patterns_loaded(self):
        """Test that anti-patterns are loaded"""
        self.assertGreater(len(self.python.anti_patterns), 0)
        self.assertIn('mutable_default_args', self.python.anti_patterns)
        self.assertIn('bare_except', self.python.anti_patterns)
    
    def test_validate_mutable_default(self):
        """Test validation catches mutable default arguments"""
        code = "def add_item(item, items=[]): pass"
        result = self.python.validate(code)
        
        self.assertFalse(result['valid'])
        self.assertTrue(any('mutable default' in issue.lower() for issue in result['issues']))
    
    def test_validate_bare_except(self):
        """Test validation catches bare except clauses"""
        code = "try: pass\nexcept: pass"
        result = self.python.validate(code)
        
        self.assertFalse(result['valid'])
        self.assertTrue(any('bare except' in issue.lower() for issue in result['issues']))
    
    def test_validate_print_statements(self):
        """Test validation warns about print statements"""
        code = "print('debug')"
        result = self.python.validate(code)
        
        self.assertTrue(any('print' in warning.lower() for warning in result['warnings']))
    
    def test_validate_global_variables(self):
        """Test validation warns about global variables"""
        code = "def func():\n    global count\n    count += 1"
        result = self.python.validate(code)
        self.assertTrue(any('global' in warning.lower() for warning in result['warnings']))
    
    def test_validate_good_code(self):
        """Test validation passes for good Python code"""
        code = """
def add_item(item, items=None):
    if items is None:
        items = []
    items.append(item)
    return items
"""
        result = self.python.validate(code)
        self.assertTrue(result['valid'])
        self.assertEqual(len(result['issues']), 0)
    
    def test_get_template_script(self):
        """Test getting basic script template"""
        template = self.python.get_template('script')
        
        self.assertIsNotNone(template)
        self.assertIn('if __name__ == "__main__":', template)
    
    def test_get_template_class(self):
        """Test getting class template"""
        template = self.python.get_template('class')
        
        self.assertIsNotNone(template)
        self.assertIn('class', template)
        self.assertIn('__init__', template)

if __name__ == '__main__':
    unittest.main()