import sqlite3
from datetime import datetime, timedelta
from core.buddai_shared import DB_PATH

class LearningMetrics:
    """Measure BuddAI's improvement over time"""
    
    def calculate_accuracy(self):
        """What % of code is accepted without correction?"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_responses,
                COUNT(CASE WHEN f.positive = 1 THEN 1 END) as positive_feedback,
                COUNT(CASE WHEN c.id IS NOT NULL THEN 1 END) as corrected
            FROM messages m
            LEFT JOIN feedback f ON m.id = f.message_id
            LEFT JOIN corrections c ON m.content LIKE '%' || c.original_code || '%'
            WHERE m.role = 'assistant'
            AND m.timestamp > ?
        """, (thirty_days_ago,))
        
        total, positive, corrected = cursor.fetchone()
        conn.close()
        
        accuracy = (positive / total) * 100 if total and total > 0 else 0
        correction_rate = (corrected / total) * 100 if total and total > 0 else 0
        
        return {
            "accuracy": accuracy,
            "correction_rate": correction_rate,
            "improvement": self.calculate_trend()
        }
    
    def calculate_trend(self):
        """Is BuddAI getting better over time?"""
        # Compare last 7 days vs previous 7 days
        recent = self.get_accuracy_for_period(7)
        previous = self.get_accuracy_for_period(7, offset=7)
        
        improvement = recent - previous
        return f"+{improvement:.1f}%" if improvement > 0 else f"{improvement:.1f}%"

    def get_accuracy_for_period(self, days: int, offset: int = 0) -> float:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        start_dt = (datetime.now() - timedelta(days=days + offset)).isoformat()
        end_dt = (datetime.now() - timedelta(days=offset)).isoformat()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN f.positive = 1 THEN 1 END) as positive
            FROM messages m
            LEFT JOIN feedback f ON m.id = f.message_id
            WHERE m.role = 'assistant'
            AND m.timestamp BETWEEN ? AND ?
        """, (start_dt, end_dt))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return 0.0
            
        total, positive = row
        return (positive / total) * 100 if total and total > 0 else 0.0