import re
from typing import List, Dict, Tuple, Optional
from validators import (
    ESP32Validator, MotorValidator, ServoValidator, MemoryValidator,
    ForgeTheoryValidator, TimingValidator, ArduinoValidator, StyleValidator
)

class CodeValidator:
    """Validate generated code before showing to user"""
    
    def __init__(self):
        self.validators = [
            ESP32Validator(),
            MotorValidator(),
            ServoValidator(),
            MemoryValidator(),
            ForgeTheoryValidator(),
            TimingValidator(),
            ArduinoValidator(),
            StyleValidator()
        ]

    def validate(self, code: str, hardware: str, user_message: str = "") -> Tuple[bool, List[Dict]]:
        """Check code against known rules"""
        issues = []
        for validator in self.validators:
            issues.extend(validator.validate(code, hardware, user_message))
        
        return len([i for i in issues if i['severity'] == 'error']) == 0, issues
    
    def auto_fix(self, code: str, issues: List[Dict]) -> str:
        """Automatically fix known issues"""
        fixed_code = code
        
        for issue in issues:
            if 'fix' in issue and issue['severity'] == 'error':
                fixed_code = issue['fix'](fixed_code)
        
        return fixed_code

class HardwareProfile:
    """Learn hardware-specific patterns"""
    
    ESP32_PATTERNS = {
        "pwm_setup": {
            "correct": "ledcSetup(channel, freq, resolution)",
            "wrong": ["analogWrite", "pwmWrite"],
            "learned_from": "James's corrections"
        },
        "serial_baud": {
            "preferred": 115200,
            "alternatives": [9600, 57600],
            "confidence": 1.0
        },
        "safety_timeout": {
            "standard": 5000,
            "pattern": "millis() - lastTime > TIMEOUT",
            "confidence": 1.0
        }
    }
    
    HARDWARE_KEYWORDS = {
        "ESP32-C3": ["esp32", "esp32c3", "c3", "esp-32"],
        "Arduino Uno": ["uno", "arduino uno", "atmega328p"],
        "Raspberry Pi Pico": ["pico", "rp2040"]
    }

    def detect_hardware(self, message: str) -> Optional[str]:
        msg_lower = message.lower()
        for hw, keywords in self.HARDWARE_KEYWORDS.items():
            if any(k in msg_lower for k in keywords):
                return hw
        return None
    
    def apply_hardware_rules(self, code: str, hardware: str) -> str:
        """Apply known hardware patterns"""
        if hardware == "ESP32-C3":
            # Apply ESP32-specific fixes
            code = self.fix_pwm(code)
            code = self.fix_serial(code)
            code = self.add_safety(code)
        return code

    def fix_pwm(self, code: str) -> str:
        for wrong in self.ESP32_PATTERNS["pwm_setup"]["wrong"]:
            if wrong in code:
                if wrong == "analogWrite":
                    code = code.replace("analogWrite", "ledcWrite")
        return code

    def fix_serial(self, code: str) -> str:
        preferred = self.ESP32_PATTERNS["serial_baud"]["preferred"]
        return re.sub(r'Serial\.begin\(\s*\d+\s*\)', f'Serial.begin({preferred})', code)

    def add_safety(self, code: str) -> str:
        if "motor" in code.lower() and "millis()" not in code:
             code += "\n// [BuddAI Safety] Warning: No non-blocking timeout detected. Consider adding safety timeout."
        return code