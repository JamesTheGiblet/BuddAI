import unittest
from unittest.mock import MagicMock, patch, ANY
import sys
import os
import json
import sqlite3
import tempfile

from buddai_executive import BuddAI

# Ensure parent dir is in path to import buddai_executive
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestV5Expansion(unittest.TestCase):
    """
    Expansion pack of 20 tests for BuddAI v5.0 features.
    Covers: Language commands, Shadow Engine, Feedback loops, Session management, and Project safeguards.
    """

    def setUp(self):
        # Create temp DB
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.db_fd)

        self.mock_storage = MagicMock()
        self.mock_personality = MagicMock()
        self.mock_project_memory = MagicMock()
        self.mock_llm = MagicMock()
        self.mock_repo_manager = MagicMock()
        self.mock_shadow = MagicMock()
        self.mock_learner = MagicMock()
        self.mock_validator = MagicMock()
        self.mock_language_registry = MagicMock()
        self.mock_hardware = MagicMock()
        self.mock_workflow = MagicMock()

        # Default mocks configuration
        self.mock_storage.current_session_id = "test_session"

        # Configure mock personality to return proper values
        def mock_get_value(key, default=None):
            value_map = {
                "identity.user_name": "Test User",
                "identity.ai_name": "BuddAI",
                "ai_fallback": {
                    "enabled": False,
                    "confidence_threshold": 70,
                    "fallback_models": []
                },
                "prompts.style_reference": "",
                "work_cycles.schedule_check_triggers": []
            }
            return value_map.get(key, default)

        self.mock_personality.get_value.side_effect = mock_get_value
        self.mock_workflow.detect_intent.return_value = {'intent': 'unknown', 'confidence': 0.0}

        # Patch all dependencies to isolate BuddAI logic
        patcher = patch.multiple('buddai_executive',
            StorageManager=MagicMock(return_value=self.mock_storage),
            PersonalityManager=MagicMock(return_value=self.mock_personality),
            get_project_memory=MagicMock(return_value=self.mock_project_memory),
            OllamaClient=MagicMock(return_value=self.mock_llm),
            RepoManager=MagicMock(return_value=self.mock_repo_manager),
            ShadowSuggestionEngine=MagicMock(return_value=self.mock_shadow),
            SmartLearner=MagicMock(return_value=self.mock_learner),
            ValidatorRegistry=MagicMock(return_value=self.mock_validator),
            get_language_registry=MagicMock(return_value=self.mock_language_registry),
            load_registry=MagicMock(return_value={}),
            HardwareProfile=MagicMock(return_value=self.mock_hardware),
            WorkflowDetector=MagicMock(return_value=self.mock_workflow),
            LearningMetrics=MagicMock(),
            ConfidenceScorer=MagicMock(),
            FallbackClient=MagicMock(),
            ConversationProtocol=MagicMock(),
            ModelFineTuner=MagicMock(),
            PromptEngine=MagicMock(),
            BuddAIPersonality=MagicMock()
        )
        self.addCleanup(patcher.stop)
        patcher.start()

        # Suppress print statements during initialization
        with patch('builtins.print'):
            self.buddai = BuddAI(user_id="test", server_mode=True, db_path=self.db_path)

        # Initialize DB tables
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS code_rules (rule_text TEXT, pattern_find TEXT, pattern_replace TEXT, confidence REAL, learned_from TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS style_preferences (user_id TEXT, category TEXT, preference TEXT, confidence REAL, extracted_at TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS feedback (message_id TEXT, positive BOOLEAN, comment TEXT, timestamp TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, session_id TEXT, role TEXT, content TEXT, timestamp TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS repo_index (user_id TEXT, content TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS sessions (session_id TEXT, user_id TEXT, started_at TEXT, title TEXT)")
        conn.commit()
        conn.close()

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.unlink(self.db_path)
            except PermissionError:
                pass

    def test_language_list(self):
        """1. Test /language list command"""
        self.mock_language_registry.get_supported_languages.return_value = ['python', 'cpp']
        mock_skill = MagicMock()
        mock_skill.name = "Python"
        mock_skill.file_extensions = ['.py']
        self.mock_language_registry.get_skill_by_name.return_value = mock_skill
        
        response = self.buddai._handle_language_command("/language list")
        self.assertIn("Supported Languages", response)
        self.assertIn("Python", response)

    def test_language_patterns(self):
        """2. Test /language <lang> patterns"""
        mock_skill = MagicMock()
        mock_skill.name = "Python"
        mock_skill.get_patterns.return_value = {"List Comp": {"description": "desc", "example": "code"}}
        self.mock_language_registry.get_skill_by_name.return_value = mock_skill
        
        response = self.buddai._handle_language_command("/language python patterns")
        self.assertIn("Python Patterns", response)
        self.assertIn("List Comp", response)

    def test_language_practices(self):
        """3. Test /language <lang> practices"""
        mock_skill = MagicMock()
        mock_skill.name = "Python"
        mock_skill.get_best_practices.return_value = ["Use snake_case"]
        self.mock_language_registry.get_skill_by_name.return_value = mock_skill
        
        response = self.buddai._handle_language_command("/language python practices")
        self.assertIn("Best Practices", response)
        self.assertIn("Use snake_case", response)

    def test_language_template(self):
        """4. Test /language <lang> template <name>"""
        mock_skill = MagicMock()
        mock_skill.get_template.return_value = "print('hello')"
        self.mock_language_registry.get_skill_by_name.return_value = mock_skill
        
        response = self.buddai._handle_language_command("/language python template basic")
        self.assertIn("print('hello')", response)

    def test_language_invalid_action(self):
        """5. Test invalid language action"""
        self.mock_language_registry.get_skill_by_name.return_value = MagicMock()
        response = self.buddai._handle_language_command("/language python unknown")
        self.assertIn("Unknown action", response)

    def test_shadow_suggestions_integration(self):
        """6. Test that shadow suggestions are appended to chat response"""
        self.mock_shadow.get_all_suggestions.return_value = ["Did you mean X?"]
    
        # Mock call_model to return string
        self.buddai.call_model = MagicMock(return_value="Hello")
    
        # Ensure hardware profile returns string instead of mock
        self.mock_hardware.apply_hardware_rules.side_effect = lambda code, *args: code

        # Mock extract_code to avoid TypeError with MagicMock
        self.buddai.extract_code = MagicMock(return_value=[])

        # Mock personality intent
        self.buddai.personality.understand_intent = MagicMock(return_value={
            'type': 'unknown', 
            'confidence': 0.0
        })
    
        # Mock _extract_code_blocks
        self.buddai._extract_code_blocks = MagicMock(return_value=[])
    
        response = self.buddai.chat("Hi")
    
        # Verify shadow suggestions were added
        self.assertIn("PROACTIVE", str(response))
        self.assertIn("Did you mean X?", str(response))

    def test_initiate_conversation(self):
        """7. Test conversation initiation calls fast model"""
        self.buddai.call_model = MagicMock(return_value="Hello there")
        with patch('builtins.print'):
            self.buddai.initiate_conversation()
        
        self.buddai.call_model.assert_called_with(
            "fast", ANY, system_task=True, hardware_override="Conversational"
        )

    def test_scan_style_no_index(self):
        """8. Test style scan with no indexed code"""
        # DB is empty by default
        with patch('builtins.print') as mock_print:
            self.buddai.scan_style_signature()
            mock_print.assert_any_call("❌ No code indexed. Run /index first.")

    def test_scan_style_with_index(self):
        """9. Test style scan with indexed code"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("INSERT INTO repo_index (user_id, content) VALUES (?, ?)", ("test", "code sample"))
        conn.commit()
        conn.close()
        
        self.buddai.call_model = MagicMock(return_value="Style: PEP8")
        
        with patch('builtins.print'):
            self.buddai.scan_style_signature()
        
        # Verify insert happened
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT preference FROM style_preferences")
        row = cursor.fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "PEP8")

    def test_record_feedback_positive(self):
        """10. Test recording positive feedback"""
        self.buddai.record_feedback(123, True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT positive FROM feedback WHERE message_id = ?", ("123",))
        row = cursor.fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], 1)

    def test_record_feedback_negative(self):
        """11. Test recording negative feedback triggers analysis"""
        self.buddai.analyze_failure = MagicMock()
        self.buddai.regenerate_response = MagicMock(return_value="Regenerated")
        
        result = self.buddai.record_feedback(123, False, "Bad code")
        
        self.buddai.analyze_failure.assert_called_with(123)
        self.assertEqual(result, "Regenerated")

    def test_regenerate_response_not_found(self):
        """12. Test regeneration when message ID not found"""
        result = self.buddai.regenerate_response(999)
        self.assertEqual(result, "Error: Message not found.")

    def test_regenerate_response_success(self):
        """13. Test successful regeneration"""
        # Insert initial message into temp DB
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO messages (id, session_id, role, content) VALUES (9, 'sess1', 'user', 'Make me a sandwich')")
        cursor.execute("INSERT INTO messages (id, session_id, role, content) VALUES (10, 'sess1', 'assistant', 'No')")
        conn.commit()
        conn.close()
        
        self.buddai.chat = MagicMock(return_value="Sandwich made")
        
        result = self.buddai.regenerate_response(10, "Make it tasty")
        
        self.buddai.chat.assert_called()
        args, _ = self.buddai.chat.call_args
        self.assertIn("Make me a sandwich", args[0])
        self.assertIn("Make it tasty", args[0])
        self.assertEqual(result, "Sandwich made")

    def test_cmd_close_project_none(self):
        """14. Test closing project when none open"""
        self.buddai.current_project = None
        with patch('builtins.print') as mock_print:
            self.buddai._cmd_close_project()
            mock_print.assert_called_with("No project currently open")

    def test_cmd_save_project_none(self):
        """15. Test saving project when none open"""
        self.buddai.current_project = None
        with patch('builtins.print') as mock_print:
            self.buddai._cmd_save_project()
            mock_print.assert_called_with("No project currently open")

    def test_cmd_timeline_none(self):
        """16. Test timeline when none open"""
        self.buddai.current_project = None
        with patch('builtins.print') as mock_print:
            self.buddai._cmd_show_timeline()
            mock_print.assert_called_with("No project currently open")

    def test_export_session_json_empty(self):
        """17. Test JSON export with empty session"""
        result = self.buddai.export_session_to_json("sess_empty")
        self.assertEqual(result, "No history found.")

    def test_import_session_json_valid(self):
        """18. Test valid JSON session import"""
        data = {
            "session_id": "sess_import",
            "messages": [{"role": "user", "content": "hi", "timestamp": "2026-01-01"}]
        }
        
        sid = self.buddai.import_session_from_json(data)
        self.assertEqual(sid, "sess_import")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM messages WHERE session_id = ?", ("sess_import",))
        count = cursor.fetchone()[0]
        conn.close()
        self.assertEqual(count, 1)

    def test_import_session_json_invalid(self):
        """19. Test invalid JSON import raises error"""
        data = {"foo": "bar"} # Missing session_id and messages
        with self.assertRaises(ValueError):
            self.buddai.import_session_from_json(data)

    def test_reset_gpu(self):
        """20. Test GPU reset delegation"""
        self.buddai.reset_gpu()
        self.mock_llm.reset_gpu.assert_called_once()

if __name__ == '__main__':
    unittest.main()