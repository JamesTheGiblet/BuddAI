#!/usr/bin/env python3
"""
BuddAI Q&A Expectation Test
Verifies that specific questions yield expected results.
"""

import unittest
import sys
import os
import tempfile
import sqlite3
from unittest.mock import patch

# Ensure parent dir is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from buddai_executive import BuddAI

class TestBuddAIExpectations(unittest.TestCase):
    def setUp(self):
        # Create temp DB to avoid polluting production data
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.db_fd)
        
        # Initialize AI with a specific user ID for testing
        self.ai = BuddAI(user_id="test_user", server_mode=False, db_path=self.db_path)
        
        # Initialize DB tables to prevent "no such table" errors
        conn = sqlite3.connect(self.db_path)
        conn.execute("CREATE TABLE IF NOT EXISTS code_rules (rule_text TEXT, pattern_find TEXT, pattern_replace TEXT, confidence REAL, learned_from TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS repo_index (id INTEGER PRIMARY KEY, user_id TEXT, file_path TEXT, repo_name TEXT, function_name TEXT, content TEXT, last_modified TIMESTAMP)")
        conn.execute("CREATE TABLE IF NOT EXISTS style_preferences (user_id TEXT, category TEXT, preference TEXT, confidence REAL, extracted_at TEXT)")
        conn.commit()
        conn.close()

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.unlink(self.db_path)
            except PermissionError:
                pass

    def test_qa_scenarios(self):
        """Run Q&A scenarios and verify results against expectations"""
        
        # Define scenarios: (Input, Expected String or Intent Type)
        scenarios = [
            # Command checks
            ("/status", "System Status"),
            ("/status", "test_user"),  # Verify user ID appears in status
            ("/skills", "Active Skills"),
            ("/help", "Available Commands"),
            
            # Intent checks (Personality Engine)
            ("Hello BuddAI", "greeting"),
            ("I want to build a robot", "idea_exploration"),
            
            # Logic checks (Mocked LLM response)
            ("What is the capital of France?", "Paris") 
        ]
        
        print(f"\n🧪 Testing {len(scenarios)} Q&A scenarios...")

        # Mock the LLM to return a predictable response for the logic check
        def mock_llm_response(model, messages, stream=False, **kwargs):
            # Helper to get text from messages
            prompt_text = ""
            if isinstance(messages, list):
                for m in messages:
                    prompt_text += str(m.get('content', ''))
            else:
                prompt_text = str(messages)
                
            # 1. Intent Detection (Heuristic: Prompt asks for JSON or intent)
            if "JSON" in prompt_text or "intent" in prompt_text.lower():
                if "Hello BuddAI" in prompt_text:
                    return '{"type": "greeting", "confidence": 0.95}'
                if "build a robot" in prompt_text:
                    return '{"type": "idea_exploration", "confidence": 0.95}'
                return '{"type": "unknown", "confidence": 0.0}'
                
            # 2. General Chat Response
            if "France" in prompt_text:
                return "The capital of France is Paris."
            return "I am operational."

        # Apply the mock globally to catch Personality engine calls too
        with patch('core.buddai_llm.OllamaClient.query', side_effect=mock_llm_response):
            # Mock check_skills to prevent Wikipedia from hijacking logic tests, but keep registry for /skills command
            with patch.object(self.ai, 'check_skills', return_value=None):
                for question, expected in scenarios:
                    with self.subTest(question=question):
                        print(f"   Input: '{question}'")
                        
                        # Execute
                        if question.startswith("/"):
                            response = self.ai.handle_slash_command(question)
                        else:
                            response = self.ai.chat(question)
                        
                        # Check Intent (if expected is an intent type)
                        if expected in ['greeting', 'idea_exploration']:
                            if hasattr(response, 'intent') and response.intent:
                                self.assertEqual(response.intent['type'], expected)
                                print(f"      ✅ Intent matched: {expected}")
                                continue
                        
                        # Check Content
                        self.assertIn(expected, str(response))
                        print(f"      ✅ Content matched: '{expected}'")

if __name__ == '__main__':
    unittest.main(verbosity=2)