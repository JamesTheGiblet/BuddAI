# validators/bluetooth_validator.py
from .base_validator import BaseValidator

class BluetoothValidator(BaseValidator):
    name = "Bluetooth Validator"
    triggers = ["bluetooth", "ble", "esp_bt"]
    priority = 3
    
    def add_ble_init(self, code: str) -> str:
        # Insert BLEDevice::init() at the beginning of the code
        return 'BLEDevice::init();\n' + code

    def validate(self, code: str, hardware: str, user_message: str) -> list:
        issues = []
        
        # Check for missing BLE init
        if "BLEDevice" in code and "BLEDevice::init" not in code:
            issues.append({
                "severity": "error",
                "message": "Missing BLEDevice::init()",
                "fix": lambda c: self.add_ble_init(c)
            })
        
        return issues