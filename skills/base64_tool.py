import base64

def run(message):
    """
    Encode or decode Base64.
    Usage: base64 encode <text> OR base64 decode <text>
    """
    try:
        if "encode" in message.lower():
            text = message.split("encode", 1)[1].strip()
            encoded = base64.b64encode(text.encode()).decode()
            return f"Encoded: `{encoded}`"
        elif "decode" in message.lower():
            text = message.split("decode", 1)[1].strip()
            decoded = base64.b64decode(text).decode()
            return f"Decoded: `{decoded}`"
        return "Usage: base64 encode <text> OR base64 decode <text>"
    except Exception as e:
        return f"Base64 Error: {e}"

skill = {
    "name": "Base64 Tool",
    "description": "Encode or decode Base64 strings",
    "triggers": ["base64"],
    "run": run
}