"""Redacted host facts and the interface for platform package providers.

This module is deliberately data-only.  It does not inspect the running host,
invoke a package manager, or turn a plan into a shell command.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Protocol, Sequence, runtime_checkable

from ..config_schema import validate_package_identifier


SAFE_ID_RE = re.compile(r"^[a-z][a-z0-9._+-]{0,63}$")
EXECUTABLE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,127}$")


def _bounded_text(value: str, field: str, *, limit: int = 240, empty: bool = False) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field} must be text.")
    if (not empty and not value.strip()) or "\x00" in value or len(value) > limit:
        qualifier = "non-empty " if not empty else ""
        raise ValueError(f"{field} must be {qualifier}text of at most {limit} characters without NUL bytes.")


def _safe_id(value: str, field: str) -> None:
    _bounded_text(value, field, limit=64)
    if not SAFE_ID_RE.fullmatch(value):
        raise ValueError(f"{field} must be a safe lowercase identifier.")


class DetectionConfidence(str, Enum):
    """How strongly host evidence supports a provider selection."""

    CONFIRMED = "confirmed"
    PARTIAL = "partial"
    UNKNOWN = "unknown"
    CONTRADICTED = "contradicted"


class PackageAvailability(str, Enum):
    """Result of checking a package in the selected provider's repositories."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNVERIFIED = "unverified"


class PackageSource(str, Enum):
    """Authority class for a package resolution."""

    OFFICIAL = "official"
    MANUAL_REVIEW = "manual-review"


@dataclass(frozen=True, slots=True)
class CommandResult:
    """Minimal captured result for injectable provider query runners."""

    returncode: int
    stdout: str = ""
    stderr: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.returncode, int) or isinstance(self.returncode, bool):
            raise TypeError("command returncode must be an integer.")
        for field, value in (("stdout", self.stdout), ("stderr", self.stderr)):
            _bounded_text(value, field, limit=100_000, empty=True)


class PrerequisiteStatus(str, Enum):
    """Non-executing result for a host or rootless-Podman prerequisite."""

    SATISFIED = "satisfied"
    ACTION_REQUIRED = "action-required"
    OPTIONAL = "optional"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ExecutableFact:
    """A deliberately narrow executable availability fact."""

    name: str
    available: bool
    version: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not EXECUTABLE_RE.fullmatch(self.name):
            raise ValueError("executable name must be a safe basename without path or shell syntax.")
        if not isinstance(self.available, bool):
            raise TypeError("executable availability must be a boolean.")
        _bounded_text(self.version, "executable version", empty=True)


@dataclass(frozen=True, slots=True)
class PrerequisiteCheck:
    """Structured, reviewable prerequisite result with a safe remedy."""

    code: str
    status: PrerequisiteStatus
    explanation: str
    remedy: str = ""

    def __post_init__(self) -> None:
        _safe_id(self.code, "prerequisite code")
        if not isinstance(self.status, PrerequisiteStatus):
            raise TypeError("prerequisite status must be a PrerequisiteStatus.")
        _bounded_text(self.explanation, "prerequisite explanation", limit=1000)
        _bounded_text(self.remedy, "prerequisite remedy", limit=1000, empty=True)


@dataclass(frozen=True, slots=True)
class RootlessPodmanStatus:
    """Redacted rootless-Podman state; never includes host identity or paths."""

    executable_available: bool = False
    rootless_usable: bool | None = None
    checks: tuple[PrerequisiteCheck, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.executable_available, bool):
            raise TypeError("Podman executable availability must be a boolean.")
        if self.rootless_usable is not None and not isinstance(self.rootless_usable, bool):
            raise TypeError("rootless_usable must be a boolean or None.")
        if not isinstance(self.checks, tuple) or not all(isinstance(item, PrerequisiteCheck) for item in self.checks):
            raise TypeError("rootless Podman checks must be a tuple of PrerequisiteCheck values.")


@dataclass(frozen=True, slots=True)
class HostProfile:
    """Minimal non-identifying host facts approved for provider/advisor use.

    Usernames, hostnames, home paths, IP addresses, environment values,
    credential/browser state, shell history, SSH configuration, and unrelated
    installed-package inventory have no representation in this model.
    """

    os_id: str
    os_id_like: tuple[str, ...]
    pretty_name: str
    version_id: str
    architecture: str
    package_provider: str | None = None
    executables: tuple[ExecutableFact, ...] = ()
    rootless_podman: RootlessPodmanStatus = RootlessPodmanStatus()
    selected_languages: tuple[str, ...] = ()
    selected_targets: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _safe_id(self.os_id, "os_id")
        for value in self.os_id_like:
            _safe_id(value, "os_id_like item")
        _bounded_text(self.pretty_name, "pretty_name")
        _bounded_text(self.version_id, "version_id", empty=True)
        _bounded_text(self.architecture, "architecture", limit=80)
        if self.package_provider is not None:
            _safe_id(self.package_provider, "package_provider")
        if not isinstance(self.executables, tuple) or not all(isinstance(item, ExecutableFact) for item in self.executables):
            raise TypeError("executables must be a tuple of ExecutableFact values.")
        if len({item.name for item in self.executables}) != len(self.executables):
            raise ValueError("executable facts must have unique names.")
        if not isinstance(self.rootless_podman, RootlessPodmanStatus):
            raise TypeError("rootless_podman must be a RootlessPodmanStatus.")
        for field, values in (("selected_languages", self.selected_languages), ("selected_targets", self.selected_targets)):
            if not isinstance(values, tuple):
                raise TypeError(f"{field} must be a tuple of strings.")
            for value in values:
                _bounded_text(value, f"{field} item", limit=120)

    def to_advisor_dict(self) -> dict[str, Any]:
        """Return the explicit allowlisted, redacted advisor representation."""

        return {
            "os_id": self.os_id,
            "os_id_like": list(self.os_id_like),
            "pretty_name": self.pretty_name,
            "version_id": self.version_id,
            "architecture": self.architecture,
            "package_provider": self.package_provider,
            "executables": [
                {"name": item.name, "available": item.available, "version": item.version}
                for item in self.executables
            ],
            "rootless_podman": {
                "executable_available": self.rootless_podman.executable_available,
                "rootless_usable": self.rootless_podman.rootless_usable,
                "checks": [
                    {
                        "code": item.code,
                        "status": item.status.value,
                        "explanation": item.explanation,
                        "remedy": item.remedy,
                    }
                    for item in self.rootless_podman.checks
                ],
            },
            "selected_languages": list(self.selected_languages),
            "selected_targets": list(self.selected_targets),
        }


@dataclass(frozen=True, slots=True)
class CapabilityRequest:
    """A project capability that a provider may resolve to packages."""

    capability_id: str
    required: bool = True
    purpose: str = ""

    def __post_init__(self) -> None:
        _safe_id(self.capability_id, "capability_id")
        if not isinstance(self.required, bool):
            raise TypeError("capability required must be a boolean.")
        _bounded_text(self.purpose, "capability purpose", limit=500, empty=True)


@dataclass(frozen=True, slots=True)
class PackageState:
    """Installed state returned by a provider without a full package inventory."""

    package_name: str
    installed: bool | None

    def __post_init__(self) -> None:
        if validate_package_identifier(self.package_name) is not None:
            raise ValueError("package_name must be a safe package identifier without options or shell syntax.")
        if self.installed is not None and not isinstance(self.installed, bool):
            raise TypeError("installed must be a boolean or None.")


@dataclass(frozen=True, slots=True)
class PackageVerification:
    """Repository availability for one exact provider package name."""

    package_name: str
    availability: PackageAvailability
    explanation: str = ""

    def __post_init__(self) -> None:
        if validate_package_identifier(self.package_name) is not None:
            raise ValueError("package_name must be a safe package identifier without options or shell syntax.")
        if not isinstance(self.availability, PackageAvailability):
            raise TypeError("availability must be a PackageAvailability.")
        _bounded_text(self.explanation, "package verification explanation", limit=1000, empty=True)


@dataclass(frozen=True, slots=True)
class PackageResolution:
    """Provider-specific package resolution with explicit verification state."""

    capability_id: str
    package_name: str
    availability: PackageAvailability = PackageAvailability.UNVERIFIED
    explanation: str = ""
    source: PackageSource = PackageSource.OFFICIAL
    installable: bool = True

    def __post_init__(self) -> None:
        _safe_id(self.capability_id, "capability_id")
        if validate_package_identifier(self.package_name) is not None:
            raise ValueError("package_name must be a safe package identifier without options or shell syntax.")
        if not isinstance(self.availability, PackageAvailability):
            raise TypeError("availability must be a PackageAvailability.")
        _bounded_text(self.explanation, "package resolution explanation", limit=1000, empty=True)
        if not isinstance(self.source, PackageSource):
            raise TypeError("source must be a PackageSource.")
        if not isinstance(self.installable, bool):
            raise TypeError("installable must be a boolean.")
        if self.source is PackageSource.MANUAL_REVIEW and self.installable:
            raise ValueError("manual-review packages cannot be marked installable.")


@dataclass(frozen=True, slots=True)
class ArgvPlan:
    """A review-only process plan represented as argv, never shell text."""

    label: str
    argv: tuple[str, ...]
    purpose: str
    requires_network: bool = False
    requires_privilege: bool = False

    def __post_init__(self) -> None:
        _bounded_text(self.label, "plan label")
        _bounded_text(self.purpose, "plan purpose", limit=1000)
        if not isinstance(self.argv, tuple) or not self.argv:
            raise ValueError("argv must be a non-empty tuple.")
        for argument in self.argv:
            _bounded_text(argument, "argv item", limit=2000, empty=True)
        if not self.argv[0]:
            raise ValueError("argv executable must not be empty.")
        if not isinstance(self.requires_network, bool) or not isinstance(self.requires_privilege, bool):
            raise TypeError("plan authority flags must be booleans.")


@runtime_checkable
class PlatformProvider(Protocol):
    """Interface implemented by explicit platform/package-manager providers."""

    provider_id: str
    package_manager_id: str
    documentation_label: str
    shell_executable: str

    def detection_confidence(self, profile: HostProfile) -> DetectionConfidence: ...

    def query_installed(self, package_names: Sequence[str]) -> tuple[PackageState, ...]: ...

    def verify_available(self, package_names: Sequence[str]) -> tuple[PackageVerification, ...]: ...

    def resolve_capabilities(self, requests: Sequence[CapabilityRequest]) -> tuple[PackageResolution, ...]: ...

    def update_plan(self, profile: HostProfile) -> ArgvPlan: ...

    def install_plan(self, packages: Sequence[PackageResolution]) -> ArgvPlan: ...

    def rootless_podman_checks(self, profile: HostProfile) -> tuple[PrerequisiteCheck, ...]: ...

    def executable_name(self, capability_id: str) -> str: ...
