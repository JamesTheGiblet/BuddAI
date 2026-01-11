"""
Tests for Pattern Merger
"""

import unittest
import sqlite3
from datetime import datetime, timedelta
try:
    from pattern.pattern_merger import PatternMerger
except ImportError:
    from pattern_merger import PatternMerger

class TestPatternMerger(unittest.TestCase):
    
    def setUp(self):
        """Create test database with similar patterns"""
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
        
        now = datetime.now().isoformat()
        
        # Similar patterns (should merge)
        self.db.execute("""
            INSERT INTO corrections 
            VALUES (1, 'fix motor control issue', 'use PWM smoothing', ?, ?, 10, 9, 1)
        """, (now, now))
        
        self.db.execute("""
            INSERT INTO corrections 
            VALUES (2, 'fix motor control problem', 'use PWM smoothing', ?, ?, 5, 4, 1)
        """, (now, now))
        
        self.db.execute("""
            INSERT INTO corrections 
            VALUES (3, 'fix motor issue', 'use PWM smoothing', ?, ?, 3, 3, 0)
        """, (now, now))
        
        # Different pattern (should not merge)
        self.db.execute("""
            INSERT INTO corrections 
            VALUES (4, 'servo jitter problem', 'add capacitor', ?, ?, 8, 7, 1)
        """, (now, now))
        
        self.db.commit()
        
        self.merger = PatternMerger(self.db, similarity_threshold=0.7)
    
    def tearDown(self):
        """Clean up"""
        self.db.close()
    
    def test_find_similar_patterns(self):
        """Test finding similar pattern groups"""
        groups = self.merger.find_similar_patterns()
        
        # Should find at least one group (the 3 motor patterns)
        self.assertGreater(len(groups), 0)
        
        # At least one group should have 2+ patterns
        self.assertTrue(any(len(g) >= 2 for g in groups))
    
    def test_jaccard_similarity(self):
        """Test Jaccard similarity calculation"""
        # Identical strings
        sim1 = self.merger._jaccard_similarity("hello world", "hello world")
        self.assertEqual(sim1, 1.0)
        
        # Completely different
        sim2 = self.merger._jaccard_similarity("abc", "xyz")
        self.assertEqual(sim2, 0.0)
        
        # Partial overlap
        sim3 = self.merger._jaccard_similarity("hello world", "hello there")
        self.assertGreater(sim3, 0.0)
        self.assertLess(sim3, 1.0)
    
    def test_levenshtein_distance(self):
        """Test Levenshtein distance calculation"""
        # Identical strings
        dist1 = self.merger._levenshtein_distance("test", "test")
        self.assertEqual(dist1, 0)
        
        # One insertion
        dist2 = self.merger._levenshtein_distance("test", "tests")
        self.assertEqual(dist2, 1)
        
        # One substitution
        dist3 = self.merger._levenshtein_distance("test", "text")
        self.assertEqual(dist3, 1)
    
    def test_levenshtein_similarity(self):
        """Test Levenshtein similarity"""
        # Identical
        sim1 = self.merger._levenshtein_similarity("test", "test")
        self.assertEqual(sim1, 1.0)
        
        # Very different
        sim2 = self.merger._levenshtein_similarity("abc", "xyz")
        self.assertLess(sim2, 0.5)
    
    def test_merge_pattern_group(self):
        """Test merging a group of patterns"""
        # Merge patterns 1, 2, 3
        result = self.merger.merge_pattern_group([1, 2, 3])
        
        self.assertIsNotNone(result)
        
        # Check that only one pattern remains
        remaining = self.db.execute("""
            SELECT COUNT(*) as c FROM corrections
            WHERE id IN (1, 2, 3)
        """).fetchone()['c']
        
        self.assertEqual(remaining, 1)
        
        # Check that statistics were combined
        primary = self.db.execute("""
            SELECT * FROM corrections WHERE id = ?
        """, (result,)).fetchone()
        
        # Total uses should be 10 + 5 + 3 = 18
        self.assertEqual(primary['use_count'], 18)
    
    def test_dry_run_merge(self):
        """Test dry run doesn't actually merge"""
        result = self.merger.merge_all_similar(dry_run=True)
        
        self.assertEqual(result['action'], 'dry_run')
        self.assertEqual(result['groups_merged'], 0)
        
        # Verify all patterns still exist
        count = self.db.execute("SELECT COUNT(*) as c FROM corrections").fetchone()['c']
        self.assertEqual(count, 4)
    
    def test_real_merge_all(self):
        """Test real merging of all similar patterns"""
        result = self.merger.merge_all_similar(dry_run=False)
        
        self.assertEqual(result['action'], 'merged')
        self.assertGreater(result['groups_merged'], 0)
        self.assertGreater(result['space_saved'], 0)
        self.assertLess(result['patterns_after'], result['patterns_before'])
    
    def test_merge_history_created(self):
        """Test that merge history is recorded"""
        self.merger.merge_all_similar(dry_run=False)
        
        history = self.merger.get_merge_history(limit=10)
        
        self.assertGreater(len(history), 0)
        self.assertIn('primary_id', history[0])
        self.assertIn('merged_ids', history[0])
    
    def test_merge_stats(self):
        """Test merge statistics"""
        self.merger.merge_all_similar(dry_run=False)
        
        stats = self.merger.get_merge_stats()
        
        self.assertIn('total_merges', stats)
        self.assertGreater(stats['total_merges'], 0)
    
    def test_no_similar_patterns(self):
        """Test behavior when no similar patterns exist"""
        # Clear database
        self.db.execute("DELETE FROM corrections")
        
        # Add only one pattern
        self.db.execute("""
            INSERT INTO corrections 
            VALUES (1, 'unique pattern', 'unique fix', ?, ?, 1, 1, 0)
        """, (datetime.now().isoformat(), datetime.now().isoformat()))
        self.db.commit()
        
        result = self.merger.merge_all_similar(dry_run=False)
        
        self.assertEqual(result['action'], 'none')
        self.assertEqual(result['groups_found'], 0)

if __name__ == '__main__':
    unittest.main()