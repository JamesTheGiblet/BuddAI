import urllib.request
import urllib.error
from typing import List, Any
from training.registry import TrainingStrategy

class PublicKnowledgeStrategy(TrainingStrategy):
    name = "public_db"
    description = "Fetch rules from a public URL (usage: /train public_db <url>)"
    
    def run(self, buddai_instance: Any, args: List[str]) -> str:
        if not args:
            return "❌ Usage: /train public_db <url>"
            
        url = args[0]
        print(f"🌐 Connecting to Public Knowledge Base: {url}...")
        
        try:
            # Set a user agent to avoid 403s from some servers
            req = urllib.request.Request(
                url, 
                data=None, 
                headers={'User-Agent': 'BuddAI/5.0 (Symbiotic Exocortex)'}
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = response.read().decode('utf-8')
                
            lines = data.splitlines()
            imported = 0
            duplicates = 0
            
            for line in lines:
                line = line.strip()
                # Support both /teach format and raw rule lists
                if line and not line.startswith('#'):
                    rule = line[7:].strip() if line.startswith('/teach ') else line
                    if len(rule) > 5: # Ignore noise
                        if buddai_instance.teach_rule(rule, source=f"public_db:{url}"):
                            imported += 1
                        else:
                            duplicates += 1
            
            return f"✅ Successfully imported {imported} rules from Public DB.\n   Skipped (duplicates): {duplicates}"
            
        except Exception as e:
            return f"❌ Failed to fetch from Public DB: {str(e)}"