"""Side-effect-free platform classification plus a narrow host reader.

OS metadata selects a provider candidate.  Executable evidence can confirm or
weaken that selection, but never selects a provider when metadata contradicts
or does not identify a supported family.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import platform
from pathlib import Path
import re
import shlex
import shutil
from typing import Callable

from .base import DetectionConfidence, ExecutableFact, HostProfile


OS_RELEASE_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
SAFE_OS_ID_RE = re.compile(r"^[a-z][a-z0-9._+-]{0,63}$")
PROVIDER_IDS = ("arch", "debian", "ubuntu")


@dataclass(frozen=True, slots=True)
class ProviderEvidence:
    provider_id: str
    package_manager: str
    documentation_label: str


PROVIDER_EVIDENCE = {
    "arch": ProviderEvidence("arch", "pacman", "CachyOS/Arch (pacman)"),
    "debian": ProviderEvidence("debian", "apt-get", "Debian (apt-get)"),
    "ubuntu": ProviderEvidence("ubuntu", "apt-get", "Ubuntu (apt-get)"),
}


class SupportLevel(str, Enum):
    SUPPORTED = "supported"
    PARTIAL = "partial"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class DetectionIssue:
    code: str
    message: str
    remedy: str
    severity: str = "warning"


@dataclass(frozen=True, slots=True)
class OsReleaseData:
    values: dict[str, str]
    issues: tuple[DetectionIssue, ...] = ()


@dataclass(frozen=True, slots=True)
class DetectionResult:
    profile: HostProfile
    support: SupportLevel
    confidence: DetectionConfidence
    detected_provider: str | None
    package_manager: str | None
    issues: tuple[DetectionIssue, ...] = ()

    @property
    def has_errors(self) -> bool:
        return any(issue.severity == "error" for issue in self.issues)


def _issue(code: str, message: str, remedy: str, severity: str = "warning") -> DetectionIssue:
    return DetectionIssue(code, message, remedy, severity)


def parse_os_release(text: str) -> OsReleaseData:
    """Parse the bounded shell-compatible assignments used by os-release."""

    if not isinstance(text, str):
        raise TypeError("os-release content must be text.")
    if "\x00" in text or len(text) > 262_144:
        return OsReleaseData({}, (_issue(
            "malformed_os_release",
            "OS release metadata is binary or unexpectedly large.",
            "Review /etc/os-release and use a reviewed provider override only if its executable proof passes.",
        ),))
    values: dict[str, str] = {}
    issues: list[DetectionIssue] = []
    for line_number, raw_line in enumerate(text.splitlines()[:512], 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            issues.append(_issue(
                "malformed_os_release_line",
                f"Ignored malformed os-release line {line_number}.",
                "Use KEY=value assignments in /etc/os-release.",
            ))
            continue
        key, raw_value = line.split("=", 1)
        if not OS_RELEASE_KEY_RE.fullmatch(key):
            issues.append(_issue(
                "malformed_os_release_key",
                f"Ignored unsupported os-release key on line {line_number}.",
                "Use standard uppercase os-release keys.",
            ))
            continue
        try:
            lexer = shlex.shlex(raw_value, posix=True)
            lexer.whitespace_split = True
            lexer.commenters = ""
            tokens = list(lexer)
        except ValueError:
            tokens = ["", ""]
        if len(tokens) > 1 or (tokens and len(tokens[0]) > 4096):
            issues.append(_issue(
                "malformed_os_release_value",
                f"Ignored malformed os-release value for {key}.",
                "Quote values containing spaces and keep metadata values bounded.",
            ))
            continue
        values[key] = tokens[0] if tokens else ""
    if len(text.splitlines()) > 512:
        issues.append(_issue(
            "os_release_too_many_lines",
            "Ignored os-release content after line 512.",
            "Review the file; a normal os-release file is small.",
        ))
    return OsReleaseData(values, tuple(issues))


def _safe_os_id(value: str) -> str:
    normalized = value.strip().lower()
    return normalized if SAFE_OS_ID_RE.fullmatch(normalized) else "unknown"


def _safe_text(value: str, fallback: str, limit: int) -> str:
    cleaned = "".join(character if ord(character) >= 32 else " " for character in value).strip()
    return cleaned[:limit] or fallback


def _provider_from_metadata(os_id: str, os_id_like: tuple[str, ...]) -> str | None:
    families = {os_id, *os_id_like}
    if os_id == "ubuntu" or "ubuntu" in os_id_like:
        return "ubuntu"
    if os_id in {"arch", "cachyos"} or "arch" in families:
        return "arch"
    if os_id == "debian" or "debian" in families:
        return "debian"
    return None


def detect_platform(
    os_release_text: str | None,
    *,
    architecture: str,
    executable_lookup: Callable[[str], str | None],
    override: str | None = None,
) -> DetectionResult:
    """Classify synthetic or host-supplied evidence without executing commands."""

    if override is not None and override not in PROVIDER_EVIDENCE:
        raise ValueError(f"Unknown platform provider {override!r}; use one of: {', '.join(PROVIDER_IDS)}.")
    parsed = parse_os_release(os_release_text or "")
    issues = list(parsed.issues)
    raw_id = parsed.values.get("ID", "")
    os_id = _safe_os_id(raw_id)
    like_values = tuple(
        item for item in (_safe_os_id(value) for value in parsed.values.get("ID_LIKE", "").split())
        if item != "unknown"
    )
    if raw_id and os_id == "unknown":
        issues.append(_issue(
            "invalid_os_id",
            "OS metadata contains an invalid ID value.",
            "Repair /etc/os-release or use a reviewed provider override with executable proof.",
        ))
    detected = _provider_from_metadata(os_id, like_values)
    requested = override or detected

    managers_to_check: list[str] = []
    for provider_id in (detected, override):
        if provider_id is not None:
            manager = PROVIDER_EVIDENCE[provider_id].package_manager
            if manager not in managers_to_check:
                managers_to_check.append(manager)
    executable_facts = tuple(
        ExecutableFact(name, executable_lookup(name) is not None)
        for name in managers_to_check
    )
    available = {fact.name: fact.available for fact in executable_facts}

    selected: str | None = requested
    manager: str | None = PROVIDER_EVIDENCE[requested].package_manager if requested else None
    if override is not None:
        proof = available.get(PROVIDER_EVIDENCE[override].package_manager, False)
        if not proof:
            selected = None
            manager = PROVIDER_EVIDENCE[override].package_manager
            confidence = DetectionConfidence.PARTIAL
            support = SupportLevel.PARTIAL
            issues.append(_issue(
                "override_proof_failed",
                f"Provider override {override!r} was not selected because {manager!r} is unavailable.",
                f"Install or expose the reviewed {manager} executable, or select the provider matching OS metadata.",
                "error",
            ))
        elif detected is not None and detected != override:
            confidence = DetectionConfidence.CONTRADICTED
            support = SupportLevel.PARTIAL
            issues.append(_issue(
                "provider_override_contradicts_os",
                f"Provider override {override!r} contradicts OS metadata for {detected!r}; executable proof passed.",
                "Proceed only after confirming this host intentionally uses the overridden package manager.",
            ))
        else:
            confidence = DetectionConfidence.CONFIRMED if detected == override else DetectionConfidence.PARTIAL
            support = SupportLevel.SUPPORTED if detected == override else SupportLevel.PARTIAL
            if detected is None:
                issues.append(_issue(
                    "provider_override_without_os_match",
                    f"Provider override {override!r} has executable proof but no matching OS metadata.",
                    "Confirm the override before using any future package plan.",
                ))
    elif detected is not None:
        manager = PROVIDER_EVIDENCE[detected].package_manager
        if available.get(manager, False):
            confidence = DetectionConfidence.CONFIRMED
            support = SupportLevel.SUPPORTED
        else:
            confidence = DetectionConfidence.PARTIAL
            support = SupportLevel.PARTIAL
            issues.append(_issue(
                "package_manager_missing",
                f"OS metadata identifies {detected!r}, but expected executable {manager!r} is unavailable.",
                f"Restore the distribution's {manager} executable before using package plans.",
            ))
    elif os_id == "unknown":
        confidence = DetectionConfidence.UNKNOWN
        support = SupportLevel.UNKNOWN
        issues.append(_issue(
            "unknown_platform",
            "OS metadata did not identify a platform provider.",
            "Review /etc/os-release or use an explicit provider override with executable proof.",
        ))
    else:
        confidence = DetectionConfidence.CONTRADICTED
        support = SupportLevel.UNSUPPORTED
        issues.append(_issue(
            "unsupported_platform",
            f"OS {os_id!r} is not in the supported provider families.",
            "Generation remains available, but do not use a package plan without a reviewed supported provider override.",
        ))

    profile = HostProfile(
        os_id=os_id,
        os_id_like=like_values,
        pretty_name=_safe_text(parsed.values.get("PRETTY_NAME", ""), "Unknown Linux", 240),
        version_id=_safe_text(parsed.values.get("VERSION_ID", ""), "", 240),
        architecture=_safe_text(architecture, "unknown", 80),
        package_provider=selected,
        executables=executable_facts,
    )
    return DetectionResult(profile, support, confidence, detected, manager, tuple(issues))


def detect_host(
    *,
    override: str | None = None,
    os_release_path: Path = Path("/etc/os-release"),
) -> DetectionResult:
    """Read only approved host facts and delegate to deterministic detection."""

    try:
        text = os_release_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        text = None
    return detect_platform(
        text,
        architecture=platform.machine(),
        executable_lookup=shutil.which,
        override=override,
    )
