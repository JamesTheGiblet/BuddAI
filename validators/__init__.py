from typing import List, Dict

class BaseValidator:
    def validate(self, code: str, hardware: str, user_message: str) -> List[Dict]:
        """Return a list of issues found."""
        return []

    def find_line(self, code: str, substring: str) -> int:
        for i, line in enumerate(code.splitlines(), 1):
            if substring in line:
                return i
        return -1

from .esp32_basics import ESP32Validator
from .motor_control import MotorValidator
from .servo_control import ServoValidator
from .memory_safety import MemoryValidator
from .forge_theory import ForgeTheoryValidator
from .timing_safety import TimingValidator
from .arduino_compat import ArduinoValidator
from .style_guide import StyleValidator
from .security_validator import SecurityValidator
