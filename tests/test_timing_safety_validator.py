#!/usr/bin/env python3
"""
Unit tests for Timing Safety Validator
Verifies detection of blocking delays, missing timeouts, and logic errors.
"""
import unittest
import sys
from pathlib import Path

# Setup path
REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from validators.timing_safety import TimingValidator

class TestTimingSafetyValidator(unittest.TestCase):
    def setUp(self):
        self.validator = TimingValidator()

    def test_blocking_delay_in_motor_code(self):
        """Should warn about delay() in motor loops"""
        code = "void loop() { // motor logic\n delay(1000); }"
        issues = self.validator.validate(code, "ESP32", "motor control")
        self.assertTrue(any("delay()" in i['message'] for i in issues))

    def test_missing_safety_timeout(self):
        """Should error on missing safety timeout for motors"""
        code = "void loop() { // motor\n ledcWrite(0, 255); }"
        issues = self.validator.validate(code, "ESP32", "motor control")
        self.assertTrue(any("No safety timeout" in i['message'] for i in issues))
        
        # Test fix generation
        fix_fn = next(i['fix'] for i in issues if "No safety timeout" in i['message'])
        fixed_code = fix_fn(code)
        self.assertIn("SAFETY_TIMEOUT", fixed_code)
        self.assertIn("millis() - lastCommand", fixed_code)

    def test_valid_safety_timeout(self):
        """Should accept code with valid timeout logic"""
        code = "void loop() { // motor\n if (millis() - lastCmd > 5000) { stop(); } }"
        issues = self.validator.validate(code, "ESP32", "motor control")
        self.assertFalse(any("No safety timeout" in i['message'] for i in issues))

    def test_broken_debounce_logic(self):
        """Should detect type mismatch in debounce logic"""
        code = "if (buttonState != lastDebounceTime) {}"
        issues = self.validator.validate(code, "ESP32", "button")
        self.assertTrue(any("Type Mismatch" in i['message'] for i in issues))

    def test_long_safety_timeout(self):
        """Should warn if timeout is too long (>5s)"""
        code = "#define SAFETY_TIMEOUT 10000"
        issues = self.validator.validate(code, "ESP32", "motor")
        self.assertTrue(any("too long" in i['message'] for i in issues))

    def test_static_timer_init(self):
        """Should detect static timers initialized with millis()"""
        code = "static unsigned long timer = millis();"
        issues = self.validator.validate(code, "ESP32", "")
        self.assertTrue(any("Static timer" in i['message'] for i in issues))

    def test_unnecessary_debounce(self):
        """Should flag debounce logic in analog/battery contexts"""
        code = "if (millis() - lastDebounceTime > 50) { readBattery(); }"
        issues = self.validator.validate(code, "ESP32", "battery voltage")
        self.assertTrue(any("Debouncing detected" in i['message'] for i in issues))

if __name__ == '__main__':
    unittest.main()