#!/usr/bin/env python3
"""
Additional coverage tests to reach 150+
"""
import unittest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

# Setup path
REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from buddai_executive import BuddAI

class TestExtendedCoverage2(unittest.TestCase):
    @patch('buddai_executive.OllamaClient')
    @patch('buddai_executive.StorageManager')
    @patch('buddai_executive.RepoManager')
    def setUp(self, MockRepo, MockStorage, MockOllama):
        with patch('builtins.print'):
            self.ai = BuddAI(user_id="test_ext_2", server_mode=True)
        self.ai.llm = MockOllama()
        self.ai.storage = MockStorage()
        self.ai.storage.current_session_id = "test_session"

    def test_executive_reset_gpu(self):
        self.ai.reset_gpu()
        self.ai.llm.reset_gpu.assert_called_once()

    def test_executive_get_sessions(self):
        self.ai.storage.get_sessions.return_value = [{"id": "1", "title": "test"}]
        sessions = self.ai.get_sessions()
        self.assertEqual(len(sessions), 1)
        self.ai.storage.get_sessions.assert_called_with(20)

    def test_executive_rename_session(self):
        self.ai.rename_session("1", "new_title")
        self.ai.storage.rename_session.assert_called_with("1", "new_title")

    def test_executive_delete_session(self):
        self.ai.delete_session("1")
        self.ai.storage.delete_session.assert_called_with("1")

    def test_executive_clear_current_session(self):
        self.ai.context_messages = ["msg"]
        self.ai.clear_current_session()
        self.ai.storage.clear_current_session.assert_called_once()
        self.assertEqual(self.ai.context_messages, [])

    def test_executive_load_session(self):
        self.ai.storage.load_session.return_value = [{"role": "user", "content": "hi"}]
        msgs = self.ai.load_session("1")
        self.assertEqual(len(msgs), 1)
        self.assertEqual(self.ai.context_messages, msgs)

    def test_executive_start_new_session(self):
        self.ai.storage.current_session_id = "new_id"
        sid = self.ai.start_new_session()
        self.ai.storage.start_new_session.assert_called_once()
        self.assertEqual(sid, "new_id")
        self.assertEqual(self.ai.context_messages, [])

    def test_executive_get_session_export_data(self):
        # Mock DB for this method since it uses direct sqlite
        with patch('sqlite3.connect') as mock_connect:
            mock_cursor = MagicMock()
            mock_connect.return_value.cursor.return_value = mock_cursor
            mock_cursor.fetchall.return_value = [("user", "hi", "2023-01-01")]
            
            data = self.ai.get_session_export_data("sess_1")
            self.assertEqual(data["session_id"], "sess_1")
            self.assertEqual(len(data["messages"]), 1)

    def test_executive_import_session_json_valid(self):
        data = {
            "session_id": "sess_import",
            "messages": [{"role": "user", "content": "hi"}]
        }
        with patch('sqlite3.connect') as mock_connect:
            mock_cursor = MagicMock()
            mock_connect.return_value.cursor.return_value = mock_cursor
            # Mock session check (not exists)
            mock_cursor.fetchone.return_value = None
            
            sid = self.ai.import_session_from_json(data)
            self.assertEqual(sid, "sess_import")

    def test_executive_import_session_json_invalid(self):
        with self.assertRaises(ValueError):
            self.ai.import_session_from_json({})

    def test_executive_slash_backup_failure(self):
        self.ai.storage.create_backup.return_value = (False, "Error")
        res = self.ai.handle_slash_command("/backup")
        self.assertIn("Backup failed", res)

    def test_executive_slash_rules_empty(self):
        with patch('sqlite3.connect') as mock_connect:
            mock_cursor = MagicMock()
            mock_connect.return_value.cursor.return_value = mock_cursor
            mock_cursor.fetchall.return_value = []
            
            res = self.ai.handle_slash_command("/rules")
            self.assertIn("No rules learned", res)

    def test_executive_slash_skills_empty(self):
        self.ai.skills_registry = {}
        res = self.ai.handle_slash_command("/skills")
        self.assertIn("No skills loaded", res)

    def test_executive_slash_skills_list(self):
        self.ai.skills_registry = {"calc": {"name": "Calculator", "description": "Math"}}
        res = self.ai.handle_slash_command("/skills")
        self.assertIn("Calculator", res)

    def test_executive_slash_teach_empty(self):
        res = self.ai.handle_slash_command("/teach")
        self.assertIn("Usage:", res)

    def test_executive_slash_correct_empty(self):
        self.ai.context_messages = []
        res = self.ai.handle_slash_command("/correct wrong")
        self.assertIn("No recent message", res)

    def test_executive_slash_learn_empty(self):
        with patch.object(self.ai.learner, 'analyze_corrections', return_value=[]):
            res = self.ai.handle_slash_command("/learn")
            self.assertIn("No new patterns", res)

    def test_executive_slash_debug_content(self):
        self.ai.last_prompt_debug = "debug info"
        res = self.ai.handle_slash_command("/debug")
        self.assertIn("debug info", res)

if __name__ == '__main__':
    unittest.main()