import re
from . import BaseValidator

class MotorValidator(BaseValidator):
    def validate(self, code: str, hardware: str, user_message: str) -> list[dict]:
        issues = []
        
        # Check 4: L298N PWM Pin Misuse
        pwm_pins = re.findall(r'ledcAttachPin\s*\(\s*(\w+)\s*,', code)
        for pin in pwm_pins:
            if re.search(r'digitalWrite\s*\(\s*' + re.escape(pin) + r'\s*,', code):
                issues.append({
                    "severity": "error",
                    "line": self.find_line(code, f"digitalWrite({pin}"),
                    "message": f"Conflict: PWM pin '{pin}' used with digitalWrite(). Use ledcWrite() for speed control.",
                    "fix": lambda c, p=pin: re.sub(r'digitalWrite\s*\(\s*' + re.escape(p) + r'\s*,\s*[^)]+\);?', f'// [Fixed] Removed conflicting digitalWrite on PWM pin {p}', c)
                })

        # Check 8: Incomplete Motor Logic (L298N Validation)
        is_l298n_request = "l298n" in user_message.lower() or "dc motor" in user_message.lower() or ("motor" in user_message.lower() and "servo" not in user_message.lower())
        
        if is_l298n_request:
            if not re.search(r'(?:#define|const\s+int)\s+\w*(?:IN1|IN2|DIR)\w*', code, re.IGNORECASE):
                issues.append({
                    "severity": "error",
                    "message": "Missing L298N Direction Pins (IN1/IN2).",
                    "fix": lambda c: "// [AUTO-FIX] L298N Definitions\n#define IN1 18\n#define IN2 19\n" + c
                })

            if not re.search(r'(?:#define|const\s+int)\s+\w*(?:ENA|ENB|PWM)\w*', code, re.IGNORECASE):
                issues.append({
                    "severity": "error",
                    "message": "Missing L298N PWM Pin (ENA).",
                    "fix": lambda c: "#define ENA 21 // [AUTO-FIX] Missing PWM Pin\n" + c
                })

            if "digitalWrite" not in code:
                issues.append({
                    "severity": "error",
                    "message": "L298N requires digitalWrite() for direction control.",
                    "fix": lambda c: re.sub(r'(void\s+loop\s*\(\s*\)\s*\{)', r'\1\n  // [AUTO-FIX] Set Direction\n  digitalWrite(IN1, HIGH);\n  digitalWrite(IN2, LOW);\n', c)
                })
        return issues
