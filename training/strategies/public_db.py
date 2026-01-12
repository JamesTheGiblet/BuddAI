"""
Public Knowledge Base Strategy
Import rules from GitHub Gists or any raw text URL
"""

import urllib.request
import urllib.error
from typing import List, Any
from training.registry import TrainingStrategy

class PublicKnowledgeStrategy(TrainingStrategy):
    name = "public_db"
    description = "Import rules from a public URL (GitHub Gist, raw text, etc.)"
    
    def run(self, buddai_instance: Any, args: List[str]) -> str:
        if not args:
            return """❌ Usage: /train public_db <URL>
            
Examples:
  /train public_db https://gist.githubusercontent.com/user/id/raw/file.txt
  /train public_db https://raw.githubusercontent.com/user/repo/main/rules.txt
  
The URL must point to a raw text file containing /teach commands."""
        
        url = args[0].strip()
        
        # Validate URL
        if not url.startswith(('http://', 'https://')):
            return "❌ URL must start with http:// or https://"
        
        try:
            # Download content
            print(f"🌐 Fetching knowledge base from: {url}")
            
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'BuddAI/5.0 (Symbiotic Exocortex)'}
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                content = response.read().decode('utf-8')
            
            # Parse rules
            rules = []
            for line in content.splitlines():
                line = line.strip()
                if line.startswith('/teach '):
                    rule = line[7:].strip()
                    if rule:  # Skip empty rules
                        rules.append(rule)
            
            if not rules:
                return f"⚠️  No /teach commands found in {url}"
            
            # Import rules
            imported = 0
            duplicates = 0
            
            for rule in rules:
                if buddai_instance.teach_rule(rule, source=f"public_db:{url}"):
                    imported += 1
                else:
                    duplicates += 1
            
            result = f"""✅ Knowledge base imported successfully!

📊 Statistics:
   • URL: {url}
   • Rules found: {len(rules)}
   • Imported: {imported}
   • Skipped (duplicates): {duplicates}
   
💡 Your BuddAI now has cloud-synced knowledge!"""
            
            return result
            
        except Exception as e:
            return f"❌ Error processing knowledge base: {e}"