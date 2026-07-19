from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = {
    "human": ROOT / "docs" / "HUMAN-START.md",
    "maintainer": ROOT / "docs" / "MAINTAINER-GUIDE.md",
    "agent": ROOT / "docs" / "AGENT-GUIDE.md",
    "operations": ROOT / "docs" / "OPERATIONS-GUIDE.md",
}
LOCAL_LINK = re.compile(r"\[[^]]+\]\((?!https?://|#)([^)#]+)(?:#([^)]+))?\)")


def _heading_slug(heading: str) -> str:
    return re.sub(r"[^a-z0-9 -]", "", heading.lower()).strip().replace(" ", "-")


class AudienceDocumentationTests(unittest.TestCase):
    def test_readme_routes_each_audience(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for path in DOCS.values():
            self.assertIn(f"docs/{path.name}", readme)

    def test_audience_pages_have_current_local_links(self) -> None:
        for audience, path in DOCS.items():
            with self.subTest(audience=audience):
                body = path.read_text(encoding="utf-8")
                self.assertNotIn("gpt-5.5", body.lower())
                for target, anchor in LOCAL_LINK.findall(body):
                    linked = path.parent / target
                    self.assertTrue(linked.is_file(), target)
                    if anchor and linked.suffix == ".md":
                        headings = {
                            _heading_slug(line.lstrip("# "))
                            for line in linked.read_text(encoding="utf-8").splitlines()
                            if line.startswith("#")
                        }
                        self.assertIn(anchor, headings, f"{target}#{anchor}")

    def test_each_page_owns_the_planned_audience_topics(self) -> None:
        expected = {
            "human": ("Install or run locally", "Create the first project", "Prepare the first task", "Common repairs"),
            "maintainer": ("Architecture and compatibility", "Providers and schemas", "Security and testing", "Release"),
            "agent": ("Contracts", "Read only what the task needs", "AGENTS.md", "Stop when the authorized task is complete"),
            "operations": ("Plans and local evidence", "Rollback and rehearsal", "Secret references", "Audit and release boundary"),
        }
        for audience, phrases in expected.items():
            body = DOCS[audience].read_text(encoding="utf-8")
            for phrase in phrases:
                self.assertIn(phrase, body)

    def test_agent_index_is_concise_and_operations_is_non_authorizing(self) -> None:
        agent = DOCS["agent"].read_text(encoding="utf-8")
        operations = DOCS["operations"].read_text(encoding="utf-8")
        self.assertLessEqual(len(agent.splitlines()), 40)
        self.assertIn("There is no `deployment apply` command", operations)
        self.assertIn("do not authorize", operations)
        self.assertNotIn("agent-starter deployment apply", operations)

    def test_documented_source_commands_remain_available(self) -> None:
        commands = (
            ("./agent-starter", "doctor", "--help"),
            ("./agent-starter", "new", "--help"),
            ("./agent-starter", "prompt", "--help"),
            ("./agent-starter", "config", "migrate", "--help"),
            ("./agent-starter", "deployment", "plan", "--help"),
            ("./agent-starter", "deployment", "check", "--help"),
            ("./agent-starter", "deployment", "build", "--help"),
            ("./agent-starter", "audit-context", "--help"),
        )
        for command in commands:
            with self.subTest(command=command):
                completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
                self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main()
