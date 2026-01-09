import hashlib

def run(message):
    """
    Generate hashes.
    Usage: sha256 <text> OR md5 <text>
    """
    try:
        msg_lower = message.lower()
        algo = "sha256"
        if "md5" in msg_lower: algo = "md5"
        elif "sha1" in msg_lower: algo = "sha1"
        
        # Extract text to hash
        # Split by algorithm name to get content
        parts = message.split(algo, 1)
        if len(parts) > 1:
            text = parts[1].strip()
        else:
            return f"Usage: {algo} <text>"
            
        h = hashlib.new(algo)
        h.update(text.encode())
        return f"🔒 {algo.upper()}: `{h.hexdigest()}`"
    except Exception as e:
        return f"Hash Error: {e}"

skill = {
    "name": "Hash Generator",
    "description": "Generate MD5/SHA1/SHA256 hashes",
    "triggers": ["hash", "md5", "sha256", "sha1"],
    "run": run
}