from __future__ import annotations

import subprocess
import re
import unittest
from pathlib import Path

from agent_starter.config_schema import migrate_config
from agent_starter.model_policy import DEFAULT_CODEX_MODEL_POLICY


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs" / "GPT-5.6-SOL-MIGRATION-REPORT.md"


class MigrationReportTests(unittest.TestCase):
    def test_report_covers_the_required_behavior_changes(self) -> None:
        body = REPORT.read_text(encoding="utf-8")
        for heading in (
            "## Release status and scope",
            "## What changed from the v0.4.8 baseline",
            "## Model selection",
            "## Schema-v1 to schema-v2 migration",
            "## Debian and Ubuntu support level",
            "## Compatibility and deprecation timeline",
        ):
            self.assertIn(heading, body)
        for subject in ("recommendation", "modular", "deployment", "packaging"):
            self.assertIn(subject, body.lower())

    def test_model_claims_match_the_typed_policy(self) -> None:
        body = REPORT.read_text(encoding="utf-8")
        policy = DEFAULT_CODEX_MODEL_POLICY
        for value in (policy.model_id, policy.display_label, policy.reasoning_effort, policy.selection, policy.fallback_behavior):
            self.assertIn(f"`{value}`", body)
        self.assertIn("GPT-5.5 is historical context only", body)
        self.assertIn("never silently downgrades", body)

    def test_v1_arch_intent_claim_matches_the_migrator(self) -> None:
        migration = migrate_config({"schema_version": 1, "cachyos_packages": ["ripgrep", "python"]})
        self.assertEqual(migration.target_version, 2)
        self.assertEqual(migration.data["extra_packages_by_provider"], {"arch": ["ripgrep", "python"]})
        self.assertNotIn("cachyos_packages", migration.data)
        body = REPORT.read_text(encoding="utf-8")
        self.assertIn("`extra_packages_by_provider.arch`", body)
        self.assertIn("never translated", body)

    def test_support_and_deprecation_claims_are_bounded(self) -> None:
        body = REPORT.read_text(encoding="utf-8")
        for value in ("CachyOS", "Arch Linux", "Debian", "Ubuntu", "T0", "T+1", "schema v3"):
            self.assertIn(value, body)
        self.assertIn("No public Python module or CLI command is formally deprecated", body)
        self.assertIn("There is no `deployment apply` command", body)
        self.assertNotIn("agent-starter deployment apply", body)

    def test_report_is_routed_and_migration_help_is_current(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        maintainer = (ROOT / "docs" / "MAINTAINER-GUIDE.md").read_text(encoding="utf-8")
        for body in (readme, maintainer):
            self.assertIn("GPT-5.6-SOL-MIGRATION-REPORT.md", body)
        completed = subprocess.run(
            ("./agent-starter", "config", "migrate", "--help"),
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("--input", completed.stdout)
        self.assertIn("--output", completed.stdout)

    def test_report_local_links_resolve(self) -> None:
        body = REPORT.read_text(encoding="utf-8")
        targets = re.findall(r"\[[^]]+\]\((?!https?://|#)([^)#]+)(?:#[^)]+)?\)", body)
        self.assertGreaterEqual(len(targets), 2)
        for target in targets:
            self.assertTrue((REPORT.parent / target).is_file(), target)

    def test_focused_runner_is_packaged(self) -> None:
        runner = ROOT / "scripts" / "migration-report-check.sh"
        self.assertTrue(runner.stat().st_mode & 0o111)
        manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")
        self.assertIn("include scripts/migration-report-check.sh", manifest.splitlines())


if __name__ == "__main__":
    unittest.main()
