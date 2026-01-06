import sqlite3
import json
from core.buddai_shared import DB_PATH, DATA_DIR

class ModelFineTuner:
    """Fine-tune local model on YOUR corrections"""
    
    def prepare_training_data(self):
        """Convert corrections to training format"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT original_code, corrected_code, reason 
            FROM corrections
        """)
        
        training_data = []
        for original, corrected, reason in cursor.fetchall():
            training_data.append({
                "prompt": f"Generate code for: {reason}",
                "completion": corrected,
                "negative_example": original
            })
        
        conn.close()
        
        # Save as JSONL for fine-tuning
        output_path = DATA_DIR / 'training_data.jsonl'
        with open(output_path, 'w', encoding='utf-8') as f:
            for item in training_data:
                f.write(json.dumps(item) + '\n')
        return f"Exported {len(training_data)} examples to {output_path}"
    
    def fine_tune_model(self):
        """Fine-tune Qwen on your corrections"""
        # This requires:
        # 1. Export training data
        # 2. Use Ollama modelfile or external training
        # 3. Create custom model: qwen2.5-coder-james:3b
        pass