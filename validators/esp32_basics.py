import re
from . import BaseValidator

class ESP32Validator(BaseValidator):
    def validate(self, code: str, hardware: str, user_message: str) -> list[dict]:
        issues = []
        if "ESP32" in hardware.upper():
            # Check 1: analogWrite
            if "analogWrite" in code:
                issues.append({
                    "severity": "error",
                    "line": self.find_line(code, "analogWrite"),
                    "message": "ESP32 doesn't support analogWrite(). Use ledcWrite()",
                    "fix": lambda c: c.replace("analogWrite", "ledcWrite")
                })
            
            # Check 18: ADC Resolution
            adc_res_match = re.search(r'#define\s+(\w*ADC\w*RES\w*)\s+(\d+)', code, re.IGNORECASE)
            if adc_res_match:
                val = int(adc_res_match.group(2))
                if val not in [4095, 4096]:
                     issues.append({
                        "severity": "error",
                        "line": self.find_line(code, adc_res_match.group(0)),
                        "message": f"Hardware Mismatch: ESP32 ADC is 12-bit (4095), not {val}.",
                        "fix": lambda c, old=adc_res_match.group(0), name=adc_res_match.group(1): c.replace(old, f"#define {name} 4095")
                    })
            
            # Check 20: Hardcoded 10-bit ADC math
            for match in re.finditer(r'/\s*(1023(?:\.0?)?f?|1024(?:\.0)f?)', code):
                issues.append({
                    "severity": "error",
                    "line": self.find_line(code, match.group(0)),
                    "message": "Hardware Mismatch: ESP32 ADC is 12-bit. Use 4095.0, not 1023/1024.",
                    "fix": lambda c, m=match.group(0): c.replace(m, "/ 4095.0")
                })
        return issues
