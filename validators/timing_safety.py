import re
from . import BaseValidator

class TimingValidator(BaseValidator):
    def has_safety_timeout(self, code: str) -> bool:
        if "millis()" not in code: return False
        if re.search(r'>\s*[A-Z_]*TIMEOUT', code): return True
        if "DISARM" in code and "millis" in code and ">" in code: return True
        comparisons = re.findall(r'>\s*(\d+)', code)
        return any(int(val) > 500 for val in comparisons)

    def validate(self, code: str, hardware: str, user_message: str) -> list[dict]:
        issues = []
        
        # Check 2: Non-blocking code
        if "delay(" in code and "motor" in code.lower():
            issues.append({
                "severity": "warning",
                "line": self.find_line(code, "delay"),
                "message": "Using delay() in motor code blocks safety checks",
                "fix": lambda c: c # No auto-fix
            })

        # Check 3: Safety timeout
        if ("motor" in code.lower() or "servo" in code.lower()):
            if not self.has_safety_timeout(code):
                is_servo = "Servo" in code and "L298N" not in code
                stop_logic = "    // STOP MOTORS\n    ledcWrite(0, 0);\n    ledcWrite(1, 0);"
                if is_servo:
                    stop_logic = "    // STOP SERVO\n    // Implement safe position (e.g. myServo.write(90));"

                issues.append({
                    "severity": "error",
                    "message": "Critical: No safety timeout detected (must be > 500ms).",
                    "fix": lambda c, sl=stop_logic: "#define SAFETY_TIMEOUT 5000\nunsigned long lastCommand = 0;\n" + \
                                     re.sub(r'(void\s+loop\s*\(\s*\)\s*\{)', \
                                            rf'\1\n  // [AUTO-FIX] Safety Timeout\n  if (millis() - lastCommand > SAFETY_TIMEOUT) {{\n{sl}\n  }}\n', c)
                })

        # Check 5: Broken Debounce Logic
        bad_debounce = re.search(r'if\s*\(\s*\w+\s*[!=]=\s*\w*DebounceTime\s*\)', code)
        if bad_debounce:
            issues.append({
                "severity": "error",
                "line": self.find_line(code, bad_debounce.group(0)),
                "message": "Type Mismatch: Comparing button state (int) with time (long).",
                "fix": lambda c: c.replace(bad_debounce.group(0), "if ((millis() - lastDebounceTime) > debounceDelay)")
            })

        # Check 6: Safety Timeout Value
        timeout_match = re.search(r'#define\s+SAFETY_TIMEOUT\s+(\d+)', code)
        if timeout_match and int(timeout_match.group(1)) > 5000:
            issues.append({
                "severity": "error",
                "line": self.find_line(code, timeout_match.group(0)),
                "message": f"Safety timeout {timeout_match.group(1)}ms is too long (Max: 5000ms).",
                "fix": lambda c: re.sub(r'(#define\s+SAFETY_TIMEOUT\s+)\d+', r'\g<1>5000', c)
            })

        # Check 7: Broken Safety Timer Logic
        bad_static = re.search(r'static\s+unsigned\s+long\s+(\w+)\s*=\s*millis\(\);', code)
        if bad_static:
            issues.append({
                "severity": "error",
                "line": self.find_line(code, bad_static.group(0)),
                "message": "Static timer initialized with millis() prevents reset. Initialize to 0.",
                "fix": lambda c: c.replace(bad_static.group(0), f"static unsigned long {bad_static.group(1)} = 0;")
            })

        # Check 10: High-Frequency Serial Logging
        if ("Serial.print" in code or "Serial.write" in code) and \
           ("motor" in code.lower() or "servo" in code.lower()):
            if not re.search(r'(print|log|debug|serial)\s*Timer', code, re.IGNORECASE) and \
               not re.search(r'last\s*(Print|Log|Debug)', code, re.IGNORECASE):
                issues.append({
                    "severity": "warning",
                    "line": self.find_line(code, "Serial.print"),
                    "message": "Serial logging in motor loops causes jitter. Ensure it's throttled (e.g. every 100ms).",
                    "fix": lambda c: c + "\n// [Performance] Warning: Serial.print() inside loops can interrupt motor timing."
                })

        # Check 19: Unnecessary Debouncing (Analog/Battery)
        if "battery" in user_message.lower() or "voltage" in user_message.lower() or "analog" in user_message.lower():
            if "button" not in user_message.lower():
                debounce_match = re.search(r'(?:debounce|lastDebounceTime)', code, re.IGNORECASE)
                if debounce_match:
                    issues.append({
                        "severity": "error",
                        "line": self.find_line(code, debounce_match.group(0)),
                        "message": "Logic Error: Debouncing detected in analog/battery code. Analog sensors don't need debouncing.",
                        "fix": lambda c: re.sub(r'.*debounce.*', '// [Fixed] Removed unnecessary debounce logic', c, flags=re.IGNORECASE)
                    })

        # Check 22: Misused Debouncing (Animation Timing)
        if "brightness" in code or "fade" in code:
            misused_debounce = re.search(r'if\s*\(\s*\(?\s*millis\(\)\s*-\s*\w+\s*\)?\s*>\s*(\w*DEBOUNCE\w*)\s*\)\s*\{', code, re.IGNORECASE)
            if misused_debounce:
                var_name = misused_debounce.group(1)
                start_index = misused_debounce.end()
                snippet = code[start_index:start_index+200]
                if any(x in snippet for x in ['brightness', 'fade', 'dutyCycle', 'ledcWrite']):
                    issues.append({
                        "severity": "error",
                        "line": self.find_line(code, var_name),
                        "message": f"Semantic Error: Using {var_name} for animation/fading. Use UPDATE_INTERVAL or FADE_SPEED.",
                        "fix": lambda c, v=var_name: c.replace(v, "FADE_SPEED" if v.isupper() else "fadeSpeed")
                    })
        return issues
