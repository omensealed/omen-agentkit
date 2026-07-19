from __future__ import annotations

import unittest

from agent_starter.entry_modes import EntryMode, entry_mode_policy, parse_entry_mode


class EntryModeTests(unittest.TestCase):
    def test_guided_and_advanced_are_typed_presentation_policies(self) -> None:
        guided = entry_mode_policy(EntryMode.GUIDED)
        advanced = entry_mode_policy(EntryMode.ADVANCED)
        self.assertFalse(guided.show_advanced_settings)
        self.assertTrue(advanced.show_advanced_settings)
        self.assertIn("safe defaults", guided.explanation.lower())
        self.assertIn("validation", advanced.explanation.lower())

    def test_mode_parser_is_strict_and_defaults_are_caller_owned(self) -> None:
        self.assertIs(parse_entry_mode("guided"), EntryMode.GUIDED)
        self.assertIs(parse_entry_mode(EntryMode.ADVANCED), EntryMode.ADVANCED)
        with self.assertRaises(ValueError):
            parse_entry_mode("beginner-ish")


if __name__ == "__main__":
    unittest.main()
