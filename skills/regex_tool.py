import re

def run(message):
    """
    Test regex patterns.
    Usage: regex test <pattern> on <string>
    """
    try:
        # Regex to capture pattern and text
        # Supports: regex test \d+ on "Order 123"
        match = re.search(r'regex test\s+(.*?)\s+on\s+(.*)', message, re.IGNORECASE)
        if match:
            pattern = match.group(1).strip()
            text = match.group(2).strip()
            
            # Strip quotes if user wrapped them
            if pattern.startswith('"') and pattern.endswith('"'): pattern = pattern[1:-1]
            if text.startswith('"') and text.endswith('"'): text = text[1:-1]
            
            found = re.findall(pattern, text)
            if found:
                return f"✅ Matches found ({len(found)}): {found}"
            return "❌ No matches found."
        return "Usage: regex test <pattern> on <string>"
    except Exception as e:
        return f"Regex Error: {e}"

skill = {
    "name": "Regex Tester",
    "description": "Test regex patterns against strings",
    "triggers": ["regex test"],
    "run": run
}