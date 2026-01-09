import unittest
from unittest.mock import patch, MagicMock
import sys
import os
from pathlib import Path

# Add parent directory to path so we can import 'skills'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skills import load_registry

class TestSkills(unittest.TestCase):
    
    def setUp(self):
        self.registry = load_registry()

    def test_registry_loading(self):
        """Ensure skills are discovered and loaded"""
        self.assertGreater(len(self.registry), 0, "No skills loaded")
        # Check for core skills
        self.assertIn("calculator", self.registry)
        self.assertIn("weather", self.registry)
        self.assertIn("timer", self.registry)
        self.assertIn("system_info", self.registry)
        self.assertIn("file_search_tool", self.registry)
        self.assertIn("code_analyzer", self.registry)
        self.assertIn("doc_generator", self.registry)
        self.assertIn("test_generator", self.registry)
        self.assertIn("project_scaffolder", self.registry)

    def test_calculator_logic(self):
        """Verify calculator skill math"""
        calc = self.registry["calculator"]["run"]
        self.assertIn("4", calc("Calculate 2 + 2"))
        self.assertIn("25", calc("5 * 5"))
        self.assertIsNone(calc("No math here"))

    def test_timer_parsing(self):
        """Verify timer parses duration correctly"""
        timer = self.registry["timer"]["run"]
        # We use 0 seconds to avoid waiting during tests
        response = timer("Set a timer for 0 seconds")
        self.assertIn("Timer started", response)

    @patch('urllib.request.urlopen')
    def test_weather_mock(self, mock_urlopen):
        """Verify weather skill with mocked network"""
        # Mock the API response so tests work offline
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b"London: +15C"
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        weather = self.registry["weather"]["run"]
        result = weather("Weather in London")
        
        self.assertIn("London: +15C", result)

    @patch('os.walk')
    @patch('pathlib.Path.cwd')
    def test_file_search_tool(self, mock_cwd, mock_walk):
        """Verify file search skill"""
        # Setup mock filesystem
        mock_cwd.return_value = Path('/root')
        mock_walk.return_value = [
            ('/root', ['subdir'], ['found_me.py', 'ignore.txt']),
            ('/root/subdir', [], ['another.py'])
        ]
        
        search = self.registry["file_search_tool"]["run"]
        
        # Test finding a file
        result = search("find file *.py")
        self.assertIn("found_me.py", result)
        self.assertIn("another.py", result)
        self.assertNotIn("ignore.txt", result)

    def test_code_analyzer(self):
        """Verify code analyzer skill"""
        analyzer = self.registry["code_analyzer"]["run"]
        
        # Test Python code
        py_code = "analyze code def foo(): pass"
        result = analyzer(py_code)
        self.assertIn("Python Structure", result)
        self.assertIn("Functions: 1", result)
        
        # Test Text/Generic
        text_code = "analyze code just some text"
        result_text = analyzer(text_code)
        self.assertIn("Text/Generic Analysis", result_text)

    def test_doc_generator(self):
        """Verify doc generator skill"""
        gen = self.registry["doc_generator"]["run"]
        
        code = 'def my_func(a, b):\n    """Adds two numbers."""\n    return a+b'
        result = gen(f"generate docs {code}")
        
        self.assertIn("API Documentation", result)
        self.assertIn("my_func(a, b)", result)
        self.assertIn("Adds two numbers.", result)

    def test_test_generator(self):
        """Verify test generator skill"""
        gen = self.registry["test_generator"]["run"]
        
        code = "def add(a, b): return a + b"
        result = gen(f"generate tests {code}")
        
        self.assertIn("import unittest", result)
        self.assertIn("class TestGenerated(unittest.TestCase):", result)
        self.assertIn("def test_add(self):", result)

    def test_project_scaffolder(self):
        """Verify project scaffolder skill"""
        scaffold = self.registry["project_scaffolder"]["run"]
        
        # Test Python
        res_py = scaffold("scaffold python project")
        self.assertIn("requirements.txt", res_py)
        self.assertIn("venv/", res_py)
        
        # Test Node
        res_node = scaffold("scaffold node project")
        self.assertIn("package.json", res_node)
        self.assertIn("node_modules/", res_node)
        
        # Test Flask
        res_flask = scaffold("scaffold flask project")
        self.assertIn("flask_app/", res_flask)
        self.assertIn("routes.py", res_flask)

        # Test React
        res_react = scaffold("scaffold react project")
        self.assertIn("react_app/", res_react)
        self.assertIn("components/", res_react)

if __name__ == '__main__':
    unittest.main(verbosity=2)