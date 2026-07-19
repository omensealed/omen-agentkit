"""Codex configuration and policy text templates."""

from __future__ import annotations

import json
from collections.abc import Callable

from ..model_policy import CodexModelPolicy, DEFAULT_CODEX_WORKSPACE_POLICY


def render_model_policy_summary(policy: CodexModelPolicy) -> str:
    if policy.selection == "inherit":
        return "inherited global Codex model and reasoning settings"
    return f"{policy.display_label} (exact ID `{policy.model_id}`), {policy.reasoning_effort} reasoning"


def render_codex_config(policy: CodexModelPolicy) -> str:
    """Render supported Codex keys while keeping command networking disabled."""

    policy.validate()
    lines = [
        "# Project-local safe defaults. Codex loads project config only after the workspace is trusted.",
    ]
    if policy.selection == "explicit":
        lines.extend(
            [
                f"model = {json.dumps(policy.model_id)}",
                f"model_reasoning_effort = {json.dumps(policy.reasoning_effort)}",
            ]
        )
    else:
        lines.append("# Model and reasoning are inherited from the user's global Codex configuration.")
    workspace_policy = DEFAULT_CODEX_WORKSPACE_POLICY
    lines.extend(
        [
            f"approval_policy = {json.dumps(workspace_policy.approval_policy)}",
            f"sandbox_mode = {json.dumps(workspace_policy.sandbox_mode)}",
            f"web_search = {json.dumps(workspace_policy.web_search)}",
            "",
            "[sandbox_workspace_write]",
            f"network_access = {str(workspace_policy.command_network_access).lower()}",
            "",
        ]
    )
    return "\n".join(lines)


CODEX_TEMPLATE_REGISTRY: dict[str, Callable[[CodexModelPolicy], str]] = {
    ".codex/config.toml": render_codex_config,
}
