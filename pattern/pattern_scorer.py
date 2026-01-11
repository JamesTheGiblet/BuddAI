"""
Pattern Relevance Scorer
Scores patterns based on age, usage, success rate, and recency
Uses exponential decay for time-based degradation
"""

import math
import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class PatternScorer:
    """
    Calculates relevance scores for patterns using multi-factor analysis
    """
    
    def __init__(self, db_connection, decay_days: int = 30):
        """
        Initialize the pattern scorer
        
        Args:
            db_connection: SQLite database connection
            decay_days: Number of days for exponential decay half-life
        """
        self.db = db_connection
        self.decay_constant = decay_days
        
        # Scoring weights (must sum to 100)
        self.weights = {
            'age': 30,        # How old is the pattern
            'usage': 25,      # How often used
            'success': 25,    # Success rate
            'recency': 20     # When last used
        }
    
    def score_pattern(self, pattern_id: int) -> Optional[float]:
        """
        Calculate relevance score for a single pattern
        
        Returns:
            Score from 0-100, or None if pattern not found
        """
        
        # Fetch pattern data
        pattern = self.db.execute("""
            SELECT 
                id,
                pattern_text,
                created_at,
                last_used,
                use_count,
                success_count,
                failure_count
            FROM corrections
            WHERE id = ?
        """, (pattern_id,)).fetchone()
        
        if not pattern:
            logger.warning(f"Pattern {pattern_id} not found")
            return None
        
        # Calculate each factor
        age_score = self._calculate_age_score(pattern)
        usage_score = self._calculate_usage_score(pattern)
        success_score = self._calculate_success_score(pattern)
        recency_score = self._calculate_recency_score(pattern)
        
        # Weighted combination
        total_score = (
            age_score * self.weights['age'] +
            usage_score * self.weights['usage'] +
            success_score * self.weights['success'] +
            recency_score * self.weights['recency']
        ) / 100.0
        
        # Log scoring breakdown
        logger.debug(f"Pattern {pattern_id} scoring: "
                    f"age={age_score:.2f}, usage={usage_score:.2f}, "
                    f"success={success_score:.2f}, recency={recency_score:.2f}, "
                    f"total={total_score:.2f}")
        
        return total_score
    
    def _calculate_age_score(self, pattern: dict) -> float:
        """
        Calculate age factor using exponential decay
        Newer patterns score higher
        
        Formula: score = 100 * e^(-days_old / decay_constant)
        """
        created = datetime.fromisoformat(pattern['created_at'])
        days_old = (datetime.now() - created).days
        
        # Exponential decay
        decay_factor = math.exp(-days_old / self.decay_constant)
        score = 100.0 * decay_factor
        
        return score
    
    def _calculate_usage_score(self, pattern: dict) -> float:
        """
        Calculate usage frequency score
        More usage = higher score, but with diminishing returns
        
        Formula: score = 100 * (1 - e^(-use_count / 10))
        """
        use_count = pattern['use_count'] or 0
        
        # Diminishing returns curve
        # 1 use = 9.5%, 5 uses = 39%, 10 uses = 63%, 20 uses = 86%
        score = 100.0 * (1 - math.exp(-use_count / 10.0))
        
        return score
    
    def _calculate_success_score(self, pattern: dict) -> float:
        """
        Calculate success rate score
        Higher success rate = higher score
        
        Formula: score = 100 * (success_count / total_uses)
        """
        success_count = pattern['success_count'] or 0
        failure_count = pattern['failure_count'] or 0
        total = success_count + failure_count
        
        if total == 0:
            # No data yet, assume 50% (neutral)
            return 50.0
        
        success_rate = success_count / total
        score = 100.0 * success_rate
        
        return score
    
    def _calculate_recency_score(self, pattern: dict) -> float:
        """
        Calculate recency score (how recently used)
        Recently used = higher score
        
        Formula: score = 100 * e^(-days_since_use / 7)
        """
        last_used = pattern['last_used']
        
        if not last_used:
            # Never used, score = 0
            return 0.0
        
        last_used_dt = datetime.fromisoformat(last_used)
        days_since_use = (datetime.now() - last_used_dt).days
        
        # Exponential decay (7 day half-life)
        decay_factor = math.exp(-days_since_use / 7.0)
        score = 100.0 * decay_factor
        
        return score
    
    def score_all_patterns(self) -> Dict[str, any]:
        """
        Score all patterns and return statistics
        
        Returns:
            {
                'total': int,
                'average': float,
                'high_value': int (score > 70),
                'medium_value': int (50 < score <= 70),
                'low_value': int (score <= 50),
                'scores': {pattern_id: score, ...}
            }
        """
        
        # Get all pattern IDs
        patterns = self.db.execute("""
            SELECT id FROM corrections
        """).fetchall()
        
        if not patterns:
            return {
                'total': 0,
                'average': 0.0,
                'high_value': 0,
                'medium_value': 0,
                'low_value': 0,
                'scores': {}
            }
        
        # Score each pattern
        scores = {}
        for pattern in patterns:
            pattern_id = pattern['id']
            score = self.score_pattern(pattern_id)
            if score is not None:
                scores[pattern_id] = score
        
        # Calculate statistics
        score_values = list(scores.values())
        average = sum(score_values) / len(score_values) if score_values else 0.0
        
        high_value = sum(1 for s in score_values if s > 70)
        medium_value = sum(1 for s in score_values if 50 < s <= 70)
        low_value = sum(1 for s in score_values if s <= 50)
        
        logger.info(f"Scored {len(scores)} patterns: "
                   f"avg={average:.2f}, "
                   f"high={high_value}, med={medium_value}, low={low_value}")
        
        return {
            'total': len(scores),
            'average': average,
            'high_value': high_value,
            'medium_value': medium_value,
            'low_value': low_value,
            'scores': scores
        }
    
    def get_top_patterns(self, limit: int = 10) -> List[Dict]:
        """
        Get top N patterns by score
        
        Returns:
            List of {id, score, pattern_text, ...}
        """
        all_scores = self.score_all_patterns()
        
        # Sort by score descending
        sorted_patterns = sorted(
            all_scores['scores'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]
        
        # Fetch full pattern data
        results = []
        for pattern_id, score in sorted_patterns:
            pattern = self.db.execute("""
                SELECT * FROM corrections WHERE id = ?
            """, (pattern_id,)).fetchone()
            
            if pattern:
                results.append({
                    'id': pattern_id,
                    'score': score,
                    'pattern_text': pattern['correction_text'],
                    'use_count': pattern['use_count'],
                    'created_at': pattern['created_at']
                })
        
        return results
    
    def get_bottom_patterns(self, limit: int = 10) -> List[Dict]:
        """
        Get bottom N patterns by score (candidates for pruning)
        
        Returns:
            List of {id, score, pattern_text, ...}
        """
        all_scores = self.score_all_patterns()
        
        # Sort by score ascending
        sorted_patterns = sorted(
            all_scores['scores'].items(),
            key=lambda x: x[1]
        )[:limit]
        
        # Fetch full pattern data
        results = []
        for pattern_id, score in sorted_patterns:
            pattern = self.db.execute("""
                SELECT * FROM corrections WHERE id = ?
            """, (pattern_id,)).fetchone()
            
            if pattern:
                results.append({
                    'id': pattern_id,
                    'score': score,
                    'pattern_text': pattern['correction_text'],
                    'use_count': pattern['use_count'],
                    'created_at': pattern['created_at']
                })
        
        return results
    
    def update_decay_constant(self, new_decay_days: int):
        """
        Update the decay constant (for tuning)
        
        Args:
            new_decay_days: New half-life in days
        """
        old_constant = self.decay_constant
        self.decay_constant = new_decay_days
        
        logger.info(f"Updated decay constant: {old_constant} -> {new_decay_days} days")
    
    def get_score_distribution(self) -> Dict[str, int]:
        """
        Get distribution of scores in buckets
        
        Returns:
            {
                '0-20': count,
                '20-40': count,
                '40-60': count,
                '60-80': count,
                '80-100': count
            }
        """
        all_scores = self.score_all_patterns()
        
        buckets = {
            '0-20': 0,
            '20-40': 0,
            '40-60': 0,
            '60-80': 0,
            '80-100': 0
        }
        
        for score in all_scores['scores'].values():
            if score <= 20:
                buckets['0-20'] += 1
            elif score <= 40:
                buckets['20-40'] += 1
            elif score <= 60:
                buckets['40-60'] += 1
            elif score <= 80:
                buckets['60-80'] += 1
            else:
                buckets['80-100'] += 1
        
        return buckets