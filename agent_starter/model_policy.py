"""Typed Codex model selection policy.

The exact model identifier is deliberately separate from its human display
label.  AgentKit never guesses a fallback model: unavailable explicit models
must be resolved by a human policy choice.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any


MODEL_SELECTIONS = frozenset({"explicit", "inherit"})
REASONING_EFFORTS = frozenset({"low", "medium", "high", "xhigh"})
FALLBACK_BEHAVIORS = frozenset({"ask", "error"})
MODEL_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


@dataclass(frozen=True, slots=True)
class CodexModelPolicy:
    """Project-level Codex model policy with no silent fallback path."""

    provider: str = "openai"
    model_id: str = "gpt-5.6-sol"
    display_label: str = "GPT-5.6-SOL"
    reasoning_effort: str = "medium"
    selection: str = "explicit"
    allow_task_routing: bool = False
    fallback_behavior: str = "ask"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "CodexModelPolicy":
        if data is None:
            return cls()
        if not isinstance(data, dict):
            raise ValueError("model_policy must be a JSON object.")
        allowed = cls.__dataclass_fields__
        unknown = sorted(set(data) - set(allowed))
        if unknown:
            raise ValueError(f"Unknown model_policy field(s): {', '.join(unknown)}")
        policy = cls(**{name: data[name] for name in allowed if name in data})
        policy.validate()
        return policy

    def validate(self) -> None:
        for name in ("provider", "model_id", "display_label", "reasoning_effort", "selection", "fallback_behavior"):
            if not isinstance(getattr(self, name), str):
                raise ValueError(f"model_policy.{name} must be text.")
        if self.provider != "openai":
            raise ValueError("model_policy.provider must remain 'openai' in the Codex-only edition.")
        if self.selection not in MODEL_SELECTIONS:
            raise ValueError("model_policy.selection must be 'explicit' or 'inherit'.")
        if self.reasoning_effort not in REASONING_EFFORTS:
            raise ValueError("model_policy.reasoning_effort must be low, medium, high, or xhigh.")
        if self.fallback_behavior not in FALLBACK_BEHAVIORS:
            raise ValueError("model_policy.fallback_behavior must be 'ask' or 'error'.")
        if not isinstance(self.allow_task_routing, bool):
            raise ValueError("model_policy.allow_task_routing must be a JSON boolean.")
        if self.selection == "explicit" and not MODEL_ID_RE.fullmatch(self.model_id):
            raise ValueError("An explicit model policy requires a safe exact model_id.")
        if not self.display_label.strip():
            raise ValueError("model_policy.display_label must not be empty.")

    def unavailable_message(self) -> str:
        """Return the required human-facing failure; never select a fallback."""

        return (
            f"The explicit Codex model {self.model_id!r} is unavailable. "
            "AgentKit did not downgrade it. Select inherited-global policy or "
            "review and explicitly choose another supported model policy."
        )

    def launch_failure_message(self) -> str:
        return (
            f"Codex launch failed while the explicit model policy was {self.model_id!r}. "
            "Verify that this exact model is available to the current account. AgentKit will not "
            "downgrade it; select inherited-global policy or explicitly review another model policy."
        )


DEFAULT_CODEX_MODEL_POLICY = CodexModelPolicy()


@dataclass(frozen=True, slots=True)
class CodexWorkspacePolicy:
    """Conservative project-local Codex settings shared by generation and launch review."""

    approval_policy: str = "on-request"
    sandbox_mode: str = "workspace-write"
    command_network_access: bool = False
    web_search: str = "cached"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


DEFAULT_CODEX_WORKSPACE_POLICY = CodexWorkspacePolicy()
