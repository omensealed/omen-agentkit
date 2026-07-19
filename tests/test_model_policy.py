from __future__ import annotations

import unittest

from agent_starter.model_policy import CodexModelPolicy, DEFAULT_CODEX_MODEL_POLICY
from agent_starter.template_sets.codex import render_codex_config, render_model_policy_summary


class ModelPolicyTests(unittest.TestCase):
    def test_quality_first_default_distinguishes_id_and_label(self) -> None:
        policy = DEFAULT_CODEX_MODEL_POLICY
        self.assertEqual(policy.model_id, "gpt-5.6-sol")
        self.assertEqual(policy.display_label, "GPT-5.6-SOL")
        self.assertEqual(policy.reasoning_effort, "medium")
        self.assertNotEqual(policy.model_id, policy.display_label)

    def test_explicit_and_inherited_codex_config(self) -> None:
        explicit = render_codex_config(CodexModelPolicy())
        self.assertIn('model = "gpt-5.6-sol"', explicit)
        self.assertIn('model_reasoning_effort = "medium"', explicit)
        self.assertIn('approval_policy = "on-request"', explicit)
        self.assertIn('sandbox_mode = "workspace-write"', explicit)
        self.assertIn('web_search = "cached"', explicit)
        self.assertIn("[sandbox_workspace_write]\nnetwork_access = false", explicit)

        inherited_policy = CodexModelPolicy(selection="inherit")
        inherited = render_codex_config(inherited_policy)
        self.assertNotIn("model =", inherited)
        self.assertNotIn("model_reasoning_effort =", inherited)
        self.assertIn("inherited", render_model_policy_summary(inherited_policy))
        self.assertIn('approval_policy = "on-request"', inherited)

    def test_unavailable_model_never_silently_falls_back(self) -> None:
        policy = CodexModelPolicy(model_id="reviewed-model", display_label="Reviewed Model")
        message = policy.unavailable_message()
        self.assertIn("did not downgrade", message)
        self.assertIn("Select inherited-global policy", message)
        self.assertNotIn("gpt-5.6-terra", message)

    def test_model_id_rejects_toml_injection(self) -> None:
        with self.assertRaises(ValueError):
            CodexModelPolicy(model_id='gpt-5.6-sol"\nnetwork_access=true').validate()


if __name__ == "__main__":
    unittest.main()
