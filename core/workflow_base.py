"""
Base Workflow Definitions
"""
from typing import List, Dict, Any

class WorkflowStep:
    """Represents a single step in a workflow"""
    def __init__(self, name: str, action: str, params: Dict = None):
        self.name = name
        self.action = action
        self.params = params or {}

class Workflow:
    """Base class for all workflows"""
    name: str = "base_workflow"
    description: str = "Base workflow"
    
    def detect(self, text: str) -> float:
        return 0.0
        
    def plan(self, text: str, context: Dict[str, Any] = None) -> List[WorkflowStep]:
        return []