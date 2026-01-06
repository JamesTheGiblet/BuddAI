import sqlite3
import re
from typing import List, Dict, Optional
from core.buddai_shared import DB_PATH, COMPLEX_TRIGGERS, MODULE_PATTERNS

class PromptEngine:
    """Handles prompt construction, hardware classification, and request analysis"""

    def classify_hardware(self, user_message: str, context_messages: List[Dict] = None) -> dict:
        """Detect what hardware this question is about"""
        
        hardware = {
            "servo": False,
            "dc_motor": False,
            "button": False,
            "led": False,
            "sensor": False,
            "weapon": False
        }
        
        msg_lower = user_message.lower()
        
        # Helper to check keywords
        def has_keywords(text, keywords):
            return any(word in text for word in keywords)

        # Keyword definitions
        servo_kws = ['servo', 'mg996', 'sg90']
        motor_kws = ['l298n', 'dc motor', 'motor driver', 'motor control']
        button_kws = ['button', 'switch', 'trigger']
        led_kws = ['led', 'light', 'brightness', 'indicator']
        # Removed 'state machine' from weapon_kws to allow abstract logic
        weapon_kws = ['weapon', 'combat', 'arming', 'fire', 'spinner', 'flipper'] 
        logic_kws = ['state machine', 'logic', 'structure', 'flow', 'armed', 'disarmed']

        # 1. Check current message first
        detected_in_current = False
        
        if has_keywords(msg_lower, servo_kws): 
            hardware["servo"] = True
            detected_in_current = True
        if has_keywords(msg_lower, motor_kws): 
            hardware["dc_motor"] = True
            detected_in_current = True
        if has_keywords(msg_lower, button_kws): 
            hardware["button"] = True
            detected_in_current = True
        if has_keywords(msg_lower, led_kws): 
            hardware["led"] = True
            detected_in_current = True
        if has_keywords(msg_lower, weapon_kws): 
            hardware["weapon"] = True
            detected_in_current = True
        if has_keywords(msg_lower, logic_kws):
            # Logic detected: Clear context (don't set any hardware)
            detected_in_current = True
            
        # 2. Context Switching: Only look back if NO hardware/logic detected in current message
        # and message is short (likely a follow-up command like "make it spin")
        if not detected_in_current and len(user_message.split()) < 10 and context_messages:
            recent = " ".join([m['content'].lower() for m in context_messages[-2:] if m['role'] == 'user'])
            
            if has_keywords(recent, servo_kws): hardware["servo"] = True
            if has_keywords(recent, motor_kws): hardware["dc_motor"] = True
            if has_keywords(recent, button_kws): hardware["button"] = True
            if has_keywords(recent, led_kws): hardware["led"] = True
            if has_keywords(recent, weapon_kws): hardware["weapon"] = True
            
        return hardware

    def get_all_rules(self) -> List[str]:
        """Get all learned rules as text"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT rule_text FROM code_rules ORDER BY confidence DESC LIMIT 50")
        rows = cursor.fetchall()
        conn.close()
        return [r[0] for r in rows]

    def filter_rules_by_hardware(self, all_rules, hardware):
        """Only return rules relevant to detected hardware"""
        
        relevant_rules = []
        
        # Define rule categories
        servo_kws = ['servo', 'attach', 'setperiodhertz']
        motor_kws = ['l298n', 'in1', 'in2', 'motor driver']
        weapon_kws = ['arming', 'disarm', 'fire', 'combat']
        button_kws = ['button', 'switch', 'debounce', 'digitalread', 'input_pullup']
        
        has_specific_context = hardware["servo"] or hardware["dc_motor"] or hardware["weapon"] or hardware["button"]
        
        for rule in all_rules:
            rule_lower = rule.lower()
            
            is_servo_rule = any(w in rule_lower for w in servo_kws)
            is_motor_rule = any(w in rule_lower for w in motor_kws)
            is_weapon_rule = any(w in rule_lower for w in weapon_kws)
            is_button_rule = any(w in rule_lower for w in button_kws)
            
            # Pattern Over-application: Strict filtering
            if has_specific_context:
                if hardware["dc_motor"] and not hardware["servo"] and is_servo_rule: continue
                if hardware["servo"] and not hardware["dc_motor"] and is_motor_rule: continue
                if not hardware["weapon"] and is_weapon_rule: continue
                if not hardware["button"] and is_button_rule: continue
            
                # If question is about weapons (logic), EXCLUDE servo rules unless servo explicitly requested
                if hardware["weapon"] and not hardware["servo"] and is_servo_rule: continue
                
            else:
                # Generic context: Exclude all specific hardware rules
                if is_servo_rule or is_motor_rule or is_weapon_rule or is_button_rule: continue

            relevant_rules.append(rule)
        
        return relevant_rules

    def build_enhanced_prompt(self, user_message: str, hardware_detected: str = None, context_messages: List[Dict] = None) -> str:
        """Build prompt with FILTERED rules"""
        
        # Classify hardware
        hardware = self.classify_hardware(user_message, context_messages)
        
        # Get ALL rules
        all_rules = self.get_all_rules()
        
        # Filter by relevance
        relevant_rules = self.filter_rules_by_hardware(all_rules, hardware)
        
        # Build focused prompt
        hardware_context = []
        if hardware["servo"]: hardware_context.append("SERVO CONTROL")
        if hardware["dc_motor"]: hardware_context.append("DC MOTOR CONTROL")
        if hardware["button"]: hardware_context.append("BUTTON INPUTS")
        if hardware["led"]: hardware_context.append("LED STATUS")
        if hardware["weapon"]: hardware_context.append("WEAPON SYSTEM")
        
        l298n_rules = ""
        if hardware["dc_motor"]:
            l298n_rules = """
- L298N WIRING RULES (MANDATORY):
  1. IN1/IN2 = Digital Output (Direction). Use digitalWrite().
  2. ENA = PWM Output (Speed). Use ledcWrite().
  3. To Move: IN1/IN2 must be OPPOSITE (HIGH/LOW).
  4. To Stop: IN1/IN2 both LOW.
  5. DO NOT treat Motors like Servos (No 'position' or 'angle').
- SAFETY RULES (MANDATORY):
  1. Implement a safety timeout (e.g., 5000ms).
  2. Stop motors if no signal is received within timeout.
  3. Use millis() for non-blocking timing.
"""

        weapon_rules = ""
        if hardware.get("weapon"):
            weapon_rules = """
- COMBAT PROTOCOL (MANDATORY):
  1. LOGIC FOCUS: This is a State Machine request, NOT just servo movement.
  2. STATES: enum State { DISARMED, ARMING, ARMED, FIRING };
  3. TRANSITIONS: DISARMED -> ARMING (2s delay) -> ARMED -> FIRING.
  4. SAFETY: Auto-disarm after 10s idle. Fire only when ARMED.
  5. STRUCTURE: Use switch(currentState) { case ... } for logic.
  6. OUTPUTS: Control relays/LEDs/Motors based on state.
"""

        # Anti-bloat rules
        anti_bloat_rules = []
        if not hardware["button"]:
            anti_bloat_rules.append("- NO EXTRA INPUTS: Do NOT add buttons, switches, or digitalRead() unless explicitly requested.")
        if not hardware["servo"]:
            anti_bloat_rules.append("- NO EXTRA SERVOS: Do NOT add Servo objects or attach() unless explicitly requested.")
        if not hardware["dc_motor"]:
            anti_bloat_rules.append("- NO EXTRA MOTORS: Do NOT add motor driver code (L298N) unless explicitly requested.")
        
        anti_bloat = "\n".join(anti_bloat_rules)

        # Modularity rule
        modularity_rule = ""
        if "function" in user_message.lower() or "naming" in user_message.lower() or "modular" in user_message.lower():
            modularity_rule = """
- CODE STRUCTURE (MANDATORY):
  1. NO MONOLITHIC LOOP: Break code into small, descriptive functions.
  2. NAMING: Use camelCase for functions (e.g., readBatteryVoltage(), updateDisplay()).
  3. loop() must ONLY call these functions, not contain raw logic.
"""

        # Status LED rule
        status_led_rule = ""
        if hardware["led"] and ("status" in user_message.lower() or "indicator" in user_message.lower()):
            status_led_rule = """
- STATUS LED RULES (MANDATORY):
  1. NO BREATHING/FADING: Do not use simple PWM fading loops.
  2. USE STATES: Define enum LEDStatus { OFF, IDLE, ACTIVE, ERROR };
  3. IMPLEMENTATION: Create void setStatusLED(LEDStatus state).
  4. PATTERNS: IDLE=Slow Blink, ACTIVE=Solid On, ERROR=Fast Blink.
"""

        prompt = f"""You are generating code for: {', '.join(hardware_context)}
You are an expert embedded developer.
TARGET HARDWARE: {hardware_detected}
ACTIVE MODULES: {', '.join(hardware_context) if hardware_context else "None (Logic Only)"}

CRITICAL: Only use code patterns relevant to the hardware mentioned.
STRICT NEGATIVE CONSTRAINTS (DO NOT IGNORE):
{anti_bloat}

MANDATORY HARDWARE RULES:
{l298n_rules}
{weapon_rules}
{status_led_rule}
{anti_bloat}
{modularity_rule}

GENERAL GUIDELINES:
- If DC MOTOR: Use L298N patterns (digitalWrite, ledcWrite)
- If SERVO: Use ESP32Servo patterns (attach, write)
- DO NOT mix servo code into motor questions
- DO NOT mix motor code into servo questions

CRITICAL RULES (MUST FOLLOW):
{chr(10).join(relevant_rules)}

USER REQUEST:
{user_message}

Generate code following ALL rules above. Do not add unrequested features.
FINAL CHECK:
1. Did you add unrequested buttons? REMOVE THEM.
2. Did you add unrequested servos? REMOVE THEM.
3. Generate code ONLY for the hardware requested.
"""
        
        return prompt

    def is_simple_question(self, message: str) -> bool:
        """Check if this is a simple question that should use FAST model"""
        message_lower = message.lower()
        
        simple_triggers = [
            "what is", "what's", "who is", "who's", "when is",
            "how do i", "can you explain", "tell me about",
            "what are", "where is", "hi", "hello", "hey",
            "good morning", "good evening"
        ]
        
        # Also check if it's just a question without code keywords
        code_keywords = ["generate", "create", "write", "build", "code", "function"]
        
        has_simple_trigger = any(trigger in message_lower for trigger in simple_triggers)
        has_code_keyword = any(keyword in message_lower for keyword in code_keywords)
        
        # Simple if: has simple trigger AND no code keywords
        return has_simple_trigger and not has_code_keyword
    
    def is_complex(self, message: str) -> bool:
        """Check if request is too complex and should be broken down"""
        message_lower = message.lower()
        
        # Count complexity triggers
        trigger_count = sum(1 for trigger in COMPLEX_TRIGGERS if trigger in message_lower)
        
        # Count how many modules mentioned
        module_count = 0
        for module, keywords in MODULE_PATTERNS.items():
            # module is used for key, keywords for values
            if any(kw in message_lower for kw in keywords):
                module_count += 1
        
        # Complex if: multiple triggers OR 3+ modules mentioned
        return trigger_count >= 2 or module_count >= 3
        
    def extract_modules(self, message: str) -> List[str]:
        """Extract which modules are needed"""
        message_lower = message.lower()
        needed_modules = []
        
        for module, keywords in MODULE_PATTERNS.items():
            # module is used for key, keywords for values
            if any(kw in message_lower for kw in keywords):
                needed_modules.append(module)
                
        return needed_modules
        
    def build_modular_plan(self, modules: List[str]) -> List[Dict[str, str]]:
        """Create a build plan from modules"""
        plan = []
        
        module_tasks = {
            "ble": "BLE communication setup with phone app control",
            "servo": "Servo motor control for flipper/weapon",
            "motor": "Motor driver setup for movement (L298N)",
            "safety": "Safety timeout and failsafe systems",
            "battery": "Battery voltage monitoring",
            "sensor": "Sensor integration (distance/proximity)"
        }
        
        for module in modules:
            if module in module_tasks:
                plan.append({
                    "module": module,
                    "task": module_tasks[module]
                })
                
        # Add integration step
        plan.append({
            "module": "integration",
            "task": "Integrate all modules into complete system"
        })
        
        return plan