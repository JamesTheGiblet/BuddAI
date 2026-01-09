import re
from . import BaseValidator

class ForgeTheoryValidator(BaseValidator):
    def validate(self, code: str, hardware: str, user_message: str) -> list[dict]:
        issues = []
        
        # Check for exponential smoothing in motor/servo code
        # Forge Theory: "Movement must be continuous and smoothed"
        if "motor" in user_message.lower() or "servo" in user_message.lower():
            # Heuristic: Look for smoothing formula pattern
            # current += (target - current) * k
            # OR current = (target * k) + (current * (1-k))
            
            has_smoothing = False
            
            # Pattern 1: Standard exponential smoothing
            if re.search(r'\+=\s*\(\s*\w+\s*-\s*\w+\s*\)\s*\*', code):
                has_smoothing = True
            
            # Pattern 2: Explicit Forge Theory comment
            if "Forge Theory" in code or "smoothing" in code.lower():
                has_smoothing = True
                
            # If writing to output without smoothing
            if not has_smoothing:
                if "ledcWrite" in code or "myservo.write" in code.lower() or "analogWrite" in code:
                    issues.append({
                        "severity": "warning",
                        "message": "Forge Theory: Direct control detected. Consider exponential smoothing for fluid movement.",
                        "fix": lambda c: "// [Forge Theory] Apply smoothing: current += (target - current) * 0.1;\n" + c
                    })
                    
        return issues