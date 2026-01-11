import unittest
import json
import os

class TestConversationalSettings(unittest.TestCase):
    def setUp(self):
        # Locate personality.json relative to this test file
        # Assumes structure: buddAI/tests/test_conversational_verification.py -> buddAI/personality.json
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        config_path = os.path.join(project_root, 'personality.json')
        
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

    def test_stress_mode_is_conversational(self):
        """Verify stress mode is no longer code-only."""
        stress_config = self.config['interaction_modes']['stressed']
        self.assertEqual(stress_config['verbosity'], 'conversational_supportive', 
                         "Stressed mode should be 'conversational_supportive'")
        
        stress_response = self.config['context_awareness']['stress_indicators']['response']
        self.assertFalse(stress_response['code_only_no_preamble'], 
                         "Stress response should allow preambles (code_only_no_preamble should be False)")

    def test_default_verbosity_is_conversational(self):
        """Verify default verbosity is conversational."""
        default_verbosity = self.config['communication']['verbosity']['default']
        self.assertEqual(default_verbosity, 'conversational_code_focused',
                         "Default verbosity should be 'conversational_code_focused'")

    def test_execution_mode_is_conversational(self):
        """Verify execution modes are conversational."""
        evening_mode = self.config['interaction_modes']['evening_build']
        self.assertEqual(evening_mode['verbosity'], 'conversational_execution',
                         "Evening build should use 'conversational_execution'")

if __name__ == '__main__':
    unittest.main()