#!/usr/bin/env python3
"""
Import Marlin firmware rules into BuddAI
Reads training/marlin_rules.txt and executes /teach commands
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from buddai_executive import BuddAI

def import_marlin_rules(rules_file: str = "training/marlin_rules.txt"):
    """Import all Marlin rules from file"""
    
    print("🔧 BuddAI Marlin Firmware Training")
    print("=" * 50)
    
    # Initialize BuddAI
    buddai = BuddAI(user_id="marlin_trainer", server_mode=True)
    
    # Read rules file
    if not os.path.exists(rules_file):
        print(f"❌ Rules file not found: {rules_file}")
        return
    
    with open(rules_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Filter /teach commands
    rules = [line.strip() for line in lines if line.strip().startswith('/teach')]
    
    print(f"\n📚 Found {len(rules)} Marlin rules to import\n")
    
    # Import each rule
    imported = 0
    for i, rule in enumerate(rules, 1):
        # Extract rule text
        rule_text = rule[7:].strip()  # Remove '/teach '
        
        # Import rule
        try:
            buddai.teach_rule(rule_text)
            imported += 1
            
            # Progress indicator
            if i % 10 == 0:
                print(f"✅ Imported {i}/{len(rules)} rules...")
        
        except Exception as e:
            print(f"❌ Error importing rule {i}: {e}")
    
    print(f"\n🎉 Import complete!")
    print(f"✅ Successfully imported {imported}/{len(rules)} rules")
    print(f"📊 Total Marlin rules in database: {imported}")
    print(f"\n💡 Rules available for Marlin firmware development")

if __name__ == '__main__':
    import_marlin_rules()