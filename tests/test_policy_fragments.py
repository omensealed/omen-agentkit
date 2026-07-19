from __future__ import annotations

import unittest

from agent_starter.generator import build_file_map
from agent_starter.models import ProjectConfig
from agent_starter.policy_fragments import (
    CANONICAL_POLICIES,
    CODEX_DEPLOYMENT_BOUNDARY,
    find_policy_conflicts,
    render_canonical_policy_registry,
    render_prompt_policy_references,
)


class PolicyFragmentTests(unittest.TestCase):
    def test_registry_has_one_owner_set_for_each_durable_policy(self) -> None:
        self.assertEqual(
            tuple(CANONICAL_POLICIES),
            ("model", "command-network", "deployment", "progress-ledger", "implementation-notes"),
        )
        self.assertEqual(CANONICAL_POLICIES["model"].owners, (".agent-starter/project.json", ".codex/config.toml"))
        self.assertEqual(CANONICAL_POLICIES["progress-ledger"].owners, ("docs/09-PROGRESS.md",))
        self.assertEqual(CANONICAL_POLICIES["implementation-notes"].owners, ("docs/11-IMPLEMENTATION-NOTES.md",))
        self.assertEqual(CANONICAL_POLICIES["deployment"].owners[0], "AGENTS.md#canonical-policy-registry")

    def test_codex_deployment_boundary_is_exact_and_rendered_once_in_agents_policy(self) -> None:
        self.assertEqual(
            CODEX_DEPLOYMENT_BOUNDARY,
            (
                "Codex may prepare code, documentation, tests, and deployment plans.",
                "Codex may run local deployment plan, check, and build operations inside the configured sandbox.",
                "Codex must stop before remote apply, repository push, release publication, database migration, or secret access unless a separate human-approved tool operation is invoked.",
                'A prompt saying "deploy it" is not sufficient production authorization.',
            ),
        )
        rendered = render_canonical_policy_registry()
        for statement in CODEX_DEPLOYMENT_BOUNDARY:
            self.assertEqual(rendered.count(statement), 1)

    def test_prompt_renderer_references_owners_without_copying_long_safety_blocks(self) -> None:
        rendered = render_prompt_policy_references()
        self.assertIn("## Canonical policy references", rendered)
        for expected in (
            ".agent-starter/project.json",
            ".codex/config.toml",
            "AGENTS.md#canonical-policy-registry",
            "docs/09-PROGRESS.md",
            "docs/11-IMPLEMENTATION-NOTES.md",
        ):
            self.assertIn(expected, rendered)
        self.assertNotIn("OAuth tokens, API keys, cookies", rendered)
        self.assertNotIn("Do not run `sudo`", rendered)
        self.assertLessEqual(len(rendered.split()), 125)

    def test_conflict_detector_has_stable_codes_for_all_five_policies(self) -> None:
        cases = {
            "model.outdated-baseline": "GPT-5.5 remains the recommended complex-coding baseline.",
            "command-network.enabled": "network_access = true",
            "deployment.prompt-authority": "Deployment is authorized by this prompt.",
            "deployment.deploy-it-authority": 'A prompt saying "deploy it" is sufficient production authorization.',
            "progress-ledger.conflicting-path": "Use docs/10-PROGRESS.md as the progress ledger.",
            "implementation-notes.conflicting-path": "Append docs/12-IMPLEMENTATION-NOTES.md after work.",
        }
        for code, text in cases.items():
            with self.subTest(code=code):
                issues = find_policy_conflicts({"prompt.md": text})
                self.assertEqual([issue.code for issue in issues], [code])
                self.assertEqual(issues[0].path, "prompt.md")

    def test_generated_contract_has_no_policy_conflicts(self) -> None:
        config = ProjectConfig(
            project_name="Policy Test",
            project_slug="policy-test",
            project_path="/tmp/policy-test",
            project_type="cli",
            languages=["python"],
            database="sqlite",
            git_enabled=False,
        )
        rendered = build_file_map(config)
        self.assertEqual(find_policy_conflicts(rendered), [])
        combined = "\n".join(rendered.values())
        for policy in CANONICAL_POLICIES.values():
            with self.subTest(policy=policy.key):
                self.assertEqual(combined.count(policy.statement), 1)


if __name__ == "__main__":
    unittest.main()
