import os
import fnmatch
from pathlib import Path

IGNORE_DIRS = {'.git', '__pycache__', 'node_modules', 'venv', 'env', '.idea', '.vscode', 'dist', 'build'}

def run(message):
    """
    Search for files by name pattern.
    Usage: find file <name_pattern>
    """
    try:
        # Extract pattern
        # "find file *.py" -> "*.py"
        lower_msg = message.lower()
        triggers = ["find file", "search file", "locate file", "search for file"]
        pattern = ""
        
        for t in triggers:
            if t in lower_msg:
                pattern = message[lower_msg.find(t) + len(t):].strip()
                break
        
        if not pattern:
            return "Usage: find file <filename_pattern> (e.g., `find file *.py`)"
            
        # Clean pattern
        pattern = pattern.replace('"', '').replace("'", "")
        
        matches = []
        root_dir = Path.cwd()
        max_matches = 20
        
        for root, dirs, files in os.walk(root_dir):
            # Skip ignored directories
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith('.')]
            
            for filename in fnmatch.filter(files, pattern):
                rel_path = Path(root).relative_to(root_dir) / filename
                matches.append(str(rel_path))
                if len(matches) >= max_matches:
                    return f"📂 Found {len(matches)}+ files matching `{pattern}` (showing first {max_matches}):\n" + "\n".join([f"- `{m}`" for m in matches])

        if matches:
            return f"📂 Found {len(matches)} files matching `{pattern}`:\n" + "\n".join([f"- `{m}`" for m in matches])
        return f"❌ No files found matching `{pattern}` in current directory."
            
    except Exception as e:
        return f"File Search Error: {e}"

skill = {
    "name": "File Search Tool",
    "description": "Find files by name pattern in the current directory",
    "triggers": ["find file", "search file", "locate file"],
    "run": run
}