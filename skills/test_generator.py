import ast

def run(message):
    """
    Generate unittest boilerplate for Python code.
    Usage: generate tests <code_snippet>
    """
    try:
        # Extract code logic
        triggers = ["generate tests", "create tests", "write tests"]
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
            return "Usage: generate tests <code_snippet>"

        tree = ast.parse(code)
        output = ["import unittest", ""]
        
        has_content = False

        # Find functions at module level
        funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
        if funcs:
            has_content = True
            output.append("class TestGenerated(unittest.TestCase):")
            for func in funcs:
                output.append(f"    def test_{func.name}(self):")
                output.append(f"        # TODO: Write test for {func.name}")
                output.append(f"        pass")
                output.append("")

        # Find classes
        classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
        for cls in classes:
            has_content = True
            output.append(f"class Test{cls.name}(unittest.TestCase):")
            methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and not n.name.startswith("__")]
            if not methods:
                output.append("    pass")
            for method in methods:
                output.append(f"    def test_{method.name}(self):")
                output.append(f"        # TODO: Write test for {cls.name}.{method.name}")
                output.append(f"        pass")
                output.append("")

        if not has_content:
            return "⚠️ No functions or classes found to test."
            
        output.append("if __name__ == '__main__':")
        output.append("    unittest.main(verbosity=2)")

        return "\n".join(output)

    except SyntaxError:
        return "❌ Syntax Error: Code provided is not valid Python."
    except Exception as e:
        return f"Generator Error: {e}"

skill = {
    "name": "Test Generator",
    "description": "Generates unittest boilerplate from Python code structure.",
    "triggers": ["generate tests", "create tests", "write tests"],
    "run": run
}