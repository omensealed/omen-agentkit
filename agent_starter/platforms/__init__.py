"""Platform-neutral host facts and provider contracts.

Host detection and package-manager providers implement the protocol in
``base`` while remaining importable from this compatibility surface.
"""

from .base import (
    ArgvPlan,
    CapabilityRequest,
    CommandResult,
    DetectionConfidence,
    ExecutableFact,
    HostProfile,
    PackageAvailability,
    PackageResolution,
    PackageSource,
    PackageState,
    PackageVerification,
    PlatformProvider,
    PrerequisiteCheck,
    PrerequisiteStatus,
    RootlessPodmanStatus,
)
from .arch import (
    ARCH_CAPABILITIES,
    ArchCapabilityRecord,
    ArchProvider,
    arch_packages_for_capabilities,
)
from .debian import (
    DEBIAN_CAPABILITIES,
    DEBIAN_FLAVORS,
    DebianCapabilityRecord,
    DebianFamilyProvider,
    DebianFlavor,
    debian_packages_for_capabilities,
)
from .detection import (
    DetectionIssue,
    DetectionResult,
    OsReleaseData,
    PROVIDER_IDS,
    SupportLevel,
    detect_host,
    detect_platform,
    parse_os_release,
)

__all__ = [
    "ArgvPlan",
    "ARCH_CAPABILITIES",
    "ArchCapabilityRecord",
    "ArchProvider",
    "CapabilityRequest",
    "DetectionConfidence",
    "DetectionIssue",
    "DetectionResult",
    "CommandResult",
    "DEBIAN_CAPABILITIES",
    "DEBIAN_FLAVORS",
    "DebianCapabilityRecord",
    "DebianFamilyProvider",
    "DebianFlavor",
    "debian_packages_for_capabilities",
    "ExecutableFact",
    "HostProfile",
    "PackageAvailability",
    "PackageResolution",
    "PackageSource",
    "PackageState",
    "PackageVerification",
    "PlatformProvider",
    "PrerequisiteCheck",
    "PrerequisiteStatus",
    "RootlessPodmanStatus",
    "OsReleaseData",
    "PROVIDER_IDS",
    "SupportLevel",
    "detect_host",
    "detect_platform",
    "parse_os_release",
    "arch_packages_for_capabilities",
]
