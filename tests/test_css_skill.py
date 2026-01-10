"""
Tests for CSS Language Skill
"""

import unittest
from languages.css_skill import CSSSkill

class TestCSSSkill(unittest.TestCase):
    
    def setUp(self):
        """Create CSS skill instance"""
        self.css = CSSSkill()
    
    def test_initialization(self):
        """Test CSS skill initializes correctly"""
        self.assertEqual(self.css.name, "CSS")
        self.assertIn('.css', self.css.file_extensions)
        self.assertIn('.scss', self.css.file_extensions)
    
    def test_supports_file(self):
        """Test file extension detection"""
        self.assertTrue(self.css.supports_file('style.css'))
        self.assertTrue(self.css.supports_file('main.scss'))
        self.assertFalse(self.css.supports_file('index.html'))
    
    def test_patterns_loaded(self):
        """Test that patterns are loaded"""
        self.assertGreater(len(self.css.patterns), 0)
        self.assertIn('flexbox', self.css.patterns)
        self.assertIn('grid', self.css.patterns)
    
    def test_anti_patterns_loaded(self):
        """Test that anti-patterns are loaded"""
        self.assertGreater(len(self.css.anti_patterns), 0)
        self.assertIn('important_overuse', self.css.anti_patterns)
    
    def test_validate_excessive_important(self):
        """Test validation catches excessive !important"""
        code = '''
        .class1 { color: red !important; }
        .class2 { color: blue !important; }
        .class3 { color: green !important; }
        .class4 { color: yellow !important; }
        .class5 { color: purple !important; }
        .class6 { color: orange !important; }
        '''
        result = self.css.validate(code)
        
        self.assertTrue(any('!important' in warning for warning in result['warnings']))
    
    def test_validate_absolute_fonts(self):
        """Test validation catches absolute font sizes"""
        code = '''
        h1 { font-size: 24px; }
        h2 { font-size: 20px; }
        h3 { font-size: 18px; }
        p { font-size: 16px; }
        '''
        result = self.css.validate(code)
        
        self.assertTrue(any('absolute' in warning.lower() for warning in result['warnings']))
    
    def test_validate_suggests_modern_layout(self):
        """Test validation suggests modern layouts"""
        code = '''
        .container { width: 100%; }
        .item { float: left; width: 33%; }
        .item2 { float: left; width: 33%; }
        .item3 { float: left; width: 33%; }
        '''
        result = self.css.validate(code)
        
        self.assertTrue(any('Flexbox' in suggestion or 'Grid' in suggestion 
                          for suggestion in result['suggestions']))
    
    def test_validate_good_css(self):
        """Test validation passes for modern CSS"""
        code = '''
        .container {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 1rem;
        }
        
        @media (min-width: 768px) {
          .container {
            grid-template-columns: repeat(2, 1fr);
          }
        }
        '''
        result = self.css.validate(code)
        
        self.assertTrue(result['valid'])
        self.assertEqual(len(result['issues']), 0)
    
    def test_get_template_reset(self):
        """Test getting CSS reset template"""
        template = self.css.get_template('reset')
        
        self.assertIsNotNone(template)
        self.assertIn('box-sizing', template)
        self.assertIn('margin: 0', template)
    
    def test_get_template_flexbox(self):
        """Test getting flexbox template"""
        template = self.css.get_template('flexbox_layout')
        
        self.assertIsNotNone(template)
        self.assertIn('display: flex', template)
        self.assertIn('justify-content', template)
    
    def test_get_template_grid(self):
        """Test getting grid template"""
        template = self.css.get_template('grid_layout')
        
        self.assertIsNotNone(template)
        self.assertIn('display: grid', template)
        self.assertIn('grid-template-columns', template)
    
    def test_get_template_variables(self):
        """Test getting variables template"""
        template = self.css.get_template('variables')
        
        self.assertIsNotNone(template)
        self.assertIn('--primary', template)
        self.assertIn(':root', template)
    
    def test_performance_tips(self):
        """Test performance tips are provided"""
        tips = self.css.get_performance_tips()
        
        self.assertGreater(len(tips), 0)
        self.assertTrue(any('transform' in tip for tip in tips))
    
    def test_responsive_breakpoints(self):
        """Test responsive breakpoints are defined"""
        breakpoints = self.css.get_responsive_breakpoints()
        
        self.assertIn('mobile', breakpoints)
        self.assertIn('tablet', breakpoints)
        self.assertIn('common_breakpoints', breakpoints)
    
    def test_modern_features(self):
        """Test modern CSS features list"""
        features = self.css.get_modern_features()
        
        self.assertGreater(len(features), 0)
        self.assertTrue(any('Grid' in feature for feature in features))
        self.assertTrue(any('Flexbox' in feature for feature in features))

if __name__ == '__main__':
    unittest.main()