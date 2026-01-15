import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add parent directory to path to import buddai_executive
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from buddai_executive import BuddAI

class TestPersonalRouting(unittest.TestCase):
    def setUp(self):
        # Mock dependencies to avoid loading full system
        self.mock_prompt_engine = MagicMock()
        self.mock_llm = MagicMock()
        
        # Patching dependencies inside BuddAI __init__
        with patch('buddai_executive.StorageManager'), \
             patch('buddai_executive.PersonalityManager'), \
             patch('buddai_executive.BuddAIPersonality'), \
             patch('buddai_executive.ShadowSuggestionEngine'), \
             patch('buddai_executive.SmartLearner'), \
             patch('buddai_executive.HardwareProfile'), \
             patch('buddai_executive.ValidatorRegistry'), \
             patch('buddai_executive.ConfidenceScorer'), \
             patch('buddai_executive.FallbackClient'), \
             patch('buddai_executive.AdaptiveLearner'), \
             patch('buddai_executive.LearningMetrics'), \
             patch('buddai_executive.get_training_registry'), \
             patch('buddai_executive.ModelFineTuner'), \
             patch('buddai_executive.ConversationProtocol'), \
             patch('buddai_executive.RepoManager'), \
             patch('buddai_executive.OllamaClient', return_value=self.mock_llm), \
             patch('buddai_executive.PromptEngine', return_value=self.mock_prompt_engine), \
             patch('buddai_executive.load_registry'), \
             patch('buddai_executive.get_language_registry'), \
             patch('buddai_executive.WorkflowDetector'), \
             patch('buddai_executive.get_project_memory'):
            
            self.ai = BuddAI(server_mode=False)
            
    def test_personal_question_routing(self):
        """Test that personal questions disable system_task mode"""
        # Setup
        question = "What's my current job?"
        self.mock_prompt_engine.is_simple_question.return_value = True
        self.mock_prompt_engine.is_complex.return_value = False
        self.ai.repo_manager.is_search_query.return_value = False
        self.ai.personality_engine.understand_intent.return_value = {'type': 'unknown', 'confidence': 0}
        self.ai.conversation_protocol.is_conversational.return_value = False
        self.ai._is_general_discussion = MagicMock(return_value=False)
        
        # Execute with spy on call_model
        with patch.object(self.ai, 'call_model') as mock_call_model:
            self.ai._route_request(question, force_model=None, forge_mode="2")
            
            # Verify system_task is False for personal questions
            mock_call_model.assert_called_with(
                "fast", 
                question, 
                system_task=False, 
                hardware_override="Conversational"
            )

    def test_impersonal_conceptual_question(self):
        """Test that impersonal conceptual questions use system_task mode"""
        question = "What is a servo motor?"
        self.mock_prompt_engine.is_simple_question.return_value = True
        self.mock_prompt_engine.is_complex.return_value = False
        self.ai.repo_manager.is_search_query.return_value = False
        self.ai.personality_engine.understand_intent.return_value = {'type': 'unknown', 'confidence': 0}
        self.ai.conversation_protocol.is_conversational.return_value = False
        self.ai._is_general_discussion = MagicMock(return_value=False)
        
        with patch.object(self.ai, 'call_model') as mock_call_model:
            self.ai._route_request(question, force_model=None, forge_mode="2")
            
            # Verify system_task is True for generic conceptual questions
            mock_call_model.assert_called_with(
                "fast", 
                question, 
                system_task=True, 
                hardware_override=None
            )

if __name__ == '__main__':
    unittest.main()