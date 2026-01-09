"""
Live test with your actual 244 patterns
"""

import sys
import os
import sqlite3

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Connect to real database
from pattern_scorer import PatternScorer
from core.buddai_shared import DB_PATH

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

if __name__ == "__main__":
    db = get_db_connection()

    # Create scorer
    scorer = PatternScorer(db)

    # Score all 244 patterns
    print("Scoring all patterns...")
    results = scorer.score_all_patterns()

    print(f"\n📊 Pattern Score Report")
    print(f"=" * 50)
    print(f"Total Patterns: {results['total']}")
    print(f"Average Score: {results['average']:.2f}")
    print(f"High Value (>70): {results['high_value']}")
    print(f"Medium Value (50-70): {results['medium_value']}")
    print(f"Low Value (<50): {results['low_value']}")

    # Show distribution
    print(f"\n📈 Score Distribution:")
    dist = scorer.get_score_distribution()
    for bucket, count in dist.items():
        bar = '█' * (count // 5)
        print(f"  {bucket:>7}: {bar} {count}")

    # Show all patterns details
    print(f"\n📋 Complete Pattern List (Sorted by Score):")
    all_patterns = scorer.get_top_patterns(results['total'])
    for i, pattern in enumerate(all_patterns, 1):
        print(f"{i}. Score: {pattern['score']:.2f} | Uses: {pattern['use_count']} | {pattern['pattern_text']}")