import os
from typing import List, Any
from training.registry import TrainingStrategy

class RuleImportStrategy(TrainingStrategy):
    name = "import_rules"
    description = "Import rules from a text file (usage: /train import_rules <filepath>)"
    
    def run(self, buddai_instance: Any, args: List[str]) -> str:
        if not args:
            return "❌ Usage: /train import_rules <filepath>"
            
        filepath = args[0]
        if not os.path.exists(filepath):
            return f"❌ File not found: {filepath}"
            
        count = 0
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('/teach '):
                        rule = line[7:].strip()
                        if buddai_instance.teach_rule(rule):
                            count += 1
            return f"✅ Imported {count} rules from {filepath}"
        except Exception as e:
            return f"❌ Error importing rules: {e}"