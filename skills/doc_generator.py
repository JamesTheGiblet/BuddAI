import ast

def run(message):
    """
    Generate Markdown documentation for Python code.
    Usage: generate docs <code_snippet>
    """
    try:
        # Extract code
        triggers = ["generate docs", "document code", "create documentation"]
        code = message
        lower_msg = message.lower()
        
        for t in triggers:
            if t in lower_msg:
                idx = lower_msg.find(t) + len(t)
                code = message[idx:].strip()
                break
        
        # Clean markdown
        if code.startswith("```"):
            lines = code.splitlines()
            if len(lines) >= 2 and lines[-1].strip() == "```":
                code = "\n".join(lines[1:-1])
            elif len(lines) >= 1:
                 code = "\n".join(lines[1:])
        code = code.strip("`").strip()

        if not code:
            return "Usage: generate docs <code_snippet>"

        tree = ast.parse(code)
        output = ["# 📘 API Documentation\n"]
        
        has_content = False

        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                has_content = True
                args = [a.arg for a in node.args.args]
                output.append(f"## 𝑓 `{node.name}({', '.join(args)})`")
                doc = ast.get_docstring(node)
                output.append(doc.strip() if doc else "_No description._")
                output.append("")
            
            elif isinstance(node, ast.ClassDef):
                has_content = True
                output.append(f"## 📦 Class `{node.name}`")
                doc = ast.get_docstring(node)
                output.append(doc.strip() if doc else "_No description._")
                output.append("")
                
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        args = [a.arg for a in item.args.args if a.arg != 'self']
                        output.append(f"* **`{item.name}({', '.join(args)})`**")
                        method_doc = ast.get_docstring(item)
                        if method_doc:
                            output.append(f"  > {method_doc.strip()}")
                output.append("")

        if not has_content:
            return "⚠️ No functions or classes found to document."

        return "\n".join(output)

    except SyntaxError:
        return "❌ Syntax Error: Code provided is not valid Python."
    except Exception as e:
        return f"Generator Error: {e}"

skill = {
    "name": "Doc Generator",
    "description": "Generates Markdown API documentation from Python code structure.",
    "triggers": ["generate docs", "document code", "create documentation"],
    "run": run
}