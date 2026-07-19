from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest import mock

from agent_starter.deployment_ci import validate_github_action_references
from agent_starter.release_safety import main, verify_release_safety


class ReleaseSafetyTests(unittest.TestCase):
    def _root(self, path: Path, *, version: str = "1.2.3", unreleased: str = "") -> Path:
        (path / "agent_starter").mkdir()
        (path / "VERSION").write_text(f"{version}\n", encoding="utf-8")
        (path / "pyproject.toml").write_text(f'[project]\nversion = "{version}"\n', encoding="utf-8")
        (path / "agent_starter/__init__.py").write_text(f'__version__ = "{version}"\n', encoding="utf-8")
        (path / "agent_starter/models.py").write_text(
            f'    kit_version: str = "{version}"\n', encoding="utf-8"
        )
        (path / "CHANGELOG.md").write_text(
            f"# Changelog\n\n## Unreleased\n\n{unreleased}\n## {version} — 2026-07-18\n\n- Release.\n",
            encoding="utf-8",
        )
        return path

    def test_exact_clean_tag_and_versions_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            report = verify_release_safety(
                self._root(Path(temp)),
                expected_tag="v1.2.3",
                actual_ref="refs/tags/v1.2.3",
                git_status_text="",
            )
            self.assertTrue(report.ok, report.issues)
            self.assertEqual(report.version, "1.2.3")

    def test_invalid_ref_dirty_source_version_and_unreleased_changes_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._root(Path(temp), version="1.2.4", unreleased="- Not moved.\n")
            report = verify_release_safety(
                root,
                expected_tag="v1.2.3",
                actual_ref="refs/heads/main",
                git_status_text=" M VERSION\n",
            )
            codes = [issue.code for issue in report.issues]
            self.assertIn("tag_ref_mismatch", codes)
            self.assertIn("dirty_release_source", codes)
            self.assertEqual(codes.count("release_version_mismatch"), 4)
            self.assertIn("release_changelog_missing", codes)
            self.assertIn("unreleased_changes_present", codes)

    def test_rejects_malformed_tag_missing_files_and_symlinked_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "VERSION").symlink_to(root / "outside")
            report = verify_release_safety(
                root,
                expected_tag="latest",
                actual_ref="refs/tags/latest",
                git_status_text="",
            )
            codes = [issue.code for issue in report.issues]
            self.assertIn("invalid_release_tag", codes)
            self.assertIn("release_file_unsafe", codes)
            self.assertIn("release_file_missing", codes)

    def test_cli_fails_when_git_cleanliness_cannot_be_proven(self) -> None:
        with tempfile.TemporaryDirectory() as temp, mock.patch(
            "agent_starter.release_safety.subprocess.run", side_effect=OSError("git unavailable")
        ):
            self.assertEqual(
                main(["--root", temp, "--expected-tag", "v1.2.3", "--actual-ref", "refs/tags/v1.2.3"]),
                2,
            )

    def test_release_workflow_requires_manual_exact_tag_and_separates_write_authority(self) -> None:
        workflow = Path(".github/workflows/release.yml").read_text(encoding="utf-8")
        header, jobs = workflow.split("jobs:\n", 1)
        self.assertIn("workflow_dispatch:", header)
        self.assertNotIn("push:", header)
        self.assertNotIn("pull_request", header)
        self.assertNotIn("workflow_run", header)
        self.assertIn("permissions:\n  contents: read", header)
        self.assertEqual(validate_github_action_references(workflow), ())
        self.assertIn("refs/tags/", Path("agent_starter/release_safety.py").read_text(encoding="utf-8"))
        verify, publish = jobs.split("  publish_release:\n", 1)
        self.assertNotIn("contents: write", verify)
        self.assertIn("persist-credentials: false", verify)
        self.assertIn("./scripts/check.sh", verify)
        self.assertIn("release-artifact-smoke.sh", verify)
        self.assertIn("environment: release", publish)
        self.assertIn("contents: write", publish)
        self.assertNotIn("id-token: write", publish)
        self.assertNotIn("actions/checkout", publish)
        self.assertNotIn("actions/setup-python", publish)
        self.assertIn("needs.verify_release.result == 'success' && inputs.publish == true", publish)
        self.assertIn("sha256sum --check SHA256SUMS", publish)
        self.assertIn('commits/$RELEASE_TAG" --jq .sha', publish)
        self.assertIn("gh release create", publish)
        self.assertIn('--repo "$GITHUB_REPOSITORY"', publish)
        self.assertNotIn("--notes-from-tag", publish)
        self.assertIn('--notes "Omen AgentKit $RELEASE_TAG.', publish)
        self.assertIn("--draft", publish)
        self.assertIn('gh release edit "$RELEASE_TAG" --repo "$GITHUB_REPOSITORY" --draft=false', publish)
        self.assertNotIn("deploy", workflow.lower())
        self.assertNotIn("secrets.", workflow)

    def test_release_policy_documents_human_tag_and_draft_failure_boundary(self) -> None:
        policy = Path("docs/RELEASE-SAFETY.md").read_text(encoding="utf-8")
        for required in (
            "manual-only",
            "existing `vMAJOR.MINOR.PATCH` tag",
            "leaving `Unreleased` empty",
            "publish: false",
            "publish: true",
            "contents: write",
            "draft release",
            "does not publish to PyPI",
            "no rollback/delete path",
        ):
            self.assertIn(required, policy)


if __name__ == "__main__":
    unittest.main()
