"""
Tests for Workflow Detector
"""

import unittest
from workflows.workflow_base import Workflow, WorkflowStep
from workflows.workflow_detector import WorkflowDetector, get_workflow_detector

class MockWorkflow(Workflow):
    """Mock workflow for testing"""
    
    def detect(self, user_input: str) -> float:
        if 'mock' in user_input.lower():
            return 0.9
        return 0.0
    
    def plan(self, user_input: str, context: dict = None):
        self.add_step('step1', 'Test step', 'test_action')
        return self.steps
    
    def _execute_step(self, step: WorkflowStep, context: dict):
        return {'result': 'success'}


class TestWorkflowDetector(unittest.TestCase):
    
    def setUp(self):
        """Create detector instance"""
        self.detector = WorkflowDetector()
    
    def test_initialization(self):
        """Test detector initializes"""
        self.assertIsNotNone(self.detector)
        self.assertIsInstance(self.detector.workflows, list)
    
    def test_detection_patterns_loaded(self):
        """Test detection patterns are loaded"""
        patterns = self.detector.detection_patterns
        
        self.assertGreater(len(patterns), 0)
        self.assertIn('create_project', patterns)
        self.assertIn('fix_bug', patterns)
        self.assertIn('add_feature', patterns)
    
    def test_detect_create_project(self):
        """Test detecting create project intent"""
        result = self.detector.detect_intent('create a new project')
        
        self.assertEqual(result['intent'], 'create_project')
        self.assertGreater(result['confidence'], 0.5)
    
    def test_detect_fix_bug(self):
        """Test detecting fix bug intent"""
        result = self.detector.detect_intent('fix this bug in the motor code')
        
        self.assertEqual(result['intent'], 'fix_bug')
        self.assertGreater(result['confidence'], 0.5)
    
    def test_detect_add_feature(self):
        """Test detecting add feature intent"""
        result = self.detector.detect_intent('I want to add WiFi support')
        
        self.assertEqual(result['intent'], 'add_feature')
        self.assertGreater(result['confidence'], 0.3)
    
    def test_detect_generate_docs(self):
        """Test detecting generate docs intent"""
        result = self.detector.detect_intent('generate documentation for this project')
        
        self.assertEqual(result['intent'], 'generate_docs')
        self.assertGreater(result['confidence'], 0.5)
    
    def test_detect_write_tests(self):
        """Test detecting write tests intent"""
        result = self.detector.detect_intent('write unit tests for this code')
        
        self.assertEqual(result['intent'], 'write_tests')
        self.assertGreater(result['confidence'], 0.5)
    
    def test_detect_review_code(self):
        """Test detecting review code intent"""
        result = self.detector.detect_intent('review this code please')
        
        self.assertEqual(result['intent'], 'review_code')
        self.assertGreater(result['confidence'], 0.5)
    
    def test_detect_unknown_intent(self):
        """Test unknown intent returns low confidence"""
        result = self.detector.detect_intent('xyz abc completely random')
        
        self.assertEqual(result['intent'], 'unknown')
        self.assertEqual(result['confidence'], 0.0)
    
    def test_register_workflow(self):
        """Test registering a workflow"""
        workflow = MockWorkflow('mock', 'Mock workflow')
        self.detector.register_workflow(workflow)
        
        self.assertIn(workflow, self.detector.workflows)
    
    def test_route_to_workflow(self):
        """Test routing to workflow"""
        workflow = MockWorkflow('mock', 'Mock workflow')
        self.detector.register_workflow(workflow)
        
        result = self.detector.route_to_workflow('run mock workflow')
        
        self.assertIsNotNone(result)
        self.assertEqual(result[0].name, 'mock')
    
    def test_get_supported_intents(self):
        """Test getting supported intents"""
        intents = self.detector.get_supported_intents()
        
        self.assertGreater(len(intents), 0)
        self.assertIn('create_project', intents)
    
    def test_get_intent_examples(self):
        """Test getting intent examples"""
        examples = self.detector.get_intent_examples('create_project')
        
        self.assertGreater(len(examples), 0)
        self.assertTrue(any('create' in ex for ex in examples))
    
    def test_global_detector_singleton(self):
        """Test global detector is singleton"""
        detector1 = get_workflow_detector()
        detector2 = get_workflow_detector()
        
        self.assertIs(detector1, detector2)

if __name__ == '__main__':
    unittest.main()