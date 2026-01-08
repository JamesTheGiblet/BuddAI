import re
from . import BaseValidator

class ArduinoValidator(BaseValidator):
    def validate(self, code: str, hardware: str, user_message: str) -> list[dict]:
        issues = []
        
        # Check 9: Unnecessary Wire.h
        wire_include = re.search(r'#include\s+[<"]Wire\.h[>"]', code)
        if wire_include:
            rest_of_code = code.replace(wire_include.group(0), "")
            if not re.search(r'\bWire\b', rest_of_code):
                issues.append({
                    "severity": "error",
                    "line": self.find_line(code, wire_include.group(0)),
                    "message": "Unnecessary #include <Wire.h> detected.",
                    "fix": lambda c: re.sub(r'#include\s+[<"]Wire\.h[>"]', '// [Auto-Fix] Removed unnecessary Wire.h', c)
                })

        # Check 12: Undefined Pin Constants
        pin_vars = set(re.findall(r'(?:digitalRead|digitalWrite|pinMode|ledcAttachPin)\s*\(\s*([a-zA-Z_]\w+)', code))
        for var in pin_vars:
            if var in ['LED_BUILTIN', 'HIGH', 'LOW', 'INPUT', 'OUTPUT', 'INPUT_PULLUP', 'true', 'false']:
                continue
            
            is_defined = re.search(r'#define\s+' + re.escape(var) + r'\b', code) or \
                         re.search(r'\b(?:const\s+)?(?:int|byte|uint8_t|short)\s+' + re.escape(var) + r'\s*=', code)
            
            if not is_defined:
                issues.append({
                    "severity": "error",
                    "message": f"Undefined variable '{var}' used in pin operation.",
                    "fix": lambda c, v=var: f"#define {v} 2 // [Auto-Fix] Defined missing pin\n" + c
                })

        # Check 25: Missing Serial.begin
        if re.search(r'Serial\.(?:print|write|println|printf)', code) and not re.search(r'Serial\.begin\s*\(', code):
            issues.append({
                "severity": "error",
                "message": "Missing Serial.begin() initialization.",
                "fix": lambda c: re.sub(r'void\s+setup\s*\(\s*\)\s*\{', r'void setup() {\n  Serial.begin(115200);', c, count=1)
            })

        # Check 26: Missing Wire.begin
        if re.search(r'Wire\.(?!h\b|begin\b)', code) and not re.search(r'Wire\.begin\s*\(', code):
            issues.append({
                "severity": "error",
                "message": "Missing Wire.begin() initialization for I2C.",
                "fix": lambda c: re.sub(r'void\s+setup\s*\(\s*\)\s*\{', r'void setup() {\n  Wire.begin();', c, count=1)
            })
        return issues
