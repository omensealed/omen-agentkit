"""Structured, read-only host readiness reporting.

Doctor detects the provider before asking it narrowly about required package
state.  It never constructs or executes update/install plans and its JSON
surface deliberately excludes executable paths and host identity.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable

from .capabilities import CAPABILITY_CATALOG
from .platforms import (
    ArchProvider,
    CapabilityRequest,
    CommandResult,
    DebianFamilyProvider,
    DetectionResult,
    PlatformProvider,
    SupportLevel,
)


ExecutableLookup = Callable[[str], str | None]
ProviderRunner = Callable[[tuple[str, ...]], CommandResult]


class DoctorStatus(str, Enum):
    PASS = "pass"
    ACTION_NEEDED = "action-needed"
    OPTIONAL = "optional"
    BLOCKED = "blocked"
    UNVERIFIED = "unverified"


@dataclass(frozen=True, slots=True)
class CodexDoctorState:
    installed: bool
    version: str
    authorized: bool | None

    def __post_init__(self) -> None:
        if not isinstance(self.installed, bool):
            raise TypeError("Codex installed state must be a boolean.")
        if (
            not isinstance(self.version, str)
            or any(ord(character) < 32 for character in self.version)
            or len(self.version) > 500
        ):
            raise ValueError("Codex version must be bounded single-line text without control characters.")
        if self.authorized is not None and not isinstance(self.authorized, bool):
            raise TypeError("Codex authorization state must be a boolean or None.")


@dataclass(frozen=True, slots=True)
class DoctorFinding:
    code: str
    status: DoctorStatus
    title: str
    explanation: str
    remedy: str = ""
    capability_id: str | None = None
    evidence: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "status": self.status.value,
            "title": self.title,
            "capability_id": self.capability_id,
            "explanation": self.explanation,
            "remedy": self.remedy,
            "evidence": list(self.evidence),
        }


@dataclass(frozen=True, slots=True)
class DoctorReport:
    kit_version: str
    python_version: str
    detection: DetectionResult
    findings: tuple[DoctorFinding, ...]

    @property
    def overall_status(self) -> DoctorStatus:
        statuses = {finding.status for finding in self.findings}
        for status in (
            DoctorStatus.BLOCKED,
            DoctorStatus.ACTION_NEEDED,
            DoctorStatus.UNVERIFIED,
            DoctorStatus.PASS,
        ):
            if status in statuses:
                return status
        return DoctorStatus.OPTIONAL

    @property
    def exit_code(self) -> int:
        # Compatibility: doctor historically failed only on platform-detection
        # errors. Missing tools remain actionable output, not a hard failure.
        return 2 if self.overall_status is DoctorStatus.BLOCKED else 0

    def to_dict(self) -> dict[str, object]:
        profile = self.detection.profile
        return {
            "schema_version": 1,
            "overall_status": self.overall_status.value,
            "starter_kit_version": self.kit_version,
            "python_version": self.python_version,
            "host": {
                "os_id": profile.os_id,
                "os_id_like": list(profile.os_id_like),
                "pretty_name": profile.pretty_name,
                "version_id": profile.version_id,
                "architecture": profile.architecture,
            },
            "provider": {
                "id": profile.package_provider,
                "detected_id": self.detection.detected_provider,
                "package_manager": self.detection.package_manager,
                "support": self.detection.support.value,
                "confidence": self.detection.confidence.value,
            },
            "findings": [finding.to_dict() for finding in self.findings],
        }


def provider_for_detection(
    detection: DetectionResult,
    *,
    runner: ProviderRunner | None = None,
) -> PlatformProvider | None:
    """Return only the provider selected by prior metadata-first detection."""

    provider_id = detection.profile.package_provider
    if provider_id == "arch":
        return ArchProvider(**({"runner": runner} if runner is not None else {}))
    if provider_id in {"debian", "ubuntu"}:
        return DebianFamilyProvider(provider_id, **({"runner": runner} if runner is not None else {}))
    return None


def _platform_finding(detection: DetectionResult) -> DoctorFinding:
    profile = detection.profile
    if profile.package_provider is None or detection.support in {SupportLevel.UNSUPPORTED, SupportLevel.UNKNOWN}:
        return DoctorFinding(
            "platform-provider",
            DoctorStatus.BLOCKED,
            "Supported platform provider",
            "No supported package provider can be selected safely from OS metadata.",
            "Use CachyOS/Arch, Debian, or Ubuntu, or provide a reviewed override whose package-manager proof passes.",
        )
    if detection.has_errors:
        return DoctorFinding(
            "platform-provider",
            DoctorStatus.BLOCKED,
            "Supported platform provider",
            f"Provider {profile.package_provider} could not be confirmed safely.",
            "Resolve the reported detection error before using provider operations.",
        )
    status = DoctorStatus.PASS if detection.support is SupportLevel.SUPPORTED else DoctorStatus.ACTION_NEEDED
    return DoctorFinding(
        "platform-provider",
        status,
        "Supported platform provider",
        f"Provider {profile.package_provider} was selected from OS metadata before capability checks.",
        "Review the detection warning before provider operations." if status is DoctorStatus.ACTION_NEEDED else "",
        evidence=(f"support: {detection.support.value}", f"confidence: {detection.confidence.value}"),
    )


def _package_manager_finding(detection: DetectionResult) -> DoctorFinding | None:
    manager = detection.package_manager
    if manager is None:
        return None
    fact = next((item for item in detection.profile.executables if item.name == manager), None)
    available = bool(fact and fact.available)
    return DoctorFinding(
        "package-manager",
        DoctorStatus.PASS if available else DoctorStatus.ACTION_NEEDED,
        f"{manager} provider executable",
        f"The selected {detection.profile.package_provider} provider requires {manager} for read-only package checks.",
        f"Install or restore {manager}, then rerun doctor." if not available else "",
        evidence=(f"{manager}: {'available' if available else 'missing'}",),
    )


def _base_tooling_finding(
    provider: PlatformProvider | None,
    *,
    query_enabled: bool,
) -> DoctorFinding | None:
    if provider is None:
        return None
    definition = CAPABILITY_CATALOG["base.tooling"]
    if not query_enabled:
        return DoctorFinding(
            "base-tooling",
            DoctorStatus.UNVERIFIED,
            definition.display_label,
            definition.purpose,
            "Restore the selected package-manager executable, then rerun doctor.",
            definition.capability_id,
            ("package query skipped: provider executable unavailable",),
        )
    try:
        resolved = provider.resolve_capabilities((CapabilityRequest("base.tooling", purpose=definition.purpose),))
        states = provider.query_installed(tuple(item.package_name for item in resolved))
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return DoctorFinding(
            "base-tooling",
            DoctorStatus.UNVERIFIED,
            definition.display_label,
            definition.purpose,
            "Restore the selected provider's local package-query capability and rerun doctor.",
            definition.capability_id,
            (f"query unavailable: {type(exc).__name__}",),
        )
    missing = tuple(item.package_name for item in states if item.installed is False)
    unknown = tuple(item.package_name for item in states if item.installed is None)
    installed = tuple(item.package_name for item in states if item.installed is True)
    if missing:
        status = DoctorStatus.ACTION_NEEDED
        remedy = f"Review provider packages needed for {definition.capability_id}: {', '.join(missing)}."
    elif unknown:
        status = DoctorStatus.UNVERIFIED
        remedy = "Review the local package-manager query failure; no installation or repository action was attempted."
    else:
        status = DoctorStatus.PASS
        remedy = ""
    evidence = tuple(
        [*(f"installed: {name}" for name in installed), *(f"missing: {name}" for name in missing), *(f"unverified: {name}" for name in unknown)]
    )
    return DoctorFinding(
        "base-tooling", status, definition.display_label, definition.purpose,
        remedy, definition.capability_id, evidence,
    )


def build_doctor_report(
    *,
    kit_version: str,
    python_version: str,
    detection: DetectionResult,
    provider: PlatformProvider | None,
    executable_lookup: ExecutableLookup,
    codex: CodexDoctorState,
) -> DoctorReport:
    """Build a deterministic report from redacted facts and read-only queries."""

    findings: list[DoctorFinding] = [_platform_finding(detection)]
    findings.extend(
        DoctorFinding(
            issue.code.replace("_", "-"),
            DoctorStatus.BLOCKED if issue.severity == "error" else DoctorStatus.UNVERIFIED,
            "Platform detection detail",
            issue.message,
            issue.remedy,
        )
        for issue in detection.issues
    )
    manager = _package_manager_finding(detection)
    if manager is not None:
        findings.append(manager)

    findings.append(DoctorFinding(
        "python-runtime",
        DoctorStatus.PASS,
        "Python runtime",
        "Python 3.11 or newer runs the standard-library AgentKit core.",
        evidence=(f"version: {python_version}",),
    ))
    base = _base_tooling_finding(
        provider,
        query_enabled=manager is not None and manager.status is DoctorStatus.PASS,
    )
    if base is not None:
        findings.append(base)

    commands = ("bash", "git", "curl")
    missing_commands = tuple(name for name in commands if executable_lookup(name) is None)
    findings.append(DoctorFinding(
        "core-executables",
        DoctorStatus.ACTION_NEEDED if missing_commands else DoctorStatus.PASS,
        "Core workflow executables",
        "Generated local workflows use Bash, Git, and curl for reviewable project operations.",
        f"Restore these executables: {', '.join(missing_commands)}." if missing_commands else "",
        "base.tooling",
        tuple(f"{name}: {'missing' if name in missing_commands else 'available'}" for name in commands),
    ))

    if codex.installed and codex.authorized is True:
        codex_status, codex_remedy = DoctorStatus.PASS, ""
    elif not codex.installed:
        codex_status, codex_remedy = DoctorStatus.ACTION_NEEDED, "Install the official Codex CLI, then authorize through its own login flow."
    elif codex.authorized is False:
        codex_status, codex_remedy = DoctorStatus.ACTION_NEEDED, "Run the official Codex CLI login flow; AgentKit never handles OAuth secrets."
    else:
        codex_status, codex_remedy = DoctorStatus.UNVERIFIED, "Run `codex login status` directly and review its result."
    findings.append(DoctorFinding(
        "codex-cli", codex_status, "OpenAI Codex CLI",
        "Codex is the sole supported coding-agent and owns its authentication state.",
        codex_remedy, evidence=(f"version: {codex.version}",),
    ))

    podman_available = executable_lookup("podman") is not None
    podman = CAPABILITY_CATALOG["sandbox.rootless-podman"]
    findings.append(DoctorFinding(
        "rootless-podman",
        DoctorStatus.PASS if podman_available else DoctorStatus.OPTIONAL,
        podman.display_label,
        podman.purpose + " This capability is optional unless a project selects sandboxing.",
        "Select sandboxing and review provider prerequisites if isolation is needed." if not podman_available else "",
        podman.capability_id,
        (f"podman: {'available' if podman_available else 'not selected/available'}",),
    ))
    return DoctorReport(kit_version, python_version, detection, tuple(findings))


def render_doctor_text(report: DoctorReport) -> str:
    """Render the structured report for the compatibility text interface."""

    payload = report.to_dict()
    provider = payload["provider"]
    assert isinstance(provider, dict)
    lines = [
        f"AgentKit doctor — overall {report.overall_status.value.upper().replace('-', ' ')}",
        f"Starter kit: {report.kit_version}",
        f"Host: {report.detection.profile.pretty_name} ({report.detection.profile.architecture})",
        f"Provider: {provider['id'] or 'not selected'} ({provider['support']}; {provider['confidence']})",
        "",
    ]
    for finding in report.findings:
        label = finding.status.value.upper().replace("-", " ")
        capability = f" [{finding.capability_id}]" if finding.capability_id else ""
        lines.append(f"[{label}] {finding.title}{capability}")
        lines.append(f"  Why: {finding.explanation}")
        for item in finding.evidence:
            lines.append(f"  - {item}")
        if finding.remedy:
            lines.append(f"  Remedy: {finding.remedy}")
    return "\n".join(lines)
