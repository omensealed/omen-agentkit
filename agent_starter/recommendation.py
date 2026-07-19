"""Non-executing capability recommendation review pipeline.

Project and advisor intent is expressed as provider-neutral capability IDs.
Only the selected platform provider may translate those IDs to package names,
and this module deliberately never constructs or executes update/install plans.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from .capabilities import CAPABILITY_CATALOG, select_capabilities
from .models import AdvisorRecommendation, ProjectConfig
from .platforms import (
    CapabilityRequest,
    HostProfile,
    PackageAvailability,
    PackageResolution,
    PackageSource,
    PlatformProvider,
)


class RecommendationSource(str, Enum):
    """Review provenance without implying approval or execution authority."""

    DETERMINISTIC = "deterministic"
    AI_SUGGESTED = "ai-suggested"
    USER_REQUESTED = "user-requested"


@dataclass(frozen=True, slots=True)
class ReviewedPackage:
    """One provider-owned package candidate and its read-only host state."""

    package_name: str
    availability: PackageAvailability
    installed: bool | None
    source: PackageSource
    installable: bool
    explanation: str = ""


@dataclass(frozen=True, slots=True)
class ReviewedCapability:
    """Provider-neutral intent joined to provider-owned package candidates."""

    capability_id: str
    display_label: str
    purpose: str
    requirement: str
    sources: tuple[RecommendationSource, ...]
    rationale: str = ""
    confidence: str = ""
    provider_id: str | None = None
    unresolved_questions: tuple[str, ...] = ()
    packages: tuple[ReviewedPackage, ...] = ()
    warning: str = ""

    @property
    def origin(self) -> str:
        """Preserve the P3-003 single-origin compatibility view."""

        return self.sources[0].value


@dataclass(frozen=True, slots=True)
class RecommendationReview:
    """Beginner-reviewable result; contains no executable command plans."""

    provider_id: str | None
    provider_label: str
    items: tuple[ReviewedCapability, ...]
    warnings: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    questions: tuple[str, ...] = ()

    @property
    def capability_ids(self) -> tuple[str, ...]:
        return tuple(item.capability_id for item in self.items)


def _baseline_capability_ids(config: ProjectConfig) -> tuple[str, ...]:
    return select_capabilities(
        config.languages,
        config.database,
        github=config.github_actions,
        rootless_podman=config.sandbox.enabled,
    )


def _intent_items(
    config: ProjectConfig,
    advisor: AdvisorRecommendation | None,
    user_capability_ids: Sequence[str],
) -> tuple[ReviewedCapability, ...]:
    baseline = _baseline_capability_ids(config)
    suggestions = {
        item.capability_id: item
        for item in (advisor.recommended_capabilities if advisor is not None else ())
    }
    if isinstance(user_capability_ids, (str, bytes)):
        raise TypeError("user_capability_ids must be a sequence of canonical capability IDs.")
    requested: list[str] = []
    for capability_id in user_capability_ids:
        if not isinstance(capability_id, str) or capability_id not in CAPABILITY_CATALOG:
            raise ValueError(f"Unknown user-requested capability ID: {capability_id!r}.")
        if capability_id not in requested:
            requested.append(capability_id)
    ordered_ids = (
        *baseline,
        *(item_id for item_id in suggestions if item_id not in baseline),
        *(item_id for item_id in requested if item_id not in baseline and item_id not in suggestions),
    )
    result: list[ReviewedCapability] = []
    for capability_id in ordered_ids:
        definition = CAPABILITY_CATALOG.get(capability_id)
        suggestion = suggestions.get(capability_id)
        purpose = definition.purpose if definition is not None else suggestion.purpose if suggestion else ""
        sources: list[RecommendationSource] = []
        if capability_id in baseline:
            sources.append(RecommendationSource.DETERMINISTIC)
        if suggestion is not None:
            sources.append(RecommendationSource.AI_SUGGESTED)
        if capability_id in requested:
            sources.append(RecommendationSource.USER_REQUESTED)
        result.append(ReviewedCapability(
            capability_id=capability_id,
            display_label=definition.display_label if definition is not None else capability_id,
            purpose=purpose,
            requirement="required" if capability_id in baseline else suggestion.requirement if suggestion else "optional",
            sources=tuple(sources),
            rationale=suggestion.rationale if suggestion else "",
            confidence=suggestion.confidence if suggestion else "high" if capability_id in baseline else "not-assessed",
            unresolved_questions=tuple(advisor.questions if advisor is not None and suggestion is not None else ()),
            warning=(
                "No provider-neutral catalog entry exists for this advisor suggestion; "
                "it was not resolved to packages."
                if definition is None else ""
            ),
        ))
    return tuple(result)


def _with_packages(
    items: tuple[ReviewedCapability, ...],
    resolutions: tuple[PackageResolution, ...],
    *,
    provider_id: str,
    availability: dict[str, tuple[PackageAvailability, str]],
    installed: dict[str, bool | None],
) -> tuple[ReviewedCapability, ...]:
    by_capability: dict[str, list[ReviewedPackage]] = {}
    for resolution in resolutions:
        resolved_availability, verification_explanation = availability.get(
            resolution.package_name,
            (resolution.availability, ""),
        )
        explanation = verification_explanation or resolution.explanation
        by_capability.setdefault(resolution.capability_id, []).append(ReviewedPackage(
            package_name=resolution.package_name,
            availability=resolved_availability,
            installed=installed.get(resolution.package_name),
            source=resolution.source,
            installable=resolution.installable,
            explanation=explanation,
        ))
    return tuple(ReviewedCapability(
        capability_id=item.capability_id,
        display_label=item.display_label,
        purpose=item.purpose,
        requirement=item.requirement,
        sources=item.sources,
        rationale=item.rationale,
        confidence=item.confidence,
        provider_id=provider_id,
        unresolved_questions=item.unresolved_questions,
        packages=tuple(by_capability.get(item.capability_id, ())),
        warning=item.warning,
    ) for item in items)


def build_recommendation_review(
    config: ProjectConfig,
    *,
    profile: HostProfile,
    provider: PlatformProvider | None,
    advisor: AdvisorRecommendation | None = None,
    user_capability_ids: Sequence[str] = (),
) -> RecommendationReview:
    """Resolve and inspect recommendations without constructing command plans."""

    items = _intent_items(config, advisor, user_capability_ids)
    warnings = [item.warning for item in items if item.warning]
    if provider is not None and provider.provider_id != profile.package_provider:
        warnings.append(
            f"The selected provider {provider.provider_id!r} does not match the detected "
            f"provider {profile.package_provider!r}; package resolution was blocked."
        )
        provider = None
    if provider is None:
        warnings.append(
            "No supported package provider was selected for this host. Capability intent is shown, "
            "but package names and installation guidance remain unresolved."
        )
        return RecommendationReview(
            provider_id=None,
            provider_label="Unsupported or unconfirmed host",
            items=items,
            warnings=tuple(dict.fromkeys(warnings)),
            risks=tuple(advisor.risks if advisor else ()),
            questions=tuple(advisor.questions if advisor else ()),
        )

    resolvable = tuple(item for item in items if item.capability_id in CAPABILITY_CATALOG)
    requests = tuple(CapabilityRequest(
        item.capability_id,
        required=item.requirement == "required",
        purpose=item.purpose,
    ) for item in resolvable)
    try:
        resolutions = provider.resolve_capabilities(requests)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        warnings.append(f"The selected provider could not resolve capability intent: {exc}")
        resolutions = ()

    candidates = tuple(dict.fromkeys(
        item.package_name
        for item in resolutions
        if item.source is PackageSource.OFFICIAL and item.installable
    ))
    availability: dict[str, tuple[PackageAvailability, str]] = {}
    installed: dict[str, bool | None] = {}
    if candidates:
        try:
            availability = {
                item.package_name: (item.availability, item.explanation)
                for item in provider.verify_available(candidates)
            }
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            warnings.append(f"Repository availability could not be verified: {exc}")
        try:
            installed = {
                item.package_name: item.installed
                for item in provider.query_installed(candidates)
            }
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            warnings.append(f"Installed state could not be checked: {exc}")

    return RecommendationReview(
        provider_id=provider.provider_id,
        provider_label=provider.documentation_label,
        items=_with_packages(
            items,
            resolutions,
            provider_id=provider.provider_id,
            availability=availability,
            installed=installed,
        ),
        warnings=tuple(dict.fromkeys(warnings)),
        risks=tuple(advisor.risks if advisor else ()),
        questions=tuple(advisor.questions if advisor else ()),
    )


def _package_status(package: ReviewedPackage) -> str:
    if package.source is PackageSource.MANUAL_REVIEW or not package.installable:
        return "manual review required; not an automatic install candidate"
    if package.installed is True:
        return "already installed"
    if package.availability is PackageAvailability.UNAVAILABLE:
        return "unavailable from configured repositories"
    if package.availability is PackageAvailability.AVAILABLE:
        return "available but not installed" if package.installed is False else "available; installed state unknown"
    return "repository availability unverified"


def render_recommendation_review(review: RecommendationReview) -> tuple[str, ...]:
    """Render a plain-language review without executable shell text."""

    lines = [f"Capability and package review — {review.provider_label}"]
    for item in review.items:
        lines.append(f"  {item.display_label} ({item.requirement})")
        lines.append(f"    Reason needed: {item.purpose}")
        lines.append(f"    Source: {', '.join(source.value for source in item.sources)}")
        lines.append(f"    Confidence: {item.confidence}")
        if item.rationale:
            lines.append(f"    Advisor rationale: {item.rationale}")
        for question in item.unresolved_questions:
            lines.append(f"    Unresolved question: {question}")
        if item.packages:
            for package in item.packages:
                lines.append(
                    f"    Provider mapping: {item.provider_id or 'unresolved'} -> {package.package_name}"
                )
                lines.append(f"      Verification: {package.availability.value}")
                lines.append(
                    "      Installed: "
                    + ("yes" if package.installed is True else "no" if package.installed is False else "unknown")
                )
                lines.append(f"      Package source: {package.source.value}")
                lines.append(f"      Review status: {_package_status(package)}")
                if package.explanation:
                    lines.append(f"      Provider note: {package.explanation}")
        elif not item.warning:
            lines.append("    Provider mapping: unresolved; no provider package candidate")
        if item.warning:
            lines.append(f"    Warning: {item.warning}")
    for warning in review.warnings:
        lines.append(f"  Warning: {warning}")
    for risk in review.risks:
        lines.append(f"  Review-wide risk: {risk}")
    for question in review.questions:
        lines.append(f"  Review-wide question: {question}")
    lines.append("No package or command was executed. Review this intent before any later approval step.")
    return tuple(lines)
