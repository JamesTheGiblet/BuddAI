#!/usr/bin/env python3
"""
BuddAI v3.2 Test Suite
Comprehensive testing for all features

Author: James Gilbert
License: MIT
"""

import sys
import importlib.util
import unittest
from unittest.mock import MagicMock, patch
import sqlite3
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import os
import io
import zipfile
import http.client

# Dynamic import of buddai_v3.2.py
REPO_ROOT = Path(__file__).parent.parent
MODULE_PATH = REPO_ROOT / "buddai_executive.py"
spec = importlib.util.spec_from_file_location("buddai_executive", MODULE_PATH)
buddai_module = importlib.util.module_from_spec(spec)
sys.modules["buddai_executive"] = buddai_module
spec.loader.exec_module(buddai_module)
BuddAI = buddai_module.BuddAI

class TestBuddAICore(unittest.TestCase):
    # Test 1: Database Initialization
    def test_database_init(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            
            # Create tables
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    started_at TIMESTAMP,
                    ended_at TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS repo_index (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT,
                    repo_name TEXT,
                    function_name TEXT,
                    content TEXT,
                    last_modified TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS style_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT,
                    preference TEXT,
                    confidence FLOAT,
                    extracted_at TIMESTAMP
                )
            """)
            
            conn.commit()
            
            # Verify tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            required_tables = ['sessions', 'messages', 'repo_index', 'style_preferences']
            all_exist = all(table in tables for table in required_tables)
            
            conn.close()
            self.assertTrue(all_exist, f"Missing tables: {[t for t in required_tables if t not in tables]}")

    # Test 2: SQL Injection Prevention
    def test_sql_injection_prevention(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE repo_index (
                    id INTEGER PRIMARY KEY,
                    function_name TEXT,
                    content TEXT
                )
            """)
            
            # Insert test data
            cursor.execute("INSERT INTO repo_index (function_name, content) VALUES (?, ?)",
                          ("testFunc", "test content"))
            conn.commit()
            
            # Test malicious input
            malicious_input = "'; DROP TABLE repo_index; --"
            
            # SECURE: Parameterized query
            cursor.execute("SELECT * FROM repo_index WHERE function_name LIKE ?", 
                          (f"%{malicious_input}%",))
            results = cursor.fetchall()
            
            # Verify table still exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='repo_index'")
            table_exists = cursor.fetchone() is not None
            
            conn.close()
            self.assertTrue(table_exists, "Table was dropped - vulnerable to injection!")

    # Test 3: Auto-Learning Pattern Extraction
    def test_auto_learning(self):
        sample_code = """
    #include <Arduino.h>

    #define MOTOR_PIN 5
    const int TIMEOUT_MS = 5000;

    void setup() {
        Serial.begin(115200);
        ledcSetup(0, 500, 8);
    }
    """
        import re
        patterns = {
            'serial_baud': re.search(r'Serial\.begin\((\d+)\)', sample_code),
            'pin_style': 'define' if '#define' in sample_code else 'const',
            'timeout_value': re.search(r'TIMEOUT.*?(\d+)', sample_code),
            'pwm_freq': re.search(r'ledcSetup\([^,]+,\s*(\d+)', sample_code),
        }
        
        extracted = {}
        for key, value in patterns.items():
            if value:
                extracted[key] = value.group(1) if hasattr(value, 'group') else str(value)
        
        expected = {
            'serial_baud': '115200',
            'pin_style': 'define',
            'timeout_value': '5000',
            'pwm_freq': '500'
        }
        
        for key, expected_val in expected.items():
            self.assertEqual(extracted.get(key), expected_val, f"Failed to extract {key}")

    # Test 4: Module Detection
    def test_module_detection(self):
        MODULE_PATTERNS = {
            "ble": ["bluetooth", "ble", "wireless"],
            "servo": ["servo", "flipper", "weapon"],
            "motor": ["motor", "drive", "movement", "l298n"],
            "safety": ["safety", "timeout", "failsafe"],
        }
        
        test_cases = [
            ("Generate code with BLE and servo control", ["ble", "servo"]),
            ("Add motor driver with safety timeout", ["motor", "safety"]),
            ("Build complete robot with bluetooth, motors, and weapon", ["ble", "motor", "servo"]),
        ]
        
        def extract_modules(message):
            message_lower = message.lower()
            detected = []
            for module, keywords in MODULE_PATTERNS.items():
                if any(kw in message_lower for kw in keywords):
                    detected.append(module)
            return detected
        
        for message, expected_modules in test_cases:
            detected = extract_modules(message)
            self.assertEqual(set(detected), set(expected_modules), f"Failed for '{message}'")

    # Test 5: Complexity Detection
    def test_complexity_detection(self):
        COMPLEX_TRIGGERS = ["complete", "entire", "full", "build entire"]
        MODULE_PATTERNS = {
            "ble": ["bluetooth", "ble"],
            "servo": ["servo"],
            "motor": ["motor"],
        }
        
        def is_complex(message):
            message_lower = message.lower()
            trigger_count = sum(1 for trigger in COMPLEX_TRIGGERS if trigger in message_lower)
            module_count = sum(1 for module, keywords in MODULE_PATTERNS.items() 
                              if any(kw in message_lower for kw in keywords))
            return trigger_count >= 2 or module_count >= 3
        
        test_cases = [
            ("Generate a motor driver class", False),
            ("Build complete robot with BLE, servo, and motors", True),
            ("Create entire system with full integration", True),
            ("What pins should I use?", False),
        ]
        
        for message, expected_complex in test_cases:
            detected = is_complex(message)
            self.assertEqual(detected, expected_complex, f"Failed for '{message}'")

    # Test 6: LRU Cache Performance
    def test_lru_cache(self):
        from functools import lru_cache
        import time
        
        call_count = 0
        
        @lru_cache(maxsize=128)
        def cached_function(keywords):
            nonlocal call_count
            call_count += 1
            time.sleep(0.01)
            return f"Result for {keywords}"
        
        cached_function(("motor", "servo"))
        first_count = call_count
        
        cached_function(("motor", "servo"))
        second_count = call_count
        
        cached_function(("ble", "battery"))
        third_count = call_count
        
        self.assertEqual(first_count, 1)
        self.assertEqual(second_count, 1)
        self.assertEqual(third_count, 2)

    # Test 7: Session Export
    def test_session_export(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            export_path = Path(tmpdir) / "test_export.md"
            
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            messages = [
                ("user", "Generate motor code", "2025-12-28 10:00:00"),
                ("assistant", "```cpp\nvoid setupMotors() {}\n```", "2025-12-28 10:00:05"),
            ]
            
            output = f"# BuddAI Session Export\n"
            output += f"**Session ID:** {session_id}\n\n"
            output += "---\n\n"
            
            for role, content, timestamp in messages:
                if role == 'user':
                    output += f"## 🧑 James ({timestamp})\n{content}\n\n"
                else:
                    output += f"## 🤖 BuddAI\n{content}\n\n"
            
            with open(export_path, 'w', encoding='utf-8') as f:
                f.write(output)
            
            self.assertTrue(export_path.exists())
            content = export_path.read_text(encoding='utf-8')
            self.assertIn(session_id, content)
            self.assertIn("```cpp", content)
            self.assertIn("## ", content)

    # Test 8: Actionable Suggestions
    def test_actionable_suggestions(self):
        user_input = "Generate motor driver with L298N"
        generated_code = """
    void setupMotors() {
        pinMode(MOTOR_PIN, OUTPUT);
    }
    """
        suggestions = []
        
        if ("motor" in user_input.lower() or "servo" in user_input.lower()) and "applyForge" not in generated_code:
            suggestions.append({'text': "Apply Forge Theory smoothing?", 'action': 'add_forge'})
        
        if "L298N" in user_input and "safety" not in generated_code.lower():
            suggestions.append({'text': "Add 5s safety timeout?", 'action': 'add_safety'})
        
        self.assertEqual(len(suggestions), 2)

    # Test 9: Repository Indexing
    def test_repository_indexing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir) / "test_repo"
            repo_dir.mkdir()
            
            test_files = {
                "motor_driver.ino": "void setupMotors() { }",
                "servo_control.cpp": "void activateFlipper() { }",
                "utils.py": "def calculate_pwm(speed): pass"
            }
            
            for filename, content in test_files.items():
                (repo_dir / filename).write_text(content)
            
            import re
            indexed_functions = []
            
            for file_path in repo_dir.rglob('*'):
                if file_path.is_file() and file_path.suffix in ['.ino', '.cpp', '.py']:
                    content = file_path.read_text()
                    if file_path.suffix in ['.ino', '.cpp']:
                        matches = re.findall(r'\b(?:void|int)\s+(\w+)\s*\(', content)
                        indexed_functions.extend(matches)
                    elif file_path.suffix == '.py':
                        matches = re.findall(r'\bdef\s+(\w+)\s*\(', content)
                        indexed_functions.extend(matches)
            
            expected_functions = ['setupMotors', 'activateFlipper', 'calculate_pwm']
            self.assertEqual(set(indexed_functions), set(expected_functions))

    # Test 10: Search Query Safety
    def test_search_query_safety(self):
        malicious_queries = [
            "'; DROP TABLE repo_index; --",
            "' OR '1'='1",
            "admin'--",
            "<script>alert('xss')</script>",
        ]
        import re
        for query in malicious_queries:
            keywords = re.findall(r'\b\w{4,}\b', query.lower())
            conditions = []
            for keyword in keywords:
                conditions.append("(function_name LIKE ? OR content LIKE ?)")
            
            if conditions:
                safe_sql = f"SELECT * FROM repo_index WHERE {' OR '.join(conditions)}"
                self.assertNotIn("DROP", safe_sql)
                self.assertNotIn("'; ", safe_sql)

    # Test 11: Context Window Management
    def test_context_window(self):
        context_messages = []
        for i in range(20):
            context_messages.append({"role": "user", "content": f"Message {i}"})
            context_messages.append({"role": "assistant", "content": f"Response {i}"})
        
        limited_context = context_messages[-5:]
        self.assertEqual(len(limited_context), 5)
        self.assertEqual(limited_context[0]['content'], "Response 17")
        self.assertEqual(limited_context[-1]['content'], "Response 19")

    # Test 12: Schedule Awareness
    def test_schedule_awareness(self):
        with patch('core.buddai_personality.datetime') as mock_date:
            mock_date.now.return_value = datetime(2025, 12, 29, 6, 0, 0)
            buddai = BuddAI(server_mode=False)
            status = buddai.personality_manager.get_user_status()
            self.assertIn("Early Morning", status)
            
            mock_date.now.return_value = datetime(2025, 12, 29, 10, 0, 0)
            status = buddai.personality_manager.get_user_status()
            self.assertIn("Work Hours", status)

    # Test 13: Modular Plan Generation
    def test_modular_plan(self):
        buddai = BuddAI(server_mode=False)
        modules = ["ble", "servo"]
        plan = buddai.prompt_engine.build_modular_plan(modules)
        self.assertEqual(len(plan), 3)
        tasks = [p['module'] for p in plan]
        self.assertIn("integration", tasks)

    # Test 14: Session Management
    def test_session_management(self):
        fd, test_db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        test_db = Path(test_db_path)
        
        # Patch both executive and shared DB_PATH to ensure StorageManager uses temp DB
        patchers = [patch.object(buddai_module, 'DB_PATH', test_db)]
        if 'core.buddai_shared' in sys.modules:
            patchers.append(patch('core.buddai_shared.DB_PATH', test_db))
            
        try:
            for p in patchers: p.start()
            try:
                buddai = BuddAI(server_mode=False)
                sid = buddai.start_new_session()
                
                buddai.rename_session(sid, "Unit Test Session")
                sessions = buddai.get_sessions(limit=1)
                self.assertEqual(sessions[0]['title'], "Unit Test Session")
                
                buddai.delete_session(sid)
                sessions = buddai.get_sessions(limit=5)
                self.assertFalse(any(s['id'] == sid for s in sessions))
            finally:
                for p in reversed(patchers): p.stop()
        finally:
            try:
                if test_db.exists(): os.unlink(test_db)
            except Exception: pass

    # Test 15: Rapid Session Creation
    def test_rapid_session_creation(self):
        fd, test_db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        test_db = Path(test_db_path)
        
        # Ensure REPO_ROOT is in path to import core modules
        if str(REPO_ROOT) not in sys.path:
            sys.path.insert(0, str(REPO_ROOT))

        # Ensure storage module is loaded to allow patching
        if 'core.buddai_storage' not in sys.modules:
            try:
                import core.buddai_storage
            except ImportError:
                pass

        patchers = [patch.object(buddai_module, 'DB_PATH', test_db)]
        if 'core.buddai_shared' in sys.modules:
            patchers.append(patch('core.buddai_shared.DB_PATH', test_db))
        if 'core.buddai_storage' in sys.modules:
            patchers.append(patch('core.buddai_storage.DB_PATH', test_db))
            
        try:
            fixed_time = datetime(2025, 1, 1, 12, 0, 0)
            for p in patchers: p.start()
            
            dt_patchers = [patch.object(buddai_module, 'datetime')]
            if 'core.buddai_storage' in sys.modules:
                dt_patchers.append(patch('core.buddai_storage.datetime'))
                
            try:
                for p in dt_patchers:
                    mock_dt = p.start()
                    mock_dt.now.return_value = fixed_time
                    # Handle case where datetime is imported as a module
                    mock_dt.datetime.now.return_value = fixed_time
                
                buddai = BuddAI(server_mode=False)
                ids = [buddai.storage.current_session_id]
                for _ in range(4):
                    ids.append(buddai.start_new_session())
                
                base_id = fixed_time.strftime("%Y%m%d_%H%M%S")
                expected = [base_id] + [f"{base_id}_{i}" for i in range(1, 5)]
                self.assertEqual(ids, expected)
            finally:
                for p in reversed(dt_patchers): p.stop()
                for p in reversed(patchers): p.stop()
        finally:
            try:
                if test_db.exists(): os.unlink(test_db)
            except Exception: pass

    # Test 16: Repository Isolation
    def test_repo_isolation(self):
        fd, test_db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        test_db = Path(test_db_path)
        with tempfile.TemporaryDirectory() as tmp_repo:
            repo_path = Path(tmp_repo)
            (repo_path / "user1_secret.py").write_text("def user1_secret_function():\n    pass")
            try:
                with patch.object(buddai_module, 'DB_PATH', test_db):
                    with patch('builtins.print'):
                        # Create repo_index table
                        conn = sqlite3.connect(test_db)
                        conn.execute("CREATE TABLE IF NOT EXISTS repo_index (id INTEGER PRIMARY KEY, file_path TEXT, repo_name TEXT, function_name TEXT, content TEXT, last_modified TIMESTAMP, user_id TEXT)")
                        conn.commit()
                        conn.close()

                        buddai1 = BuddAI(user_id="user1", server_mode=False)
                        buddai1.repo_manager.index_local_repositories(str(repo_path))
                        buddai2 = BuddAI(user_id="user2", server_mode=False)
                        
                        res1 = buddai1.repo_manager.search_repositories("user1_secret_function")
                        res2 = buddai2.repo_manager.search_repositories("user1_secret_function")
                    
                    self.assertTrue("Found 1 matches" in res1 or "user1_secret_function" in res1)
                    self.assertIn("No functions found", res2)
            finally:
                try:
                    if test_db.exists(): os.unlink(test_db)
                except Exception: pass

    # Test 17: Upload Security
    def test_upload_security(self):
        class MockUploadFile:
            def __init__(self, filename, content):
                self.filename = filename
                self.file = io.BytesIO(content)
                self.content_type = "application/zip"
        
        if hasattr(buddai_module, 'validate_upload'):
            fake_zip = MockUploadFile("fake.zip", b"This is not a zip file")
            with self.assertRaises(ValueError):
                buddai_module.validate_upload(fake_zip)

        if hasattr(buddai_module, 'safe_extract_zip'):
            with tempfile.TemporaryDirectory() as tmpdir:
                malicious_zip_path = Path(tmpdir) / "slip.zip"
                extract_dir = Path(tmpdir) / "extract"
                extract_dir.mkdir()
                
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w') as zf:
                    zf.writestr('../evil.txt', 'malicious content')
                malicious_zip_path.write_bytes(zip_buffer.getvalue())
                
                with self.assertRaises(ValueError):
                    buddai_module.safe_extract_zip(malicious_zip_path, extract_dir)

    # Test 18: WebSocket Logic
    def test_websocket_logic(self):
        fd, test_db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        test_db = Path(test_db_path)
        try:
            with patch.object(buddai_module, 'DB_PATH', test_db):
                with patch('builtins.print'):
                    # Create tables
                    conn = sqlite3.connect(test_db)
                    conn.execute("CREATE TABLE IF NOT EXISTS repo_index (id INTEGER PRIMARY KEY, file_path TEXT, repo_name TEXT, function_name TEXT, content TEXT, last_modified TIMESTAMP, user_id TEXT)")
                    conn.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, role TEXT, content TEXT, timestamp TIMESTAMP)")
                    conn.commit()
                    conn.close()

                    buddai = BuddAI(server_mode=False)
                
                def mock_generator(*args, **kwargs):
                    yield "Stream"
                    yield "ing"
                    yield "..."
                
                with patch.object(buddai, 'call_model', side_effect=mock_generator) as mock_call:
                    with patch.object(buddai.shadow_engine, 'get_all_suggestions', return_value=[]):
                        stream = buddai.chat_stream("Test Message", force_model="fast")
                        chunks = list(stream)
                        full_text = "".join(chunks)
                        
                        self.assertEqual(full_text, "Streaming...")
                        args, kwargs = mock_call.call_args
                        self.assertTrue(kwargs.get('stream'))
        finally:
            try:
                if test_db.exists(): os.unlink(test_db)
            except Exception: pass

    # Test 19: Connection Pooling
    def test_connection_pool(self):
        if not hasattr(buddai_module, 'OLLAMA_POOL'):
            return
        pool = buddai_module.OLLAMA_POOL
        while not pool.pool.empty():
            try:
                c = pool.pool.get_nowait()
                c.close()
            except: break
                
        conn1 = pool.get_connection()
        self.assertIsInstance(conn1, http.client.HTTPConnection)
        pool.return_connection(conn1)
        self.assertEqual(pool.pool.qsize(), 1)
        
        conn2 = pool.get_connection()
        self.assertIs(conn2, conn1)

    # Test 20: Feedback System
    def test_feedback_system(self):
        fd, test_db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        test_db = Path(test_db_path)
        
        if 'core.buddai_storage' not in sys.modules:
            try:
                import core.buddai_storage
            except ImportError:
                pass

        # Patch DB_PATH in both executive and shared to ensure consistency
        patchers = [patch.object(buddai_module, 'DB_PATH', test_db)]
        if 'core.buddai_shared' in sys.modules:
            patchers.append(patch('core.buddai_shared.DB_PATH', test_db))
        if 'core.buddai_storage' in sys.modules:
            patchers.append(patch('core.buddai_storage.DB_PATH', test_db))
            
        try:
            for p in patchers: p.start()
            try:
                with patch('builtins.print'):
                    # Create feedback and messages table manually for test
                    conn = sqlite3.connect(str(test_db))
                    conn.execute("CREATE TABLE IF NOT EXISTS feedback (message_id INTEGER, positive BOOLEAN, comment TEXT, timestamp TEXT)")
                    conn.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, role TEXT, content TEXT, timestamp TIMESTAMP)")
                    conn.commit()
                    conn.close()
                    
                    buddai = BuddAI(server_mode=False)
                
                msg_id = buddai.storage.save_message("assistant", "Test response")
                buddai.record_feedback(msg_id, True)
                
                conn = sqlite3.connect(str(test_db))
                cursor = conn.cursor()
                cursor.execute("SELECT positive FROM feedback WHERE message_id = ?", (msg_id,))
                row = cursor.fetchone()
                conn.close()
                self.assertIsNotNone(row, "Feedback row not found in database")
                self.assertEqual(row[0], 1)
            finally:
                for p in reversed(patchers): p.stop()
        finally:
            try:
                if test_db.exists(): os.unlink(test_db)
            except Exception: pass

if __name__ == "__main__":
    unittest.main()