import urllib.request
import urllib.parse
import re

def meta():
    """
    Metadata for the Weather skill.
    """
    return {
        "name": "Weather",
        "description": "Fetches current weather using wttr.in (no API key required).",
        "triggers": ["weather", "temperature", "forecast"]
    }

def run(payload):
    """
    Fetches weather data.
    """
    prompt = payload if isinstance(payload, str) else payload.get("prompt", "")
    
    location = ""
    # Extract location: "weather in London", "weather for Paris"
    match = re.search(r'\b(?:in|for|at)\s+(.+)', prompt, re.IGNORECASE)
    if match:
        location = match.group(1).strip().rstrip("?.!")
    
    try:
        query = urllib.parse.quote(location) if location else ""
        # format=3 gives a concise one-line output (e.g., "London: ⛅️ +13°C")
        url = f"https://wttr.in/{query}?format=3"
        
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'curl/7.68.0'} # Mimic curl to ensure text output
        )
        
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                result = response.read().decode('utf-8').strip()
                return f"🌦️ {result}"
            return f"❌ Weather error: {response.status}"
                
    except Exception as e:
        return f"❌ Failed to fetch weather: {str(e)}"