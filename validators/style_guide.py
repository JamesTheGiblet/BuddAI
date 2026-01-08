import re
from . import BaseValidator

class StyleValidator(BaseValidator):
    def refactor_loop_to_function(self, code: str) -> str:
        loop_match = re.search(r'void\s+loop\s*\(\s*\)\s*\{', code)
        if not loop_match: return code
        
        start_idx = loop_match.end()
        brace_count = 1
        loop_body_end = -1
        
        for i, char in enumerate(code[start_idx:], start=start_idx):
            if char == '{': brace_count += 1
            elif char == '}': brace_count -= 1
            
            if brace_count == 0:
                loop_body_end = i
                break
        
        if loop_body_end == -1: return code
        
        body = code[start_idx:loop_body_end]
        new_code = code[:start_idx] + "\n  runSystemLogic();\n" + code[loop_body_end:]
        new_code += "\n\nvoid runSystemLogic() {" + body + "}\n"
        return new_code

    def validate(self, code: str, hardware: str, user_message: str) -> list[dict]:
        issues = []
        
        # Check 11: Feature Bloat (Unrequested Button)
        if user_message:
            msg_lower = user_message.lower()
            if not any(w in msg_lower for w in ['button', 'switch', 'input', 'trigger']):
                for match in re.finditer(r'(?:int|bool|byte)\s+(\w*(?:button|btn|switch)\w*)\s*=\s*digitalRead\s*\([^;]+;', code, re.IGNORECASE):
                    issues.append({
                        "severity": "error",
                        "line": self.find_line(code, match.group(0)),
                        "message": f"Feature Bloat: Unrequested button code detected ('{match.group(1)}').",
                        "fix": lambda c, m=match.group(0): c.replace(m, "")
                    })
                
                for match in re.finditer(r'digitalRead\s*\(\s*(\w*(?:BUTTON|BTN|SWITCH)\w*)\s*\)', code, re.IGNORECASE):
                    issues.append({
                        "severity": "error",
                        "line": self.find_line(code, match.group(0)),
                        "message": f"Feature Bloat: Unrequested button check detected ('{match.group(1)}').",
                        "fix": lambda c, m=match.group(0): c.replace(m, "0")
                    })
                
                for match in re.finditer(r'pinMode\s*\(\s*\w+\s*,\s*INPUT(?:_PULLUP)?\s*\);', code):
                    issues.append({
                        "severity": "error",
                        "line": self.find_line(code, match.group(0)),
                        "message": "Feature Bloat: Unrequested input pin configuration.",
                        "fix": lambda c, m=match.group(0): c.replace(m, "")
                    })
                
                for match in re.finditer(r'(?:int|bool|byte)\s+(\w*(?:button|btn|switch)\w*)\s*=\s*(?:LOW|HIGH|0|1|false|true)\s*;', code, re.IGNORECASE):
                    issues.append({
                        "severity": "error",
                        "line": self.find_line(code, match.group(0)),
                        "message": f"Feature Bloat: Unused button variable '{match.group(1)}'.",
                        "fix": lambda c, m=match.group(0): c.replace(m, "")
                    })

        # Check 15: Function Naming Conventions
        func_defs = re.finditer(r'\b(void|int|bool|float|double|String|char|long|unsigned(?:\s+long)?)\s+([a-zA-Z0-9_]+)\s*\(', code)
        for match in func_defs:
            func_name = match.group(2)
            if func_name in ['setup', 'loop', 'main']: continue
            
            if not re.match(r'^[a-z][a-zA-Z0-9]*$', func_name):
                suggestion = func_name
                if '_' in func_name:
                    components = func_name.split('_')
                    suggestion = components[0].lower() + ''.join(x.title() for x in components[1:])
                elif func_name[0].isupper():
                    suggestion = func_name[0].lower() + func_name[1:]
                
                issues.append({
                    "severity": "warning",
                    "line": self.find_line(code, match.group(0)),
                    "message": f"Style: Function '{func_name}' should be camelCase (e.g., '{suggestion}').",
                    "fix": lambda c, old=func_name, new=suggestion: c.replace(old, new)
                })

        # Check 16: Monolithic Code Structure
        if "function" in user_message.lower() or "naming" in user_message.lower() or "modular" in user_message.lower():
            has_custom_funcs = False
            for match in re.finditer(r'\b(void|int|bool|float|double|String|char|long|unsigned(?:\s+long)?)\s+([a-zA-Z0-9_]+)\s*\(', code):
                if match.group(2) not in ['setup', 'loop', 'main']:
                    has_custom_funcs = True
                    break
            
            if not has_custom_funcs:
                issues.append({
                    "severity": "error",
                    "message": "Structure Violation: Request asked for functions but code is monolithic.",
                    "fix": lambda c: c.replace("void loop() {", "void loop() {\n  runSystemLogic();\n}\n\nvoid runSystemLogic() {") + "\n}"
                })

        # Check 17: Loop Length
        if "function" in user_message.lower() or "naming" in user_message.lower() or "modular" in user_message.lower():
            loop_match = re.search(r'void\s+loop\s*\(\s*\)\s*\{', code)
            if loop_match:
                start_idx = loop_match.end()
                brace_count = 1
                loop_body = ""
                for char in code[start_idx:]:
                    if char == '{': brace_count += 1
                    elif char == '}': brace_count -= 1
                    if brace_count == 0: break
                    loop_body += char
                
                lines = [line.strip() for line in loop_body.split('\n')]
                significant_lines = [l for l in lines if l and not l.startswith('//') and not l.startswith('/*') and l != '']
                
                if len(significant_lines) >= 10:
                    issues.append({
                        "severity": "error",
                        "message": f"Modularity Violation: loop() has {len(significant_lines)} lines (limit 10). Move logic to functions.",
                        "fix": lambda c: self.refactor_loop_to_function(c)
                    })

        # Check 21: Status LED Pattern
        if "status" in user_message.lower() and ("led" in user_message.lower() or "indicator" in user_message.lower()):
            breathing_match = re.search(r'(?:dutyCycle|brightness)\s*(\+=|\+\+|\-=|\-\-)', code)
            if breathing_match:
                issues.append({
                    "severity": "error",
                    "line": self.find_line(code, breathing_match.group(0)),
                    "message": "Wrong Pattern: Status indicators should use Blink Patterns (States), not Breathing/Fading.",
                    "fix": lambda c: c + "\n// [Fix Required] Implement setStatusLED(LEDStatus state) instead of fading."
                })

            if not re.search(r'enum\s+(?:StatusState|LEDStatus)\s*\{', code):
                issues.append({
                    "severity": "error",
                    "message": "Missing Status Enum: Status LEDs require a state machine (enum LEDStatus {OFF, IDLE, ACTIVE, ERROR}).",
                    "fix": lambda c: c.replace("void setup", "\n// [AUTO-FIX] Status Enum\nenum LEDStatus { OFF, IDLE, ACTIVE, ERROR };\nLEDStatus currentStatus = IDLE;\nunsigned long lastBlink = 0;\n\nvoid setup") if "void setup" in c else "// [AUTO-FIX] Status Enum\nenum LEDStatus { OFF, IDLE, ACTIVE, ERROR };\nLEDStatus currentStatus = IDLE;\nunsigned long lastBlink = 0;\n" + c
                })
        return issues
