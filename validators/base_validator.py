"""
Base validator interface
All validators inherit from this
"""

class BaseValidator:
    """Base class for all validators"""
    
    name = "Base Validator"
    triggers = []  # Keywords that activate this validator
    priority = 5   # 1=critical, 10=nice-to-have
    
    def validate(self, code: str, context: dict) -> list:
        """
        Validate code and return issues
        
        Args:
            code: The code to validate
            context: Dict with hardware, libraries, etc.
            
        Returns:
            List of issue dicts:
            {
                'severity': 'error|warning|info',
                'line': line_number or None,
                'message': 'What is wrong',
                'fix': 'How to fix it'
            }
        """
        raise NotImplementedError
    
    def matches_context(self, code: str, context: dict) -> bool:
        """
        Check if this validator should run
        
        Returns:
            bool: True if any trigger keyword in code
        """
        code_lower = code.lower()
        return any(trigger.lower() in code_lower for trigger in self.triggers)

    def find_line(self, code: str, substring: str) -> int:
        for i, line in enumerate(code.splitlines(), 1):
            if substring in line:
                return i
        return -1