"""
Validator Registry
Auto-discovers and manages validators
"""

import os
import inspect
import importlib
from pathlib import Path
from typing import List, Dict, Tuple
from .base_validator import BaseValidator

class ValidatorRegistry:
    def __init__(self):
        self.validators = {}
        self.load_validators()
    
    def load_validators(self):
        """Auto-discover validators in validators/ folder"""
        validator_dir = Path(__file__).parent
        count = 0
        
        for file in validator_dir.glob('*.py'):
            if file.name.startswith('_') or file.name == 'base_validator.py':
                continue
            
            # Import the module
            module_name = file.stem
            try:
                module = importlib.import_module(f'.{module_name}', package='validators')
            except Exception as e:
                print(f"⚠️ Failed to load validator module {module_name}: {e}")
                continue
            
            # Find validator classes
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                
                # Check if it's a class and not BaseValidator itself
                if not isinstance(attr, type) or attr.__name__ == 'BaseValidator':
                    continue
                
                # Robust inheritance check (handles import path differences)
                is_validator = False
                try:
                    if issubclass(attr, BaseValidator):
                        is_validator = True
                except TypeError:
                    pass
                
                if not is_validator:
                    is_validator = any(b.__name__ == 'BaseValidator' for b in attr.__mro__)
                
                if is_validator:
                    # Instantiate and register
                    try:
                        validator = attr()
                        # Use class name if name attribute is missing or default
                        v_name = getattr(validator, 'name', None)
                        if not v_name or v_name == "Base Validator":
                            v_name = attr.__name__
                            
                        self.validators[v_name] = validator
                        count += 1
                    except Exception as e:
                        print(f"⚠️ Failed to instantiate {attr.__name__}: {e}")
    
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

    def auto_fix(self, code: str, issues: List[Dict]) -> str:
        """Automatically fix known issues"""
        fixed_code = code
        
        for issue in issues:
            if 'fix' in issue and issue['severity'] == 'error':
                fixed_code = issue['fix'](fixed_code)
        
        return fixed_code

    def validate(self, code: str, hardware: str, user_message: str = "") -> Tuple[bool, List[Dict]]:
        """Check code against known rules"""
        issues = []
        for validator in self.validators.values():
            # Handle legacy validators that expect (code, context)
            sig = inspect.signature(validator.validate)
            if len(sig.parameters) == 2:
                context = {"hardware": hardware, "user_message": user_message}
                issues.extend(validator.validate(code, context))
            else:
                issues.extend(validator.validate(code, hardware, user_message))
        
        return len([i for i in issues if i['severity'] == 'error']) == 0, issues