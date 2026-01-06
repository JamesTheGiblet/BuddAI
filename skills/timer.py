import time
import re
import threading

def meta():
    """
    Metadata for the Timer skill.
    """
    return {
        "name": "Timer",
        "description": "Sets a non-blocking timer (background thread).",
        "triggers": ["timer", "sleep", "wait for"]
    }

def run(payload):
    """
    Executes the blocking sleep.
    """
    prompt = payload if isinstance(payload, str) else payload.get("prompt", "")
    
    # Regex to capture number and optional unit (e.g., "5", "5s", "5 minutes")
    match = re.search(r'(\d+)\s*(seconds?|secs?|s|minutes?|mins?|m)?', prompt.lower())
    
    if not match:
        return None # Fallback to LLM if no time found
        
    amount = int(match.group(1))
    unit = match.group(2)
    
    duration = amount
    if unit and unit.startswith('m'):
        duration *= 60
        
    if duration > 3600:
        return f"❌ Timer too long ({duration}s). Max 1 hour."
        
    def _timer_thread():
        time.sleep(duration)
        print(f"\n\n⏰ 🔔 BEEP! Timer finished ({duration}s).\n")

    t = threading.Thread(target=_timer_thread, daemon=True)
    t.start()
    
    return f"⏰ Timer started for {duration} seconds (running in background)..."