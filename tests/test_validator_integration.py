#!/usr/bin/env python3
"""
Integration tests for Validator Registry
Verifies that multiple validators work together and auto-fix chains correctly.
"""
import unittest
import sys
from pathlib import Path

# Setup path
REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from validators.registry import ValidatorRegistry

class TestValidatorIntegration(unittest.TestCase):
    def setUp(self):
        self.registry = ValidatorRegistry()

    def test_registry_loading(self):
        """Ensure validators are loaded dynamically"""
        self.assertGreater(len(self.registry.validators), 0)
        self.assertIn("ESP32Validator", self.registry.validators)
        self.assertIn("MotorValidator", self.registry.validators)

    def test_combined_validation(self):
        """Test multiple validators triggering on one piece of code"""
        # Code has:
        # 1. analogWrite (ESP32Validator)
        # 2. delay (TimingValidator)
        # 3. No safety timeout (TimingValidator)
        # 4. Missing pins (MotorValidator)
        code = """
        void loop() {
            // motor control logic
            analogWrite(13, 255);
            delay(1000);
        }
        """
        user_message = "motor control with esp32"
        
        valid, issues = self.registry.validate(code, "ESP32", user_message)
        
        self.assertFalse(valid)
        messages = [i['message'] for i in issues]
        
        self.assertTrue(any("analogWrite" in m for m in messages))
        self.assertTrue(any("delay()" in m for m in messages))
        self.assertTrue(any("No safety timeout" in m for m in messages))

    def test_auto_fix_chain(self):
        """Test applying fixes via the registry"""
        code = "void loop() { analogWrite(13, 100); }"
        valid, issues = self.registry.validate(code, "ESP32", "")
        
        fixed_code = self.registry.auto_fix(code, issues)
        self.assertIn("ledcWrite", fixed_code)
        self.assertNotIn("analogWrite", fixed_code)

if __name__ == '__main__':
    unittest.main()