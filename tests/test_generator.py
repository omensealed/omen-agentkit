from __future__ import annotations

import json
import hashlib
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from time import sleep

from agent_starter.generator import (
    EXECUTABLE_FILES,
    REQUIRED_FILES,
    ValidationReport,
    _codex_scripts,
    _manifest,
    _new_note_script,
    _redacted_config_dict,
    _shell_files,
    build_file_map,
    generate_project,
    validate_project,
)
from agent_starter.generation import registry
from agent_starter.generation import service
from agent_starter.generation import validation
from agent_starter.models import (
    AdvisorRecommendation,
    CapabilityDecision,
    CapabilityDecisionState,
    ProjectConfig,
)


class GeneratorTests(unittest.TestCase):
    def test_generation_service_preserves_exports_and_dry_run_nonmutation(self) -> None:
        from agent_starter import generator

        exports = (
            (generator.GenerationReport, service.GenerationReport),
            (generator._timestamp, service._timestamp),
            (generator._safe_relative, service._safe_relative),
            (generator._assert_safe_root, service._assert_safe_root),
            (generator._assert_no_symlink_parent, service._assert_no_symlink_parent),
            (generator._atomic_write, service._atomic_write),
            (generator._reuse_existing_generation_timestamps, service._reuse_existing_generation_timestamps),
            (generate_project, service.generate_project),
        )
        for legacy, moved in exports:
            self.assertIs(legacy, moved)

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "dry-run-project"
            mutations: list[bool] = []
            report = generate_project(
                self.make_config(root),
                dry_run=True,
                _mutation_observer=lambda: mutations.append(True),
            )
            self.assertFalse(root.exists())
            self.assertEqual(mutations, [])
            self.assertEqual(report.root, root.resolve())
            self.assertIn("AGENTS.md", report.created)
            self.assertEqual(report.validation_errors, [])

    def test_validation_module_preserves_exports_and_missing_root_diagnostic(self) -> None:
        self.assertIs(ValidationReport, validation.ValidationReport)
        self.assertIs(_shell_files, validation._shell_files)
        self.assertIs(validate_project, validation.validate_project)
        with tempfile.TemporaryDirectory() as temp:
            missing = (Path(temp) / "missing").resolve()
            report = validate_project(missing)
        self.assertIsInstance(report, ValidationReport)
        self.assertEqual(report.root, missing)
        self.assertEqual(report.errors, [f"Project directory does not exist: {missing}"])
        self.assertEqual(report.warnings, [])
        self.assertEqual(report.checked, [])
        self.assertFalse(report.ok)

    def test_artifact_registry_preserves_exports_and_aggregate_bytes(self) -> None:
        exports = (
            (REQUIRED_FILES, registry.REQUIRED_FILES),
            (EXECUTABLE_FILES, registry.EXECUTABLE_FILES),
            (_redacted_config_dict, registry._redacted_config_dict),
            (_codex_scripts, registry._codex_scripts),
            (_new_note_script, registry._new_note_script),
            (build_file_map, registry.build_file_map),
            (_manifest, registry._manifest),
        )
        for legacy, moved in exports:
            self.assertIs(legacy, moved)

        config = ProjectConfig(
            project_name="Registry Lock",
            project_slug="registry-lock",
            project_path="/tmp/registry-lock",
            project_mode="existing",
            project_type="web",
            languages=["python", "javascript"],
            database="sqlite",
            git_enabled=False,
            github_actions=True,
            created_at="2026-01-02T03:04:05Z",
            updated_at="2026-01-02T03:04:05Z",
        )
        files = build_file_map(config)
        digest = hashlib.sha256()
        for path, content in sorted(files.items()):
            digest.update(path.encode())
            digest.update(b"\0")
            digest.update(content.encode())
            digest.update(b"\0")
        self.assertEqual(len(files), 49)
        self.assertEqual(digest.hexdigest(), "9e9f438ff708fc39fe81874030564efa724374d6503ffb68b9fd30cc0b2633b9")

    def make_config(self, root: Path, **overrides: object) -> ProjectConfig:
        values: dict[str, object] = {
            "project_name": "Generated Test",
            "project_slug": "generated-test",
            "project_path": str(root),
            "project_mode": "new",
            "project_type": "cli",
            "description": "A generated test project.",
            "languages": ["python"],
            "database": "sqlite",
            "primary_agent": "codex",
            "github_actions": True,
            "git_enabled": False,
        }
        values.update(overrides)
        return ProjectConfig(**values)

    def test_generation_and_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            config = self.make_config(
                root,
                advisor=AdvisorRecommendation(
                    summary="Structured test recommendation.",
                    raw_output="terminal noise",
                    source="test",
                ),
                capability_decisions=[
                    CapabilityDecision(
                        "language.python", CapabilityDecisionState.ACCEPTED, "required", ""
                    ),
                    CapabilityDecision(
                        "database.sqlite", CapabilityDecisionState.CHALLENGED, "required",
                        "SQLite-backed persistence will not be available.",
                    ),
                ],
            )
            report = generate_project(config)
            self.assertTrue(report.ok, report.validation_errors)
            for relative in REQUIRED_FILES:
                self.assertTrue((root / relative).is_file(), relative)
            deployment = (root / "docs/16-DEPLOYMENT.md").read_text(encoding="utf-8")
            self.assertIn("# Deployment planning", deployment)
            self.assertIn("No deployment target is selected or approved by generation", deployment)
            self.assertTrue(os.access(root / "START_AGENT.sh", os.X_OK))
            self.assertTrue((root / ".codex/config.toml").is_file())
            codex_config = (root / ".codex/config.toml").read_text(encoding="utf-8")
            self.assertIn('model = "gpt-5.6-sol"', codex_config)
            self.assertIn('model_reasoning_effort = "medium"', codex_config)
            self.assertIn('approval_policy = "on-request"', codex_config)
            self.assertIn('sandbox_mode = "workspace-write"', codex_config)
            self.assertIn('web_search = "cached"', codex_config)
            self.assertIn("[sandbox_workspace_write]\nnetwork_access = false", codex_config)
            rsync_excludes = (root / ".agent-starter/rsync-excludes").read_text(encoding="utf-8")
            self.assertIn(".git/", rsync_excludes)
            self.assertIn(".agent-starter/proposals/", rsync_excludes)
            self.assertIn(".codex/sessions/", rsync_excludes)
            next_steps = (root / "NEXT_STEPS.md").read_text(encoding="utf-8")
            self.assertIn("Keep GitHub local-first", next_steps)
            self.assertIn("placeholder", next_steps)
            self.assertIn("./START_AGENT.sh", next_steps)
            start_here = (root / "START_HERE.md").read_text(encoding="utf-8")
            self.assertIn("## Project summary", start_here)
            self.assertIn("## First safe local commands", start_here)
            self.assertLessEqual(len(start_here.split()), 260)
            agent_index = (root / "docs/AGENT-INDEX.md").read_text(encoding="utf-8")
            self.assertIn("## Project and module map", agent_index)
            self.assertIn("## Minimum files by task type", agent_index)
            self.assertLessEqual(len(agent_index.split()), 650)
            self.assertIn(
                "OpenAI Codex CLI is the sole intended coding agent",
                (root / "AGENTS.md").read_text(encoding="utf-8"),
            )
            agents = (root / "AGENTS.md").read_text(encoding="utf-8")
            architecture = (root / "docs/02-ARCHITECTURE.md").read_text(encoding="utf-8")
            for document in (agents, architecture):
                self.assertIn("## Modularity contract", document)
                self.assertIn("Identify the existing module responsible before editing", document)
                self.assertIn("Preserve compatibility at public interfaces", document)
            saved = json.loads((root / ".agent-starter/project.json").read_text())
            self.assertEqual(saved["advisor"]["raw_output"], "")
            self.assertEqual(saved["capability_decisions"][0]["decision"], "accepted")
            self.assertEqual(saved["capability_decisions"][1]["decision"], "challenged")
            advisor_doc = (root / "docs/AI-STACK-RECOMMENDATION.md").read_text(encoding="utf-8")
            self.assertIn("Human capability decisions", advisor_doc)
            self.assertIn("AI-reviewed structured recommendation", advisor_doc)
            self.assertIn("SQLite-backed persistence will not be available", advisor_doc)
            self.assertIn("do not authorize package installation or command execution", advisor_doc)
            self.assertTrue(validate_project(root).ok)

    def test_generated_gitignore_excludes_ai_local_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            config = self.make_config(root)
            report = generate_project(config)
            self.assertTrue(report.ok, report.validation_errors)
            gitignore = (root / ".gitignore").read_text(encoding="utf-8")
            for expected in (
                "AGENTS.md",
                "FIRST_PROMPT.md",
                "FIRST_RUN_AUTONOMOUS.md",
                ".agents/",
                ".codex/",
                ".agent-starter/",
                ".codex/*.jsonl",
                ".codex/sessions/",
                ".agent-starter/runtime.json",
                ".agent-starter/proposals/",
                "docs/09-PROGRESS.md",
                "docs/11-IMPLEMENTATION-NOTES.md",
                "docs/14-AGENT-HANDOFF.md",
                "docs/AI-STACK-RECOMMENDATION.md",
                "docs/agent-prompts/",
                "!.env.sandbox.example",
                "!.env.*.example",
                "NEXT_PROMPT.md",
                "LOCAL_MODEL_HANDOFF.md",
                "*-codex-prompt.md",
            ):
                self.assertIn(expected, gitignore)
            rsync_excludes = (root / ".agent-starter/rsync-excludes").read_text(encoding="utf-8")
            self.assertNotIn("!.env.sandbox.example", rsync_excludes)
            self.assertNotIn(".env.sandbox.example", rsync_excludes)
            self.assertNotIn("\n.env.*\n", f"\n{rsync_excludes}\n")
            self.assertIn(".env.local", rsync_excludes)

    def test_validation_rejects_mutable_managed_action_references(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            config = self.make_config(root, github_actions=True)
            report = generate_project(config)
            self.assertTrue(report.ok, report.validation_errors)
            workflow = root / ".github/workflows/ci.yml"
            original = workflow.read_text(encoding="utf-8")
            workflow.write_text(
                original.replace(
                    "actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0 # v7.0.0",
                    "actions/checkout@v7 # v7.0.0",
                ),
                encoding="utf-8",
            )
            validation_report = validate_project(root)
            self.assertFalse(validation_report.ok)
            self.assertTrue(any("mutable_action_reference" in error for error in validation_report.errors))

    def test_generated_gitignore_keeps_ai_memory_local_and_enduser_docs_trackable(self) -> None:
        if shutil.which("git") is None:
            self.skipTest("git is not installed")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            config = self.make_config(root)
            report = generate_project(config)
            self.assertTrue(report.ok, report.validation_errors)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)

            ignored = (
                "AGENTS.md",
                "FIRST_PROMPT.md",
                "docs/09-PROGRESS.md",
                "docs/11-IMPLEMENTATION-NOTES.md",
                "docs/14-AGENT-HANDOFF.md",
                "docs/agent-prompts/example.md",
                ".agent-starter/project.json",
                ".agents/skills/agentkit/SKILL.md",
                ".codex/config.toml",
            )
            check_ignored = subprocess.run(["git", "check-ignore", *ignored], cwd=root, text=True, capture_output=True)
            self.assertEqual(check_ignored.returncode, 0, check_ignored.stderr)
            for expected in ignored:
                self.assertIn(expected, check_ignored.stdout)

            trackable = (
                "README.md",
                "START_HERE.md",
                "NEXT_STEPS.md",
                "LICENSE",
                "SECURITY.md",
                "CONTRIBUTING.md",
                "docs/00-PROJECT-BRIEF.md",
                "docs/01-REQUIREMENTS.md",
                "docs/02-ARCHITECTURE.md",
                "docs/AGENT-INDEX.md",
                "docs/10-DECISIONS.md",
                "docs/12-RELEASE-CHECKLIST.md",
                "docs/16-DEPLOYMENT.md",
            )
            check_trackable = subprocess.run(["git", "check-ignore", *trackable], cwd=root, text=True, capture_output=True)
            self.assertEqual(check_trackable.returncode, 1, check_trackable.stdout)

    def test_default_license_is_agpl(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            report = generate_project(self.make_config(root))
            self.assertTrue(report.ok, report.validation_errors)
            license_text = (root / "LICENSE").read_text(encoding="utf-8")
            self.assertIn("SPDX-License-Identifier: AGPL-3.0-or-later", license_text)
            saved = json.loads((root / ".agent-starter/project.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["license_name"], "AGPL-3.0-or-later")

    def test_spdx_license_files_are_generated(self) -> None:
        cases = {
            "Apache-2.0": "SPDX-License-Identifier: Apache-2.0",
            "BSD-3-Clause": "SPDX-License-Identifier: BSD-3-Clause",
            "GPL-3.0-or-later": "SPDX-License-Identifier: GPL-3.0-or-later",
            "AGPL-3.0-or-later": "SPDX-License-Identifier: AGPL-3.0-or-later",
            "MPL-2.0": "SPDX-License-Identifier: MPL-2.0",
        }
        with tempfile.TemporaryDirectory() as temp:
            for license_name, expected in cases.items():
                with self.subTest(license_name=license_name):
                    root = Path(temp) / license_name.lower().replace(".", "-")
                    config = self.make_config(root, license_name=license_name)
                    report = generate_project(config)
                    self.assertTrue(report.ok, report.validation_errors)
                    license_text = (root / "LICENSE").read_text(encoding="utf-8")
                    self.assertIn(expected, license_text)

    def test_unchanged_generation_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            config = self.make_config(root)
            first_mutations: list[bool] = []
            second_mutations: list[bool] = []
            first = generate_project(config, _mutation_observer=lambda: first_mutations.append(True))
            second = generate_project(config, _mutation_observer=lambda: second_mutations.append(True))
            self.assertTrue(first.created)
            self.assertTrue(first_mutations)
            self.assertFalse(second.conflicts)
            self.assertFalse(second.created)
            self.assertTrue(second.unchanged)
            self.assertEqual(second_mutations, [])

    def test_fresh_config_regeneration_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            first = generate_project(self.make_config(root))
            sleep(1.1)
            second = generate_project(self.make_config(root))
            self.assertTrue(first.created)
            self.assertFalse(second.conflicts)
            self.assertFalse(second.created)
            self.assertIn(".agent-starter/manifest.json", second.unchanged)
            self.assertIn(".agent-starter/project.json", second.unchanged)
            self.assertIn(".agents/skills/agentkit/agentkit-skill.json", second.unchanged)

    def test_existing_start_here_is_preserved_as_a_proposal_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            root.mkdir()
            original = "# My existing start page\n\nKeep this human-written content.\n"
            (root / "START_HERE.md").write_text(original, encoding="utf-8")
            report = generate_project(self.make_config(root, project_mode="existing"))
            self.assertTrue(report.ok, report.validation_errors)
            self.assertEqual((root / "START_HERE.md").read_text(encoding="utf-8"), original)
            self.assertIn("START_HERE.md", report.conflicts)
            proposal_paths = [Path(path) for path in report.proposals if path.endswith("START_HERE.md")]
            self.assertEqual(len(proposal_paths), 1)
            self.assertIn("## Project summary", (root / proposal_paths[0]).read_text(encoding="utf-8"))

    def test_existing_agent_index_is_preserved_as_a_proposal_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            (root / "docs").mkdir(parents=True)
            original = "# Existing agent map\n\nKeep this repository-specific map.\n"
            (root / "docs/AGENT-INDEX.md").write_text(original, encoding="utf-8")
            report = generate_project(self.make_config(root, project_mode="existing"))
            self.assertTrue(report.ok, report.validation_errors)
            self.assertEqual((root / "docs/AGENT-INDEX.md").read_text(encoding="utf-8"), original)
            self.assertIn("docs/AGENT-INDEX.md", report.conflicts)
            proposals = [Path(path) for path in report.proposals if path.endswith("docs/AGENT-INDEX.md")]
            self.assertEqual(len(proposals), 1)
            self.assertIn("## Minimum files by task type", (root / proposals[0]).read_text(encoding="utf-8"))

    def test_existing_deployment_doc_is_preserved_as_a_proposal_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            (root / "docs").mkdir(parents=True)
            original = "# Existing deployment runbook\n\nKeep this repository-specific content.\n"
            (root / "docs/16-DEPLOYMENT.md").write_text(original, encoding="utf-8")
            report = generate_project(self.make_config(root, project_mode="existing"))
            self.assertTrue(report.ok, report.validation_errors)
            self.assertEqual((root / "docs/16-DEPLOYMENT.md").read_text(encoding="utf-8"), original)
            self.assertIn("docs/16-DEPLOYMENT.md", report.conflicts)
            proposals = [Path(path) for path in report.proposals if path.endswith("docs/16-DEPLOYMENT.md")]
            self.assertEqual(len(proposals), 1)
            self.assertIn("## Authority and maturity", (root / proposals[0]).read_text(encoding="utf-8"))

    def test_conflict_is_preserved_as_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            config = self.make_config(root)
            generate_project(config)
            (root / "README.md").write_text("user content\n", encoding="utf-8")
            report = generate_project(config)
            self.assertIn("README.md", report.conflicts)
            self.assertEqual((root / "README.md").read_text(), "user content\n")
            self.assertTrue(any(path.endswith("README.md") for path in report.proposals))

    def test_force_backs_up_before_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            config = self.make_config(root)
            generate_project(config)
            (root / "README.md").write_text("old\n", encoding="utf-8")
            report = generate_project(config, force=True)
            self.assertIn("README.md", report.overwritten)
            self.assertTrue(any(path.endswith("README.md") for path in report.backups))
            self.assertNotEqual((root / "README.md").read_text(), "old\n")


    def test_invalid_package_name_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config = self.make_config(Path(temp) / "project", cachyos_packages=["--overwrite=*"])
            with self.assertRaises(ValueError):
                generate_project(config)

    def test_v1_arch_packages_survive_generation_without_other_provider_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            config = ProjectConfig.from_dict(
                {
                    "schema_version": 1,
                    "project_name": "V1 Arch Extras",
                    "project_path": str(root),
                    "project_mode": "new",
                    "database": "none",
                    "primary_agent": "codex",
                    "git_enabled": False,
                    "cachyos_packages": ["arch-only-extra"],
                }
            )
            self.assertTrue(generate_project(config).ok)
            saved = json.loads((root / ".agent-starter/project.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["extra_packages_by_provider"]["arch"], ["arch-only-extra"])
            self.assertNotIn("debian", saved["extra_packages_by_provider"])
            bootstrap = (root / "scripts/bootstrap-dev.sh").read_text(encoding="utf-8")
            arch_line = next(line for line in bootstrap.splitlines() if line.startswith("ARCH_PACKAGES="))
            debian_line = next(line for line in bootstrap.splitlines() if line.startswith("DEBIAN_PACKAGES="))
            ubuntu_line = next(line for line in bootstrap.splitlines() if line.startswith("UBUNTU_PACKAGES="))
            self.assertIn("arch-only-extra", arch_line)
            self.assertNotIn("arch-only-extra", debian_line)
            self.assertNotIn("arch-only-extra", ubuntu_line)

    def test_existing_schema_v1_metadata_remains_valid(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            self.assertTrue(generate_project(self.make_config(root)).ok)
            metadata = root / ".agent-starter/project.json"
            data = json.loads(metadata.read_text(encoding="utf-8"))
            data["schema_version"] = 1
            metadata.write_text(json.dumps(data), encoding="utf-8")
            report = validate_project(root)
            self.assertTrue(report.ok)
            self.assertNotIn("Unknown project.json schema version.", report.warnings)

    def test_generated_authoritative_content_has_no_gpt_5_5_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            self.assertTrue(generate_project(self.make_config(root)).ok)
            for path in root.rglob("*"):
                if path.is_file():
                    self.assertNotIn("gpt-5.5", path.read_text(encoding="utf-8", errors="ignore"), str(path))

    def test_symlinked_proposals_directory_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = base / "project"
            config = self.make_config(root)
            generate_project(config)
            (root / "README.md").write_text("user content\n", encoding="utf-8")
            outside = base / "outside"
            outside.mkdir()
            proposals = root / ".agent-starter" / "proposals"
            proposals.symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                generate_project(config)
            self.assertFalse(any(outside.iterdir()))

    def test_dangerous_root_is_rejected(self) -> None:
        config = self.make_config(Path.home())
        with self.assertRaises(ValueError):
            generate_project(config, dry_run=True)


if __name__ == "__main__":
    unittest.main()
