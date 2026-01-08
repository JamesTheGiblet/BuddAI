#!/usr/bin/env python3
"""
Unit tests for BuddAI Analytics
Verifies calculation of accuracy, trends, and fallback statistics.
"""

import unittest
import sqlite3
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import patch

# Setup path
REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.buddai_analytics import LearningMetrics

class TestAnalytics(unittest.TestCase):
    def setUp(self):
        # Create temp DB
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.db_fd)
        self.db_path_obj = Path(self.db_path)
        
        # Patch DB_PATH in analytics module
        self.db_patcher = patch('core.buddai_analytics.DB_PATH', self.db_path_obj)
        self.db_patcher.start()
        
        # Initialize DB tables
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT,
                content TEXT,
                timestamp TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS code_rules (
                id INTEGER PRIMARY KEY,
                rule_text TEXT,
                learned_from TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                message_id INTEGER,
                positive BOOLEAN
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS corrections (
                id INTEGER PRIMARY KEY,
                original_code TEXT
            )
        """)
        
        conn.commit()
        conn.close()
        
        self.metrics = LearningMetrics()

    def tearDown(self):
        self.db_patcher.stop()
        try:
            os.unlink(self.db_path)
        except:
            pass

    def test_fallback_stats(self):
        """Test calculation of fallback statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 1. Insert Messages (10 total assistant, 4 fallbacks)
        # 6 normal responses
        for _ in range(6):
            cursor.execute("INSERT INTO messages (role, content) VALUES (?, ?)", ("assistant", "Normal response"))
        # 4 fallback responses
        for _ in range(4):
            cursor.execute("INSERT INTO messages (role, content) VALUES (?, ?)", ("assistant", "Response with Fallback Triggered inside"))
        # Some user messages (should be ignored)
        cursor.execute("INSERT INTO messages (role, content) VALUES (?, ?)", ("user", "Help me"))
            
        # 2. Insert Rules (2 from fallback)
        cursor.execute("INSERT INTO code_rules (rule_text, learned_from) VALUES (?, ?)", ("Rule 1", "fallback_claude"))
        cursor.execute("INSERT INTO code_rules (rule_text, learned_from) VALUES (?, ?)", ("Rule 2", "fallback_gpt4"))
        cursor.execute("INSERT INTO code_rules (rule_text, learned_from) VALUES (?, ?)", ("Rule 3", "user_correction"))
        
        conn.commit()
        conn.close()
        
        # Calculate stats
        stats = self.metrics.get_fallback_stats()
        
        # Assertions
        # Total escalations: 4
        self.assertEqual(stats['total_escalations'], 4)
        
        # Fallback rate: 4 / 10 = 40.0%
        self.assertEqual(stats['fallback_rate'], 40.0)
        
        # Learning success: 2 rules / 4 escalations = 50.0%
        self.assertEqual(stats['learning_success'], 50.0)

    def test_fallback_stats_empty(self):
        """Test stats with empty database"""
        stats = self.metrics.get_fallback_stats()
        
        self.assertEqual(stats['total_escalations'], 0)
        self.assertEqual(stats['fallback_rate'], 0.0)
        self.assertEqual(stats['learning_success'], 0.0)

if __name__ == '__main__':
    unittest.main()
