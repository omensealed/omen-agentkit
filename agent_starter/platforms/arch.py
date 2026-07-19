"""CachyOS/Arch provider with official-repository-first package policy."""

from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True, slots=True)
class ArchCapabilityRecord:
    capability_id: str
    packages: tuple[str, ...]
    executable: str = ""
    source: PackageSource = PackageSource.OFFICIAL
    explanation: str = ""

    def __post_init__(self) -> None:
        CapabilityRequest(self.capability_id)
        if not self.packages:
            raise ValueError("Arch capability records require at least one package.")
        for package in self.packages:
            PackageState(package, None)
        if self.source is PackageSource.MANUAL_REVIEW and "AUR" not in self.explanation:
            raise ValueError("Manual Arch capability records must identify the AUR review boundary.")


ARCH_CAPABILITIES: dict[str, ArchCapabilityRecord] = {
    "base.tooling": ArchCapabilityRecord(
        "base.tooling", ("git", "curl", "jq", "ripgrep", "fd", "unzip", "base-devel"), "git"
    ),
    "optional.github-cli": ArchCapabilityRecord("optional.github-cli", ("github-cli",), "gh"),
    "optional.shellcheck": ArchCapabilityRecord("optional.shellcheck", ("shellcheck",), "shellcheck"),
    "language.python": ArchCapabilityRecord("language.python", ("python", "python-pip"), "python3"),
    "language.javascript": ArchCapabilityRecord("language.javascript", ("nodejs", "npm"), "node"),
    "language.rust": ArchCapabilityRecord("language.rust", ("rustup",), "rustup"),
    "language.go": ArchCapabilityRecord("language.go", ("go",), "go"),
    "language.php": ArchCapabilityRecord("language.php", ("php", "composer"), "php"),
    "language.cpp": ArchCapabilityRecord(
        "language.cpp", ("base-devel", "cmake", "ninja", "clang", "gdb"), "cmake"
    ),
    "language.java": ArchCapabilityRecord("language.java", ("jdk-openjdk",), "java"),
    "language.godot": ArchCapabilityRecord("language.godot", ("godot",), "godot"),
    "language.shell": ArchCapabilityRecord("language.shell", ("bash", "shellcheck"), "bash"),
    "database.sqlite": ArchCapabilityRecord("database.sqlite", ("sqlite",), "sqlite3"),
    "database.mariadb": ArchCapabilityRecord("database.mariadb", ("mariadb",), "mariadb"),
    "database.postgresql": ArchCapabilityRecord("database.postgresql", ("postgresql",), "psql"),
    "sandbox.rootless-podman": ArchCapabilityRecord(
        "sandbox.rootless-podman", ("podman", "passt", "fuse-overlayfs"), "podman"
    ),
}
require_complete_provider_catalog("arch", ARCH_CAPABILITIES)


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


def arch_packages_for_capabilities(
    capability_ids: Sequence[str],
    *,
    catalog: Mapping[str, ArchCapabilityRecord] = ARCH_CAPABILITIES,
) -> tuple[str, ...]:
    """Resolve official capability records for compatibility package output."""

    packages: list[str] = []
    for capability_id in _unique(capability_ids):
        record = catalog.get(capability_id)
        if record is None:
            raise ValueError(f"Unknown Arch capability: {capability_id}")
        if record.source is not PackageSource.OFFICIAL:
            raise ValueError(f"Capability {capability_id} requires manual review and cannot enter an install plan.")
        packages.extend(record.packages)
    return _unique(packages)


class ArchProvider(PlatformProvider):
    """CachyOS/Arch implementation; package mutations are plans, never calls."""

    provider_id = "arch"
    package_manager_id = "pacman"
    documentation_label = "CachyOS/Arch (official repositories via pacman)"
    shell_executable = "/bin/bash"

    def __init__(
        self,
        *,
        runner: Runner = _readonly_runner,
        catalog: Mapping[str, ArchCapabilityRecord] = ARCH_CAPABILITIES,
    ) -> None:
        self._runner = runner
        self._catalog = dict(catalog)

    def detection_confidence(self, profile: HostProfile) -> DetectionConfidence:
        metadata_matches = profile.os_id in {"arch", "cachyos"} or "arch" in profile.os_id_like
        pacman = next((fact for fact in profile.executables if fact.name == "pacman"), None)
        if profile.package_provider != self.provider_id:
            return DetectionConfidence.CONTRADICTED
        if not metadata_matches:
            return DetectionConfidence.CONTRADICTED
        return DetectionConfidence.CONFIRMED if pacman and pacman.available else DetectionConfidence.PARTIAL

    def _run_query(self, argv: tuple[str, ...]) -> CommandResult | None:
        try:
            return self._runner(argv)
        except (OSError, subprocess.SubprocessError):
            return None

    def query_installed(self, package_names: Sequence[str]) -> tuple[PackageState, ...]:
        states: list[PackageState] = []
        for package in _unique(package_names):
            PackageState(package, None)
            result = self._run_query(("pacman", "-Qq", package))
            installed = None if result is None or result.returncode not in {0, 1} else result.returncode == 0
            states.append(PackageState(package, installed))
        return tuple(states)

    def verify_available(self, package_names: Sequence[str]) -> tuple[PackageVerification, ...]:
        verified: list[PackageVerification] = []
        for package in _unique(package_names):
            PackageState(package, None)
            result = self._run_query(("pacman", "-Si", package))
            if result is None or result.returncode not in {0, 1}:
                availability = PackageAvailability.UNVERIFIED
                explanation = "Could not query the local pacman sync metadata; no package action was attempted."
            elif result.returncode == 0:
                availability = PackageAvailability.AVAILABLE
                explanation = "Found in configured official pacman repository metadata."
            else:
                availability = PackageAvailability.UNAVAILABLE
                explanation = "Not found in configured official pacman repository metadata; AUR was not queried."
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
            explanation = record.explanation or "Official CachyOS/Arch repository candidate; verify before planning install."
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
            raise ValueError(f"Unsupported required Arch capabilities: {', '.join(unknown)}")
        return tuple(resolutions)

    def update_plan(self, profile: HostProfile) -> ArgvPlan:
        if self.detection_confidence(profile) is not DetectionConfidence.CONFIRMED:
            raise ValueError("A confirmed CachyOS/Arch profile with pacman is required for an update plan.")
        return ArgvPlan(
            "Review Arch system update",
            ("sudo", "pacman", "-Syu"),
            "Separate human-operated full-system update; never embed this in project bootstrap.",
            requires_network=True,
            requires_privilege=True,
        )

    def install_plan(self, packages: Sequence[PackageResolution]) -> ArgvPlan:
        if isinstance(packages, (str, bytes)) or not all(isinstance(item, PackageResolution) for item in packages):
            raise TypeError("packages must be a sequence of PackageResolution values.")
        names: list[str] = []
        for package in packages:
            if package.source is not PackageSource.OFFICIAL or not package.installable:
                raise ValueError(f"Package {package.package_name} requires manual/AUR review and cannot enter a plan.")
            if package.availability is not PackageAvailability.AVAILABLE:
                raise ValueError(f"Package {package.package_name} must be verified available before planning install.")
            names.append(package.package_name)
        if not names:
            raise ValueError("At least one verified official package is required for an install plan.")
        return ArgvPlan(
            "Install verified Arch packages",
            ("sudo", "pacman", "-S", "--needed", *_unique(names)),
            "Human-reviewed installation from configured official pacman repositories.",
            requires_network=True,
            requires_privilege=True,
        )

    def rootless_podman_checks(self, profile: HostProfile) -> tuple[PrerequisiteCheck, ...]:
        checks = list(profile.rootless_podman.checks)
        podman = next((fact for fact in profile.executables if fact.name == "podman"), None)
        executable_available = profile.rootless_podman.executable_available or bool(podman and podman.available)
        checks.insert(0, PrerequisiteCheck(
            "podman-executable",
            PrerequisiteStatus.SATISFIED if executable_available else PrerequisiteStatus.ACTION_REQUIRED,
            "Podman executable is available." if executable_available else "Podman executable is unavailable.",
            "Review the sandbox.rootless-podman official package capability." if not executable_available else "",
        ))
        return tuple(checks)

    def executable_name(self, capability_id: str) -> str:
        record = self._catalog.get(capability_id)
        if record is None:
            raise ValueError(f"Unknown Arch capability: {capability_id}")
        return record.executable
