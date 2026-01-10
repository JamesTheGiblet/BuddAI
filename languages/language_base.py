"""
Base class for language skills
All language skills inherit from this
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

class LanguageSkill(ABC):
    """
    Base class for language-specific skills
    
    Each language (HTML, CSS, JS, Python, etc.) implements this interface
    to provide language-specific patterns, validators, and best practices
    """
    
    def __init__(self, name: str, file_extensions: List[str]):
        self.name = name
        self.file_extensions = file_extensions
        self.patterns = {}
        self.anti_patterns = {}
        self.best_practices = []
        
        # Load patterns on init
        self._load_patterns()
    
    @abstractmethod
    def _load_patterns(self):
        """Load language-specific patterns"""
        pass
    
    @abstractmethod
    def validate(self, code: str) -> Dict:
        """
        Validate code for this language
        
        Returns:
            {
                'valid': bool,
                'issues': List[str],
                'warnings': List[str],
                'suggestions': List[str]
            }
        """
        pass
    
    @abstractmethod
    def get_template(self, template_name: str) -> Optional[str]:
        """Get a code template for this language"""
        pass
    
    def get_patterns(self) -> Dict:
        """Get all patterns for this language"""
        return self.patterns
    
    def get_anti_patterns(self) -> Dict:
        """Get all anti-patterns to avoid"""
        return self.anti_patterns
    
    def get_best_practices(self) -> List[str]:
        """Get best practices for this language"""
        return self.best_practices
    
    def supports_file(self, filename: str) -> bool:
        """Check if this skill handles the given file"""
        return any(filename.endswith(ext) for ext in self.file_extensions)