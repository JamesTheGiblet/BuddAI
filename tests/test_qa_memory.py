import unittest
import sqlite3
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add repo root to path
REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from buddai_executive import BuddAI
import core.buddai_shared

class TestQAMemory(unittest.TestCase):
    def setUp(self):
        # Create temp DB
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.db_fd)
        self.db_path_obj = Path(self.db_path)
        
        # Patch DB paths to use our temp DB
        self.patches = [
            patch('buddai_executive.DB_PATH', self.db_path_obj),
            patch('core.buddai_shared.DB_PATH', self.db_path_obj),
            patch('core.buddai_storage.DB_PATH', self.db_path_obj),
            patch('builtins.print') # Suppress print output
        ]
        for p in self.patches:
            p.start()
            
        # Initialize DB tables
        conn = sqlite3.connect(self.db_path)
        conn.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, session_id TEXT, role TEXT, content TEXT, timestamp TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS qa_memory (id INTEGER PRIMARY KEY, question TEXT, answer TEXT, timestamp TEXT, tags TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS feedback (message_id INTEGER, positive BOOLEAN, comment TEXT, timestamp TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS sessions (session_id TEXT PRIMARY KEY, user_id TEXT, started_at TEXT, title TEXT)")
        conn.commit()
        conn.close()

        # Initialize BuddAI with mocked dependencies
        with patch('core.buddai_llm.OllamaClient'), \
             patch('core.buddai_knowledge.RepoManager'), \
             patch('core.buddai_personality.PersonalityManager'):
            self.buddai = BuddAI(db_path=self.db_path)

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_index_good_response(self):
        """Test that index_good_response correctly saves Q&A pairs"""
        # Setup conversation history in DB
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        session_id = "sess_1"
        
        # User question
        cursor.execute("INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)", 
                      (session_id, "user", "How do I use PWM on ESP32?"))
        q_id = cursor.lastrowid
        
        # Assistant answer
        cursor.execute("INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)", 
                      (session_id, "assistant", "Use ledcSetup and ledcWrite."))
        a_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        # Run indexing
        self.buddai.index_good_response(a_id)
        
        # Verify data in qa_memory
        conn = sqlite3.connect(self.db_path)
        row = conn.execute("SELECT question, answer FROM qa_memory").fetchone()
        conn.close()
        
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "How do I use PWM on ESP32?")
        self.assertEqual(row[1], "Use ledcSetup and ledcWrite.")

    def test_retrieve_relevant_qa(self):
        """Test retrieval of relevant past solutions"""
        # Insert mock QA data
        conn = sqlite3.connect(self.db_path)
        conn.execute("INSERT INTO qa_memory (question, answer) VALUES (?, ?)", 
                    ("How to blink LED?", "Use digitalWrite(pin, HIGH)"))
        conn.commit()
        conn.close()
        
        # Retrieve using keywords
        context = self.buddai.retrieve_relevant_qa("I want to blink an LED")
        
        self.assertIn("RELEVANT PAST SOLUTIONS", context)
        self.assertIn("How to blink LED?", context)
        self.assertIn("Use digitalWrite", context)

    def test_retrieve_no_match(self):
        """Test retrieval with no matching keywords"""
        context = self.buddai.retrieve_relevant_qa("Something completely different")
        self.assertEqual(context, "")

    def test_record_feedback_indexes_positive(self):
        """Test that positive feedback triggers indexing"""
        with patch.object(self.buddai, 'index_good_response') as mock_index:
            self.buddai.record_feedback(123, True)
            mock_index.assert_called_with(123)

    def test_remember_command(self):
        """Test /remember command manually indexes last response"""
        self.buddai.last_generated_id = 55
        
        with patch.object(self.buddai, 'index_good_response') as mock_index:
            response = self.buddai.handle_slash_command("/remember")
            
            self.assertIn("indexed", response)
            mock_index.assert_called_with(55)

    def test_remember_command_no_history(self):
        """Test /remember command when no history exists"""
        self.buddai.last_generated_id = None
        response = self.buddai.handle_slash_command("/remember")
        self.assertIn("No recent response", response)

    def test_stuck_command(self):
        """Test /stuck command output"""
        response = self.buddai.handle_slash_command("/stuck")
        self.assertIn("Stuck? Here are some tools", response)
        self.assertIn("wiki <term>", response)

if __name__ == '__main__':
    unittest.main()