import json

def run(message):
    """
    Validate and pretty-print JSON.
    Usage: format json {...}
    """
    try:
        # Heuristic: Find first '{' or '['
        start = -1
        for i, char in enumerate(message):
            if char in '{[':
                start = i
                break
        
        if start == -1:
            return "❌ No JSON object or array found in message."
            
        json_str = message[start:]
        parsed = json.loads(json_str)
        return "```json\n" + json.dumps(parsed, indent=2) + "\n```"
    except json.JSONDecodeError as e:
        return f"❌ Invalid JSON: {e}"

skill = {
    "name": "JSON Formatter",
    "description": "Validate and pretty-print JSON",
    "triggers": ["format json", "pretty json", "validate json"],
    "run": run
}