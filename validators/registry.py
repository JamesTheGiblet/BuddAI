"""
Validator Registry
Auto-discovers and manages validators
"""

import os
import importlib
from pathlib import Path
from typing import List
from .base_validator import BaseValidator

class ValidatorRegistry:
    def __init__(self):
        self.validators = {}
        self.load_validators()
    
    def load_validators(self):
        """Auto-discover validators in validators/ folder"""
        validator_dir = Path(__file__).parent
        
        for file in validator_dir.glob('*.py'):
            if file.name.startswith('_') or file.name == 'base_validator.py':
                continue
            
            # Import the module
            module_name = file.stem
            module = importlib.import_module(f'.{module_name}', package='validators')
            
            # Find validator classes
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, BaseValidator) and 
                    attr != BaseValidator):
                    
                    # Instantiate and register
                    validator = attr()
                    self.validators[validator.name] = validator
                    print(f"✅ Loaded validator: {validator.name}")
    
    def get_validators_for(self, code: str, context: dict) -> List[BaseValidator]:
        """Get validators that match this code/context"""
        relevant = []
        
        for validator in self.validators.values():
            if validator.matches_context(code, context):
                relevant.append(validator)
        
        # Sort by priority (lower number = higher priority)
        relevant.sort(key=lambda v: v.priority)
        
        return relevant
    
    def validate_all(self, code: str, context: dict) -> list:
        """Run all relevant validators"""
        validators = self.get_validators_for(code, context)
        all_issues = []
        
        for validator in validators:
            issues = validator.validate(code, context)
            all_issues.extend(issues)
        
        return all_issues