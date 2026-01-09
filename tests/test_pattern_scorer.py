"""
Tests for Pattern Scorer
"""

import unittest
import sqlite3
from datetime import datetime, timedelta
from pattern_scorer import PatternScorer

class TestPatternScorer(unittest.TestCase):
    
    def setUp(self):
        """Create test database with sample patterns"""
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
        
        # Insert test patterns
        now = datetime.now().isoformat()
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        month_ago = (datetime.now() - timedelta(days=30)).isoformat()
        year_ago = (datetime.now() - timedelta(days=365)).isoformat()
        
        self.db.execute("""
            INSERT INTO corrections (pattern_text, correction_text, created_at, last_used, use_count, success_count, failure_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ('test1', 'fix1', now, now, 10, 9, 1))  # Recent, high usage, high success
        
        self.db.execute("""
            INSERT INTO corrections (pattern_text, correction_text, created_at, last_used, use_count, success_count, failure_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ('test2', 'fix2', month_ago, week_ago, 5, 4, 1))  # Medium age, medium usage
        
        self.db.execute("""
            INSERT INTO corrections (pattern_text, correction_text, created_at, last_used, use_count, success_count, failure_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ('test3', 'fix3', year_ago, year_ago, 1, 0, 1))  # Old, low usage, failed
        
        self.db.commit()
        
        self.scorer = PatternScorer(self.db)
    
    def tearDown(self):
        """Clean up"""
        self.db.close()
    
    def test_score_pattern_exists(self):
        """Test scoring an existing pattern"""
        score = self.scorer.score_pattern(1)
        self.assertIsNotNone(score)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)
    
    def test_score_pattern_not_found(self):
        """Test scoring non-existent pattern"""
        score = self.scorer.score_pattern(999)
        self.assertIsNone(score)
    
    def test_recent_pattern_scores_higher(self):
        """Test that recent patterns score higher than old ones"""
        score1 = self.scorer.score_pattern(1)  # Recent
        score3 = self.scorer.score_pattern(3)  # Old
        
        self.assertGreater(score1, score3)
    
    def test_high_usage_scores_higher(self):
        """Test that frequently used patterns score higher"""
        score1 = self.scorer.score_pattern(1)  # 10 uses
        score3 = self.scorer.score_pattern(3)  # 1 use
        
        self.assertGreater(score1, score3)
    
    def test_score_all_patterns(self):
        """Test scoring all patterns"""
        results = self.scorer.score_all_patterns()
        
        self.assertEqual(results['total'], 3)
        self.assertGreater(results['average'], 0)
        self.assertIn('scores', results)
        self.assertEqual(len(results['scores']), 3)
    
    def test_get_top_patterns(self):
        """Test getting highest scored patterns"""
        top = self.scorer.get_top_patterns(limit=2)
        
        self.assertEqual(len(top), 2)
        self.assertGreater(top[0]['score'], top[1]['score'])
    
    def test_get_bottom_patterns(self):
        """Test getting lowest scored patterns"""
        bottom = self.scorer.get_bottom_patterns(limit=2)
        
        self.assertEqual(len(bottom), 2)
        self.assertLess(bottom[0]['score'], bottom[1]['score'])
    
    def test_score_distribution(self):
        """Test score distribution calculation"""
        dist = self.scorer.get_score_distribution()
        
        self.assertIn('0-20', dist)
        self.assertIn('20-40', dist)
        self.assertIn('40-60', dist)
        self.assertIn('60-80', dist)
        self.assertIn('80-100', dist)
        
        total = sum(dist.values())
        self.assertEqual(total, 3)
    
    def test_update_decay_constant(self):
        """Test updating decay constant"""
        old_constant = self.scorer.decay_constant
        self.scorer.update_decay_constant(60)
        
        self.assertEqual(self.scorer.decay_constant, 60)
        self.assertNotEqual(self.scorer.decay_constant, old_constant)
    
    def test_age_score_decreases_with_time(self):
        """Test that age score uses exponential decay"""
        # Pattern 1 (recent) should have higher age score than pattern 3 (old)
        pattern1 = self.db.execute("SELECT * FROM corrections WHERE id = 1").fetchone()
        pattern3 = self.db.execute("SELECT * FROM corrections WHERE id = 3").fetchone()
        
        age_score1 = self.scorer._calculate_age_score(pattern1)
        age_score3 = self.scorer._calculate_age_score(pattern3)
        
        self.assertGreater(age_score1, age_score3)
        self.assertLess(age_score3, 20)  # Year old pattern should score very low

if __name__ == '__main__':
    unittest.main()