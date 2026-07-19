from __future__ import annotations

import re
import unittest
from pathlib import Path

from agent_starter.release_safety import verify_release_safety


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_VERSION = "0.5.0"


class ReleaseCandidateTests(unittest.TestCase):
    def test_candidate_version_and_changelog_are_aligned(self) -> None:
        self.assertEqual((ROOT / "VERSION").read_text(encoding="utf-8").strip(), CANDIDATE_VERSION)
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        package = (ROOT / "agent_starter" / "__init__.py").read_text(encoding="utf-8")
        models = (ROOT / "agent_starter" / "models.py").read_text(encoding="utf-8")
        self.assertIn(f'version = "{CANDIDATE_VERSION}"', pyproject)
        self.assertIn(f'__version__ = "{CANDIDATE_VERSION}"', package)
        self.assertIn(f'kit_version: str = "{CANDIDATE_VERSION}"', models)
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn(f"## {CANDIDATE_VERSION} — 2026-07-19", changelog)
        unreleased = changelog.split("## Unreleased", 1)[1].split(f"## {CANDIDATE_VERSION}", 1)[0]
        self.assertFalse(unreleased.strip())

    def test_local_candidate_evidence_is_specific_and_non_publishing(self) -> None:
        body = (ROOT / "docs" / "RELEASE-CANDIDATE-0.5.0.md").read_text(encoding="utf-8")
        self.assertIn("local unpublished candidate", body)
        self.assertIn("`dirty_release_source`", body)
        self.assertIn("no commit, tag, push, release, or publication", body.lower())
        self.assertNotIn("PLACEHOLDER", body)
        self.assertIn("cli_ai_agent_starter_kit-0.5.0-py3-none-any.whl", body)
        self.assertIn("cli_ai_agent_starter_kit-0.5.0.tar.gz", body)
        self.assertIn("`SHA256SUMS`", body)
        self.assertIn("not hard-coded into source", body)
        self.assertIsNone(re.search(r"\b[0-9a-f]{64}\b", body))

    def test_burn_in_is_manual_secret_safe_and_has_no_telemetry(self) -> None:
        policy = (ROOT / "docs" / "BURN-IN.md").read_text(encoding="utf-8")
        form = (ROOT / ".github" / "ISSUE_TEMPLATE" / "migration-burn-in.yml").read_text(encoding="utf-8")
        combined = f"{policy}\n{form}".lower()
        for phrase in ("user-submitted", "no telemetry", "do not include", "credentials", "api keys", "cookies"):
            self.assertIn(phrase, combined)
        for forbidden in ("uploads automatically", "reports in the background", "inspects credentials"):
            self.assertNotIn(forbidden, combined)
        self.assertIn("type: checkboxes", form)
        self.assertIn("I removed credentials", form)

    def test_release_gate_remains_fail_closed_until_human_commit_and_tag(self) -> None:
        report = verify_release_safety(
            ROOT,
            expected_tag="v0.5.0",
            actual_ref="refs/tags/v0.5.0",
            git_status_text=" M VERSION\n",
        )
        codes = [issue.code for issue in report.issues]
        self.assertEqual(codes, ["dirty_release_source"])

    def test_compatibility_window_remains_binding(self) -> None:
        migration = (ROOT / "docs" / "GPT-5.6-SOL-MIGRATION-REPORT.md").read_text(encoding="utf-8")
        candidate = (ROOT / "docs" / "RELEASE-CANDIDATE-0.5.0.md").read_text(encoding="utf-8")
        for phrase in ("T0", "T+1", "No public Python module or CLI command is formally deprecated"):
            self.assertIn(phrase, migration)
        self.assertIn("Compatibility shims remain required through 0.5.0", candidate)
        self.assertIn("following minor stable release", candidate)

    def test_candidate_runner_is_packaged(self) -> None:
        runner = ROOT / "scripts" / "release-candidate-check.sh"
        self.assertTrue(runner.stat().st_mode & 0o111)
        manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8").splitlines()
        self.assertIn("include scripts/release-candidate-check.sh", manifest)
        self.assertIn("include docs/BURN-IN.md", manifest)
        self.assertIn("include docs/GPT-5.6-SOL-MIGRATION-REPORT.md", manifest)
        self.assertIn("include docs/RELEASE-CANDIDATE-0.5.0.md", manifest)
        self.assertNotIn("exclude docs/RELEASE-CANDIDATE-0.5.0.md", manifest)
        self.assertIn("include .github/ISSUE_TEMPLATE/migration-burn-in.yml", manifest)


if __name__ == "__main__":
    unittest.main()
