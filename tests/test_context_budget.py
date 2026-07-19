from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from agent_starter.cli import command_audit_context, main
from agent_starter.cli_app import inspection_commands
from agent_starter.context_budget import ContextAuditError, audit_context, render_context_audit
from agent_starter.generator import generate_project
from agent_starter.models import ProjectConfig


class ContextBudgetTests(unittest.TestCase):
    def test_generated_default_context_is_measured_without_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            config = ProjectConfig(
                project_name="My Project",
                project_slug="my-project",
                project_path=str(root),
                description="A maintainable Python command-line project.",
                languages=["python"],
                database="sqlite",
                git_enabled=False,
                codex_agentkit_skill=True,
            )
            self.assertTrue(generate_project(config).ok)
            report = audit_context(root)

        self.assertTrue(report.advisory_only)
        self.assertFalse(report.blocking)
        metrics = {item.path: item for item in report.files}
        self.assertEqual((metrics["START_HERE.md"].words, metrics["START_HERE.md"].lines), (127, 33))
        self.assertEqual((metrics["docs/AGENT-INDEX.md"].words, metrics["docs/AGENT-INDEX.md"].lines), (430, 63))
        self.assertEqual((metrics["FIRST_PROMPT.md"].words, metrics["FIRST_PROMPT.md"].lines), (452, 59))
        self.assertEqual(report.task_prompt_words, 452)
        self.assertEqual(
            report.default_required_files,
            (
                "docs/AGENT-INDEX.md",
                "AGENTS.md",
                "docs/09-PROGRESS.md",
                "docs/14-AGENT-HANDOFF.md",
                "docs/04-DEVELOPMENT-ENVIRONMENT.md",
                "docs/05-TESTING.md",
            ),
        )
        self.assertEqual(report.default_required_file_count, 6)
        self.assertTrue(all(item.within_suggested_target for item in report.files))
        self.assertIn("advisory only", render_context_audit(report).lower())

    def test_duplicate_paragraphs_are_fingerprinted_and_symlinks_are_refused(self) -> None:
        duplicate = "This deliberately repeated paragraph has enough stable words to verify duplicate context detection without depending on Markdown punctuation or line wrapping."
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "docs").mkdir()
            (root / "START_HERE.md").write_text(f"# Start\n\n{duplicate}\n", encoding="utf-8")
            wrapped_duplicate = duplicate.replace("stable words", "stable\nwords")
            (root / "AGENTS.md").write_text(f"# Policy\n\n{wrapped_duplicate}\n", encoding="utf-8")
            (root / "FIRST_PROMPT.md").write_text(
                "Read `docs/AGENT-INDEX.md` first, then `AGENTS.md`.\n",
                encoding="utf-8",
            )
            (root / "docs/AGENT-INDEX.md").write_text(
                "| Baseline/discovery | `AGENTS.md`, `docs/09-PROGRESS.md` |\n",
                encoding="utf-8",
            )
            report = audit_context(root)
            self.assertEqual(len(report.duplicate_paragraphs), 1)
            self.assertEqual(report.duplicate_paragraphs[0].paths, ("AGENTS.md", "START_HERE.md"))
            self.assertEqual(len(report.duplicate_paragraphs[0].fingerprint), 64)

            oversized = " ".join(f"word{index}" for index in range(501))
            (root / "FIRST_PROMPT.md").write_text(oversized, encoding="utf-8")
            report = audit_context(root)
            self.assertFalse(report.blocking)
            self.assertIn("context.suggested-target-exceeded", {item.code for item in report.issues})

            (root / "START_HERE.md").unlink()
            (root / "START_HERE.md").symlink_to("AGENTS.md")
            with self.assertRaises(ContextAuditError):
                audit_context(root)

    def test_cli_json_is_non_blocking_and_legacy_export_is_direct(self) -> None:
        self.assertIs(command_audit_context, inspection_commands.command_audit_context)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = main(["audit-context", str(root), "--json"])
            payload = json.loads(output.getvalue())
        self.assertEqual(result, 0)
        self.assertTrue(payload["advisory_only"])
        self.assertFalse(payload["blocking"])
        self.assertTrue(payload["issues"])


if __name__ == "__main__":
    unittest.main()
