# tests/test_validators.py
from validators import ESP32Validator, MotorValidator

def test_esp32_validator():
    validator = ESP32Validator()
    
    bad_code = """
    void loop() {
        analogWrite(LED_PIN, 128);  // Wrong for ESP32
        int val = analogRead(A0) / 1023.0;  // Wrong ADC
    }
    """
    
    issues = validator.validate(bad_code, "ESP32-C3", "")
    
    assert len(issues) == 2
    assert "analogWrite" in issues[0]['message']
    assert "4095" in issues[1]['message']

def test_motor_validator():
    validator = MotorValidator()
    
    code_missing_pins = """
    void loop() {
        ledcWrite(0, 255);  // No pin definitions!
    }
    """
    
    issues = validator.validate(code_missing_pins, "ESP32", "motor driver l298n")
    
    assert any("IN1" in issue['message'] for issue in issues)
    assert any("ENA" in issue['message'] for issue in issues)