import unittest
import sys
import os
from datetime import datetime

def run_suite():
    """
    Discover and run all tests in the tests/ directory.
    """
    # Get directories
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(tests_dir)
    reports_dir = os.path.join(tests_dir, "reports")
    
    if not os.path.exists(reports_dir):
        os.makedirs(reports_dir)
    
    # Add project root to sys.path to allow imports of 'core', 'skills', etc.
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        
    # Discover tests
    loader = unittest.TestLoader()
    suite = loader.discover(tests_dir, pattern="test_*.py", top_level_dir=project_root)
    
    # Setup report file
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    report_path = os.path.join(reports_dir, f"test_report_{timestamp}.txt")
    
    print(f"🚀 Running tests... (Logging to {report_path})")
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"BuddAI Test Report\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*60 + "\n\n")
        
        # Run tests
        runner = unittest.TextTestRunner(stream=f, verbosity=2)
        result = runner.run(suite)
        
        f.write("\n" + "="*60 + "\n")
        f.write(f"SUMMARY:\n")
        f.write(f"Ran: {result.testsRun} tests\n")
        f.write(f"Failures: {len(result.failures)}\n")
        f.write(f"Errors: {len(result.errors)}\n")
        
    if result.wasSuccessful():
        print(f"✅ All {result.testsRun} tests passed!")
    else:
        print(f"❌ Tests failed! ({len(result.failures)} failures, {len(result.errors)} errors)")
        print(f"📝 Check report: {report_path}")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_suite()
    sys.exit(0 if success else 1)