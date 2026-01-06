import sqlite3
import re
import ast
from pathlib import Path
from datetime import datetime

class RepoManager:
    """Manages local repository indexing and retrieval (RAG)"""
    
    def __init__(self, db_path: Path, user_id: str):
        self.db_path = db_path
        self.user_id = user_id

    def is_search_query(self, message: str) -> bool:
        """Check if this is a search query that should query repo_index"""
        message_lower = message.lower()
        search_triggers = [
            "show me", "find", "search for", "list all",
            "what functions", "which repos", "do i have",
            "where did i", "have i used", "examples of",
            "show all", "display"
        ]
        return any(trigger in message_lower for trigger in search_triggers)

    def search_repositories(self, query: str) -> str:
        """Search repo_index for relevant functions and code"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM repo_index WHERE user_id = ?", (self.user_id,))
        count = cursor.fetchone()[0]
        print(f"\n🔍 Searching {count} indexed functions...\n")

        # Extract keywords from query
        keywords = re.findall(r'\b\w{4,}\b', query.lower())
        # Add specific search terms
        specific_terms = []
        if "exponential" in query.lower() or "decay" in query.lower():
            specific_terms.append("applyForge")
            specific_terms.append("exp(")
        if "forge" in query.lower():
            specific_terms.append("Forge")
        keywords.extend(specific_terms)
        
        if not keywords:
            print("❌ No search terms found")
            conn.close()
            return "No search terms provided."
            
        # Build parameterized query
        conditions = []
        params = []
        for keyword in keywords:
            conditions.append("(function_name LIKE ? OR content LIKE ? OR repo_name LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])
            
        sql = f"SELECT repo_name, file_path, function_name, content FROM repo_index WHERE ({' OR '.join(conditions)}) AND user_id = ? ORDER BY last_modified DESC LIMIT 10"
        params.append(self.user_id)
        
        cursor.execute(sql, params)
        results = cursor.fetchall()
        conn.close()
        if not results:
            return f"❌ No functions found matching: {', '.join(keywords)}\n\nTry: /index <path> to index more repositories"
        # Format results
        output = f"✅ Found {len(results)} matches for: {', '.join(set(keywords))}\n\n"
        for i, (repo, file_path, func, content) in enumerate(results, 1):
            # Extract relevant snippet
            lines = content.split('\n')
            snippet_lines = []
            for line in lines[:30]:  # First 30 lines
                if any(kw in line.lower() for kw in keywords):
                    snippet_lines.append(line)
                if len(snippet_lines) >= 10:
                    break
            if not snippet_lines:
                snippet_lines = lines[:10]
            snippet = '\n'.join(snippet_lines)
            output += f"**{i}. {func}()** in {repo}\n"
            output += f"   📁 {Path(file_path).name}\n"
            output += f"\n```cpp\n{snippet}\n```\n"
            output += f"   ---\n\n"
        return output

    def index_local_repositories(self, root_path: str) -> None:
        """Crawl directories and index .py, .ino, and .cpp files"""
        print(f"\n🔍 Indexing repositories in: {root_path}")
        path = Path(root_path)
        
        if not path.exists():
            print(f"❌ Path not found: {root_path}")
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        count = 0
        
        for file_path in path.rglob('*'):
            if file_path.is_file() and file_path.suffix in ['.py', '.ino', '.cpp', '.h', '.js', '.jsx', '.html', '.css']:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        
                    functions = []
                    
                    # Python parsing
                    if file_path.suffix == '.py':
                        try:
                            tree = ast.parse(content)
                            for node in ast.walk(tree):
                                if isinstance(node, ast.FunctionDef):
                                    functions.append(node.name)
                        except:
                            pass
                            
                    # C++/Arduino parsing
                    elif file_path.suffix in ['.ino', '.cpp', '.h']:
                        matches = re.findall(r'\b(?:void|int|bool|float|double|String|char)\s+(\w+)\s*\(', content)
                        functions.extend(matches)

                    # JS/Web parsing
                    elif file_path.suffix in ['.js', '.jsx']:
                        matches = re.findall(r'(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?:async\s*)?\(?.*?\)?\s*=>)', content)
                        functions.extend([m[0] or m[1] for m in matches if m[0] or m[1]])

                    # HTML/CSS - Index as whole file
                    elif file_path.suffix in ['.html', '.css']:
                        functions.append("file_content")
                    
                    # Determine repo name
                    try:
                        repo_name = file_path.relative_to(path).parts[0]
                    except:
                        repo_name = "unknown"
                        
                    timestamp = datetime.fromtimestamp(file_path.stat().st_mtime)
                    
                    for func in functions:
                        cursor.execute("""
                            INSERT INTO repo_index (user_id, file_path, repo_name, function_name, content, last_modified)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (self.user_id, str(file_path), repo_name, func, content, timestamp.isoformat()))
                        count += 1
                        
                except Exception:
                    pass
                    
        conn.commit()
        conn.close()
        print(f"✅ Indexed {count} functions across repositories")

    def retrieve_style_context(self, message: str, prompt_template: str, user_name: str) -> str:
        """Search repo_index for code snippets matching the request"""
        # Extract potential keywords (nouns/modules)
        keywords = re.findall(r'\b\w{4,}\b', message.lower())
        if not keywords:
            return ""

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build a search query for function names or repo names
        search_terms = " OR ".join([f"function_name LIKE '%{k}%'" for k in keywords])
        search_terms += " OR " + " OR ".join([f"repo_name LIKE '%{k}%'" for k in keywords])
        
        query = f"SELECT repo_name, function_name, content FROM repo_index WHERE ({search_terms}) AND user_id = ? LIMIT 2"
        
        cursor.execute(query, (self.user_id,))
        results = cursor.fetchall()
        conn.close()
        
        if not results:
            return ""
            
        context_block = prompt_template.format(user_name=user_name)
        for repo, func, content in results:
            # Just grab the first 500 chars of the file to save context window
            snippet = content[:500] + "..."
            context_block += f"Repo: {repo} | Function: {func}\nCode:\n{snippet}\n---\n"
        
        return context_block