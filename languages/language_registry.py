"""
Language Skill Registry
Auto-discovery and management of language skills
"""

import os
import importlib
import logging
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class LanguageRegistry:
    """
    Registry for language skills
    Auto-discovers and manages all language skills
    """
    
    def __init__(self):
        self.skills: Dict[str, object] = {}
        self.file_extension_map: Dict[str, str] = {}
        self._discover_skills()
    
    def _discover_skills(self):
        """Auto-discover language skills"""
        
        # Get the languages directory
        languages_dir = Path(__file__).parent
        
        # Find all skill files
        skill_files = [
            f for f in os.listdir(languages_dir)
            if f.endswith('_skill.py') and f != 'language_base.py'
        ]
        
        logger.info(f"Discovering language skills in {languages_dir}")
        
        for skill_file in skill_files:
            try:
                # Import the module
                module_name = skill_file[:-3]  # Remove .py
                module = importlib.import_module(f'languages.{module_name}')
                
                # Find the skill class dynamically
                skill_class = None
                for attr_name in dir(module):
                    if attr_name.endswith('Skill') and attr_name != 'LanguageSkill':
                        attr = getattr(module, attr_name)
                        if isinstance(attr, type) and attr.__module__ == module.__name__:
                            skill_class = attr
                            break
                
                if skill_class:
                    skill_instance = skill_class()
                    
                    # Register the skill
                    skill_name = skill_instance.name.lower()
                    self.skills[skill_name] = skill_instance
                    
                    # Map file extensions to skills
                    for ext in skill_instance.file_extensions:
                        self.file_extension_map[ext] = skill_name
                    
                    logger.info(f"Registered language skill: {skill_instance.name}")
                
            except Exception as e:
                logger.error(f"Failed to load skill {skill_file}: {e}")
        
        logger.info(f"Loaded {len(self.skills)} language skills")
    
    def get_skill_for_file(self, filename: str) -> Optional[object]:
        """Get the appropriate skill for a filename"""
        
        for ext, skill_name in self.file_extension_map.items():
            if filename.endswith(ext):
                return self.skills.get(skill_name)
        
        return None
    
    def get_skill_by_name(self, name: str) -> Optional[object]:
        """Get a skill by name"""
        return self.skills.get(name.lower())
    
    def get_all_skills(self) -> Dict[str, object]:
        """Get all registered skills"""
        return self.skills.copy()
    
    def validate_code(self, code: str, language: str) -> Dict:
        """
        Validate code for a specific language
        
        Args:
            code: Source code to validate
            language: Language name (html, css, javascript, etc.)
        
        Returns:
            Validation result dictionary
        """
        
        skill = self.get_skill_by_name(language)
        
        if not skill:
            return {
                'valid': True,
                'issues': [],
                'warnings': [],
                'suggestions': [f'No language skill found for {language}']
            }
        
        return skill.validate(code)
    
    def get_template(self, language: str, template_name: str) -> Optional[str]:
        """Get a code template for a language"""
        
        skill = self.get_skill_by_name(language)
        
        if not skill:
            return None
        
        return skill.get_template(template_name)
    
    def get_patterns(self, language: str) -> Dict:
        """Get patterns for a language"""
        
        skill = self.get_skill_by_name(language)
        
        if not skill:
            return {}
        
        return skill.get_patterns()
    
    def get_best_practices(self, language: str) -> List[str]:
        """Get best practices for a language"""
        
        skill = self.get_skill_by_name(language)
        
        if not skill:
            return []
        
        return skill.get_best_practices()
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages"""
        return list(self.skills.keys())
    
    def get_supported_extensions(self) -> List[str]:
        """Get list of supported file extensions"""
        return list(self.file_extension_map.keys())


# Global registry instance
_registry = None

def get_language_registry() -> LanguageRegistry:
    """Get or create the global language registry"""
    global _registry
    if _registry is None:
        _registry = LanguageRegistry()
    return _registry