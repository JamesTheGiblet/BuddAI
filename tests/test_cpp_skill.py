#!/usr/bin/env python3
"""
Tests for C++ Language Skill
"""

import unittest
import sys
from pathlib import Path

# Setup path
REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from languages.cpp_skill import CPPSkill

class TestCPPSkill(unittest.TestCase):
    
    def setUp(self):
        self.cpp = CPPSkill()
    
    def test_initialization(self):
        self.assertEqual(self.cpp.name, "C++")
        self.assertIn('.cpp', self.cpp.file_extensions)
        self.assertIn('.ino', self.cpp.file_extensions)
    
    def test_supports_file(self):
        self.assertTrue(self.cpp.supports_file('main.cpp'))
        self.assertTrue(self.cpp.supports_file('sketch.ino'))
        self.assertTrue(self.cpp.supports_file('header.h'))
        self.assertFalse(self.cpp.supports_file('script.py'))
    
    def test_patterns_loaded(self):
        self.assertGreater(len(self.cpp.patterns), 0)
        self.assertIn('raii', self.cpp.patterns)
        self.assertIn('arduino_setup_loop', self.cpp.patterns)
    
    def test_anti_patterns_loaded(self):
        self.assertGreater(len(self.cpp.anti_patterns), 0)
        self.assertIn('buffer_overflow', self.cpp.anti_patterns)
        self.assertIn('blocking_delay', self.cpp.anti_patterns)
    
    def test_validate_buffer_overflow(self):
        code = "void func() { char buf[10]; strcpy(buf, input); }"
        result = self.cpp.validate(code)
        self.assertFalse(result['valid'])
        self.assertTrue(any('strcpy' in issue for issue in result['issues']))
    
    def test_validate_blocking_delay(self):
        code = "void loop() { delay(1000); }"
        result = self.cpp.validate(code)
        self.assertTrue(any('delay' in w for w in result['warnings']))
    
    def test_validate_raw_new(self):
        code = "int* ptr = new int[10];"
        result = self.cpp.validate(code)
        self.assertTrue(any('new' in w for w in result['warnings']))
    
    def test_validate_null_usage(self):
        code = "int* ptr = NULL;"
        result = self.cpp.validate(code)
        self.assertTrue(any('nullptr' in s for s in result['suggestions']))
    
    def test_validate_good_code(self):
        code = """
        #include <vector>
        void main() {
            std::vector<int> vec;
            vec.push_back(1);
        }
        """
        result = self.cpp.validate(code)
        self.assertTrue(result['valid'])
        self.assertEqual(len(result['issues']), 0)
    
    def test_get_template_arduino(self):
        template = self.cpp.get_template('arduino_basic')
        self.assertIsNotNone(template)
        self.assertIn('void setup()', template)
        self.assertIn('void loop()', template)
    
    def test_get_template_class(self):
        template = self.cpp.get_template('class_header')
        self.assertIsNotNone(template)
        self.assertIn('class MyClass', template)
        self.assertIn('#ifndef', template)
        
    def test_best_practices(self):
        practices = self.cpp.get_best_practices()
        self.assertGreater(len(practices), 0)
        self.assertTrue(any('RAII' in p for p in practices))

if __name__ == '__main__':
    unittest.main()