import importlib
import pkgutil
from pathlib import Path
from typing import Dict, List, Any, Optional

class TrainingStrategy:
    """Base class for training strategies"""
    name: str = "base"
    description: str = "Base strategy"
    
    def run(self, buddai_instance: Any, args: List[str]) -> str:
        """Execute the training strategy"""
        raise NotImplementedError("Strategies must implement run()")

class TrainingRegistry:
    """Registry for discovering and managing training strategies"""
    
    def __init__(self):
        self.strategies: Dict[str, TrainingStrategy] = {}
        self.discover_strategies()
    
    def discover_strategies(self):
        """Auto-discover strategies in the strategies directory"""
        strategies_path = Path(__file__).parent / "strategies"
        
        if not strategies_path.exists():
            return

        for _, name, _ in pkgutil.iter_modules([str(strategies_path)]):
            try:
                module = importlib.import_module(f"training.strategies.{name}")
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and 
                        issubclass(attr, TrainingStrategy) and 
                        attr is not TrainingStrategy):
                        
                        strategy = attr()
                        self.strategies[strategy.name] = strategy
            except Exception as e:
                print(f"❌ Failed to load training strategy {name}: {e}")

    def get_strategy(self, name: str) -> Optional[TrainingStrategy]:
        return self.strategies.get(name)

    def list_strategies(self) -> Dict[str, str]:
        return {name: strategy.description for name, strategy in self.strategies.items()}

_registry = None

def get_training_registry() -> TrainingRegistry:
    global _registry
    if _registry is None:
        _registry = TrainingRegistry()
    return _registry