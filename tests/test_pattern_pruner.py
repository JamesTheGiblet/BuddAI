#!/usr/bin/env python3
"""
Unit tests for Pattern Pruner
Verifies candidate identification, safety filters, and pruning logic.
"""

import unittest
import sqlite3
from unittest.mock import MagicMock
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from pattern.pattern_pruner import PatternPruner
except ImportError:
    from pattern_pruner import PatternPruner

class TestPatternPruner(unittest.TestCase):
    def setUp(self):
        # Create in-memory DB
        self.db = sqlite3.connect(':memory:')
        self.db.row_factory = sqlite3.Row
        
        # Create corrections table
        self.db.execute("""
            CREATE TABLE corrections (
                id INTEGER PRIMARY KEY,
                pattern_text TEXT,
                correction_text TEXT,
                created_at TEXT,
                last_used TEXT,
                use_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0
            )
        """)
        
        # Create favorites table (for safety filter test)
        self.db.execute("""
            CREATE TABLE favorites (
                id INTEGER PRIMARY KEY,
                pattern_id INTEGER,
                created_at TEXT
            )
        """)
        
        self.mock_scorer = MagicMock()
        # Initialize pruner with small limits for testing
        self.pruner = PatternPruner(
            self.db, 
            self.mock_scorer, 
            min_score_threshold=20.0, 
            min_keep_count=2, 
            min_age_days=30
        )

    def tearDown(self):
        self.db.close()

    def test_identify_prune_candidates_low_score(self):
        """Test that low scoring patterns are identified"""
        now = datetime.now()
        old_date = (now - timedelta(days=60)).isoformat()
        
        # Insert 3 patterns
        self.db.execute("INSERT INTO corrections (id, pattern_text, created_at) VALUES (1, 'p1', ?)", (old_date,))
        self.db.execute("INSERT INTO corrections (id, pattern_text, created_at) VALUES (2, 'p2', ?)", (old_date,))
        self.db.execute("INSERT INTO corrections (id, pattern_text, created_at) VALUES (3, 'p3', ?)", (old_date,))
        
        # Mock scores: 1 and 3 are low (<20), 2 is high
        self.mock_scorer.score_all_patterns.return_value = {
            'total': 3,
            'scores': {1: 10.0, 2: 50.0, 3: 15.0}
        }
        
        # min_keep_count is 2. Total is 3. We can prune at most 1 pattern.
        # Candidates < 20 are [1, 3].
        # It should pick the lowest score (1) to stay within limits.
        
        candidates = self.pruner.identify_prune_candidates()
        
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]['id'], 1)
        self.assertEqual(candidates[0]['score'], 10.0)

    def test_safety_filter_recent(self):
        """Test that recent patterns are protected"""
        now = datetime.now()
        recent_date = (now - timedelta(days=10)).isoformat()
        old_date = (now - timedelta(days=60)).isoformat()
        
        # 1 is recent (low score), 2 is old (low score)
        self.db.execute("INSERT INTO corrections (id, pattern_text, created_at) VALUES (1, 'p1', ?)", (recent_date,))
        self.db.execute("INSERT INTO corrections (id, pattern_text, created_at) VALUES (2, 'p2', ?)", (old_date,))
        self.db.execute("INSERT INTO corrections (id, pattern_text, created_at) VALUES (3, 'p3', ?)", (old_date,))
        
        self.mock_scorer.score_all_patterns.return_value = {
            'total': 3,
            'scores': {1: 10.0, 2: 10.0, 3: 50.0}
        }
        
        # min_keep_count=2. Can prune 1.
        # Candidates: 1 and 2.
        # 1 is too recent (<30 days). Should be filtered out.
        # 2 is old enough.
        
        candidates = self.pruner.identify_prune_candidates()
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]['id'], 2)

    def test_safety_filter_favorites(self):
        """Test that favorited patterns are protected"""
        now = datetime.now()
        old_date = (now - timedelta(days=60)).isoformat()
        
        self.db.execute("INSERT INTO corrections (id, pattern_text, created_at) VALUES (1, 'p1', ?)", (old_date,))
        self.db.execute("INSERT INTO favorites (pattern_id) VALUES (1)")
        
        self.mock_scorer.score_all_patterns.return_value = {
            'total': 1,
            'scores': {1: 10.0}
        }
        
        candidates = self.pruner.identify_prune_candidates()
        self.assertEqual(len(candidates), 0)

    def test_prune_patterns_real(self):
        """Test actual pruning (backup + delete)"""
        now = datetime.now()
        old_date = (now - timedelta(days=60)).isoformat()
        
        self.db.execute("INSERT INTO corrections (id, pattern_text, correction_text, created_at) VALUES (1, 'p1', 'c1', ?)", (old_date,))
        self.db.execute("INSERT INTO corrections (id, pattern_text, correction_text, created_at) VALUES (2, 'p2', 'c2', ?)", (old_date,))
        self.db.execute("INSERT INTO corrections (id, pattern_text, correction_text, created_at) VALUES (3, 'p3', 'c3', ?)", (old_date,))
        
        # min_keep_count=2. Can prune 1.
        self.mock_scorer.score_all_patterns.return_value = {
            'total': 3,
            'scores': {1: 10.0, 2: 50.0, 3: 50.0}
        }
        
        result = self.pruner.prune_patterns(dry_run=False)
        
        self.assertEqual(result['action'], 'pruned')
        self.assertEqual(result['removed'], 1)
        self.assertEqual(result['pattern_ids'], [1])
        
        # Verify DB has 2 left
        count = self.db.execute("SELECT COUNT(*) FROM corrections").fetchone()[0]
        self.assertEqual(count, 2)
        
        # Verify backup exists
        backup = self.db.execute("SELECT * FROM pattern_backups WHERE original_id=1").fetchone()
        self.assertIsNotNone(backup)
        self.assertEqual(backup['pattern_text'], 'p1')

    def test_restore_pattern(self):
        """Test restoring a pattern from backup"""
        # Create a backup entry manually
        cursor = self.db.execute("""
            INSERT INTO pattern_backups (original_id, pattern_text, correction_text, created_at, use_count, success_count, failure_count, score, reason)
            VALUES (1, 'p1', 'c1', '2023-01-01', 5, 5, 0, 10.0, 'Low score')
        """)
        backup_id = cursor.lastrowid
        
        success = self.pruner.restore_pattern(backup_id)
        self.assertTrue(success)
        
        # Verify it's back in corrections
        restored = self.db.execute("SELECT * FROM corrections WHERE pattern_text='p1'").fetchone()
        self.assertIsNotNone(restored)
        self.assertEqual(restored['correction_text'], 'c1')

if __name__ == '__main__':
    unittest.main()