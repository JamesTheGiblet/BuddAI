#!/usr/bin/env python3
"""
BuddAI v3.2 Integration Test Suite
Tests API endpoints and server integration

Author: James Gilbert
License: MIT
"""

import sys
import os
import importlib.util
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import json

# Dynamic import of buddai_v3.2.py
REPO_ROOT = Path(__file__).parent.parent
MODULE_PATH = REPO_ROOT / "buddai_executive.py"
spec = importlib.util.spec_from_file_location("buddai_executive", MODULE_PATH)
buddai_module = importlib.util.module_from_spec(spec)
sys.modules["buddai_executive"] = buddai_module
spec.loader.exec_module(buddai_module)

# Check for server dependencies
SERVER_AVAILABLE = getattr(buddai_module, "SERVER_AVAILABLE", False)

if SERVER_AVAILABLE:
    # Load buddai_server.py dynamically to get 'app'
    SERVER_PATH = REPO_ROOT / "buddai_server.py"
    spec_server = importlib.util.spec_from_file_location("buddai_server", SERVER_PATH)
    server_module = importlib.util.module_from_spec(spec_server)
    sys.modules["buddai_server"] = server_module
    spec_server.loader.exec_module(server_module)
    
    from fastapi.testclient import TestClient
    app = server_module.app
    client = TestClient(app)
else:
    print("⚠️  Server dependencies missing. Integration tests skipped.")

@unittest.skipUnless(SERVER_AVAILABLE, "Server dependencies not installed")
class TestBuddAIIntegration(unittest.TestCase):
    
    def setUp(self):
        # Create a fresh temp DB for each test
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.db_fd)
        
        # Patch DB_PATH in the module
        self.db_patcher = patch("buddai_executive.DB_PATH", Path(self.db_path))
        self.mock_db_path = self.db_patcher.start()
        
        # Reset the manager to ensure fresh BuddAI instances connected to temp DB
        if hasattr(buddai_module, 'buddai_manager'):
            buddai_module.buddai_manager.instances = {}
        
        # Suppress prints
        self.print_patcher = patch("builtins.print")
        self.print_patcher.start()

    def tearDown(self):
        self.db_patcher.stop()
        self.print_patcher.stop()
        try:
            os.unlink(self.db_path)
        except:
            pass

    def test_health_check(self):
        """GET / returns 200 and status"""
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("BuddAI API", response.text)
        self.assertIn("Online", response.text)

    def test_chat_flow(self):
        """POST /api/chat returns response"""
        # Mock the internal chat method to avoid Ollama dependency
        with patch.object(buddai_module.BuddAI, 'chat', return_value="Integrated Response") as mock_chat:
            response = client.post("/api/chat", json={"message": "Hello API"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"response": "Integrated Response", "message_id": None})
            
            # Verify user_id header handling (default)
            mock_chat.assert_called_once()

    def test_session_lifecycle_api(self):
        """Test full session CRUD via API"""
        # 1. Create
        resp = client.post("/api/session/new")
        self.assertEqual(resp.status_code, 200)
        session_id = resp.json()["session_id"]
        
        # 2. List
        resp = client.get("/api/sessions")
        self.assertEqual(resp.status_code, 200)
        sessions = resp.json()["sessions"]
        self.assertTrue(any(s["id"] == session_id for s in sessions))
        
        # 3. Rename
        new_title = "API Test Session"
        resp = client.post("/api/session/rename", json={"session_id": session_id, "title": new_title})
        self.assertEqual(resp.status_code, 200)
        
        resp = client.get("/api/sessions")
        updated_session = next(s for s in resp.json()["sessions"] if s["id"] == session_id)
        self.assertEqual(updated_session["title"], new_title)
        
        # 4. Load
        resp = client.post("/api/session/load", json={"session_id": session_id})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["session_id"], session_id)
        
        # 5. Delete
        resp = client.post("/api/session/delete", json={"session_id": session_id})
        self.assertEqual(resp.status_code, 200)
        
        resp = client.get("/api/sessions")
        self.assertFalse(any(s["id"] == session_id for s in resp.json()["sessions"]))

    def test_multi_user_isolation_api(self):
        """Verify data isolation between users via API headers"""
        user1_headers = {"user-id": "user1"}
        user2_headers = {"user-id": "user2"}
        
        # User 1 creates session
        resp1 = client.post("/api/session/new", headers=user1_headers)
        sid1 = resp1.json()["session_id"]
        client.post("/api/session/rename", json={"session_id": sid1, "title": "User1 Chat"}, headers=user1_headers)
        
        # User 2 creates session
        resp2 = client.post("/api/session/new", headers=user2_headers)
        sid2 = resp2.json()["session_id"]
        client.post("/api/session/rename", json={"session_id": sid2, "title": "User2 Chat"}, headers=user2_headers)
        
        # Verify User 1 sees only their session
        list1 = client.get("/api/sessions", headers=user1_headers).json()["sessions"]
        ids1 = [s["id"] for s in list1]
        self.assertIn(sid1, ids1)
        self.assertNotIn(sid2, ids1)
        
        # Verify User 2 sees only their session
        list2 = client.get("/api/sessions", headers=user2_headers).json()["sessions"]
        ids2 = [s["id"] for s in list2]
        self.assertIn(sid2, ids2)
        self.assertNotIn(sid1, ids2)

    def test_upload_api(self):
        """Test file upload endpoint"""
        with tempfile.TemporaryDirectory() as tmp_data_dir:
            with patch("buddai_executive.DATA_DIR", Path(tmp_data_dir)):
                # Mock indexing to avoid parsing logic
                with patch.object(buddai_module.RepoManager, 'index_local_repositories') as mock_index:
                    
                    # Create dummy file
                    files = {'file': ('test.py', b'print("hello")', 'text/x-python')}
                    
                    response = client.post("/api/upload", files=files)
                    self.assertEqual(response.status_code, 200)
                    self.assertIn("Successfully indexed", response.json()["message"])
                    mock_index.assert_called()

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 BuddAI v3.2 Integration Tests")
    print("="*60)
    unittest.main(verbosity=2)