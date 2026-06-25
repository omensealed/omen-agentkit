from __future__ import annotations

import re
import unittest
from pathlib import Path

from agent_starter import __version__
from agent_starter.models import ProjectConfig


class ReleaseConsistencyTests(unittest.TestCase):
    def test_version_is_consistent(self) -> None:
        root = Path(__file__).resolve().parents[1]
        version_file = (root / "VERSION").read_text(encoding="utf-8").strip()
        pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
        match = re.search(r'^version = "([^"]+)"$', pyproject, re.MULTILINE)
        self.assertIsNotNone(match)
        self.assertEqual(version_file, __version__)
        self.assertEqual(version_file, match.group(1))
        self.assertEqual(version_file, ProjectConfig().kit_version)


if __name__ == "__main__":
    unittest.main()
