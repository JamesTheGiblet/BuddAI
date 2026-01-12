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
from unittest.mock import patch, MagicMock, mock_open
import urllib.request

# Add repo root to path
REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
import buddai_executive
import core.buddai_shared
BuddAI = buddai_executive.BuddAI

class TestExtendedFeatures(unittest.TestCase):
    def setUp(self):
        # Create temp DB
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.db_fd)
        self.db_path_obj = Path(self.db_path)
        
        # Patch DB paths in both executive and shared modules
        self.patches = [
            patch('buddai_executive.DB_PATH', self.db_path_obj),
            patch('core.buddai_shared.DB_PATH', self.db_path_obj),
            patch('builtins.print')
        ]
        
        for p in self.patches:
            p.start()
            
        # Initialize DB tables required for tests
        conn = sqlite3.connect(self.db_path)
        conn.execute("CREATE TABLE IF NOT EXISTS repo_index (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, file_path TEXT, repo_name TEXT, function_name TEXT, content TEXT, last_modified TIMESTAMP)")
        conn.execute("CREATE TABLE IF NOT EXISTS code_rules (rule_text TEXT, pattern_find TEXT, pattern_replace TEXT, confidence REAL, learned_from TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS style_preferences (user_id TEXT, category TEXT, preference TEXT, confidence REAL, extracted_at TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS compilation_log (id INTEGER PRIMARY KEY, timestamp TEXT, code TEXT, success BOOLEAN, errors TEXT, hardware TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS corrections (id INTEGER PRIMARY KEY, timestamp TEXT, original_code TEXT, corrected_code TEXT, reason TEXT, context TEXT, processed BOOLEAN)")
        conn.execute("CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY, message_id INTEGER, positive BOOLEAN, comment TEXT, timestamp TEXT)")
        conn.commit()
        conn.close()
        
        # Patch index_gists to prevent background thread from polluting DB or printing
        self.gist_patcher = patch('core.buddai_knowledge.RepoManager.index_gists')
        self.gist_patcher.start()
        
        # Initialize BuddAI
        self.buddai = BuddAI(server_mode=False, db_path=self.db_path_obj)

    def tearDown(self):
        self.gist_patcher.stop()
        for p in reversed(self.patches):
            p.stop()
        
        # Close connections if any (BuddAI might have opened some)
        if hasattr(self.buddai, 'storage') and hasattr(self.buddai.storage, 'conn'):
            try:
                self.buddai.storage.conn.close()
            except:
                pass
        
        # Force garbage collection to release file handles
        self.buddai = None
        import gc
        gc.collect()
        
        if os.path.exists(self.db_path):
            for _ in range(5):
                try:
                    os.unlink(self.db_path)
                    break
                except PermissionError:
                    import time
                    time.sleep(0.1)

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
        conn.execute("INSERT INTO style_preferences (user_id, category, preference, confidence, extracted_at) VALUES ('default', 'Naming', 'camelCase', 0.9, '2024-01-01')")
        conn.commit()
        conn.close()
        
        summary = self.buddai.get_style_summary()
        self.assertIn("Naming: camelCase", summary)

    # Test 25: Learned Rules Retrieval
    def test_learned_rules_retrieval(self):
        """Test retrieval of high-confidence rules"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("INSERT INTO code_rules (rule_text, pattern_find, pattern_replace, confidence, learned_from) VALUES ('Use const', 'int ', 'const int ', 0.85, 'manual')")
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

    # Test 31: Slash Command /personality
    def test_slash_command_personality(self):
        """Test /personality command"""
        # Create mock response
        with patch('urllib.request.urlopen') as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = b'{"meta": {"version": "4.5"}}'
            mock_response.status = 200
            mock_response.__enter__.return_value = mock_response
            mock_response.__exit__.return_value = None
            mock_urlopen.return_value = mock_response

            # JSON to be returned when reading personality.json
            valid_personality = json.dumps({"meta": {"version": "4.5"}, "identity": {"name": "BuddAI"}})

            # Mock open for writing AND reading (so PersonalityManager doesn't crash)
            with patch('builtins.open', mock_open(read_data=valid_personality)) as mock_file:
                # Mock PersonalityManager and others
                with patch('buddai_executive.PersonalityManager'), \
                     patch('buddai_executive.ConversationProtocol'), \
                     patch('buddai_executive.BuddAIPersonality'):
                    
                    res = self.buddai.handle_slash_command("/personality load http://test.com/p.json")
                    self.assertIn("updated and reloaded", res)

    def test_slash_command_personality_text(self):
        """Test /personality command with text file fallback"""
        with patch('urllib.request.urlopen') as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = b'# New Persona\nYou are a coding wizard.'
            mock_response.status = 200
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response

            valid_personality = json.dumps({"identity": {}})
            with patch('builtins.open', mock_open(read_data=valid_personality)):
                with patch('buddai_executive.PersonalityManager'), \
                     patch('buddai_executive.ConversationProtocol'), \
                     patch('buddai_executive.BuddAIPersonality'):
                    
                    res = self.buddai.handle_slash_command("/personality load http://test.com/p.txt")
                    self.assertIn("updated and reloaded", res)

    # Test 32: Slash Command /gists
    def test_slash_command_gists(self):
        """Test /gists command lists indexed gists"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO repo_index (user_id, file_path, repo_name, function_name, content, last_modified)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ("default", "https://gist.github.com/user/123", "Gist Memory", "my_gist.py", "print('hello')", "2024-01-01T12:00:00"))
        conn.commit()
        conn.close()
        
        resp = self.buddai.handle_slash_command("/gists")
        self.assertIn("my_gist.py", resp)
        self.assertIn("https://gist.github.com/user/123", resp)

    # Test 33: Slash Command /train
    def test_slash_command_train(self):
        """Test /train command listing and execution"""
        # Mock registry
        self.buddai.training_registry = MagicMock()
        self.buddai.training_registry.list_strategies.return_value = {"test_strat": "Test Desc"}
        
        # Mock strategy
        mock_strat = MagicMock()
        mock_strat.run.return_value = "Strategy Ran"
        self.buddai.training_registry.get_strategy.side_effect = lambda x: mock_strat if x == "test_strat" else None

        # Test List
        res = self.buddai.handle_slash_command("/train")
        self.assertIn("test_strat", res)
        self.assertIn("Test Desc", res)

        # Test Run
        res = self.buddai.handle_slash_command("/train test_strat arg1")
        self.assertIn("Strategy Ran", res)
        mock_strat.run.assert_called_with(self.buddai, ["arg1"])

        # Test Unknown
        res = self.buddai.handle_slash_command("/train unknown")
        self.assertIn("Unknown training strategy", res)

    # Test 34: GistLoader Silent Mode
    def test_gist_loader_silent(self):
        """Test GistLoader silent mode suppresses output"""
        with patch('builtins.print') as mock_print:
            # Mock file existence to avoid actual file check printing if not silent
            with patch('pathlib.Path.exists', return_value=False):
                 self.buddai.repo_manager.index_gists(silent=True)
                 mock_print.assert_not_called()

    # Test 35: List Indexed Gists Empty
    def test_list_indexed_gists_empty(self):
        """Test listing gists when none exist"""
        # Ensure DB is empty for gists
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM repo_index WHERE repo_name = 'Gist Memory'")
        conn.commit()
        conn.close()
        
        gists = self.buddai.repo_manager.list_indexed_gists()
        self.assertEqual(gists, [])

    # Test 36: Retrieve Style Context No Keywords
    def test_retrieve_style_context_no_keywords(self):
        """Test style context retrieval with no keywords"""
        ctx = self.buddai.repo_manager.retrieve_style_context("hi", "Template {user_name}", "User")
        self.assertEqual(ctx, "")

    # Test 37: Retrieve Style Context With Keywords
    def test_retrieve_style_context_keywords(self):
        """Test style context retrieval with keywords"""
        # Insert mock data
        conn = sqlite3.connect(self.db_path)
        conn.execute("INSERT INTO repo_index (user_id, repo_name, function_name, content, last_modified) VALUES (?, ?, ?, ?, ?)",
                     ("default", "TestRepo", "test_func", "code content", "2024-01-01"))
        conn.commit()
        conn.close()
        
        ctx = self.buddai.repo_manager.retrieve_style_context("how does test_func work", "Template {user_name}", "User")
        self.assertIn("Template User", ctx)
        self.assertIn("test_func", ctx)

    # Test 38: Initiate Conversation
    def test_initiate_conversation(self):
        """Test conversation initiation"""
        with patch.object(self.buddai, 'call_model', return_value='"Hello User"'):
            self.buddai.initiate_conversation()
            # Check if message saved
            self.assertEqual(self.buddai.context_messages[-1]['role'], 'assistant')
            self.assertIn("Hello User", self.buddai.context_messages[-1]['content'])

    # Test 39: Slash Command /knowledge
    def test_slash_command_knowledge(self):
        """Test /knowledge command"""
        # Insert rule
        conn = sqlite3.connect(self.db_path)
        conn.execute("INSERT INTO code_rules (rule_text, learned_from) VALUES (?, ?)", ("Rule 1", "manual"))
        conn.commit()
        conn.close()
        
        res = self.buddai.handle_slash_command("/knowledge")
        self.assertIn("manual", res)
        self.assertIn("1 rules", res)

    # Test 40: Slash Command /fallback-stats
    def test_slash_command_fallback_stats(self):
        """Test /fallback-stats command"""
        with patch.object(self.buddai.metrics, 'get_fallback_stats', return_value={'total_escalations': 5, 'fallback_rate': 10, 'learning_success': 50}):
            res = self.buddai.handle_slash_command("/fallback-stats")
            self.assertIn("Total escalations: 5", res)

    # Test 41: Slash Command /skills
    def test_slash_command_skills(self):
        """Test /skills command"""
        self.buddai.skills_registry = {'test': {'name': 'Test Skill', 'description': 'Testing'}}
        res = self.buddai.handle_slash_command("/skills")
        self.assertIn("Test Skill", res)

    # Test 42: Slash Command /reload
    def test_slash_command_reload(self):
        """Test /reload command"""
        with patch('skills.load_registry', return_value={'new': 'skill'}):
            res = self.buddai.handle_slash_command("/reload")
            self.assertIn("Reloaded 1 skills", res)
            self.assertEqual(self.buddai.skills_registry, {'new': 'skill'})

    # Test 43: Slash Command /language list
    def test_slash_command_language_list(self):
        """Test /language list command"""
        with patch.object(self.buddai.language_registry, 'get_supported_languages', return_value=['python']):
            mock_skill = MagicMock()
            mock_skill.name = "Python"
            mock_skill.file_extensions = ['.py']
            with patch.object(self.buddai.language_registry, 'get_skill_by_name', return_value=mock_skill):
                res = self.buddai.handle_slash_command("/language list")
                self.assertIn("Python", res)
                self.assertIn(".py", res)

    # Test 44: Slash Command /language unknown
    def test_slash_command_language_unknown(self):
        """Test /language with unknown language"""
        with patch.object(self.buddai.language_registry, 'get_skill_by_name', return_value=None):
            res = self.buddai.handle_slash_command("/language unknown action")
            self.assertIn("not supported", res)

    # Test 45: Slash Command /language patterns
    def test_slash_command_language_patterns(self):
        """Test /language patterns command"""
        mock_skill = MagicMock()
        mock_skill.name = "Python"
        mock_skill.get_patterns.return_value = {'pat1': {'description': 'desc', 'example': 'ex'}}
        with patch.object(self.buddai.language_registry, 'get_skill_by_name', return_value=mock_skill):
            res = self.buddai.handle_slash_command("/language python patterns")
            self.assertIn("pat1", res)
            self.assertIn("desc", res)

    # Test 46: Slash Command /language practices
    def test_slash_command_language_practices(self):
        """Test /language practices command"""
        mock_skill = MagicMock()
        mock_skill.name = "Python"
        mock_skill.get_best_practices.return_value = ["Practice 1"]
        with patch.object(self.buddai.language_registry, 'get_skill_by_name', return_value=mock_skill):
            res = self.buddai.handle_slash_command("/language python practices")
            self.assertIn("Practice 1", res)

    # Test 47: Slash Command /language template
    def test_slash_command_language_template(self):
        """Test /language template command"""
        mock_skill = MagicMock()
        mock_skill.get_template.return_value = "def main(): pass"
        with patch.object(self.buddai.language_registry, 'get_skill_by_name', return_value=mock_skill):
            res = self.buddai.handle_slash_command("/language python template basic")
            self.assertIn("def main(): pass", res)

    # Test 48: Slash Command /language template missing
    def test_slash_command_language_template_missing(self):
        """Test /language template command with missing template"""
        mock_skill = MagicMock()
        mock_skill.get_template.return_value = None
        with patch.object(self.buddai.language_registry, 'get_skill_by_name', return_value=mock_skill):
            res = self.buddai.handle_slash_command("/language python template unknown")
            self.assertIn("not found", res)

    # Test 49: Slash Command /language invalid action
    def test_slash_command_language_invalid_action(self):
        """Test /language with invalid action"""
        mock_skill = MagicMock()
        with patch.object(self.buddai.language_registry, 'get_skill_by_name', return_value=mock_skill):
            res = self.buddai.handle_slash_command("/language python invalid")
            self.assertIn("Unknown action", res)

if __name__ == '__main__':
    unittest.main()