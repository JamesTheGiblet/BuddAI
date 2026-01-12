import sqlite3
import urllib.request
from pathlib import Path
from datetime import datetime

class GistLoader:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        # Assumes gist_memory.txt is in the same directory as this script
        self.gist_file_path = Path(__file__).parent / "gist_memory.txt"

    def index_gists(self, user_id: str = "default", silent: bool = False) -> None:
        """Index Gists defined in gist_memory.txt"""
        
        if not self.gist_file_path.exists():
            if not silent:
                print(f"❌ Gist memory file not found at {self.gist_file_path}")
            return

        if not silent:
            print(f"\n🔍 Indexing Gists from: {self.gist_file_path}")
        
        try:
            with open(self.gist_file_path, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f if line.strip().startswith('http')]
        except Exception as e:
            if not silent:
                print(f"❌ Error reading gist file: {e}")
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Ensure table exists
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
        
        count = 0
        
        for url in urls:
            try:
                if not silent:
                    print(f"   - Fetching {url}...", end="\r")
                with urllib.request.urlopen(url) as response:
                    content = response.read().decode('utf-8')
                
                filename = url.split('/')[-1] or "gist_content.txt"
                timestamp = datetime.now()
                
                cursor.execute("DELETE FROM repo_index WHERE file_path = ? AND user_id = ?", (url, user_id))
                
                cursor.execute("""
                    INSERT INTO repo_index (user_id, file_path, repo_name, function_name, content, last_modified)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, url, "Gist Memory", filename, content, timestamp.isoformat()))
                
                count += 1
            except Exception as e:
                if not silent:
                    print(f"   ❌ Failed to fetch {url}: {e}")
                
        conn.commit()
        conn.close()
        if not silent:
            print(f"\n✅ Indexed {count} Gists.                         ")