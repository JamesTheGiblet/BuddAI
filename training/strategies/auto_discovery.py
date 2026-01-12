import os
from pathlib import Path
from typing import List, Any
from training.registry import TrainingStrategy

class AutoDiscoveryStrategy(TrainingStrategy):
    name = "auto_discovery"
    description = "Auto-detect and import rules from .txt files in the training directory"
    
    def run(self, buddai_instance: Any, args: List[str]) -> str:
        # Determine training directory (parent of strategies package)
        training_dir = Path(__file__).parent.parent
        
        if not training_dir.exists():
            return f"❌ Training directory not found: {training_dir}"
            
        # Find all .txt files
        txt_files = list(training_dir.glob("*.txt"))
        
        if not txt_files:
            return f"⚠️ No .txt files found in {training_dir}"
            
        results = []
        total_rules = 0
        
        for file_path in txt_files:
            try:
                count = 0
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('/teach '):
                            rule = line[7:].strip()
                            # The executive's teach_rule now handles deduplication
                            if buddai_instance.teach_rule(rule):
                                count += 1
                
                if count > 0:
                    results.append(f"{file_path.name} ({count})")
                    total_rules += count
            except Exception as e:
                results.append(f"{file_path.name} (Error: {str(e)})")
        
        if total_rules == 0:
            return f"⚠️ Scanned {len(txt_files)} files but found no /teach commands."
            
        return f"✅ Auto-detected and imported {total_rules} rules from:\n   - " + "\n   - ".join(results)