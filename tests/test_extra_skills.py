#!/usr/bin/env python3
"""
Unit tests for Extra Skills (Regex, JSON, Base64, Color, Hash)
"""
import unittest
from unittest.mock import patch
import sys
from pathlib import Path

# Setup path
REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Import skills directly to test logic without registry loading overhead
from skills import regex_tool, json_tool, base64_tool, color_tool, hash_tool, file_search_tool

class TestExtraSkills(unittest.TestCase):

    def test_regex_tool(self):
        # Test match
        res = regex_tool.run('regex test \\d+ on "Order 123"')
        self.assertIn("123", res)
        # Test no match
        res = regex_tool.run('regex test abc on "123"')
        self.assertIn("No matches", res)

    def test_json_tool(self):
        # Test valid JSON
        res = json_tool.run('format json {"key": "value"}')
        self.assertIn('"key": "value"', res)
        # Test invalid JSON
        res = json_tool.run('format json {invalid}')
        self.assertIn("Invalid JSON", res)

    def test_base64_tool(self):
        # Test encode
        res = base64_tool.run('base64 encode hello')
        self.assertIn("aGVsbG8=", res)
        # Test decode
        res = base64_tool.run('base64 decode aGVsbG8=')
        self.assertIn("hello", res)

    def test_color_tool(self):
        # Test Hex to RGB
        self.assertIn("(255, 0, 0)", color_tool.run("hex to rgb #FF0000"))
        # Test RGB to Hex
        self.assertIn("#00ff00", color_tool.run("rgb to hex 0, 255, 0"))

    def test_hash_tool(self):
        self.assertIn("5d41402abc4b2a76b9719d911017c592", hash_tool.run("md5 hello"))

    def test_file_search_tool(self):
        # Mock os.walk to simulate file system
        with patch('os.walk') as mock_walk:
            mock_walk.return_value = [('/root', [], ['test_file.py'])]
            with patch('pathlib.Path.cwd', return_value=Path('/root')):
                res = file_search_tool.run("find file *.py")
                self.assertIn("test_file.py", res)

if __name__ == '__main__':
    unittest.main()