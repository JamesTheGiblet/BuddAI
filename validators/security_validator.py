import re
from .base_validator import BaseValidator

class SecurityValidator(BaseValidator):
    name = "Security Validator"
    triggers = ["api_key", "password", "secret", "token", "ssid", "wifi"]
    priority = 1  # High priority
    
    def validate(self, code: str, hardware: str, user_message: str) -> list:
        issues = []
        
        # Check for potential API keys (sk-...)
        if re.search(r'sk-[a-zA-Z0-9]{32,}', code):
            issues.append({
                "severity": "error",
                "message": "Security Risk: Hardcoded OpenAI API Key detected.",
                "fix": lambda c: re.sub(r'sk-[a-zA-Z0-9]{32,}', 'YOUR_API_KEY_HERE', c)
            })
            
        # Check for WiFi credentials
        if 'WiFi.begin' in code:
            if re.search(r'WiFi\.begin\s*\(\s*"[^"]+"\s*,\s*"[^"]+"\s*\)', code):
                 issues.append({
                    "severity": "warning",
                    "message": "Security Risk: Hardcoded WiFi credentials.",
                    "fix": lambda c: re.sub(r'WiFi\.begin\s*\(\s*"([^"]+)"\s*,\s*"([^"]+)"\s*\)', 'WiFi.begin("YOUR_SSID", "YOUR_PASSWORD")', c)
                })

        # Check for generic password assignments
        if re.search(r'(password|secret|key)\s*=\s*"[^"]{5,}"', code, re.IGNORECASE):
             issues.append({
                "severity": "warning",
                "message": "Security Risk: Potential hardcoded secret.",
                "fix": lambda c: re.sub(r'(password|secret|key)(\s*=\s*)"[^"]{5,}"', r'\1\2"REDACTED"', c, flags=re.IGNORECASE)
            })

        return issues