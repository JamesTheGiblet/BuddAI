"""
Documentation Workflow
"""
import os
from typing import List, Dict, Any
from core.workflow_base import Workflow, WorkflowStep

class DocumentationWorkflow(Workflow):
    name = "generate_documentation"
    description = "Generates documentation for a project"
    
    def detect(self, text: str) -> float:
        text = text.lower()
        if "document" in text or "docs" in text:
            if "generate" in text or "create" in text or "write" in text:
                return 0.9
            return 0.6
        if "readme" in text:
            return 0.8
        return 0.0
        
    def plan(self, text: str, context: Dict[str, Any] = None) -> List[WorkflowStep]:
        steps = []
        steps.append(WorkflowStep("Analyze Project", "analyze_project"))
        steps.append(WorkflowStep("Generate README", "generate_readme"))
        steps.append(WorkflowStep("Generate Architecture", "generate_architecture"))
        steps.append(WorkflowStep("Generate Contributing", "generate_contributing"))
        return steps

    def _analyze_project(self, params: Dict, context: Dict) -> Dict:
        return {"type": "unknown", "source_files": []}

    def _detect_project_type(self, path: str) -> str:
        if os.path.exists(os.path.join(path, 'requirements.txt')):
            return 'python'
        if os.path.exists(os.path.join(path, 'package.json')):
            return 'javascript'
        return 'unknown'

    def _find_source_files(self, path: str) -> List[str]:
        files = []
        for root, _, filenames in os.walk(path):
            for f in filenames:
                if f.endswith(('.py', '.js', '.cpp', '.h')):
                    files.append(os.path.join(root, f))
        return files

    def _generate_readme(self, params: Dict, context: Dict) -> Dict:
        return {"file": "README.md", "content": "# Project\n\nAuto-generated README"}

    def _generate_architecture(self, params: Dict, context: Dict) -> Dict:
        return {"file": "ARCHITECTURE.md", "content": "# Architecture\n\nOverview"}

    def _generate_contributing(self, params: Dict, context: Dict) -> Dict:
        return {"file": "CONTRIBUTING.md", "content": "# Contributing\n\nGuidelines"}