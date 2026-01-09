#!/usr/bin/env python3
"""
Unit tests for Forge Theory Validator
Verifies detection of unsmoothed motion and application of exponential decay.
"""
import unittest
import sys
from pathlib import Path

# Setup path
REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from validators.forge_theory import ForgeTheoryValidator

class TestForgeTheoryValidator(unittest.TestCase):
    def setUp(self):
        self.validator = ForgeTheoryValidator()

    def test_no_motor_context(self):
        """Should ignore code unrelated to motors/servos"""
        code = "ledcWrite(0, 255);"
        issues = self.validator.validate(code, "ESP32", "turn on led")
        self.assertEqual(len(issues), 0)

    def test_missing_smoothing(self):
        """Should flag direct writes in motor context"""
        code = "void loop() { ledcWrite(motorPin, 255); }"
        issues = self.validator.validate(code, "ESP32", "control motor speed")
        self.assertEqual(len(issues), 1)
        self.assertIn("Forge Theory", issues[0]['message'])
        
        # Test fix
        fixed = issues[0]['fix'](code)
        self.assertIn("// [Forge Theory]", fixed)

    def test_present_smoothing_formula(self):
        """Should accept code with smoothing formula"""
        code = "currentSpeed += (targetSpeed - currentSpeed) * 0.1;\nledcWrite(motorPin, currentSpeed);"
        issues = self.validator.validate(code, "ESP32", "control motor speed")
        self.assertEqual(len(issues), 0)

    def test_present_smoothing_comment(self):
        """Should accept code with explicit Forge Theory comment"""
        code = "// Forge Theory applied\nledcWrite(motorPin, val);"
        issues = self.validator.validate(code, "ESP32", "control motor speed")
        self.assertEqual(len(issues), 0)

if __name__ == '__main__':
    unittest.main()