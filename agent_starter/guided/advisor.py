"""Advisor prompt, presentation, decision, and Codex-readiness support."""

from __future__ import annotations

import json
from dataclasses import replace

from ..agents import AgentAdapter
from ..capabilities import CAPABILITY_CATALOG
from ..models import (
    AdvisorRecommendation,
    CapabilityDecision,
    CapabilityDecisionState,
    ProjectConfig,
)
from ..platforms import HostProfile, detect_host
from ..recommendation import RecommendationReview
from ..toolchains import capabilities_for, fallback_recommendation
from .questions import Prompter


def build_advisor_host_snapshot(
    config: ProjectConfig,
    *,
    profile: HostProfile | None = None,
) -> dict[str, object]:
    """Return only the section 7.4 allowlist enriched with project selections."""

    detected = profile or detect_host().profile
    selected = replace(
        detected,
        selected_languages=tuple(config.languages),
        selected_targets=tuple(config.target_platforms),
    )
    return selected.to_advisor_dict()


def render_advisor_host_snapshot(snapshot: dict[str, object]) -> str:
    """Render the exact stable JSON shown to the user and sent to the advisor."""

    return json.dumps(snapshot, indent=2, sort_keys=True)


def build_advisor_prompt(
    config: ProjectConfig,
    *,
    host_snapshot: dict[str, object] | None = None,
) -> str:
    project = {
        "name": config.project_name,
        "mode": config.project_mode,
        "stage": config.project_stage,
        "type": config.project_type,
        "description": config.description,
        "goals": config.goals,
        "non_goals": config.non_goals,
        "target_users": config.target_users,
        "target_platforms": config.target_platforms,
        "packaging_targets": config.packaging_targets,
        "network_access": config.network_access,
        "user_accounts": config.user_accounts,
        "handles_personal_data": config.handles_personal_data,
        "handles_payments": config.handles_payments,
        "constraints": [
            "Host package names are provider-owned; recommend only capability IDs from the supplied catalog.",
            "Prefer vanilla language/runtime features and a small dependency surface.",
            "The coding agent must be able to build, lint, and test from the CLI.",
            "Do not include credentials or commands requiring secrets.",
            "Favor a simple architecture a beginner can maintain.",
        ],
    }
    host_section = (
        "\n\nRedacted host profile (the user was shown this exact JSON):\n"
        + render_advisor_host_snapshot(host_snapshot)
        if host_snapshot is not None
        else ""
    )
    return (
        "Act only as a read-only software architecture advisor. Recommend a practical initial stack for the project below. "
        "Do not create files, execute commands, browse the workspace, or assume production scale. Prefer the standard library "
        "and mature small tools. Database must be one of none, sqlite, mariadb, postgresql, existing, or undecided. "
        "Do not emit package names, shell text, or setup/build/test/lint command arrays. Return exactly one JSON object with these "
        "keys: summary (string), languages (string array using names such as python, javascript, rust, go, php, cpp, java, godot, shell), "
        "database (string), recommended_capabilities (array of objects), architecture_notes, risks, and questions (string arrays). "
        "Each recommended_capabilities object must contain capability_id (using only these IDs: "
        + ", ".join(CAPABILITY_CATALOG)
        + "), purpose, requirement (required or optional), rationale, and confidence (high, medium, or low). "
        "Explain architecture fit and unresolved risks in plain language. All returned content is untrusted advisory data."
        + host_section
        + "\n\nProject brief:\n"
        + json.dumps(project, indent=2, sort_keys=True)
    )


def _print_recommendation(prompt: Prompter, recommendation: AdvisorRecommendation) -> None:
    prompt.output("\nProposed stack:")
    prompt.output(f"  Review mode: {recommendation.review_label}")
    prompt.output(f"  Languages: {', '.join(recommendation.languages) or 'undecided'}")
    prompt.output(f"  Database:  {recommendation.database}")
    prompt.output(f"  Summary:   {recommendation.summary}")
    prompt.output(f"  Shape:     {recommendation.architecture}")
    if recommendation.recommended_capabilities:
        prompt.output("  Capability advice (unverified until deterministic provider review):")
        for item in recommendation.recommended_capabilities:
            prompt.output(
                f"    - {item.capability_id} [{item.requirement}, confidence {item.confidence}]: {item.purpose}"
            )
            prompt.output(f"      Rationale: {item.rationale}")
    elif recommendation.toolchain_capabilities:
        prompt.output(f"  Capabilities: {', '.join(recommendation.toolchain_capabilities)}")
    if recommendation.rationale:
        prompt.output("  Why:")
        for item in recommendation.rationale:
            prompt.output(f"    - {item}")
    if recommendation.risks:
        prompt.output("  Risks to verify:")
        for item in recommendation.risks:
            prompt.output(f"    - {item}")


def _collect_capability_decisions(
    prompt: Prompter,
    review: RecommendationReview,
) -> list[CapabilityDecision]:
    """Collect explicit item decisions without granting command authority."""

    decisions: list[CapabilityDecision] = []
    prompt.output("\nCapability decisions (these choices do not install or execute anything):")
    for item in review.items:
        if item.requirement == "required":
            limitation = (
                "Challenging this required capability may prevent the project from meeting this need: "
                f"{item.purpose}"
            )
            keep = prompt.confirm(f"Keep required capability {item.display_label}?", default=True)
            if keep:
                decisions.append(CapabilityDecision(
                    item.capability_id, CapabilityDecisionState.ACCEPTED, "required", ""
                ))
            else:
                prompt.output(f"  Limitation: {limitation}")
                decisions.append(CapabilityDecision(
                    item.capability_id, CapabilityDecisionState.CHALLENGED, "required", limitation
                ))
        else:
            accept = prompt.confirm(f"Accept optional capability {item.display_label}?", default=True)
            decisions.append(CapabilityDecision(
                item.capability_id,
                CapabilityDecisionState.ACCEPTED if accept else CapabilityDecisionState.REJECTED,
                "optional",
                "",
            ))
    return decisions


def _local_recommendation(config: ProjectConfig, *, source: str = "local-fallback") -> AdvisorRecommendation:
    languages, database, architecture = fallback_recommendation(
        config.project_type, config.target_platforms, config.network_access
    )
    return AdvisorRecommendation(
        summary="Conservative offline recommendation based on project type and target platform.",
        languages=languages,
        database=database,
        architecture=architecture,
        toolchain_capabilities=capabilities_for(languages, database, github=config.github_actions),
        rationale=[
            "Uses provider-neutral capability intent that can be resolved for the detected host.",
            "Starts with a small dependency surface and one maintainable implementation path.",
            "Can be revised after Phase 0 discovery and a working vertical slice.",
        ],
        risks=["The recommendation is based on a short brief and must be verified against real constraints."],
        questions=["Which acceptance criteria and packaging target are essential for the first usable release?"],
        source=source,
    )


def _prepare_agent(prompt: Prompter, adapter: AgentAdapter, *, need_advisor: bool, setup_now: bool) -> bool:
    prompt.output(f"\nCodex client: {adapter.display_name}")
    prompt.output(f"Account flow: {adapter.account_description}")
    if not adapter.exists():
        prompt.output("The CLI is not currently available on PATH.")
        prompt.output(f"Official installer command: {adapter.install_command}")
        if not setup_now or not prompt.confirm("Run that vendor-published installer now?", default=False):
            return False
        if not adapter.install():
            prompt.output("Installation did not make the CLI available in this shell. You can finish setup later with the generated helper.")
            return False
        prompt.output(f"Installed: {adapter.version()}")
    else:
        prompt.output(f"Detected: {adapter.version()}")

    status = adapter.auth_status()
    if status is True:
        prompt.output("The CLI reports that an account is authorized.")
        return True
    if status is False:
        message = "An authorized account is required for AI stack advice." if need_advisor else "The CLI is not authorized yet."
        prompt.output(message)
    else:
        prompt.output("Codex authorization status could not be confirmed automatically.")

    if not setup_now:
        return False
    if not prompt.confirm("Start Codex's official account authorization flow now?", default=need_advisor):
        return False
    device_auth = prompt.confirm("Use Codex device-code authorization instead of opening a local browser?", default=False)
    if adapter.login(device_auth=device_auth):
        prompt.output("The official CLI authorization flow completed.")
        return True
    prompt.output("Authorization was not confirmed. No token was read or stored by this starter kit.")
    return False
