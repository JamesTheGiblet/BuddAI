"""
Tests for HTML Language Skill
"""

import unittest
from languages.html_skill import HTMLSkill

class TestHTMLSkill(unittest.TestCase):
    
    def setUp(self):
        """Create HTML skill instance"""
        self.html = HTMLSkill()
    
    def test_initialization(self):
        """Test HTML skill initializes correctly"""
        self.assertEqual(self.html.name, "HTML")
        self.assertIn('.html', self.html.file_extensions)
        self.assertIn('.htm', self.html.file_extensions)
    
    def test_supports_file(self):
        """Test file extension detection"""
        self.assertTrue(self.html.supports_file('index.html'))
        self.assertTrue(self.html.supports_file('page.htm'))
        self.assertFalse(self.html.supports_file('style.css'))
    
    def test_patterns_loaded(self):
        """Test that patterns are loaded"""
        self.assertGreater(len(self.html.patterns), 0)
        self.assertIn('semantic_structure', self.html.patterns)
        self.assertIn('accessible_images', self.html.patterns)
    
    def test_anti_patterns_loaded(self):
        """Test that anti-patterns are loaded"""
        self.assertGreater(len(self.html.anti_patterns), 0)
        self.assertIn('divitis', self.html.anti_patterns)
        self.assertIn('missing_alt', self.html.anti_patterns)
    
    def test_validate_missing_doctype(self):
        """Test validation catches missing DOCTYPE"""
        code = '<html><body><h1>Test</h1></body></html>'
        result = self.html.validate(code)
        
        self.assertFalse(result['valid'])
        self.assertTrue(any('DOCTYPE' in issue for issue in result['issues']))
    
    def test_validate_missing_alt(self):
        """Test validation catches images without alt"""
        code = '<!DOCTYPE html><html><body><img src="test.jpg"></body></html>'
        result = self.html.validate(code)
        
        self.assertFalse(result['valid'])
        self.assertTrue(any('alt' in issue for issue in result['issues']))
    
    def test_validate_deprecated_tags(self):
        """Test validation catches deprecated tags"""
        code = '<!DOCTYPE html><html><body><font>Old style</font></body></html>'
        result = self.html.validate(code)
        
        self.assertFalse(result['valid'])
        self.assertTrue(any('deprecated' in issue.lower() for issue in result['issues']))
    
    def test_validate_good_html(self):
        """Test validation passes for good HTML"""
        code = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test</title>
</head>
<body>
    <header>
        <h1>Test Page</h1>
    </header>
    <main>
        <img src="test.jpg" alt="Test image">
    </main>
</body>
</html>'''
        result = self.html.validate(code)
        
        self.assertTrue(result['valid'])
        self.assertEqual(len(result['issues']), 0)
    
    def test_get_template_basic(self):
        """Test getting basic template"""
        template = self.html.get_template('basic')
        
        self.assertIsNotNone(template)
        self.assertIn('<!DOCTYPE html>', template)
        self.assertIn('<header>', template)
        self.assertIn('<main>', template)
    
    def test_get_template_form(self):
        """Test getting form template"""
        template = self.html.get_template('form')
        
        self.assertIsNotNone(template)
        self.assertIn('<form', template)
        self.assertIn('<label', template)
        self.assertIn('required', template)
    
    def test_get_template_invalid(self):
        """Test getting non-existent template"""
        template = self.html.get_template('nonexistent')
        
        self.assertIsNone(template)
    
    def test_best_practices(self):
        """Test best practices are defined"""
        practices = self.html.get_best_practices()
        
        self.assertGreater(len(practices), 0)
        self.assertTrue(any('semantic' in p.lower() for p in practices))
    
    def test_accessibility_checklist(self):
        """Test accessibility checklist exists"""
        checklist = self.html.get_accessibility_checklist()
        
        self.assertGreater(len(checklist), 0)
        self.assertTrue(any('alt' in item for item in checklist))
    
    def test_seo_checklist(self):
        """Test SEO checklist exists"""
        checklist = self.html.get_seo_checklist()
        
        self.assertGreater(len(checklist), 0)
        self.assertTrue(any('title' in item.lower() for item in checklist))

if __name__ == '__main__':
    unittest.main()