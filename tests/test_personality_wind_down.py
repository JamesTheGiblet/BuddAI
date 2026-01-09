#!/usr/bin/env python3
"""
Specific test for Wind Down personality mode.
"""
import unittest
import sys
from pathlib import Path

# Setup path
REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.buddai_personality import PersonalityManager

class TestPersonalityWindDown(unittest.TestCase):
    def setUp(self):
        self.pm = PersonalityManager()

    def test_wind_down_mode_configuration(self):
        """Verify wind_down mode loads new note and interaction style"""
        # Fetch the weekday schedule
        weekday_schedule = self.pm.get_value("work_cycles.schedule.weekdays.0-4")
        self.assertIsNotNone(weekday_schedule, "Weekday schedule not found")
        
        # Access the specific time slot (key contains dots, so might not work with dot notation accessor)
        wind_down_config = weekday_schedule.get("21.0-24.0")
        
        self.assertIsNotNone(wind_down_config, "Wind down configuration (21.0-24.0) not found")
        self.assertEqual(wind_down_config.get("mode"), "wind_down")
        self.assertEqual(wind_down_config.get("interaction_style"), "reflection_planning_learning")
        self.assertEqual(wind_down_config.get("note"), "Encourage asking learning questions to deepen understanding.")

if __name__ == '__main__':
    unittest.main()