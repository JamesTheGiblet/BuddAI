import ast

def run(message):
    """
    Analyze code snippets for basic metrics.
    Usage: analyze code <code_snippet>
    """
    try:
        # Extract code from message
        triggers = ["analyze code", "check code", "code stats"]
        code = message
        lower_msg = message.lower()
        
        for t in triggers:
            if t in lower_msg:
                idx = lower_msg.find(t) + len(t)
                code = message[idx:].strip()
                break
        
        # Strip markdown code blocks
        if code.startswith("```"):
            lines = code.splitlines()
            # If it's a block like ```python ... ```
            if len(lines) >= 2 and lines[-1].strip() == "```":
                code = "\n".join(lines[1:-1])
            elif len(lines) >= 1:
                 # Just strip the first line if it is ```
                 code = "\n".join(lines[1:])
        
        code = code.strip("`").strip()

        if not code:
            return "Usage: analyze code <code_snippet>"

        stats = []
        stats.append(f"📊 Code Analysis Report")
        stats.append(f"-----------------------")
        stats.append(f"📏 Total Characters: {len(code)}")
        stats.append(f"📝 Total Lines: {len(code.splitlines())}")

        # Try Python AST analysis
        try:
            tree = ast.parse(code)
            functions = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
            classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
            imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
            
            stats.append(f"🐍 Python Structure:")
            stats.append(f"   • Functions: {len(functions)}")
            stats.append(f"   • Classes: {len(classes)}")
            stats.append(f"   • Imports: {len(imports)}")
            
        except SyntaxError:
            stats.append("📄 Text/Generic Analysis:")
            non_empty = [l for l in code.splitlines() if l.strip()]
            stats.append(f"   • Non-empty lines: {len(non_empty)}")

        return "\n".join(stats)

    except Exception as e:
        return f"Analysis Error: {e}"

skill = {
    "name": "Code Analyzer",
    "description": "Analyze code snippets for basic metrics (lines, functions, classes)",
    "triggers": ["analyze code", "check code", "code stats"],
    "run": run
}