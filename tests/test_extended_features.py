#!/usr/bin/env python3
"""
Extended Feature Tests for BuddAI
Adds 15 additional tests to reach the target of 30.
"""

import unittest
import sys
import os
import tempfile
import sqlite3
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import importlib.util

# Dynamic import setup
REPO_ROOT = Path(__file__).parent.parent
MODULE_PATH = REPO_ROOT / "buddai_executive.py"
spec = importlib.util.spec_from_file_location("buddai_executive", MODULE_PATH)
buddai_module = importlib.util.module_from_spec(spec)
sys.modules["buddai_executive"] = buddai_module
spec.loader.exec_module(buddai_module)
BuddAI = buddai_module.BuddAI

class TestExtendedFeatures(unittest.TestCase):
    def setUp(self):
        # Create temp DB
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.db_fd)
        self.db_path_obj = Path(self.db_path)
        
        # Manual Patch of the imported module's DB_PATH
        self.original_db_path = buddai_module.DB_PATH
        buddai_module.DB_PATH = self.db_path_obj
        
        # Suppress prints
        self.print_patcher = patch("builtins.print")
        self.print_patcher.start()
        
        # Initialize BuddAI
        self.buddai = BuddAI(server_mode=False)

    def tearDown(self):
        # Restore DB_PATH
        buddai_module.DB_PATH = self.original_db_path
        self.print_patcher.stop()
        try:
            os.unlink(self.db_path)
        except:
            pass

    # Test 16: Personality Forge Config
    def test_personality_forge_config(self):
        """Verify Forge Theory constants are loaded from personality"""
        k = self.buddai.personality_manager.get_value("forge_theory.constants.aggressive.value")
        self.assertEqual(k, 0.3, "Forge Theory Aggressive K should be 0.3")

    # Test 17: Extended Hardware Detection
    def test_hardware_detection_extended(self):
        """Ensure hardware detection delegates to profile"""
        with patch.object(self.buddai.hardware_profile, 'detect_hardware', return_value="MockHW"):
            res = self.buddai.detect_hardware("msg")
            self.assertEqual(res, "MockHW")

    # Test 18: Slash Command /teach
    def test_slash_command_teach(self):
        """Test /teach command saves rule to DB"""
        # Init table
        conn = sqlite3.connect(self.db_path)
        conn.execute("CREATE TABLE IF NOT EXISTS code_rules (rule_text TEXT, pattern_find TEXT, pattern_replace TEXT, confidence REAL, learned_from TEXT)")
        conn.commit()
        conn.close()
        
        resp = self.buddai.handle_slash_command("/teach Always use camelCase")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT rule_text FROM code_rules")
        row = cursor.fetchone()
        conn.close()
        
        self.assertIn("Learned rule", resp)
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "Always use camelCase")

    # Test 19: Slash Command /metrics
    def test_slash_command_metrics(self):
        """Test /metrics command output"""
        with patch.object(self.buddai.metrics, 'calculate_accuracy', return_value={'accuracy': 95.5, 'correction_rate': 5.0, 'improvement': '+10%'}):
            resp = self.buddai.handle_slash_command("/metrics")
            self.assertIn("95.5%", resp)

    # Test 20: Slash Command /status
    def test_slash_command_status(self):
        """Test /status command output"""
        resp = self.buddai.handle_slash_command("/status")
        self.assertIn("System Status", resp)
        self.assertIn("Session", resp)

    # Test 21: Clear Session
    def test_clear_session(self):
        """Test clearing context messages"""
        self.buddai.context_messages = [{"role": "user", "content": "hi"}]
        self.buddai.clear_current_session()
        self.assertEqual(len(self.buddai.context_messages), 0)

    # Test 22: GPU Reset
    def test_gpu_reset(self):
        """Test GPU reset delegation"""
        with patch.object(self.buddai.llm, 'reset_gpu', return_value="GPU Reset"):
            res = self.buddai.reset_gpu()
            self.assertEqual(res, "GPU Reset")

    # Test 23: Get Recent Context
    def test_get_recent_context_json(self):
        """Test context retrieval as JSON"""
        self.buddai.context_messages = [{"role": "user", "content": "test"}]
        ctx = self.buddai.get_recent_context(limit=1)
        self.assertIsInstance(ctx, str)
        self.assertIn('"content": "test"', ctx)

    # Test 24: Style Summary
    def test_style_summary(self):
        """Test retrieval of style preferences from DB"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("CREATE TABLE IF NOT EXISTS style_preferences (category TEXT, preference TEXT, confidence REAL)")
        conn.execute("INSERT INTO style_preferences VALUES ('Naming', 'camelCase', 0.9)")
        conn.commit()
        conn.close()
        
        summary = self.buddai.get_style_summary()
        self.assertIn("Naming: camelCase", summary)

    # Test 25: Learned Rules Retrieval
    def test_learned_rules_retrieval(self):
        """Test retrieval of high-confidence rules"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("CREATE TABLE IF NOT EXISTS code_rules (rule_text TEXT, pattern_find TEXT, pattern_replace TEXT, confidence REAL)")
        conn.execute("INSERT INTO code_rules VALUES ('Use const', 'int ', 'const int ', 0.85)")
        conn.commit()
        conn.close()
        
        rules = self.buddai.get_learned_rules()
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0]['confidence'], 0.85)

    # Test 26: Log Compilation Result
    def test_log_compilation(self):
        """Test logging compilation results to DB"""
        self.buddai.log_compilation_result("void setup() {}", True, "")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT success FROM compilation_log")
        row = cursor.fetchone()
        conn.close()
        
        self.assertIsNotNone(row)
        self.assertEqual(row[0], 1)

    # Test 27: Save Correction
    def test_save_correction(self):
        """Test saving user corrections to DB"""
        self.buddai.save_correction("bad code", "good code", "syntax error")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT reason FROM corrections")
        row = cursor.fetchone()
        conn.close()
        
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "syntax error")

    # Test 28: Check Skills Trigger
    def test_check_skills_trigger(self):
        """Test skill triggering mechanism"""
        self.buddai.skills_registry = {
            "test_skill": {
                "triggers": ["magic word"],
                "name": "Magic",
                "run": lambda x: "Magic happened"
            }
        }
        
        res = self.buddai.check_skills("Please say the magic word now")
        self.assertEqual(res, "Magic happened")

    # Test 29: Apply Style Signature (Regex)
    def test_apply_style_signature_regex(self):
        """Test regex replacement based on learned rules"""
        with patch.object(self.buddai, 'get_learned_rules', return_value=[
            {'find': 'int pin', 'replace': 'const int pin', 'confidence': 0.99}
        ]):
            code = "void setup() { int pin = 5; }"
            new_code = self.buddai.apply_style_signature(code)
            self.assertIn("const int pin", new_code)

    # Test 30: Analyze Failure
    def test_analyze_failure(self):
        """Test failure analysis logic (DB read)"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, content TEXT)")
        conn.execute("INSERT INTO messages (id, content) VALUES (1, 'Failed code')")
        conn.commit()
        conn.close()
        
        # Should run without error
        try:
            self.buddai.analyze_failure(1)
        except Exception as e:
            self.fail(f"analyze_failure raised exception: {e}")

if __name__ == '__main__':
    unittest.main()