import re
from . import BaseValidator

class ServoValidator(BaseValidator):
    def validate(self, code: str, hardware: str, user_message: str) -> list[dict]:
        issues = []
        
        # Check 14: State Machine for Weapons (Combat Protocol)
        if "weapon" in user_message.lower() or "combat" in user_message.lower() or "state machine" in user_message.lower():
            if "enum" not in code and "bool isArmed" not in code:
                 issues.append({
                    "severity": "error",
                    "message": "Combat code requires a State Machine (enum State or bool isArmed).",
                    "fix": lambda c: c.replace("void setup", "\n// [AUTO-FIX] State Machine\nenum State { DISARMED, ARMING, ARMED, FIRING };\nState currentState = DISARMED;\nunsigned long stateTimer = 0;\n\nvoid setup") if "void setup" in c else "// [AUTO-FIX] State Machine\nenum State { DISARMED, ARMING, ARMED, FIRING };\nState currentState = DISARMED;\n" + c
                })
            
            if "Serial.read" not in code and "Serial.available" not in code:
                 issues.append({
                    "severity": "error",
                    "message": "Missing Serial Command handling (e.g., 'A' to Arm).",
                    "fix": lambda c: c.replace("void loop() {", "void loop() {\n  if (Serial.available()) {\n    char cmd = Serial.read();\n    // Handle commands\n  }\n")
                })
        return issues
