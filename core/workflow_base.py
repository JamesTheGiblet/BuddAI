"""
Base Workflow Class
All workflows inherit from this
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class WorkflowStep:
    """Represents a single step in a workflow"""
    
    def __init__(self, name: str, description: str, action: str, parameters: Dict = None):
        self.name = name
        self.description = description
        self.action = action
        self.parameters = parameters or {}
        self.status = 'pending'  # pending, running, completed, failed
        self.result = None
        self.error = None
        self.started_at = None
        self.completed_at = None
    
    def start(self):
        """Mark step as started"""
        self.status = 'running'
        self.started_at = datetime.now().isoformat()
    
    def complete(self, result: Any = None):
        """Mark step as completed"""
        self.status = 'completed'
        self.result = result
        self.completed_at = datetime.now().isoformat()
    
    def fail(self, error: str):
        """Mark step as failed"""
        self.status = 'failed'
        self.error = error
        self.completed_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'description': self.description,
            'action': self.action,
            'parameters': self.parameters,
            'status': self.status,
            'result': self.result,
            'error': self.error,
            'started_at': self.started_at,
            'completed_at': self.completed_at
        }


class Workflow(ABC):
    """
    Base class for all workflows
    
    A workflow is a series of steps that accomplish a specific goal
    Examples: create_project, fix_bug, add_feature, refactor_code
    """
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.steps: List[WorkflowStep] = []
        self.status = 'initialized'
        self.created_at = datetime.now().isoformat()
        self.started_at = None
        self.completed_at = None
        self.metadata = {}
    
    @abstractmethod
    def detect(self, user_input: str) -> float:
        """
        Detect if this workflow matches the user input
        
        Args:
            user_input: User's message/request
        
        Returns:
            Confidence score (0.0 to 1.0)
        """
        pass
    
    @abstractmethod
    def plan(self, user_input: str, context: Dict = None) -> List[WorkflowStep]:
        """
        Create a plan (list of steps) for this workflow
        
        Args:
            user_input: User's message/request
            context: Additional context (files, repo info, etc.)
        
        Returns:
            List of WorkflowStep objects
        """
        pass
    
    def execute(self, context: Dict = None) -> Dict:
        """
        Execute the workflow
        
        Args:
            context: Execution context
        
        Returns:
            Execution result
        """
        self.status = 'running'
        self.started_at = datetime.now().isoformat()
        
        results = []
        
        try:
            for step in self.steps:
                logger.info(f"Executing workflow step: {step.name}")
                step.start()
                
                try:
                    # Execute step
                    result = self._execute_step(step, context)
                    step.complete(result)
                    results.append(result)
                    
                except Exception as e:
                    step.fail(str(e))
                    logger.error(f"Step failed: {step.name} - {e}")
                    
                    if self._is_critical_step(step):
                        self.status = 'failed'
                        raise
            
            self.status = 'completed'
            self.completed_at = datetime.now().isoformat()
            
            return {
                'success': True,
                'workflow': self.name,
                'steps_completed': len([s for s in self.steps if s.status == 'completed']),
                'total_steps': len(self.steps),
                'results': results,
                'metadata': self.metadata
            }
            
        except Exception as e:
            self.status = 'failed'
            self.completed_at = datetime.now().isoformat()
            
            return {
                'success': False,
                'workflow': self.name,
                'error': str(e),
                'steps_completed': len([s for s in self.steps if s.status == 'completed']),
                'total_steps': len(self.steps)
            }
    
    @abstractmethod
    def _execute_step(self, step: WorkflowStep, context: Dict) -> Any:
        """Execute a single step"""
        pass
    
    def _is_critical_step(self, step: WorkflowStep) -> bool:
        """Determine if a step is critical (failure stops workflow)"""
        # By default, all steps are critical
        # Override in subclasses for more nuanced behavior
        return True
    
    def add_step(self, name: str, description: str, action: str, parameters: Dict = None):
        """Add a step to the workflow"""
        step = WorkflowStep(name, description, action, parameters)
        self.steps.append(step)
        return step
    
    def get_summary(self) -> Dict:
        """Get workflow summary"""
        return {
            'name': self.name,
            'description': self.description,
            'status': self.status,
            'total_steps': len(self.steps),
            'completed_steps': len([s for s in self.steps if s.status == 'completed']),
            'failed_steps': len([s for s in self.steps if s.status == 'failed']),
            'created_at': self.created_at,
            'started_at': self.started_at,
            'completed_at': self.completed_at
        }
    
    def get_plan_preview(self) -> str:
        """Get human-readable plan preview"""
        output = f"📋 Workflow: {self.name}\n"
        output += f"Description: {self.description}\n\n"
        output += f"Steps ({len(self.steps)}):\n"
        
        for i, step in enumerate(self.steps, 1):
            status_icon = {
                'pending': '⏸️',
                'running': '▶️',
                'completed': '✅',
                'failed': '❌'
            }.get(step.status, '❓')
            
            output += f"{i}. {status_icon} {step.name}\n"
            output += f"   {step.description}\n"
        
        return output