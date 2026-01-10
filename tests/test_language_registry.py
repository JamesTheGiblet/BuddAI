"""
Tests for Language Registry
"""

import unittest
from languages.language_registry import LanguageRegistry, get_language_registry

class TestLanguageRegistry(unittest.TestCase):
    
    def setUp(self):
        """Create registry instance"""
        self.registry = LanguageRegistry()
    
    def test_initialization(self):
        """Test registry initializes"""
        self.assertIsNotNone(self.registry)
        self.assertIsInstance(self.registry.skills, dict)
    
    def test_skills_discovered(self):
        """Test that skills are auto-discovered"""
        self.assertGreater(len(self.registry.skills), 0)
        self.assertIn('html', self.registry.skills)
        self.assertIn('css', self.registry.skills)
        self.assertIn('javascript', self.registry.skills)
    
    def test_get_skill_by_name(self):
        """Test getting skill by name"""
        html_skill = self.registry.get_skill_by_name('html')
        self.assertIsNotNone(html_skill)
        self.assertEqual(html_skill.name, 'HTML')
    
    def test_get_skill_for_file(self):
        """Test getting skill for filename"""
        html_skill = self.registry.get_skill_for_file('index.html')
        self.assertIsNotNone(html_skill)
        self.assertEqual(html_skill.name, 'HTML')
        
        css_skill = self.registry.get_skill_for_file('style.css')
        self.assertIsNotNone(css_skill)
        self.assertEqual(css_skill.name, 'CSS')
        
        js_skill = self.registry.get_skill_for_file('app.js')
        self.assertIsNotNone(js_skill)
        self.assertEqual(js_skill.name, 'JavaScript')
    
    def test_validate_code(self):
        """Test code validation through registry"""
        code = '<!DOCTYPE html><html><body><h1>Test</h1></body></html>'
        result = self.registry.validate_code(code, 'html')
        
        self.assertIn('valid', result)
        self.assertIn('issues', result)
    
    def test_get_template(self):
        """Test getting template through registry"""
        template = self.registry.get_template('html', 'basic')
        
        self.assertIsNotNone(template)
        self.assertIn('<!DOCTYPE html>', template)
    
    def test_get_patterns(self):
        """Test getting patterns through registry"""
        patterns = self.registry.get_patterns('css')
        
        self.assertIsInstance(patterns, dict)
        self.assertGreater(len(patterns), 0)
    
    def test_get_best_practices(self):
        """Test getting best practices through registry"""
        practices = self.registry.get_best_practices('javascript')
        
        self.assertIsInstance(practices, list)
        self.assertGreater(len(practices), 0)
    
    def test_get_supported_languages(self):
        """Test getting supported languages"""
        languages = self.registry.get_supported_languages()
        
        self.assertIn('html', languages)
        self.assertIn('css', languages)
        self.assertIn('javascript', languages)
    
    def test_get_supported_extensions(self):
        """Test getting supported extensions"""
        extensions = self.registry.get_supported_extensions()
        
        self.assertIn('.html', extensions)
        self.assertIn('.css', extensions)
        self.assertIn('.js', extensions)
    
    def test_global_registry_singleton(self):
        """Test that global registry is a singleton"""
        registry1 = get_language_registry()
        registry2 = get_language_registry()
        
        self.assertIs(registry1, registry2)
        
    def test_get_all_skills(self):
        """Test retrieving all skills"""
        skills = self.registry.get_all_skills()
        self.assertIsInstance(skills, dict)
        self.assertGreater(len(skills), 0)

if __name__ == '__main__':
    unittest.main()