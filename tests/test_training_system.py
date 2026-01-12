import unittest
import os
import tempfile
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from training.strategies.public_knowledge import PublicKnowledgeStrategy

# Ensure we can import from root
sys.path.append(str(Path(__file__).parent.parent))

from training.registry import TrainingRegistry, TrainingStrategy
from training.strategies.rule_import import RuleImportStrategy
from training.strategies.fine_tuning import FineTuningStrategy
from training.strategies.auto_discovery import AutoDiscoveryStrategy

class TestTrainingSystem(unittest.TestCase):
    def setUp(self):
        self.registry = TrainingRegistry()

    def test_registry_discovery(self):
        """Test that standard strategies are auto-discovered"""
        strategies = self.registry.list_strategies()
        self.assertIn('fine_tune', strategies)
        self.assertIn('import_rules', strategies)
        self.assertIn('auto_discovery', strategies)
        self.assertIn('public_db', strategies)
        
    def test_strategy_retrieval(self):
        """Test retrieving a specific strategy"""
        strategy = self.registry.get_strategy('import_rules')
        self.assertIsInstance(strategy, RuleImportStrategy)
        self.assertEqual(strategy.name, 'import_rules')

    def test_import_rules_strategy(self):
        """Test the rule import strategy logic"""
        strategy = RuleImportStrategy()
        mock_buddai = MagicMock()
        
        # Create a temporary file with rules
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as f:
            f.write("/teach Always use const for variables\n")
            f.write("Just a comment line\n")
            f.write("/teach Prefer async await over callbacks\n")
            temp_path = f.name
            
        try:
            # Run strategy
            result = strategy.run(mock_buddai, [temp_path])
            
            # Verify results
            self.assertIn("Imported 2 rules", result)
            self.assertEqual(mock_buddai.teach_rule.call_count, 2)
            
            # Verify specific calls
            mock_buddai.teach_rule.assert_any_call("Always use const for variables")
            mock_buddai.teach_rule.assert_any_call("Prefer async await over callbacks")
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_auto_discovery_strategy(self):
        """Test auto discovery of files in training dir"""
        strategy = AutoDiscoveryStrategy()
        mock_buddai = MagicMock()
        
        # Mock the path to point to a temp dir
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a dummy training file
            dummy_file = Path(temp_dir) / "3d_printer_failures.txt"
            with open(dummy_file, 'w', encoding='utf-8') as f:
                f.write("/teach Check bed leveling before print\n")
                f.write("/teach Use PETG for heat resistance\n")
            
            # Patch Path in the strategy module to redirect file discovery to our temp dir
            with patch('training.strategies.auto_discovery.Path') as MockPath:
                # Configure mock so Path(__file__).parent.parent resolves to temp_dir
                MockPath.return_value.parent.parent = Path(temp_dir)
                
                result = strategy.run(mock_buddai, [])
                
                self.assertIn("Auto-detected and imported 2 rules", result)
                self.assertIn("3d_printer_failures.txt", result)
                mock_buddai.teach_rule.assert_any_call("Check bed leveling before print")
                mock_buddai.teach_rule.assert_any_call("Use PETG for heat resistance")

    def test_public_knowledge_strategy(self):
        """Test fetching rules from a remote URL"""
        strategy = PublicKnowledgeStrategy()
        mock_buddai = MagicMock()
        
        # Mock the network response
        mock_response = MagicMock()
        mock_response.read.return_value = b"/teach Remote Rule 1\n# Comment\nRemote Rule 2"
        mock_response.__enter__.return_value = mock_response
        
        with patch('urllib.request.urlopen', return_value=mock_response):
            result = strategy.run(mock_buddai, ["http://example.com/rules.txt"])
            
            self.assertIn("imported 2 rules", result)
            # Verify source tracking
            mock_buddai.teach_rule.assert_any_call("Remote Rule 1", source="public_db:http://example.com/rules.txt")
            mock_buddai.teach_rule.assert_any_call("Remote Rule 2", source="public_db:http://example.com/rules.txt")

    def test_public_knowledge_deduplication(self):
        """Test that public knowledge strategy counts duplicates correctly"""
        strategy = PublicKnowledgeStrategy()
        mock_buddai = MagicMock()
        
        # Mock teach_rule to return True (new) once, then False (duplicate)
        mock_buddai.teach_rule.side_effect = [True, False]
        
        # Mock network response
        mock_response = MagicMock()
        mock_response.read.return_value = b"/teach Rule 1\n/teach Rule 2"
        mock_response.__enter__.return_value = mock_response
        
        with patch('urllib.request.urlopen', return_value=mock_response):
            result = strategy.run(mock_buddai, ["http://example.com"])
            
            self.assertIn("imported 1 rules", result)
            self.assertIn("Skipped (duplicates): 1", result)

if __name__ == '__main__':
    unittest.main()