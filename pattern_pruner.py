"""
Pattern Pruner
Safely removes low-value patterns to prevent database bloat
Includes safety mechanisms and backup system
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class PatternPruner:
    """
    Safely prune low-value patterns from the database
    
    Safety mechanisms:
    - Never prune recent patterns (configurable threshold)
    - Never prune user-favorited patterns
    - Always backup before deletion
    - Dry-run mode for testing
    - Configurable minimum pattern count
    """
    
    def __init__(self, db_connection, scorer, 
                 min_score_threshold: float = 20.0,
                 min_keep_count: int = 50,
                 min_age_days: int = 30):
        """
        Initialize the pattern pruner
        
        Args:
            db_connection: SQLite database connection
            scorer: PatternScorer instance
            min_score_threshold: Minimum score to keep (default 20)
            min_keep_count: Always keep at least this many patterns
            min_age_days: Only prune patterns older than this
        """
        self.db = db_connection
        self.scorer = scorer
        self.min_score_threshold = min_score_threshold
        self.min_keep_count = min_keep_count
        self.min_age_days = min_age_days
        
        # Create backup table if it doesn't exist
        self._ensure_backup_table()
    
    def _ensure_backup_table(self):
        """Create backup table for deleted patterns"""
        
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS pattern_backups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_id INTEGER,
                pattern_text TEXT,
                correction_text TEXT,
                created_at TEXT,
                deleted_at TEXT DEFAULT CURRENT_TIMESTAMP,
                use_count INTEGER,
                success_count INTEGER,
                failure_count INTEGER,
                score REAL,
                reason TEXT
            )
        """)
        self.db.commit()
    
    def identify_prune_candidates(self) -> List[Dict]:
        """
        Identify patterns that are candidates for pruning
        
        Returns:
            List of {id, score, reason, ...}
        """
        
        # Get all pattern scores
        all_scores = self.scorer.score_all_patterns()
        
        if all_scores['total'] == 0:
            logger.info("No patterns to evaluate")
            return []
        
        # Find low-scoring patterns
        candidates = []
        for pattern_id, score in all_scores['scores'].items():
            if score < self.min_score_threshold:
                candidates.append({
                    'id': pattern_id,
                    'score': score,
                    'reason': f'Low score ({score:.2f} < {self.min_score_threshold})'
                })
        
        logger.info(f"Found {len(candidates)} low-scoring patterns")
        
        # Apply safety filters
        candidates = self._apply_safety_filters(candidates)
        
        logger.info(f"After safety filters: {len(candidates)} candidates remain")
        
        return candidates
    
    def _apply_safety_filters(self, candidates: List[Dict]) -> List[Dict]:
        """
        Apply safety filters to prune candidates
        
        Safety rules:
        1. Never prune favorited patterns
        2. Never prune recent patterns
        3. Keep minimum pattern count
        """
        
        filtered = []
        
        for candidate in candidates:
            pattern_id = candidate['id']
            
            # Filter 1: Check if favorited (if we have favorites table)
            try:
                favorited = self.db.execute("""
                    SELECT 1 FROM favorites WHERE pattern_id = ?
                """, (pattern_id,)).fetchone()
                
                if favorited:
                    logger.debug(f"Skipping pattern {pattern_id}: favorited")
                    continue
            except:
                # Favorites table doesn't exist, that's okay
                pass
            
            # Filter 2: Check age
            pattern = self.db.execute("""
                SELECT created_at FROM corrections WHERE id = ?
            """, (pattern_id,)).fetchone()
            
            if pattern:
                created = datetime.fromisoformat(pattern['created_at'])
                age_days = (datetime.now() - created).days
                
                if age_days < self.min_age_days:
                    logger.debug(f"Skipping pattern {pattern_id}: too recent ({age_days} days)")
                    continue
            
            filtered.append(candidate)
        
        # Filter 3: Ensure we keep minimum count
        total_patterns = self.db.execute("""
            SELECT COUNT(*) as count FROM corrections
        """).fetchone()['count']
        
        max_to_prune = total_patterns - self.min_keep_count
        
        if max_to_prune <= 0:
            logger.info(f"Cannot prune: only {total_patterns} patterns (minimum {self.min_keep_count})")
            return []
        
        # Limit to max_to_prune
        if len(filtered) > max_to_prune:
            # Sort by score ascending (lowest first)
            filtered.sort(key=lambda x: x['score'])
            filtered = filtered[:max_to_prune]
            logger.info(f"Limited to {max_to_prune} patterns to maintain minimum count")
        
        return filtered
    
    def prune_patterns(self, dry_run: bool = True) -> Dict:
        """
        Prune low-value patterns
        
        Args:
            dry_run: If True, only report what would be deleted
        
        Returns:
            {
                'action': 'dry_run' or 'pruned',
                'candidates': int,
                'removed': int,
                'pattern_ids': [list of IDs],
                'total_before': int,
                'total_after': int,
                'backed_up': int
            }
        """
        
        # Get total before
        total_before = self.db.execute("""
            SELECT COUNT(*) as count FROM corrections
        """).fetchone()['count']
        
        # Identify candidates
        candidates = self.identify_prune_candidates()
        
        if not candidates:
            return {
                'action': 'none',
                'candidates': 0,
                'removed': 0,
                'pattern_ids': [],
                'total_before': total_before,
                'total_after': total_before,
                'backed_up': 0,
                'message': 'No patterns to prune'
            }
        
        if dry_run:
            return {
                'action': 'dry_run',
                'candidates': len(candidates),
                'removed': 0,
                'pattern_ids': [c['id'] for c in candidates],
                'total_before': total_before,
                'total_after': total_before,
                'backed_up': 0,
                'message': f'Would prune {len(candidates)} patterns (dry run)'
            }
        
        # REAL PRUNING - Backup first
        backed_up = self._backup_patterns(candidates)
        
        # Delete patterns
        removed = 0
        pattern_ids = []
        
        for candidate in candidates:
            pattern_id = candidate['id']
            
            try:
                self.db.execute("""
                    DELETE FROM corrections WHERE id = ?
                """, (pattern_id,))
                
                removed += 1
                pattern_ids.append(pattern_id)
                
                logger.info(f"Pruned pattern {pattern_id} (score: {candidate['score']:.2f})")
                
            except Exception as e:
                logger.error(f"Failed to prune pattern {pattern_id}: {e}")
        
        self.db.commit()
        
        # Get total after
        total_after = self.db.execute("""
            SELECT COUNT(*) as count FROM corrections
        """).fetchone()['count']
        
        logger.info(f"Pruning complete: {removed} patterns removed, {backed_up} backed up")
        
        return {
            'action': 'pruned',
            'candidates': len(candidates),
            'removed': removed,
            'pattern_ids': pattern_ids,
            'total_before': total_before,
            'total_after': total_after,
            'backed_up': backed_up,
            'message': f'Pruned {removed} patterns successfully'
        }
    
    def _backup_patterns(self, candidates: List[Dict]) -> int:
        """
        Backup patterns before deletion
        
        Returns:
            Number of patterns backed up
        """
        
        backed_up = 0
        
        for candidate in candidates:
            pattern_id = candidate['id']
            
            # Get full pattern data
            pattern = self.db.execute("""
                SELECT * FROM corrections WHERE id = ?
            """, (pattern_id,)).fetchone()
            
            if not pattern:
                logger.warning(f"Pattern {pattern_id} not found for backup")
                continue
            
            try:
                # Insert into backup table
                self.db.execute("""
                    INSERT INTO pattern_backups (
                        original_id, pattern_text, correction_text,
                        created_at, use_count, success_count, failure_count,
                        score, reason
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    pattern_id,
                    pattern['pattern_text'],
                    pattern['correction_text'],
                    pattern['created_at'],
                    pattern['use_count'],
                    pattern['success_count'],
                    pattern['failure_count'],
                    candidate['score'],
                    candidate['reason']
                ))
                
                backed_up += 1
                
            except Exception as e:
                logger.error(f"Failed to backup pattern {pattern_id}: {e}")
        
        self.db.commit()
        
        logger.info(f"Backed up {backed_up} patterns")
        
        return backed_up
    
    def restore_pattern(self, backup_id: int) -> bool:
        """
        Restore a pattern from backup
        
        Args:
            backup_id: ID from pattern_backups table
        
        Returns:
            True if restored successfully
        """
        
        # Get backup
        backup = self.db.execute("""
            SELECT * FROM pattern_backups WHERE id = ?
        """, (backup_id,)).fetchone()
        
        if not backup:
            logger.error(f"Backup {backup_id} not found")
            return False
        
        try:
            # Restore to corrections table
            self.db.execute("""
                INSERT INTO corrections (
                    pattern_text, correction_text, created_at,
                    use_count, success_count, failure_count
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                backup['pattern_text'],
                backup['correction_text'],
                backup['created_at'],
                backup['use_count'],
                backup['success_count'],
                backup['failure_count']
            ))
            
            self.db.commit()
            
            logger.info(f"Restored pattern from backup {backup_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore backup {backup_id}: {e}")
            return False
    
    def get_backup_stats(self) -> Dict:
        """
        Get statistics on backups
        
        Returns:
            {
                'total_backups': int,
                'backup_size_mb': float,
                'oldest_backup': str,
                'newest_backup': str
            }
        """
        
        try:
            stats = self.db.execute("""
                SELECT 
                    COUNT(*) as total,
                    MIN(deleted_at) as oldest,
                    MAX(deleted_at) as newest
                FROM pattern_backups
            """).fetchone()
            
            return {
                'total_backups': stats['total'],
                'oldest_backup': stats['oldest'],
                'newest_backup': stats['newest']
            }
            
        except:
            return {
                'total_backups': 0,
                'oldest_backup': None,
                'newest_backup': None
            }
    
    def list_backups(self, limit: int = 10) -> List[Dict]:
        """
        List recent backups
        
        Returns:
            List of backup info
        """
        
        try:
            backups = self.db.execute("""
                SELECT 
                    id, original_id, pattern_text, score, 
                    reason, deleted_at
                FROM pattern_backups
                ORDER BY deleted_at DESC
                LIMIT ?
            """, (limit,)).fetchall()
            
            return [
                {
                    'id': b['id'],
                    'original_id': b['original_id'],
                    'pattern_text': b['pattern_text'][:50] + '...',
                    'score': b['score'],
                    'reason': b['reason'],
                    'deleted_at': b['deleted_at']
                }
                for b in backups
            ]
            
        except:
            return []