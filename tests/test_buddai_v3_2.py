#!/usr/bin/env python3
"""
Unit tests for BuddAI v3.2
Verifies type hints and core functionality including the new routing logic.
"""

import unittest
import sys
import importlib.util
from pathlib import Path
from typing import List, Dict, Optional
from unittest.mock import MagicMock, patch
from core.buddai_prompt_engine import PromptEngine

# Load buddai_v3.2.py dynamically due to version number in filename
REPO_ROOT = Path(__file__).parent.parent
MODULE_PATH = REPO_ROOT / "buddai_executive.py"

if not MODULE_PATH.exists():
    print(f"Error: Could not find {MODULE_PATH}")
    sys.exit(1)

spec = importlib.util.spec_from_file_location("buddai_executive", MODULE_PATH)
buddai_module = importlib.util.module_from_spec(spec)
sys.modules["buddai_executive"] = buddai_module
spec.loader.exec_module(buddai_module)

BuddAI = buddai_module.BuddAI

class TestBuddAITypesAndLogic(unittest.TestCase):
    
    def setUp(self):
        # Suppress print statements during tests
        self.original_stdout = sys.stdout
        sys.stdout = MagicMock()
        
        # Initialize BuddAI in non-server mode, mocking DB interactions
        with patch('sqlite3.connect') as mock_sql:
            # Mock mkdir to prevent creating directories during tests
            with patch('pathlib.Path.mkdir'):
                self.buddai = BuddAI(server_mode=False)
            self.mock_conn = mock_sql.return_value
            self.mock_cursor = self.mock_conn.cursor.return_value

    def tearDown(self):
        sys.stdout = self.original_stdout

    def test_method_annotations(self):
        """Verify type hints exist on key methods"""
        # chat
        chat_hints = BuddAI.chat.__annotations__
        self.assertEqual(chat_hints['user_message'], str)
        self.assertEqual(chat_hints['return'], str)
        
        # is_complex
        self.assertEqual(PromptEngine.is_complex.__annotations__['return'], bool)
        
        # extract_modules
        self.assertEqual(PromptEngine.extract_modules.__annotations__['return'], List[str])
        
        # build_modular_plan
        self.assertEqual(PromptEngine.build_modular_plan.__annotations__['return'], List[Dict[str, str]])

    def test_routing_simple_question(self):
        """Test that simple questions route to the FAST model"""
        with patch.object(self.buddai, 'call_model', return_value="Fast response") as mock_call:
            response = self.buddai._route_request("What is a servo?", force_model=None, forge_mode="2")
            
            mock_call.assert_called_with("fast", "What is a servo?", system_task=True, hardware_override=None)
            self.assertEqual(response, "Fast response")

    def test_routing_complex_request(self):
        """Test that complex requests route to modular build"""
        complex_msg = "Build a complete robot with servo and motor"
        
        with patch.object(self.buddai, 'execute_modular_build', return_value="Modular code") as mock_build:
            # Mock is_complex to ensure it returns True for this test case
            with patch.object(self.buddai.prompt_engine, 'is_complex', return_value=True):
                response = self.buddai._route_request(complex_msg, force_model=None, forge_mode="2")
                
                mock_build.assert_called()
                self.assertEqual(response, "Modular code")

    def test_routing_search_query(self):
        """Test that search queries route to repository search"""
        search_msg = "Show me functions using applyForge"
        
        with patch.object(self.buddai.repo_manager, 'search_repositories', return_value="Search results") as mock_search:
            # Mock is_search_query to ensure True
            with patch.object(self.buddai.repo_manager, 'is_search_query', return_value=True):
                # Ensure is_complex is False so it doesn't preempt search
                with patch.object(self.buddai.prompt_engine, 'is_complex', return_value=False):
                    response = self.buddai._route_request(search_msg, force_model=None, forge_mode="2")
                    
                    mock_search.assert_called_with(search_msg)
                    self.assertEqual(response, "Search results")

    def test_routing_forced_model(self):
        """Test that force_model overrides other logic"""
        with patch.object(self.buddai, 'call_model', return_value="Forced response") as mock_call:
            response = self.buddai._route_request("Complex build request", force_model="balanced", forge_mode="2")
            
            mock_call.assert_called_with("balanced", "Complex build request")
            self.assertEqual(response, "Forced response")

    def test_extract_modules(self):
        """Verify module extraction logic"""
        msg = "I need a robot with bluetooth and a flipper weapon"
        modules = self.buddai.prompt_engine.extract_modules(msg)
        self.assertIn("ble", modules)
        self.assertIn("servo", modules)
        self.assertNotIn("motor", modules)

if __name__ == '__main__':
    unittest.main()