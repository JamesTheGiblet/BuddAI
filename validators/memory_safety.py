
import re
from . import BaseValidator

class MemoryValidator(BaseValidator):
    def validate(self, code: str, hardware: str, user_message: str) -> list[dict]:
        issues = []
        
        # Check 24: Unused Variables in Setup
        setup_match = re.search(r'void\s+setup\s*\(\s*\)\s*\{', code)
        if setup_match:
            start_idx = setup_match.end()
            brace_count = 1
            setup_body = ""
            for char in code[start_idx:]:
                if char == '{': brace_count += 1
                elif char == '}': brace_count -= 1
                if brace_count == 0: break
                setup_body += char
            
            clean_body = re.sub(r'//.*', '', setup_body)
            clean_body = re.sub(r'/\*.*?\*/', '', clean_body, flags=re.DOTALL)

            local_vars = re.finditer(r'\b((?:static\s+)?(?:const\s+)?(?:int|float|bool|char|String|long|double|byte|uint8_t|unsigned(?:\s+long)?))\s+([a-zA-Z_]\w*)\s*(?:=|;)', clean_body)
            
            for match in local_vars:
                var_type = match.group(1)
                var_name = match.group(2)
                if len(re.findall(r'\b' + re.escape(var_name) + r'\b', clean_body)) == 1:
                    issues.append({
                        "severity": "warning",
                        "line": self.find_line(code, f"{var_type} {var_name}"),
                        "message": f"Unused variable '{var_name}' in setup().",
                        "fix": lambda c, v=var_name, t=var_type: re.sub(r'\b' + re.escape(t) + r'\s+' + re.escape(v) + r'[^;]*;\s*', '', c)
                    })
        return issues
import re
from . import BaseValidator

class MemoryValidator(BaseValidator):
    def validate(self, code: str, hardware: str, user_message: str) -> list[dict]:
        issues = []
        
        # Check 24: Unused Variables in Setup
        setup_match = re.search(r'void\s+setup\s*\(\s*\)\s*\{', code)
        if setup_match:
            start_idx = setup_match.end()
            brace_count = 1
            setup_body = ""
            for char in code[start_idx:]:
                if char == '{': brace_count += 1
                elif char == '}': brace_count -= 1
                if brace_count == 0: break
                setup_body += char
            
            clean_body = re.sub(r'//.*', '', setup_body)
            clean_body = re.sub(r'/\*.*?\*/', '', clean_body, flags=re.DOTALL)

            local_vars = re.finditer(r'\b((?:static\s+)?(?:const\s+)?(?:int|float|bool|char|String|long|double|byte|uint8_t|unsigned(?:\s+long)?))\s+([a-zA-Z_]\w*)\s*(?:=|;)', clean_body)
            
            for match in local_vars:
                var_type = match.group(1)
                var_name = match.group(2)
                if len(re.findall(r'\b' + re.escape(var_name) + r'\b', clean_body)) == 1:
                    issues.append({
                        "severity": "warning",
                        "line": self.find_line(code, f"{var_type} {var_name}"),
                        "message": f"Unused variable '{var_name}' in setup().",
                        "fix": lambda c, v=var_name, t=var_type: re.sub(r'\b' + re.escape(t) + r'\s+' + re.escape(v) + r'[^;]*;\s*', '', c)
                    })
        return issues
