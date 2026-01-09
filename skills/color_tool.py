import re

def run(message):
    """
    Convert colors between Hex and RGB.
    Usage: hex to rgb #FF0000 OR rgb to hex 255, 0, 0
    """
    msg = message.lower()
    try:
        # Hex to RGB
        if "#" in msg:
            hex_match = re.search(r'#([0-9a-fA-F]{6})', msg)
            if hex_match:
                hex_val = hex_match.group(1)
                r = int(hex_val[0:2], 16)
                g = int(hex_val[2:4], 16)
                b = int(hex_val[4:6], 16)
                return f"🎨 RGB: ({r}, {g}, {b})"
        
        # RGB to Hex
        rgb_match = re.search(r'(\d+)\s*,\s*(\d+)\s*,\s*(\d+)', msg)
        if rgb_match:
            r, g, b = map(int, rgb_match.groups())
            return "🎨 Hex: #{:02x}{:02x}{:02x}".format(r, g, b)
                
        return "Usage: hex to rgb #RRGGBB OR rgb to hex R, G, B"
    except Exception as e:
        return f"Color Error: {e}"

skill = {
    "name": "Color Converter",
    "description": "Convert between Hex and RGB colors",
    "triggers": ["hex to rgb", "rgb to hex", "color convert"],
    "run": run
}