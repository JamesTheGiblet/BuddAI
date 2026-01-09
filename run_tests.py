#!/usr/bin/env python3
import unittest
import sys
import os

def run_tests():
    """Run the full BuddAI test suite"""
    print("🧪 Starting BuddAI Validation Suite...")
    
    # Discover and run tests
    loader = unittest.TestLoader()
    start_dir = os.path.join(os.path.dirname(__file__), 'tests')
    
    if not os.path.exists(start_dir):
        print(f"❌ Test directory not found: {start_dir}")
        return

    # Run all tests
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    if result.wasSuccessful():
        print("\n✅ All tests passed! System is production ready.")
        sys.exit(0)
    else:
        print(f"\n❌ Validation Failed: {len(result.failures)} failures, {len(result.errors)} errors.")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()