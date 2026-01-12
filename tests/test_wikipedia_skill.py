import unittest
from unittest.mock import MagicMock, patch
import sys
import os
from pathlib import Path
import json

# Add repo root to path
sys.path.append(str(Path(__file__).parent.parent))

from skills.wikipedia import run_wikipedia

class TestWikipediaSkill(unittest.TestCase):
    def test_wiki_search_success(self):
        """Test successful Wikipedia search and summary retrieval"""
        # Mock responses
        mock_search_response = {
            "query": {
                "search": [{"title": "Python (programming language)"}]
            }
        }
        mock_summary_response = {
            "query": {
                "pages": {
                    "123": {
                        "extract": "Python is a high-level, general-purpose programming language."
                    }
                }
            }
        }

        with patch('urllib.request.urlopen') as mock_urlopen:
            # Configure side effects for two calls (search then summary)
            mock_resp1 = MagicMock()
            mock_resp1.read.return_value = json.dumps(mock_search_response).encode('utf-8')
            mock_resp1.__enter__.return_value = mock_resp1
            
            mock_resp2 = MagicMock()
            mock_resp2.read.return_value = json.dumps(mock_summary_response).encode('utf-8')
            mock_resp2.__enter__.return_value = mock_resp2
            
            # urlopen is a context manager, so we mock the return of __enter__
            mock_urlopen.side_effect = [mock_resp1, mock_resp2]
            
            result = run_wikipedia("wiki python")
            
            self.assertIn("Python (programming language)", result)
            self.assertIn("Python is a high-level", result)
            self.assertIn("https://en.wikipedia.org/wiki/Python", result)

    def test_wiki_no_results(self):
        """Test handling of queries with no results"""
        mock_search_response = {"query": {"search": []}}
        
        with patch('urllib.request.urlopen') as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(mock_search_response).encode('utf-8')
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp
            
            result = run_wikipedia("wiki asdfghjkl_nonexistent")
            self.assertIn("No Wikipedia results found", result)

    def test_wiki_api_error(self):
        """Test handling of network/API errors"""
        with patch('urllib.request.urlopen', side_effect=Exception("Network error")):
            result = run_wikipedia("wiki error_test")
            self.assertIn("Wikipedia Error", result)

if __name__ == '__main__':
    unittest.main()