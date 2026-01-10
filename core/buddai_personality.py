import json
from pathlib import Path
from typing import Dict, Any, Union, List
from datetime import datetime

class PersonalityManager:
    """Manages AI personality, prompts, and user schedules"""
    
    def __init__(self):
        self.personality = self.load_personality()
        self.validate_personality_schema()

    def load_personality(self) -> Dict:
        """Loads personality from a JSON file."""
        personality_path = Path(__file__).parent.parent / "personality.json"
        if personality_path.exists():
            print("🧠 Loading custom personality...")
            with open(personality_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # Default personality if file doesn't exist
            print("🧠 Using default 'James' personality.")
            return {
                "user_name": "James",
                "ai_name": "BuddAI",
                "welcome_message": "BuddAI Executive v4.0 - Decoupled & Personality Sync",
                "schedule_check_triggers": ["what should i be doing", "my schedule", "schedule check"],
                "schedule": {
                    "weekdays": {"0-4": {"5.5-6.5": "Early Morning Build Session 🌅 (5:30-6:30 AM)", "6.5-17.0": "Work Hours (Facilities Caretaker) 🏢", "17.0-21.0": "Evening Build Session 🌙 (5:00-9:00 PM)", "default": "Rest Time 💤"}},
                    "saturday": { "5": { "default": "Weekend Freedom 🎨 (Creative Mode)" } },
                    "sunday": { "6": { "0-21.0": "Weekend Freedom 🎨 (Until 9 PM)", "default": "Rest Time 💤" } }
                },
                "style_scan_prompt": "Analyze this code sample from {user_name}'s repositories.\nExtract 3 distinct coding preferences or patterns.",
                "style_reference_prompt": "\n[REFERENCE STYLE FROM {user_name}'S PAST PROJECTS]\n",
                "integration_task_prompt": "INTEGRATION TASK: Combine modules into a cohesive GilBot system.\n\n[MODULES]\n{modules_summary}\n\n[FORGE PARAMETERS]\nSet k = {k_val} for all applyForge() calls.\n\n[REQUIREMENTS]\n1. Implement applyForge() math helper.\n2. Use k={k_val} to smooth motor and servo transitions.\n3. Ensure naming matches {user_name}'s style: activateFlipper(), setMotors()."
            }

    def validate_personality_schema(self) -> bool:
        """Validate the loaded personality against required schema."""
        if not self.personality:
            return False

        required_structure = {
            "meta": ["version"],
            "identity": ["user_name", "ai_name"],
            "communication": ["welcome_message"],
            "work_cycles": ["schedule"],
            "forge_theory": ["enabled", "constants"],
            "prompts": ["style_scan", "integration_task"]
        }
        
        missing = []
        
        version = self.get_value("meta.version")
        if version and version != "4.5":
             print(f"⚠️ Warning: Personality version mismatch. Loaded: {version}, Expected: 4.5")

        for section, keys in required_structure.items():
            if section not in self.personality:
                missing.append(f"Missing section: {section}")
                continue
                
            for key in keys:
                if key not in self.personality[section]:
                    missing.append(f"Missing key: {section}.{key}")
        
        if missing:
            print("⚠️ Personality Schema Validation Failed:")
            for m in missing:
                print(f"  - {m}")
            return False
            
        return True

    def get_value(self, path: Union[str, List[str]], default: Any = None) -> Any:
        """Access nested personality keys using dot notation or list of keys."""
        if isinstance(path, str):
            keys = path.split('.')
        else:
            keys = path
            
        val = self.personality
        for key in keys:
            if isinstance(val, dict):
                val = val.get(key)
            else:
                return default
        return val if val is not None else default

    def get_user_status(self) -> str:
        """Determine user's context based on defined schedule from personality file."""
        schedule = self.get_value("work_cycles.schedule")
        if not schedule:
            # Fallback for simple personality files
            schedule = self.personality.get("schedule")
        if not schedule:
            return "Schedule not defined."

        now = datetime.now()
        day = now.weekday() # 0=Mon, 6=Sun
        t = now.hour + (now.minute / 60.0)

        # Check all schedule groups (e.g., 'weekdays', 'weekends')
        for group, day_ranges in schedule.items():
            for day_range, time_slots in day_ranges.items():
                try:
                    # Parse day range (e.g., "0-4" or "5")
                    if '-' in day_range:
                        start_day, end_day = map(int, day_range.split('-'))
                        if not (start_day <= day <= end_day):
                            continue
                    elif int(day_range) != day:
                        continue
                    
                    # We found the right day group, now check time slots
                    for time_range, status in time_slots.items():
                        if time_range == "default": continue
                        start_time, end_time = map(float, time_range.split('-'))
                        if start_time <= t < end_time:
                            return status.get("description", status) if isinstance(status, dict) else status
                    
                    default_status = time_slots.get("default", "No status for this time.")
                    return default_status.get("description", default_status) if isinstance(default_status, dict) else default_status
                    
                except (ValueError, TypeError): continue
        return "No schedule match for today."