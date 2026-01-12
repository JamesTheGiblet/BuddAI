import unittest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path
import sqlite3
import tempfile
import os

# Setup path
REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from buddai_executive import BuddAI

class TestSmartLearning(unittest.TestCase):
    def setUp(self):
        # Create temp DB file so connections share the same DB
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.db_fd)

        # Mock dependencies to avoid full initialization
        with patch('buddai_executive.StorageManager'), \
             patch('buddai_executive.PersonalityManager'), \
             patch('buddai_executive.RepoManager'), \
             patch('buddai_executive.OllamaClient'), \
             patch('builtins.print'):
            self.ai = BuddAI(server_mode=False)
            # Use temp DB
            self.ai.db_path = self.db_path

        # Setup DB schema
        conn = sqlite3.connect(self.ai.db_path)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS code_rules (rule_text TEXT, pattern_find TEXT, pattern_replace TEXT, confidence REAL, learned_from TEXT)")
        conn.commit()
        conn.close()

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_teach_rule_returns_true_for_new(self):
        """Test that teach_rule returns True when a new rule is added"""
        result = self.ai.teach_rule("Always use const")
        self.assertTrue(result)

    def test_teach_rule_returns_false_for_duplicate(self):
        """Test that teach_rule returns False when rule exists"""
        self.ai.teach_rule("Always use const")
        result = self.ai.teach_rule("Always use const")
        self.assertFalse(result)

    def test_teach_rule_persistence(self):
        """Test that rule is actually saved to database"""
        self.ai.teach_rule("Use async await")
        
        conn = sqlite3.connect(self.ai.db_path)
        row = conn.execute("SELECT rule_text FROM code_rules WHERE rule_text = ?", ("Use async await",)).fetchone()
        conn.close()
        
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "Use async await")

if __name__ == '__main__':
    unittest.main()