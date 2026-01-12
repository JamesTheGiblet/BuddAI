#!/usr/bin/env python3
"""
Additional Coverage Tests for BuddAI
Adds 16 tests to improve overall system coverage.
"""

import unittest
import sys
import os
import tempfile
import sqlite3
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import importlib.util

# Dynamic import setup
REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

MODULE_PATH = REPO_ROOT / "buddai_executive.py"
spec = importlib.util.spec_from_file_location("buddai_executive", MODULE_PATH)
buddai_module = importlib.util.module_from_spec(spec)
sys.modules["buddai_executive"] = buddai_module
spec.loader.exec_module(buddai_module)
BuddAI = buddai_module.BuddAI

class TestAdditionalCoverage(unittest.TestCase):
    def setUp(self):
        # Create temp DB
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.db_fd)
        self.db_path_obj = Path(self.db_path)
        
        # Patch DB_PATH
        self.db_patcher = patch.object(buddai_module, 'DB_PATH', self.db_path_obj)
        self.db_patcher.start()
        
        # Suppress prints
        self.print_patcher = patch("builtins.print")
        self.print_patcher.start()
        
        # Initialize BuddAI
        self.buddai = BuddAI(server_mode=False)
        
        # Create tables required for tests
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS repo_index (id INTEGER PRIMARY KEY, file_path TEXT, repo_name TEXT, function_name TEXT, content TEXT, last_modified TIMESTAMP, user_id TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, role TEXT, content TEXT, timestamp TIMESTAMP)")
        cursor.execute("CREATE TABLE IF NOT EXISTS code_rules (rule_text TEXT, confidence FLOAT, pattern_find TEXT, pattern_replace TEXT, learned_from TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS style_preferences (id INTEGER PRIMARY KEY, user_id TEXT, category TEXT, preference TEXT, confidence FLOAT, extracted_at TIMESTAMP)")
        conn.commit()
        conn.close()

    def tearDown(self):
        self.db_patcher.stop()
        self.print_patcher.stop()
        try:
            os.unlink(self.db_path)
        except:
            pass

    # Test 31: Welcome Message Formatting
    def test_welcome_message(self):
        """Test welcome message includes rule count"""
        with patch('sqlite3.connect') as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            mock_cursor.fetchone.return_value = [42]
            
            with patch('builtins.print') as mock_print:
                self.buddai.display_welcome_message()
                # Check if any print call contained '42'
                found = any('42' in str(call) for call in mock_print.call_args_list)
                self.assertTrue(found)

    # Test 32: Scan Style - No Index
    def test_scan_style_no_index(self):
        """Test scan_style_signature when no code is indexed"""
        with patch('sqlite3.connect') as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            mock_cursor.fetchall.return_value = []
            
            with patch('builtins.print') as mock_print:
                self.buddai.scan_style_signature()
                mock_print.assert_any_call("❌ No code indexed. Run /index first.")

    # Test 33: Scan Style - Execution
    def test_scan_style_execution(self):
        """Test successful style scan and DB insertion"""
        with patch('sqlite3.connect') as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            mock_cursor.fetchall.return_value = [("code sample",)]
            
            with patch.object(self.buddai, 'call_model', return_value="Naming: camelCase"):
                self.buddai.scan_style_signature()
                
                # Verify insertion
                insert_calls = [c for c in mock_cursor.execute.call_args_list if "INSERT INTO style_preferences" in c[0][0]]
                self.assertTrue(len(insert_calls) > 0)
                self.assertIn("camelCase", insert_calls[0][0][1])

    # Test 34: Get Applicable Rules Filtering
    def test_get_applicable_rules(self):
        """Test that only high-confidence rules are returned"""
        with patch('sqlite3.connect') as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            # Return one high confidence, one low
            mock_cursor.fetchall.return_value = [("Rule 1", 0.8), ("Rule 2", 0.4)]
            
            # The method itself filters in SQL usually, but let's verify the SQL query
            self.buddai.get_applicable_rules("msg")
            
            call_args = mock_cursor.execute.call_args[0][0]
            self.assertIn("confidence > 0.6", call_args)

    # Test 35: Teach Rule Persistence
    def test_teach_rule(self):
        """Test explicit rule teaching persistence"""
        with patch('sqlite3.connect') as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            
            # Fix: fetchone must return None to simulate "rule not found"
            mock_cursor.fetchone.return_value = None
            
            self.buddai.teach_rule("Always use const")
            
            # Verify insert was called (it might not be the very last call if commit/close happened)
            # We check all calls to execute
            all_calls = [str(call) for call in mock_cursor.execute.call_args_list]
            insert_called = any("INSERT INTO code_rules" in call for call in all_calls)
            
            self.assertTrue(insert_called, "INSERT statement was not executed")

    # Test 36: Regenerate - Invalid ID
    def test_regenerate_invalid_id(self):
        """Test regeneration with non-existent message ID"""
        with patch('sqlite3.connect') as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            mock_cursor.fetchone.return_value = None
            
            result = self.buddai.regenerate_response(999)
            self.assertEqual(result, "Error: Message not found.")

    # Test 37: Regenerate - Success Flow
    def test_regenerate_success(self):
        """Test successful regeneration flow"""
        with patch('sqlite3.connect') as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            # First fetch: session_id, current_id
            # Second fetch: user prompt
            mock_cursor.fetchone.side_effect = [("sess1", 10), ("User Prompt",)]
            
            with patch.object(self.buddai, 'chat', return_value="New Response") as mock_chat:
                result = self.buddai.regenerate_response(10, "Better comment")
                
                self.assertEqual(result, "New Response")
                mock_chat.assert_called()
                self.assertIn("Feedback: Better comment", mock_chat.call_args[0][0])

    # Test 38: Slash Command - Reload
    def test_slash_reload(self):
        """Test /reload command refreshes registry"""
        with patch.object(buddai_module, 'load_registry', return_value={'new': 'skill'}):
            res = self.buddai.handle_slash_command("/reload")
            self.assertIn("Reloaded 1 skills", res)
            self.assertEqual(self.buddai.skills_registry, {'new': 'skill'})

    # Test 39: Slash Command - Debug Empty
    def test_slash_debug_empty(self):
        """Test /debug when no prompt has been sent"""
        self.buddai.last_prompt_debug = None
        res = self.buddai.handle_slash_command("/debug")
        self.assertIn("No prompt sent yet", res)

    # Test 40: Slash Command - Validate No Context
    def test_slash_validate_no_context(self):
        """Test /validate with no history"""
        self.buddai.context_messages = []
        res = self.buddai.handle_slash_command("/validate")
        self.assertIn("No recent code", res)

    # Test 41: Slash Command - Validate No Code
    def test_slash_validate_no_code(self):
        """Test /validate when last message has no code"""
        self.buddai.context_messages = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "Hello there"}
        ]
        res = self.buddai.handle_slash_command("/validate")
        self.assertIn("No code blocks found", res)

    # Test 42: Import Session - Collision
    def test_import_session_collision(self):
        """Test importing session with ID collision generates new ID"""
        data = {
            "session_id": "sess1",
            "messages": [{"role": "user", "content": "hi"}]
        }
        
        with patch('sqlite3.connect') as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            # First check: returns row (collision)
            mock_cursor.fetchone.return_value = [1]
            
            new_id = self.buddai.import_session_from_json(data)
            
            self.assertNotEqual(new_id, "sess1")
            self.assertTrue("sess1_imp_" in new_id)

    # Test 43: Export Session to Markdown
    def test_export_markdown(self):
        """Test markdown export content generation"""
        with patch('sqlite3.connect') as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            mock_cursor.fetchall.return_value = [("user", "hi", "2025-01-01")]
            
            with patch('builtins.open', mock_open()) as mock_file:
                with patch('buddai_executive.DATA_DIR', Path('/tmp')):
                    res = self.buddai.export_session_to_markdown("sess1")
                    
                    self.assertIn("exported to", res)
                    handle = mock_file()
                    handle.write.assert_any_call("# BuddAI Session: sess1\n\n")

    # Test 44: Backup Delegation
    def test_backup_delegation(self):
        """Test backup command delegates to storage manager"""
        with patch.object(self.buddai.storage, 'create_backup', return_value=(True, "path.db")):
            res = self.buddai.handle_slash_command("/backup")
            self.assertIn("backed up to: path.db", res)

    # Test 45: Metrics Delegation
    def test_metrics_delegation(self):
        """Test metrics command delegates to metrics component"""
        with patch.object(self.buddai.metrics, 'calculate_accuracy', return_value={'accuracy': 100, 'correction_rate': 0, 'improvement': '0'}):
            res = self.buddai.handle_slash_command("/metrics")
            self.assertIn("100.0%", res)

    # Test 46: Hardware Detection Flow
    def test_hardware_detection_flow(self):
        """Test chat flow updates hardware profile"""
        with patch.object(self.buddai.hardware_profile, 'detect_hardware', return_value="Arduino Uno"):
            with patch.object(self.buddai, '_route_request', return_value="Response"):
                self.buddai.chat("Use Arduino Uno")
                self.assertEqual(self.buddai.current_hardware, "Arduino Uno")

    # Test 47: General Discussion Detection
    def test_is_general_discussion(self):
        """Test detection of general discussion vs code requests"""
        # Discussion keywords present
        self.assertTrue(self.buddai._is_general_discussion("What is the difference between X and Y?"))
        # Code keywords present (should be False even if discussion keywords exist)
        self.assertFalse(self.buddai._is_general_discussion("Write code to replace the string"))
        # Neither
        self.assertFalse(self.buddai._is_general_discussion("Hello world"))

    # Test 48: Get Learned Rules - Empty
    def test_get_learned_rules_empty(self):
        """Test retrieving rules when none exist"""
        with patch('sqlite3.connect') as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            mock_cursor.fetchall.return_value = []
            
            rules = self.buddai.get_learned_rules()
            self.assertEqual(rules, [])

    # Test 49: Log Compilation Failure
    def test_log_compilation_failure(self):
        """Test logging a failed compilation"""
        with patch('sqlite3.connect') as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            
            self.buddai.log_compilation_result("bad code", False, "Syntax Error")
            
            # Verify insert
            call_args = mock_cursor.execute.call_args_list
            # Find the INSERT call
            insert_call = next(c for c in call_args if "INSERT INTO compilation_log" in c[0][0])
            params = insert_call[0][1]
            # success is at index 2 (0-based: timestamp, code, success, errors, hardware)
            self.assertEqual(params[2], False)
            self.assertEqual(params[3], "Syntax Error")

    # Test 50: Apply Style Signature - No Rules
    def test_apply_style_signature_no_rules(self):
        """Test style signature application with no rules"""
        with patch.object(self.buddai, 'get_learned_rules', return_value=[]):
            with patch.object(self.buddai.hardware_profile, 'apply_hardware_rules', side_effect=lambda c, h: c):
                code = "int x = 1;"
                result = self.buddai.apply_style_signature(code)
                self.assertEqual(result, code)

    # Test 51: Get Mode Note - No Schedule
    def test_get_mode_note_no_schedule(self):
        """Test getting mode note when no schedule is defined"""
        with patch.object(self.buddai.personality_manager, 'get_value', return_value=None):
            note = self.buddai._get_current_mode_note()
            self.assertIsNone(note)

if __name__ == '__main__':
    unittest.main()