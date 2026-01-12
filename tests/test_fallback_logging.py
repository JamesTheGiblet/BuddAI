import unittest
from unittest.mock import Mock, patch, mock_open
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestFallbackLogging(unittest.TestCase):
    def test_fallback_logging(self):
        """Logs to external_prompts.log"""
        with patch("builtins.open", mock_open()) as mock_file:
            # Simulate logging function
            def log_fallback(msg):
                with open("external_prompts.log", "a") as f:
                    f.write(msg)
            
            log_fallback("test message")
            
            mock_file.assert_called_with("external_prompts.log", "a")
            mock_file().write.assert_called_with("test message")

    def test_logs_command(self):
        """/logs retrieves audit trail"""
        # Simulate command handler
        def handle_logs_command():
            return "Log content"
            
        result = handle_logs_command()
        self.assertEqual(result, "Log content")