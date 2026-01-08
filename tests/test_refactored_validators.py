#!/usr/bin/env python3
"""
Unit tests for the refactored Validator system.
"""
import unittest
import sys
from pathlib import Path

# Setup path
REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from validators import (
    ESP32Validator, MotorValidator, ServoValidator, MemoryValidator,
    ForgeTheoryValidator, TimingValidator, ArduinoValidator, StyleValidator
)

class TestRefactoredValidators(unittest.TestCase):
    def test_esp32_validator(self):
        val = ESP32Validator()
        code = "analogWrite(PIN, 100);"
        issues = val.validate(code, "ESP32", "")
        self.assertTrue(any("analogWrite" in i['message'] for i in issues))
        
    def test_motor_validator(self):
        val = MotorValidator()
        # Test missing pins for L298N
        issues = val.validate("void loop() {}", "ESP32", "I need L298N code")
        self.assertTrue(any("Missing L298N" in i['message'] for i in issues))

    def test_servo_validator(self):
        val = ServoValidator()
        issues = val.validate("void setup() {}", "ESP32", "weapon system")
        self.assertTrue(any("State Machine" in i['message'] for i in issues))

    def test_memory_validator(self):
        val = MemoryValidator()
        code = "void setup() { int x = 10; }"
        issues = val.validate(code, "ESP32", "")
        self.assertTrue(any("Unused variable 'x'" in i['message'] for i in issues))

    def test_arduino_validator(self):
        val = ArduinoValidator()
        code = "#include <Wire.h>\nvoid setup() {}"
        issues = val.validate(code, "ESP32", "")
        self.assertTrue(any("Unnecessary #include <Wire.h>" in i['message'] for i in issues))

    def test_style_validator(self):
        val = StyleValidator()
        code = "void MyFunction() {}"
        issues = val.validate(code, "ESP32", "")
        self.assertTrue(any("camelCase" in i['message'] for i in issues))

    def test_timing_validator(self):
        val = TimingValidator()
        code = "void loop() { // motor logic\n delay(1000); }"
        issues = val.validate(code, "ESP32", "motor control")
        self.assertTrue(any("delay()" in i['message'] for i in issues))

    def test_forge_theory_validator(self):
        val = ForgeTheoryValidator()
        issues = val.validate("code", "ESP32", "")
        self.assertEqual(issues, [])

if __name__ == '__main__':
    unittest.main()