"""
Pattern Merger
Combines similar patterns to reduce duplication and improve database efficiency
Uses multiple similarity algorithms for accurate matching
"""

import logging
from datetime import datetime
from typing import List, Dict, Set, Tuple, Optional

logger = logging.getLogger(__name__)

class PatternMerger:
    """
    Merge similar patterns to reduce duplication
    
    Benefits:
    - Reduces database size
    - Improves query performance
    - Consolidates knowledge
    - Eliminates redundancy
    """
    
    def __init__(self, db_connection, similarity_threshold: float = 0.85):
        """
        Initialize the pattern merger
        
        Args:
            db_connection: SQLite database connection
            similarity_threshold: Minimum similarity to merge (0-1)
        """
        self.db = db_connection
        self.similarity_threshold = similarity_threshold
        
        # Create merge history table
        self._ensure_merge_history_table()
    
    def _ensure_merge_history_table(self):
        """Create table to track merge history"""
        
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS merge_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                merged_at TEXT DEFAULT CURRENT_TIMESTAMP,
                primary_pattern_id INTEGER,
                merged_pattern_ids TEXT,
                similarity_score REAL,
                patterns_merged INTEGER,
                total_uses_before INTEGER,
                total_uses_after INTEGER
            )
        """)
        self.db.commit()
    
    def find_similar_patterns(self) -> List[List[int]]:
        """
        Find groups of similar patterns
        
        Returns:
            List of pattern ID groups that should be merged
            e.g., [[1, 5, 12], [3, 8], [15, 20, 25]]
        """
        
        # Get all patterns
        patterns = self.db.execute("""
            SELECT id, pattern_text, correction_text
            FROM corrections
            ORDER BY id
        """).fetchall()
        
        if len(patterns) < 2:
            logger.info("Not enough patterns to merge")
            return []
        
        similar_groups = []
        processed = set()
        
        for i, p1 in enumerate(patterns):
            if p1['id'] in processed:
                continue
            
            group = [p1['id']]
            
            for p2 in patterns[i+1:]:
                if p2['id'] in processed:
                    continue
                
                # Calculate similarity
                similarity = self._calculate_pattern_similarity(p1, p2)
                
                if similarity >= self.similarity_threshold:
                    group.append(p2['id'])
                    processed.add(p2['id'])
                    
                    logger.debug(f"Patterns {p1['id']} and {p2['id']} are similar ({similarity:.2f})")
            
            # Only add groups with 2+ patterns
            if len(group) > 1:
                similar_groups.append(group)
                processed.update(group)
        
        logger.info(f"Found {len(similar_groups)} groups of similar patterns")
        
        return similar_groups
    
    def _calculate_pattern_similarity(self, p1: dict, p2: dict) -> float:
        """
        Calculate similarity between two patterns
        
        Uses combination of:
        - Jaccard similarity (word overlap)
        - Levenshtein distance (character edits)
        - Correction similarity
        
        Returns:
            Similarity score (0-1)
        """
        
        # Jaccard similarity on pattern text
        jaccard_pattern = self._jaccard_similarity(
            p1['pattern_text'],
            p2['pattern_text']
        )
        
        # Jaccard similarity on correction text
        jaccard_correction = self._jaccard_similarity(
            p1['correction_text'],
            p2['correction_text']
        )
        
        # Levenshtein similarity on pattern text
        levenshtein_pattern = self._levenshtein_similarity(
            p1['pattern_text'],
            p2['pattern_text']
        )
        
        # Weighted combination
        # Pattern text is most important, correction is secondary
        similarity = (
            jaccard_pattern * 0.5 +
            levenshtein_pattern * 0.3 +
            jaccard_correction * 0.2
        )
        
        return similarity
    
    def _jaccard_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate Jaccard similarity (word overlap)
        
        Formula: |A ∩ B| / |A ∪ B|
        """
        
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 and not words2:
            return 1.0  # Both empty
        
        if not words1 or not words2:
            return 0.0  # One empty
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union)
    
    def _levenshtein_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate Levenshtein similarity (character edits)
        
        Returns normalized similarity (0-1)
        """
        
        distance = self._levenshtein_distance(text1, text2)
        max_len = max(len(text1), len(text2))
        
        if max_len == 0:
            return 1.0
        
        similarity = 1 - (distance / max_len)
        return max(0.0, similarity)
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """
        Calculate Levenshtein distance (minimum edits to transform s1 to s2)
        
        Dynamic programming implementation
        """
        
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            
            for j, c2 in enumerate(s2):
                # Cost of insertions, deletions, substitutions
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                
                current_row.append(min(insertions, deletions, substitutions))
            
            previous_row = current_row
        
        return previous_row[-1]
    
    def merge_pattern_group(self, pattern_ids: List[int]) -> Optional[int]:
        """
        Merge a group of patterns into one
        
        Strategy:
        - Use the most-used pattern as the primary
        - Combine all usage statistics
        - Delete the others
        - Log to merge history
        
        Args:
            pattern_ids: List of pattern IDs to merge
        
        Returns:
            ID of the primary (merged) pattern, or None if failed
        """
        
        if len(pattern_ids) < 2:
            logger.warning("Need at least 2 patterns to merge")
            return None
        
        # Fetch all patterns
        patterns = []
        for pid in pattern_ids:
            pattern = self.db.execute("""
                SELECT * FROM corrections WHERE id = ?
            """, (pid,)).fetchone()
            
            if pattern:
                patterns.append(pattern)
        
        if len(patterns) < 2:
            logger.warning("Couldn't fetch all patterns for merge")
            return None
        
        # Find primary pattern (most uses)
        primary = max(patterns, key=lambda p: p['use_count'])
        primary_id = primary['id']
        
        # Calculate combined statistics
        total_uses = sum(p['use_count'] for p in patterns)
        total_success = sum(p['success_count'] for p in patterns)
        total_failure = sum(p['failure_count'] for p in patterns)
        
        # Find most recent last_used
        last_used_dates = [p['last_used'] for p in patterns if p['last_used']]
        most_recent = max(last_used_dates) if last_used_dates else primary['last_used']
        
        # Update primary pattern with combined stats
        try:
            self.db.execute("""
                UPDATE corrections
                SET use_count = ?,
                    success_count = ?,
                    failure_count = ?,
                    last_used = ?
                WHERE id = ?
            """, (total_uses, total_success, total_failure, most_recent, primary_id))
            
            # Delete other patterns
            other_ids = [p['id'] for p in patterns if p['id'] != primary_id]
            
            for pid in other_ids:
                self.db.execute("""
                    DELETE FROM corrections WHERE id = ?
                """, (pid,))
            
            # Log to merge history
            self.db.execute("""
                INSERT INTO merge_history (
                    primary_pattern_id, merged_pattern_ids,
                    patterns_merged, total_uses_before, total_uses_after
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                primary_id,
                ','.join(map(str, other_ids)),
                len(patterns),
                sum(p['use_count'] for p in patterns),
                total_uses
            ))
            
            self.db.commit()
            
            logger.info(f"Merged {len(patterns)} patterns into pattern {primary_id}")
            
            return primary_id
            
        except Exception as e:
            logger.error(f"Failed to merge patterns: {e}")
            self.db.rollback()
            return None
    
    def merge_all_similar(self, dry_run: bool = True) -> Dict:
        """
        Find and merge all similar patterns
        
        Args:
            dry_run: If True, only report what would be merged
        
        Returns:
            {
                'action': 'dry_run' or 'merged',
                'groups_found': int,
                'groups_merged': int,
                'patterns_before': int,
                'patterns_after': int,
                'space_saved': int
            }
        """
        
        # Count patterns before
        patterns_before = self.db.execute("""
            SELECT COUNT(*) as count FROM corrections
        """).fetchone()['count']
        
        # Find similar groups
        similar_groups = self.find_similar_patterns()
        
        if not similar_groups:
            return {
                'action': 'none',
                'groups_found': 0,
                'groups_merged': 0,
                'patterns_before': patterns_before,
                'patterns_after': patterns_before,
                'space_saved': 0,
                'message': 'No similar patterns found'
            }
        
        if dry_run:
            patterns_to_remove = sum(len(group) - 1 for group in similar_groups)
            
            return {
                'action': 'dry_run',
                'groups_found': len(similar_groups),
                'groups_merged': 0,
                'patterns_before': patterns_before,
                'patterns_after': patterns_before - patterns_to_remove,
                'space_saved': patterns_to_remove,
                'message': f'Would merge {len(similar_groups)} groups (dry run)'
            }
        
        # REAL MERGING
        merged_count = 0
        
        for group in similar_groups:
            result = self.merge_pattern_group(group)
            
            if result:
                merged_count += 1
        
        # Count patterns after
        patterns_after = self.db.execute("""
            SELECT COUNT(*) as count FROM corrections
        """).fetchone()['count']
        
        space_saved = patterns_before - patterns_after
        
        logger.info(f"Merged {merged_count} groups, saved {space_saved} patterns")
        
        return {
            'action': 'merged',
            'groups_found': len(similar_groups),
            'groups_merged': merged_count,
            'patterns_before': patterns_before,
            'patterns_after': patterns_after,
            'space_saved': space_saved,
            'message': f'Merged {merged_count} groups successfully'
        }
    
    def get_merge_history(self, limit: int = 10) -> List[Dict]:
        """
        Get recent merge history
        
        Returns:
            List of merge records
        """
        
        try:
            history = self.db.execute("""
                SELECT * FROM merge_history
                ORDER BY merged_at DESC
                LIMIT ?
            """, (limit,)).fetchall()
            
            return [
                {
                    'id': h['id'],
                    'merged_at': h['merged_at'],
                    'primary_id': h['primary_pattern_id'],
                    'merged_ids': h['merged_pattern_ids'],
                    'patterns_merged': h['patterns_merged'],
                    'total_uses_before': h['total_uses_before'],
                    'total_uses_after': h['total_uses_after']
                }
                for h in history
            ]
            
        except:
            return []
    
    def get_merge_stats(self) -> Dict:
        """
        Get overall merge statistics
        
        Returns:
            {
                'total_merges': int,
                'total_patterns_merged': int,
                'total_space_saved': int
            }
        """
        
        try:
            stats = self.db.execute("""
                SELECT 
                    COUNT(*) as total_merges,
                    SUM(patterns_merged) as total_patterns,
                    SUM(patterns_merged - 1) as space_saved
                FROM merge_history
            """).fetchone()
            
            return {
                'total_merges': stats['total_merges'] or 0,
                'total_patterns_merged': stats['total_patterns'] or 0,
                'total_space_saved': stats['space_saved'] or 0
            }
            
        except:
            return {
                'total_merges': 0,
                'total_patterns_merged': 0,
                'total_space_saved': 0
            }