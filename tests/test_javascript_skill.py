"""
Tests for JavaScript Language Skill
"""

import unittest
from languages.javascript_skill import JavaScriptSkill

class TestJavaScriptSkill(unittest.TestCase):
    
    def setUp(self):
        """Create JavaScript skill instance"""
        self.js = JavaScriptSkill()
    
    def test_initialization(self):
        """Test JavaScript skill initializes correctly"""
        self.assertEqual(self.js.name, "JavaScript")
        self.assertIn('.js', self.js.file_extensions)
        self.assertIn('.jsx', self.js.file_extensions)
    
    def test_supports_file(self):
        """Test file extension detection"""
        self.assertTrue(self.js.supports_file('app.js'))
        self.assertTrue(self.js.supports_file('Component.jsx'))
        self.assertTrue(self.js.supports_file('module.mjs'))
        self.assertFalse(self.js.supports_file('style.css'))
    
    def test_patterns_loaded(self):
        """Test that patterns are loaded"""
        self.assertGreater(len(self.js.patterns), 0)
        self.assertIn('arrow_functions', self.js.patterns)
        self.assertIn('async_await', self.js.patterns)
    
    def test_anti_patterns_loaded(self):
        """Test that anti-patterns are loaded"""
        self.assertGreater(len(self.js.anti_patterns), 0)
        self.assertIn('var_keyword', self.js.anti_patterns)
        self.assertIn('loose_equality', self.js.anti_patterns)
    
    def test_validate_var_usage(self):
        """Test validation catches var usage"""
        code = 'var x = 10;\nvar y = 20;'
        result = self.js.validate(code)
        
        self.assertTrue(any('var' in warning for warning in result['warnings']))
    
    def test_validate_loose_equality(self):
        """Test validation catches loose equality"""
        code = 'if (x == 5) { console.log("test"); }'
        result = self.js.validate(code)
        
        self.assertTrue(any('loose equality' in warning.lower() for warning in result['warnings']))
    
    def test_validate_missing_error_handling(self):
        """Test validation catches missing error handling in async code"""
        code = '''
        async function getData() {
          const response = await fetch(url);
          return response.json();
        }
        '''
        result = self.js.validate(code)
        
        self.assertTrue(any('error handling' in warning.lower() for warning in result['warnings']))
    
    def test_validate_eval_usage(self):
        """Test validation catches eval usage"""
        code = 'const result = eval("2 + 2");'
        result = self.js.validate(code)
        
        self.assertFalse(result['valid'])
        self.assertTrue(any('eval' in issue.lower() for issue in result['issues']))
    
    def test_validate_good_javascript(self):
        """Test validation passes for modern JavaScript"""
        code = '''
        const fetchData = async (url) => {
          try {
            const response = await fetch(url);
            const data = await response.json();
            return data;
          } catch (error) {
            console.error(error);
            throw error;
          }
        };
        '''
        result = self.js.validate(code)
        
        self.assertTrue(result['valid'])
        self.assertEqual(len(result['issues']), 0)
    
    def test_get_template_async_fetch(self):
        """Test getting async fetch template"""
        template = self.js.get_template('async_fetch')
        
        self.assertIsNotNone(template)
        self.assertIn('async', template)
        self.assertIn('await', template)
        self.assertIn('try', template)
    
    def test_get_template_dom_manipulation(self):
        """Test getting DOM manipulation template"""
        template = self.js.get_template('dom_manipulation')
        
        self.assertIsNotNone(template)
        self.assertIn('querySelector', template)
        self.assertIn('addEventListener', template)
    
    def test_get_template_array_operations(self):
        """Test getting array operations template"""
        template = self.js.get_template('array_operations')
        
        self.assertIsNotNone(template)
        self.assertIn('.map(', template)
        self.assertIn('.filter(', template)
        self.assertIn('.reduce(', template)
    
    def test_common_pitfalls(self):
        """Test common pitfalls are documented"""
        pitfalls = self.js.get_common_pitfalls()
        
        self.assertGreater(len(pitfalls), 0)
        self.assertTrue(any('var' in p for p in pitfalls))
    
    def test_es6_features(self):
        """Test ES6+ features list"""
        features = self.js.get_es6_features()
        
        self.assertGreater(len(features), 0)
        self.assertTrue(any('arrow' in f.lower() for f in features))
        self.assertTrue(any('async' in f.lower() for f in features))
    
    def test_performance_tips(self):
        """Test performance tips are provided"""
        tips = self.js.get_performance_tips()
        
        self.assertGreater(len(tips), 0)
        self.assertTrue(any('debounce' in tip.lower() for tip in tips))

if __name__ == '__main__':
    unittest.main()