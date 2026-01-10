"""
Python Language Skill
PEP 8, Modern Python features, and best practices
"""

import re
from typing import Dict, List, Optional
from .language_base import LanguageSkill

class PythonSkill(LanguageSkill):
    """
    Python language skill
    
    Provides:
    - Modern Python patterns
    - PEP 8 validation
    - Common pitfalls detection
    - Anti-pattern detection
    """
    
    def __init__(self):
        super().__init__(
            name="Python",
            file_extensions=['.py', '.pyw', '.pyi']
        )
    
    def _load_patterns(self):
        """Load Python patterns and best practices"""
        
        self.patterns = {
            'list_comprehension': {
                'description': 'List comprehensions for concise list creation',
                'pattern': r'\[.* for .* in .*\]',
                'example': 'squares = [x**2 for x in range(10)]'
            },
            'context_managers': {
                'description': 'Context managers for resource management',
                'pattern': r'\bwith\s+',
                'example': 'with open("file.txt") as f:\n    data = f.read()'
            },
            'f_strings': {
                'description': 'F-strings for string interpolation',
                'pattern': r'f[\'"].*\{.*\}[\'"]',
                'example': 'name = "World"\nprint(f"Hello {name}")'
            },
            'type_hints': {
                'description': 'Type hints for better code clarity',
                'pattern': r':\s*[A-Z]\w+|->\s*[A-Z]\w+',
                'example': 'def greet(name: str) -> str:'
            }
        }
        
        self.anti_patterns = {
            'mutable_default_args': {
                'description': 'Mutable default arguments',
                'pattern': r'def\s+\w+\s*\(.*=\s*(\[\]|\{\})',
                'fix': 'Use None as default and initialize inside function'
            },
            'bare_except': {
                'description': 'Bare except clause',
                'pattern': r'\bexcept\s*:',
                'fix': 'Catch specific exceptions (e.g., except ValueError:)'
            },
            'global_variables': {
                'description': 'Use of global variables',
                'pattern': r'\bglobal\s+\w+',
                'fix': 'Pass variables as arguments or use a class'
            }
        }

    def validate(self, code: str) -> Dict:
        """
        Validate Python code
        """
        issues = []
        warnings = []
        suggestions = []
        
        # Check for mutable default arguments
        if re.search(r'def\s+\w+\s*\([^)]*=\s*(\[\]|\{\})', code):
            issues.append('Mutable default argument detected (e.g., list=[] or dict={})')
            
        # Check for bare except
        if re.search(r'\bexcept\s*:', code):
            issues.append('Bare except clause detected - catch specific exceptions')
            
        # Check for print statements (suggest logging)
        if re.search(r'\bprint\s*\(', code):
            warnings.append('Found print() statements - consider using logging module')
            
        # Check for global variables
        if re.search(r'\bglobal\s+\w+', code):
            warnings.append('Found "global" keyword - consider passing arguments or using a class')
            
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'suggestions': suggestions
        }
        
    def get_template(self, template_name: str) -> Optional[str]:
        """Get Python template by name"""
        templates = {
            'script': '''#!/usr/bin/env python3
"""
Script Description
"""

import argparse
import logging

def main():
    parser = argparse.ArgumentParser(description="Script Description")
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info("Starting script...")

if __name__ == "__main__":
    main()''',
            'class': '''class ClassName:
    """
    Class Description
    """
    
    def __init__(self, param):
        """Initialize class"""
        self.param = param
        
    def method(self):
        """Method description"""
        pass'''
        }
        return templates.get(template_name)