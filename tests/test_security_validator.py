#!/usr/bin/env python3
"""
Unit tests for Security Validator
"""
import unittest
import sys
from pathlib import Path

# Setup path
REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from validators.security_validator import SecurityValidator

class TestSecurityValidator(unittest.TestCase):
    def setUp(self):
        self.validator = SecurityValidator()

    def test_openai_key_detection(self):
        code = 'const char* key = "sk-1234567890abcdef1234567890abcdef";'
        issues = self.validator.validate(code, "ESP32", "")
        self.assertTrue(any("OpenAI API Key" in i['message'] for i in issues))
        
        fixed = issues[0]['fix'](code)
        self.assertIn("YOUR_API_KEY_HERE", fixed)

    def test_wifi_credentials(self):
        code = 'WiFi.begin("MyHome", "SecretPass123");'
        issues = self.validator.validate(code, "ESP32", "")
        self.assertTrue(any("WiFi credentials" in i['message'] for i in issues))
        
        fixed = issues[0]['fix'](code)
        self.assertIn("YOUR_SSID", fixed)

    def test_generic_secret(self):
        code = 'String password = "SuperSecretPassword";'
        issues = self.validator.validate(code, "ESP32", "")
        self.assertTrue(any("hardcoded secret" in i['message'] for i in issues))
        
        fixed = issues[0]['fix'](code)
        self.assertIn("REDACTED", fixed)

if __name__ == '__main__':
    unittest.main()