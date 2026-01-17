"""
Workflow Detector
Analyzes user input and routes to appropriate workflow
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from .workflow_base import Workflow

logger = logging.getLogger(__name__)

class WorkflowDetector:
    """
    Detects user intent and routes to appropriate workflow
    
    Analyzes patterns in user input to determine:
    - What the user wants to accomplish
    - Which workflow can handle it
    - Confidence level of the match
    """
    
    def __init__(self):
        self.workflows: List[Workflow] = []
        self.detection_patterns = self._load_detection_patterns()
    
    def _load_detection_patterns(self) -> Dict:
        """Load intent detection patterns"""
        return {
            'create_project': {
                'keywords': ['create', 'new', 'start', 'init', 'initialize', 'scaffold', 'generate'],
                'objects': ['project', 'app', 'application', 'repo', 'repository'],
                'patterns': [
                    r'create\s+(?:a\s+)?(?:new\s+)?project',
                    r'start\s+(?:a\s+)?(?:new\s+)?project',
                    r'initialize\s+(?:a\s+)?project',
                    r'scaffold\s+(?:a\s+)?project'
                ],
                'examples': [
                    'create a new project',
                    'start a new ESP32 project',
                    'initialize a web app'
                ]
            },
            'fix_bug': {
                'keywords': ['fix', 'debug', 'solve', 'resolve', 'repair'],
                'objects': ['bug', 'error', 'issue', 'problem', 'crash'],
                'patterns': [
                    r'fix\s+(?:the\s+|a\s+|this\s+)?bug',
                    r'debug\s+(?:the\s+)?(?:a\s+)?issue',
                    r'solve\s+(?:the\s+)?(?:a\s+)?problem',
                    r'(?:the\s+)?code\s+(?:is\s+)?(?:not\s+)?working'
                ],
                'examples': [
                    'fix this bug',
                    'debug the motor issue',
                    'the servo isn\'t working'
                ]
            },
            'add_feature': {
                'keywords': ['add', 'implement', 'create', 'build', 'develop'],
                'objects': ['feature', 'function', 'capability', 'functionality'],
                'patterns': [
                    r'add\s+(?:a\s+)?(?:new\s+)?feature',
                    r'implement\s+(?:a\s+)?feature',
                    r'build\s+(?:a\s+)?feature',
                    r'i\s+(?:want|need)\s+to\s+add'
                ],
                'examples': [
                    'add a new feature',
                    'implement WiFi connectivity',
                    'I want to add sensor support'
                ]
            },
            'refactor_code': {
                'keywords': ['refactor', 'improve', 'optimize', 'restructure', 'clean', 'reorganize'],
                'objects': ['code', 'structure', 'architecture', 'organization'],
                'patterns': [
                    r'refactor\s+(?:the\s+)?(?:this\s+)?code',
                    r'improve\s+(?:the\s+)?(?:code\s+)?structure',
                    r'clean\s+up\s+(?:the\s+)?code',
                    r'make\s+(?:the\s+)?code\s+(?:better|cleaner)'
                ],
                'examples': [
                    'refactor this code',
                    'improve the code structure',
                    'clean up this mess'
                ]
            },
            'generate_docs': {
                'keywords': ['document', 'write', 'create', 'generate'],
                'objects': ['documentation', 'docs', 'readme', 'guide', 'manual'],
                'patterns': [
                    r'(?:write|create|generate)\s+(?:the\s+)?(?:a\s+)?documentation',
                    r'(?:write|create|generate)\s+(?:a\s+)?(?:the\s+)?readme',
                    r'document\s+(?:this|the)\s+(?:code|project)',
                    r'i\s+need\s+documentation'
                ],
                'examples': [
                    'generate documentation',
                    'write a README',
                    'document this project'
                ]
            },
            'write_tests': {
                'keywords': ['test', 'write', 'create', 'generate', 'add'],
                'objects': ['tests', 'test', 'unit test', 'testing'],
                'patterns': [
                    r'(?:write|create|generate|add)\s+(?:some\s+)?tests',
                    r'(?:write|create|generate|add)\s+unit\s+tests',
                    r'i\s+need\s+tests',
                    r'test\s+coverage'
                ],
                'examples': [
                    'write tests for this',
                    'create unit tests',
                    'I need test coverage'
                ]
            },
            'review_code': {
                'keywords': ['review', 'check', 'analyze', 'examine', 'audit', 'validate'],
                'objects': ['code', 'pr', 'pull request', 'changes'],
                'patterns': [
                    r'review\s+(?:this\s+)?(?:the\s+)?code',
                    r'check\s+(?:this\s+)?(?:the\s+)?code',
                    r'analyze\s+(?:this\s+)?(?:the\s+)?code',
                    r'what\'s\s+wrong\s+with'
                ],
                'examples': [
                    'review this code',
                    'check my implementation',
                    'what\'s wrong with this?'
                ]
            },
            'get_metric': {
                'keywords': ['how many', 'count', 'number', 'total', 'stats', 'metrics', 'accuracy', 'pass rate'],
                'objects': ['tests', 'rules', 'projects', 'files', 'lines', 'coverage'],
                'patterns': [
                    r'how\s+many',
                    r'what\s+is\s+the\s+(?:count|number|total)',
                    r'show\s+(?:me\s+)?(?:the\s+)?(?:stats|metrics)',
                    r'what\'s\s+my\s+(?:job|company|product|accuracy)'
                ],
                'examples': [
                    'how many tests do we have',
                    'what is the total line count',
                    'show me the stats'
                ]
            },
            'system_query': {
                'keywords': ['what', 'who', 'where', 'when', 'why', 'status', 'info', 'about', 'version', 'components', 'architecture', 'structure'],
                'objects': ['system', 'buddai', 'version', 'model', 'capabilities', 'you', 'yourself', 'components', 'architecture', 'skills', 'validators', 'languages'],
                'patterns': [
                    r'who\s+are\s+you',
                    r'what\s+is\s+this',
                    r'system\s+status',
                    r'tell\s+me\s+about',
                    r'what\s+can\s+you\s+do',
                    r'what\s+are\s+(?:your|buddai\'?s?)\s+(?:main\s+)?components',
                    r'describe\s+(?:your|buddai\'?s?)\s+architecture'
                ],
                'examples': [
                    'who are you',
                    'system status',
                    'tell me about yourself'
                ]
            },
            'explain_code': {
                'keywords': ['explain', 'what', 'how', 'why', 'understand'],
                'objects': ['does', 'work', 'mean', 'is'],
                'patterns': [
                    r'explain\s+(?:this\s+)?(?:the\s+)?code',
                    r'what\s+does\s+this\s+(?:do|mean)',
                    r'how\s+does\s+this\s+work',
                    r'i\s+don\'t\s+understand'
                ],
                'examples': [
                    'explain this code',
                    'what does this do?',
                    'how does this work?'
                ]
            }
        }
    
    def register_workflow(self, workflow: Workflow):
        """Register a workflow"""
        self.workflows.append(workflow)
        logger.info(f"Registered workflow: {workflow.name}")
    
    def detect_intent(self, user_input: str) -> Dict:
        """
        Detect user intent from input
        
        Args:
            user_input: User's message/request
        
        Returns:
            {
                'intent': str,
                'confidence': float,
                'matches': List[str],
                'workflow': Optional[Workflow]
            }
        """
        
        user_input_lower = user_input.lower()
        
        # Score each intent
        intent_scores = {}
        
        for intent, config in self.detection_patterns.items():
            score = 0
            matches = []
            
            # Check keywords
            keyword_matches = sum(1 for kw in config['keywords'] if kw in user_input_lower)
            object_matches = sum(1 for obj in config['objects'] if obj in user_input_lower)
            
            score += keyword_matches * 2  # Keywords worth 2 points
            score += object_matches * 3   # Objects worth 3 points
            
            if keyword_matches > 0:
                matches.append(f"keywords: {keyword_matches}")
            if object_matches > 0:
                matches.append(f"objects: {object_matches}")
            
            # Check regex patterns
            for pattern in config['patterns']:
                if re.search(pattern, user_input_lower):
                    score += 5  # Pattern match worth 5 points
                    matches.append(f"pattern: {pattern}")
                    break
            
            if score > 0:
                intent_scores[intent] = {
                    'score': score,
                    'matches': matches
                }
        
        # No matches
        if not intent_scores:
            return {
                'intent': 'unknown',
                'confidence': 0.0,
                'matches': [],
                'workflow': None
            }
        
        # Get best match
        best_intent = max(intent_scores.items(), key=lambda x: x[1]['score'])
        intent_name = best_intent[0]
        intent_data = best_intent[1]
        
        # Normalize confidence (max score is ~10)
        confidence = min(1.0, intent_data['score'] / 10.0)
        
        # Find matching workflow
        matching_workflow = None
        for workflow in self.workflows:
            workflow_confidence = workflow.detect(user_input)
            if workflow_confidence > 0.5:  # Threshold
                matching_workflow = workflow
                break
        
        return {
            'intent': intent_name,
            'confidence': confidence,
            'matches': intent_data['matches'],
            'workflow': matching_workflow
        }
    
    def route_to_workflow(self, user_input: str, context: Dict = None) -> Optional[Tuple[Workflow, List]]:
        """
        Route user input to appropriate workflow
        
        Args:
            user_input: User's message/request
            context: Additional context
        
        Returns:
            Tuple of (workflow, plan) or None
        """
        
        # Detect intent
        detection = self.detect_intent(user_input)
        
        if detection['confidence'] < 0.3:
            logger.info(f"Low confidence ({detection['confidence']:.2f}) for intent: {detection['intent']}")
            return None
        
        logger.info(f"Detected intent: {detection['intent']} (confidence: {detection['confidence']:.2f})")
        
        # Try registered workflows first
        if detection['workflow']:
            workflow = detection['workflow']
            plan = workflow.plan(user_input, context)
            return (workflow, plan)
        
        # Try each workflow
        best_match = None
        best_confidence = 0.0
        
        for workflow in self.workflows:
            confidence = workflow.detect(user_input)
            
            if confidence > best_confidence:
                best_confidence = confidence
                best_match = workflow
        
        if best_match and best_confidence > 0.5:
            plan = best_match.plan(user_input, context)
            return (best_match, plan)
        
        return None
    
    def get_supported_intents(self) -> List[str]:
        """Get list of supported intents"""
        return list(self.detection_patterns.keys())
    
    def get_intent_examples(self, intent: str) -> List[str]:
        """Get example phrases for an intent"""
        if intent in self.detection_patterns:
            return self.detection_patterns[intent]['examples']
        return []


# Global detector instance
_detector = None

def get_workflow_detector() -> WorkflowDetector:
    """Get or create global workflow detector"""
    global _detector
    if _detector is None:
        _detector = WorkflowDetector()
    return _detector