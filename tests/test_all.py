import unittest
import sys
import os

def run_suite():
    """
    Discover and run all tests in the tests/ directory.
    """
    # Get directories
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(tests_dir)
    
    # Add project root to sys.path to allow imports of 'core', 'skills', etc.
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        
    # Discover tests
    loader = unittest.TestLoader()
    suite = loader.discover(tests_dir, pattern="test_*.py", top_level_dir=project_root)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_suite()
    sys.exit(0 if success else 1)