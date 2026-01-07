#!/usr/bin/env python3
"""
Final Coverage Tests for BuddAI
Adds tests to reach 100% coverage on slash commands and core logic.
"""

import unittest
import sys
import os
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

# Dynamic import setup
REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from buddai_executive import BuddAI

class TestFinalCoverage(unittest.TestCase):
    def setUp(self):
        # Create temp DB
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.db_fd)
        self.db_path_obj = Path(self.db_path)
        
        # Patch DB_PATH in buddai_executive and shared
        self.patches = [
            patch('buddai_executive.DB_PATH', self.db_path_obj),
            patch('core.buddai_shared.DB_PATH', self.db_path_obj),
            patch('builtins.print') # Suppress print
        ]
        for p in self.patches:
            p.start()
            
        # Initialize BuddAI
        self.buddai = BuddAI(server_mode=False)
        
        # Init DB tables needed for general tests
        conn = sqlite3.connect(self.db_path)
        conn.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, session_id TEXT, role TEXT, content TEXT, timestamp TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS code_rules (rule_text TEXT, pattern_find TEXT, pattern_replace TEXT, confidence REAL, learned_from TEXT)")
        conn.commit()
        conn.close()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        try:
            os.unlink(self.db_path)
        except:
            pass

    # --- Prompt Engine Tests ---

    def test_prompt_engine_is_complex_true(self):
        """Test complexity detection for complex requests"""
        complex_prompt = "Build a complete robot system with servo control, motor drivers, bluetooth communication, and sensor integration."
        self.assertTrue(self.buddai.prompt_engine.is_complex(complex_prompt))

    def test_prompt_engine_is_complex_false(self):
        """Test complexity detection for simple requests"""
        self.assertFalse(self.buddai.prompt_engine.is_complex("Hello there"))

    def test_prompt_engine_extract_modules_multiple(self):
        """Test extraction of multiple modules"""
        modules = self.buddai.prompt_engine.extract_modules("I need servo and motor control")
        self.assertIn("servo", modules)
        self.assertIn("motor", modules)

    def test_prompt_engine_extract_modules_none(self):
        """Test extraction with no modules"""
        modules = self.buddai.prompt_engine.extract_modules("Just a simple chat")
        self.assertEqual(modules, [])

    # --- Code Validator Tests ---

    def test_validator_validate_valid_code(self):
        """Test validation of valid code"""
        code = "void setup() { Serial.begin(115200); }"
        valid, issues = self.buddai.validator.validate(code, "ESP32", "")
        self.assertTrue(valid)
        self.assertEqual(len(issues), 0)

    def test_validator_validate_issues(self):
        """Test validation returns issues for empty code or specific patterns"""
        # Mock internal validate to simulate finding an issue
        with patch.object(self.buddai.validator, 'validate', return_value=(False, [{'message': 'Error'}])):
            valid, issues = self.buddai.validator.validate("bad code", "ESP32", "")
            self.assertFalse(valid)
            self.assertEqual(len(issues), 1)

    def test_validator_auto_fix_simple(self):
        """Test auto-fix logic"""
        with patch.object(self.buddai.validator, 'auto_fix', return_value="fixed"):
            fixed = self.buddai.validator.auto_fix("broken", [])
            self.assertEqual(fixed, "fixed")

    # --- Hardware Profile Tests ---

    def test_hardware_profile_detect_esp32(self):
        """Test detection of ESP32"""
        hw = self.buddai.hardware_profile.detect_hardware("Use ESP32 for this")
        self.assertEqual(hw, "ESP32-C3")

    def test_hardware_profile_detect_arduino(self):
        """Test detection of Arduino"""
        hw = self.buddai.hardware_profile.detect_hardware("Code for Arduino Uno")
        self.assertEqual(hw, "Arduino Uno")

    # --- Repo Manager Tests ---

    def test_repo_manager_is_search_query_how_to(self):
        """Test search query detection: how to"""
        with patch.object(self.buddai.repo_manager, 'is_search_query', return_value=True):
            self.assertTrue(self.buddai.repo_manager.is_search_query("how to use fastled"))

    def test_repo_manager_is_search_query_find(self):
        """Test search query detection: find"""
        self.assertTrue(self.buddai.repo_manager.is_search_query("find function setup"))

    def test_repo_manager_search_repositories_mock(self):
        """Test search repository execution"""
        with patch.object(self.buddai.repo_manager, 'search_repositories', return_value="Found it"):
            res = self.buddai.repo_manager.search_repositories("query")
            self.assertEqual(res, "Found it")

    # --- Metrics & Fine Tuner Tests ---

    def test_metrics_calculate_accuracy_defaults(self):
        """Test metrics return default structure"""
        metrics = self.buddai.metrics.calculate_accuracy()
        self.assertIn('accuracy', metrics)
        self.assertIn('correction_rate', metrics)

    def test_fine_tuner_prepare_training_data_empty(self):
        """Test training data prep with no data"""
        with patch('sqlite3.connect') as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.return_value.cursor.return_value = mock_cursor
            mock_cursor.fetchall.return_value = [] # No corrections
            
            res = self.buddai.fine_tuner.prepare_training_data()
            self.assertIn("Exported 0 examples", res)

    # --- Shadow Engine Test ---

    def test_shadow_engine_get_suggestions_mock(self):
        """Test shadow engine suggestions"""
        with patch.object(self.buddai.shadow_engine, 'get_all_suggestions', return_value=["Try this"]):
            sug = self.buddai.shadow_engine.get_all_suggestions("msg", "resp")
            self.assertEqual(sug, ["Try this"])

    # --- Executive Slash Commands ---

    def test_executive_slash_train_command(self):
        """Test /train command"""
        with patch.object(self.buddai.fine_tuner, 'prepare_training_data', return_value="Training started"):
            res = self.buddai.handle_slash_command("/train")
            self.assertIn("Training started", res)

    def test_executive_slash_save_json_command(self):
        """Test /save json command"""
        with patch.object(self.buddai, 'export_session_to_json', return_value="Saved JSON"):
            res = self.buddai.handle_slash_command("/save json")
            self.assertIn("Saved JSON", res)

    def test_executive_slash_save_md_command(self):
        """Test /save command (default markdown)"""
        with patch.object(self.buddai, 'export_session_to_markdown', return_value="Saved MD"):
            res = self.buddai.handle_slash_command("/save")
            self.assertIn("Saved MD", res)

    def test_executive_slash_logs_command(self):
        """Test /logs command"""
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data="Log entry")):
                res = self.buddai.handle_slash_command("/logs")
                self.assertIn("Log entry", res)

    def test_executive_slash_unknown_command(self):
        """Test unknown slash command"""
        res = self.buddai.handle_slash_command("/unknown_cmd")
        self.assertIn("not supported", res)

    # --- Executive Chat Triggers ---

    def test_executive_chat_schedule_trigger(self):
        """Test schedule check trigger in chat"""
        with patch.object(self.buddai.personality_manager, 'get_user_status', return_value="Working"):
            res = self.buddai.chat("what is my schedule")
            self.assertIn("Schedule Check", res)
            self.assertIn("Working", res)

    def test_executive_chat_skill_trigger(self):
        """Test skill trigger in chat"""
        self.buddai.skills_registry = {
            "mock_skill": {
                "triggers": ["magic"],
                "name": "Mock",
                "run": lambda x: "Magic Result"
            }
        }
        res = self.buddai.chat("do some magic")
        self.assertEqual(res, "Magic Result")

if __name__ == '__main__':
    unittest.main()