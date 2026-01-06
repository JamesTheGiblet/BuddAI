import unittest
import io
import sys
from pathlib import Path

def meta():
    """
    Metadata for the Test Runner skill.
    """
    return {
        "name": "Self-Diagnostic",
        "description": "Runs the internal unit test suite (tests/*.py).",
        "triggers": ["test all", "run tests", "self diagnostic", "check systems", "verify integrity"]
    }

def run(payload):
    """
    Discovers and runs tests in the tests/ directory.
    """
    # Root dir is parent of skills/ (i.e., buddAI/)
    root_dir = Path(__file__).parent.parent
    tests_dir = root_dir / "tests"
    
    if not tests_dir.exists():
        return "❌ Diagnostics failed: 'tests' directory not found."

    # Capture output
    log_capture = io.StringIO()
    
    # Create a test runner that writes to our capture stream
    runner = unittest.TextTestRunner(stream=log_capture, verbosity=1)
    loader = unittest.TestLoader()
    
    try:
        # Ensure root_dir is in sys.path so tests can import 'core', 'skills', etc.
        if str(root_dir) not in sys.path:
            sys.path.insert(0, str(root_dir))
            
        # Discover tests
        suite = loader.discover(str(tests_dir), pattern="test_*.py", top_level_dir=str(root_dir))
        
        num_tests = suite.countTestCases()
        if num_tests == 0:
            return "⚠️ No tests found in tests/ directory."
            
        # Run tests
        result = runner.run(suite)
        
        # Get output string
        output = log_capture.getvalue()
        
        # Construct response
        header = "✅ **All Systems Operational**" if result.wasSuccessful() else "❌ **System Failures Detected**"
        stats = f"Executed {result.testsRun} tests."
        
        if not result.wasSuccessful():
            stats += f"\n🔴 Failures: {len(result.failures)}"
            stats += f"\n⚠️ Errors: {len(result.errors)}"
            
        # Limit output length for chat
        console_output = output
        if len(console_output) > 1500:
            console_output = "..." + console_output[-1500:]
            
        return f"{header}\n{stats}\n\n**Console Output:**\n```text\n{console_output}\n```"
        
    except Exception as e:
        return f"❌ Execution Error: {str(e)}"