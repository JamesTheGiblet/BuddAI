import re

def meta():
    """
    Defines the metadata for the Calculator skill.
    """
    return {
        "name": "Smart Calculator",
        "description": "Performs basic arithmetic operations detected in the prompt.",
        "triggers": ["calculate", "compute", "solve", "math", "+", "-", "*", "/"]
    }

def run(payload):
    """
    Executes the calculation logic.
    Accepts a string prompt or a dictionary context.
    """
    # Normalize input
    prompt = payload if isinstance(payload, str) else payload.get("prompt", "")
    
    # 1. Extract the mathematical expression
    # Regex looks for sequences of numbers and operators
    # Allowed: digits, whitespace, +, -, *, /, ., (, )
    match = re.search(r'([\d\.\s\+\-\*\/\(\)]+)', prompt)
    
    if not match:
        return None # Fallback to LLM if no math found
        
    expression = match.group(0).strip()
    
    if not any(char.isdigit() for char in expression):
        return None
    
    # 2. Safety Check (Double verification)
    allowed_chars = set("0123456789.+-*/() ")
    if not set(expression).issubset(allowed_chars):
        return "Calculation aborted: Invalid characters detected."
    
    # 3. Execute
    try:
        # pylint: disable=eval-used
        result = eval(expression, {"__builtins__": None}, {})
        return f"🧮 Result: {expression} = {result}"
    except ZeroDivisionError:
        return "🧮 Error: Division by zero is not allowed."
    except Exception as e:
        return f"🧮 Calculation Error: {str(e)}"