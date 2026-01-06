import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from core.buddai_shared import DB_PATH, DATA_DIR

class StorageManager:
    """Manages Database, Sessions, and Backups"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.current_session_id = None
        self.ensure_data_dir()
        self.init_database()
        self.start_new_session()

    def ensure_data_dir(self) -> None:
        DATA_DIR.mkdir(exist_ok=True)
        
    def init_database(self) -> None:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Core Tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT,
                started_at TIMESTAMP,
                ended_at TIMESTAMP,
                title TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                role TEXT,
                content TEXT,
                timestamp TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS repo_index (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                file_path TEXT,
                repo_name TEXT,
                function_name TEXT,
                content TEXT,
                last_modified TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS style_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                category TEXT,
                preference TEXT,
                confidence FLOAT,
                extracted_at TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER,
                positive BOOLEAN,
                comment TEXT,
                timestamp TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS corrections (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                original_code TEXT,
                corrected_code TEXT,
                reason TEXT,
                context TEXT,
                processed BOOLEAN DEFAULT 0
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS compilation_log (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                code TEXT,
                success BOOLEAN,
                errors TEXT,
                hardware TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS code_rules (
                id INTEGER PRIMARY KEY,
                rule_text TEXT,
                pattern_find TEXT,
                pattern_replace TEXT,
                context TEXT,
                confidence FLOAT,
                learned_from TEXT,
                times_applied INTEGER DEFAULT 0
            )
        """)

        # Migrations (Idempotent)
        try: cursor.execute("ALTER TABLE sessions ADD COLUMN title TEXT")
        except: pass
        try: cursor.execute("ALTER TABLE sessions ADD COLUMN user_id TEXT")
        except: pass
        try: cursor.execute("ALTER TABLE repo_index ADD COLUMN user_id TEXT")
        except: pass
        try: cursor.execute("ALTER TABLE style_preferences ADD COLUMN user_id TEXT")
        except: pass
        try: cursor.execute("ALTER TABLE feedback ADD COLUMN comment TEXT")
        except: pass
        try: cursor.execute("ALTER TABLE corrections ADD COLUMN processed BOOLEAN DEFAULT 0")
        except: pass

        conn.commit()
        conn.close()
        
    def create_session(self) -> str:
        now = datetime.now()
        base_id = now.strftime("%Y%m%d_%H%M%S")
        session_id = base_id
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        counter = 0
        while True:
            try:
                cursor.execute(
                    "INSERT INTO sessions (session_id, user_id, started_at) VALUES (?, ?, ?)",
                    (session_id, self.user_id, now.isoformat())
                )
                conn.commit()
                break
            except sqlite3.IntegrityError:
                counter += 1
                session_id = f"{base_id}_{counter}"
                
        conn.close()
        return session_id
        
    def start_new_session(self) -> str:
        self.current_session_id = self.create_session()
        return self.current_session_id

    def end_session(self) -> None:
        if not self.current_session_id: return
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE sessions SET ended_at = ? WHERE session_id = ?",
            (datetime.now().isoformat(), self.current_session_id)
        )
        conn.commit()
        conn.close()
        
    def save_message(self, role: str, content: str) -> int:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
            (self.current_session_id, role, content, datetime.now().isoformat())
        )
        msg_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return msg_id

    def get_sessions(self, limit: int = 20) -> List[Dict[str, str]]:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT session_id, started_at, title FROM sessions WHERE user_id = ? ORDER BY started_at DESC LIMIT ?", (self.user_id, limit))
        rows = cursor.fetchall()
        conn.close()
        return [{"id": r[0], "date": r[1], "title": r[2] if len(r) > 2 else None} for r in rows]

    def rename_session(self, session_id: str, new_title: str) -> None:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE sessions SET title = ? WHERE session_id = ? AND user_id = ?", (new_title, session_id, self.user_id))
        conn.commit()
        conn.close()

    def delete_session(self, session_id: str) -> None:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE session_id = ? AND user_id = ?", (session_id, self.user_id))
        if cursor.rowcount > 0:
            cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        conn.commit()
        conn.close()

    def clear_current_session(self) -> None:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages WHERE session_id = ?", (self.current_session_id,))
        conn.commit()
        conn.close()

    def load_session(self, session_id: str) -> List[Dict[str, str]]:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT 1 FROM sessions WHERE session_id = ? AND user_id = ?", (session_id, self.user_id))
        if not cursor.fetchone():
            conn.close()
            return []
            
        cursor.execute("SELECT id, role, content, timestamp FROM messages WHERE session_id = ? ORDER BY id ASC", (session_id,))
        rows = cursor.fetchall()
        conn.close()
        
        self.current_session_id = session_id
        return [{"id": r[0], "role": r[1], "content": r[2], "timestamp": r[3]} for r in rows]

    def create_backup(self) -> Tuple[bool, str]:
        if not DB_PATH.exists(): return False, "Database file not found."
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = DATA_DIR / "backups"
        backup_dir.mkdir(exist_ok=True)
        backup_path = backup_dir / f"conversations_{timestamp}.db"
        try:
            src = sqlite3.connect(DB_PATH); dst = sqlite3.connect(backup_path)
            with dst: src.backup(dst)
            dst.close(); src.close()
            return True, str(backup_path)
        except Exception as e: return False, str(e)