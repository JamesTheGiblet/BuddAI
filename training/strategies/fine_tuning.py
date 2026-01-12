from typing import List, Any
from training.registry import TrainingStrategy
from core.buddai_training import ModelFineTuner

class FineTuningStrategy(TrainingStrategy):
    name = "fine_tune"
    description = "Export corrections for model fine-tuning"
    
    def __init__(self):
        self.fine_tuner = ModelFineTuner()

    def run(self, buddai_instance: Any, args: List[str]) -> str:
        result = self.fine_tuner.prepare_training_data()
        return f"✅ {result}"