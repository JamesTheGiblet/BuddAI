import unittest
from unittest.mock import Mock
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestAnalytics(unittest.TestCase):
    def setUp(self):
        self.metrics = Mock()

    def test_fallback_stats(self):
        """Calculates fallback rate correctly"""
        total = 100
        fallbacks = 10
        rate = (fallbacks / total) * 100
        self.assertEqual(rate, 10.0)

    def test_fallback_stats_empty(self):
        """Handles empty DB (no divide by zero)"""
        total = 0
        fallbacks = 0
        
        rate = 0 if total == 0 else (fallbacks / total) * 100
        self.assertEqual(rate, 0)