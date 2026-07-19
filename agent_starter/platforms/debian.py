"""Debian/Ubuntu provider with apt metadata queries and no source mutation."""

from __future__ import annotations

from dataclasses import dataclass
import re
import subprocess
from typing import Callable, Mapping, Sequence

from ..capabilities import require_complete_provider_catalog
from .base import (
    ArgvPlan,
    CapabilityRequest,
    CommandResult,
    DetectionConfidence,
    HostProfile,
    PackageAvailability,
    PackageResolution,
    PackageSource,
    PackageState,
    PackageVerification,
    PlatformProvider,
    PrerequisiteCheck,
    PrerequisiteStatus,
)


THIRD_PARTY_REVIEW_TERMS = ("source", "key", "pinning", "removal")


@dataclass(frozen=True, slots=True)
class DebianCapabilityRecord:
    capability_id: str
    packages: tuple[str, ...]
    executable: str = ""
    executable_aliases: tuple[tuple[str, str], ...] = ()
    source: PackageSource = PackageSource.OFFICIAL
    explanation: str = ""

    def __post_init__(self) -> None:
        CapabilityRequest(self.capability_id)
        if not self.packages:
            raise ValueError("Debian capability records require at least one package.")
        for package in self.packages:
            PackageState(package, None)
        for generic_name, provider_name in self.executable_aliases:
            if not generic_name or not provider_name or "/" in generic_name or "/" in provider_name:
                raise ValueError("Executable aliases must be safe basenames.")
        if self.source is PackageSource.MANUAL_REVIEW:
            explanation = self.explanation.lower()
            missing = [term for term in THIRD_PARTY_REVIEW_TERMS if term not in explanation]
            if missing:
                raise ValueError(
                    "Manual third-party records must document source, key, pinning, and removal review."
                )


DEBIAN_CAPABILITIES: dict[str, DebianCapabilityRecord] = {
    "base.tooling": DebianCapabilityRecord(
        "base.tooling",
        ("git", "curl", "jq", "ripgrep", "fd-find", "unzip", "build-essential"),
        "git",
        (("fd", "fdfind"),),
    ),
    "optional.github-cli": DebianCapabilityRecord("optional.github-cli", ("gh",), "gh"),
    "optional.shellcheck": DebianCapabilityRecord("optional.shellcheck", ("shellcheck",), "shellcheck"),
    "language.python": DebianCapabilityRecord(
        "language.python", ("python3", "python3-venv", "python3-pip"), "python3"
    ),
    "language.javascript": DebianCapabilityRecord("language.javascript", ("nodejs", "npm"), "node"),
    "language.rust": DebianCapabilityRecord("language.rust", ("rustc", "cargo"), "cargo"),
    "language.go": DebianCapabilityRecord("language.go", ("golang-go",), "go"),
    "language.php": DebianCapabilityRecord("language.php", ("php-cli", "composer"), "php"),
    "language.cpp": DebianCapabilityRecord(
        "language.cpp", ("build-essential", "cmake", "ninja-build", "clang", "gdb"), "cmake"
    ),
    "language.java": DebianCapabilityRecord("language.java", ("default-jdk",), "java"),
    "language.godot": DebianCapabilityRecord("language.godot", ("godot3",), "godot3"),
    "language.shell": DebianCapabilityRecord("language.shell", ("bash", "shellcheck"), "bash"),
    "database.sqlite": DebianCapabilityRecord("database.sqlite", ("sqlite3",), "sqlite3"),
    "database.mariadb": DebianCapabilityRecord("database.mariadb", ("mariadb-server",), "mariadb"),
    "database.postgresql": DebianCapabilityRecord("database.postgresql", ("postgresql",), "psql"),
    "sandbox.rootless-podman": DebianCapabilityRecord(
        "sandbox.rootless-podman",
        ("podman", "uidmap", "slirp4netns", "fuse-overlayfs"),
        "podman",
    ),
}
require_complete_provider_catalog("debian-family", DEBIAN_CAPABILITIES)


@dataclass(frozen=True, slots=True)
class DebianFlavor:
    provider_id: str
    documentation_label: str
    capability_overrides: Mapping[str, DebianCapabilityRecord]


DEBIAN_FLAVORS = {
    "debian": DebianFlavor("debian", "Debian (official APT repositories)", {}),
    "ubuntu": DebianFlavor("ubuntu", "Ubuntu (official APT repositories)", {}),
}


Runner = Callable[[tuple[str, ...]], CommandResult]


def _readonly_runner(argv: tuple[str, ...]) -> CommandResult:
    result = subprocess.run(
        argv,
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    return CommandResult(result.returncode, result.stdout, result.stderr)


def _unique(values: Sequence[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise TypeError("Expected a sequence of identifiers, not one string.")
    if not all(isinstance(value, str) for value in values):
        raise TypeError("Identifier sequences may contain only strings.")
    return tuple(dict.fromkeys(values))


def debian_packages_for_capabilities(
    capability_ids: Sequence[str],
    *,
    flavor: str = "debian",
    catalog: Mapping[str, DebianCapabilityRecord] = DEBIAN_CAPABILITIES,
) -> tuple[str, ...]:
    """Resolve official Debian/Ubuntu package names without querying the host."""

    if flavor not in DEBIAN_FLAVORS:
        raise ValueError("Debian-family flavor must be 'debian' or 'ubuntu'.")
    records = {**catalog, **DEBIAN_FLAVORS[flavor].capability_overrides}
    packages: list[str] = []
    for capability_id in _unique(capability_ids):
        record = records.get(capability_id)
        if record is None:
            raise ValueError(f"Unknown {flavor} capability: {capability_id}")
        if record.source is not PackageSource.OFFICIAL:
            raise ValueError(f"Capability {capability_id} requires third-party review and cannot enter a plan.")
        packages.extend(record.packages)
    return _unique(packages)


class DebianFamilyProvider(PlatformProvider):
    """One data-driven provider for Debian and Ubuntu flavor identities."""

    package_manager_id = "apt-get"
    shell_executable = "/bin/sh"

    def __init__(
        self,
        flavor: str,
        *,
        runner: Runner = _readonly_runner,
        catalog: Mapping[str, DebianCapabilityRecord] = DEBIAN_CAPABILITIES,
    ) -> None:
        if flavor not in DEBIAN_FLAVORS:
            raise ValueError("Debian-family flavor must be 'debian' or 'ubuntu'.")
        self._flavor = DEBIAN_FLAVORS[flavor]
        self.provider_id = self._flavor.provider_id
        self.documentation_label = self._flavor.documentation_label
        self._runner = runner
        self._catalog = {**catalog, **self._flavor.capability_overrides}

    def detection_confidence(self, profile: HostProfile) -> DetectionConfidence:
        if profile.package_provider != self.provider_id:
            return DetectionConfidence.CONTRADICTED
        metadata_matches = (
            profile.os_id == self.provider_id
            or self.provider_id in profile.os_id_like
            or (self.provider_id == "debian" and profile.os_id == "debian")
        )
        if not metadata_matches:
            return DetectionConfidence.CONTRADICTED
        apt_get = next((fact for fact in profile.executables if fact.name == "apt-get"), None)
        return DetectionConfidence.CONFIRMED if apt_get and apt_get.available else DetectionConfidence.PARTIAL

    def _run_query(self, argv: tuple[str, ...]) -> CommandResult | None:
        try:
            return self._runner(argv)
        except (OSError, subprocess.SubprocessError):
            return None

    def query_installed(self, package_names: Sequence[str]) -> tuple[PackageState, ...]:
        states: list[PackageState] = []
        for package in _unique(package_names):
            PackageState(package, None)
            result = self._run_query(("dpkg-query", "-W", "-f=${Status}", package))
            if result is None or result.returncode not in {0, 1}:
                installed = None
            else:
                installed = result.returncode == 0 and result.stdout.strip() == "install ok installed"
            states.append(PackageState(package, installed))
        return tuple(states)

    def verify_available(self, package_names: Sequence[str]) -> tuple[PackageVerification, ...]:
        verified: list[PackageVerification] = []
        for package in _unique(package_names):
            PackageState(package, None)
            result = self._run_query(("apt-cache", "policy", package))
            candidate = None
            if result is not None and result.returncode == 0:
                match = re.search(r"(?m)^\s*Candidate:\s*(\S+)\s*$", result.stdout)
                candidate = match.group(1) if match else None
            if result is None or result.returncode != 0 or candidate is None:
                availability = PackageAvailability.UNVERIFIED
                explanation = "Could not verify package candidate from local APT metadata; no source was changed."
            elif candidate == "(none)":
                availability = PackageAvailability.UNAVAILABLE
                explanation = "No candidate exists in configured APT repositories; no PPA or third-party source was added."
            else:
                availability = PackageAvailability.AVAILABLE
                explanation = "Candidate found in configured APT metadata."
            verified.append(PackageVerification(package, availability, explanation))
        return tuple(verified)

    def resolve_capabilities(self, requests: Sequence[CapabilityRequest]) -> tuple[PackageResolution, ...]:
        if isinstance(requests, (str, bytes)) or not all(isinstance(item, CapabilityRequest) for item in requests):
            raise TypeError("requests must be a sequence of CapabilityRequest values.")
        resolutions: list[PackageResolution] = []
        unknown: list[str] = []
        for request in requests:
            record = self._catalog.get(request.capability_id)
            if record is None:
                if request.required:
                    unknown.append(request.capability_id)
                continue
            manual = record.source is PackageSource.MANUAL_REVIEW
            explanation = record.explanation or "Official Debian-family package candidate; verify APT metadata first."
            for package in record.packages:
                resolutions.append(PackageResolution(
                    request.capability_id,
                    package,
                    PackageAvailability.UNVERIFIED,
                    explanation,
                    record.source,
                    not manual,
                ))
        if unknown:
            raise ValueError(f"Unsupported required {self.provider_id} capabilities: {', '.join(unknown)}")
        return tuple(resolutions)

    def update_plan(self, profile: HostProfile) -> ArgvPlan:
        if self.detection_confidence(profile) is not DetectionConfidence.CONFIRMED:
            raise ValueError("A confirmed Debian/Ubuntu profile with apt-get is required for an index-refresh plan.")
        return ArgvPlan(
            "Refresh APT package indexes",
            ("sudo", "apt-get", "update"),
            "Refresh configured repository metadata separately; this does not upgrade installed packages.",
            requires_network=True,
            requires_privilege=True,
        )

    def install_plan(self, packages: Sequence[PackageResolution]) -> ArgvPlan:
        if isinstance(packages, (str, bytes)) or not all(isinstance(item, PackageResolution) for item in packages):
            raise TypeError("packages must be a sequence of PackageResolution values.")
        names: list[str] = []
        for package in packages:
            if package.source is not PackageSource.OFFICIAL or not package.installable:
                raise ValueError(f"Package {package.package_name} requires third-party review and cannot enter a plan.")
            if package.availability is not PackageAvailability.AVAILABLE:
                raise ValueError(f"Package {package.package_name} must be verified available before planning install.")
            names.append(package.package_name)
        if not names:
            raise ValueError("At least one verified official package is required for an install plan.")
        return ArgvPlan(
            "Install verified Debian-family packages",
            ("sudo", "apt-get", "install", "--yes", *_unique(names)),
            "Human-reviewed install from already configured official APT repositories; no source changes.",
            requires_network=True,
            requires_privilege=True,
        )

    def rootless_podman_checks(self, profile: HostProfile) -> tuple[PrerequisiteCheck, ...]:
        checks = list(profile.rootless_podman.checks)
        podman = next((fact for fact in profile.executables if fact.name == "podman"), None)
        available = profile.rootless_podman.executable_available or bool(podman and podman.available)
        checks.insert(0, PrerequisiteCheck(
            "podman-executable",
            PrerequisiteStatus.SATISFIED if available else PrerequisiteStatus.ACTION_REQUIRED,
            "Podman executable is available." if available else "Podman executable is unavailable.",
            "Review the sandbox.rootless-podman official package capability." if not available else "",
        ))
        return tuple(checks)

    def executable_name(self, capability_id: str) -> str:
        record = self._catalog.get(capability_id)
        if record is None:
            raise ValueError(f"Unknown {self.provider_id} capability: {capability_id}")
        return record.executable

    def executable_aliases(self, capability_id: str) -> dict[str, str]:
        record = self._catalog.get(capability_id)
        if record is None:
            raise ValueError(f"Unknown {self.provider_id} capability: {capability_id}")
        return dict(record.executable_aliases)
