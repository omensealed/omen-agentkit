from __future__ import annotations

import unittest

from agent_starter.models import AdvisorCapability, AdvisorRecommendation, ProjectConfig, SandboxConfig
from agent_starter.platforms import (
    CapabilityRequest,
    DetectionConfidence,
    ExecutableFact,
    HostProfile,
    PackageAvailability,
    PackageResolution,
    PackageSource,
    PackageState,
    PackageVerification,
)
from agent_starter.recommendation import (
    RecommendationSource,
    build_recommendation_review,
    render_recommendation_review,
)


class FakeProvider:
    provider_id = "debian"
    package_manager_id = "apt-get"
    documentation_label = "Debian test provider"
    shell_executable = "/bin/sh"

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[str, ...]]] = []

    def detection_confidence(self, profile: HostProfile) -> DetectionConfidence:
        return DetectionConfidence.CONFIRMED

    def resolve_capabilities(self, requests: object) -> tuple[PackageResolution, ...]:
        typed = tuple(requests)  # type: ignore[arg-type]
        self.calls.append(("resolve", tuple(item.capability_id for item in typed)))
        mapping = {
            "base.tooling": ("git",),
            "language.python": ("python3", "python3-venv"),
            "database.sqlite": ("sqlite3",),
            "sandbox.rootless-podman": ("podman", "uidmap"),
            "optional.shellcheck": ("shellcheck",),
        }
        return tuple(
            PackageResolution(request.capability_id, package)
            for request in typed
            for package in mapping[request.capability_id]
        )

    def verify_available(self, package_names: object) -> tuple[PackageVerification, ...]:
        names = tuple(package_names)  # type: ignore[arg-type]
        self.calls.append(("verify", names))
        return tuple(PackageVerification(
            name,
            PackageAvailability.UNAVAILABLE if name == "shellcheck" else PackageAvailability.AVAILABLE,
        ) for name in names)

    def query_installed(self, package_names: object) -> tuple[PackageState, ...]:
        names = tuple(package_names)  # type: ignore[arg-type]
        self.calls.append(("installed", names))
        return tuple(PackageState(name, name in {"git", "python3"}) for name in names)

    def update_plan(self, profile: HostProfile):
        raise AssertionError("recommendation review must not construct an update plan")

    def install_plan(self, packages: object):
        raise AssertionError("recommendation review must not construct an install plan")

    def rootless_podman_checks(self, profile: HostProfile):
        return ()

    def executable_name(self, capability_id: str) -> str:
        return capability_id


class ManualSourceProvider(FakeProvider):
    def resolve_capabilities(self, requests: object) -> tuple[PackageResolution, ...]:
        resolutions = super().resolve_capabilities(requests)
        return tuple(
            PackageResolution(
                item.capability_id,
                item.package_name,
                source=PackageSource.MANUAL_REVIEW,
                installable=False,
                explanation="Third-party source requires separate human review.",
            )
            if item.capability_id == "optional.shellcheck" else item
            for item in resolutions
        )


class RecommendationPipelineTests(unittest.TestCase):
    def config(self) -> ProjectConfig:
        return ProjectConfig(
            project_name="Pipeline",
            languages=["python"],
            database="sqlite",
            github_actions=False,
            sandbox=SandboxConfig(enabled=True, mode="toolchain"),
        )

    def profile(self) -> HostProfile:
        return HostProfile(
            os_id="debian",
            os_id_like=(),
            pretty_name="Debian GNU/Linux 12",
            version_id="12",
            architecture="x86_64",
            package_provider="debian",
            executables=(ExecutableFact("apt-get", True),),
        )

    def test_pipeline_merges_ids_then_uses_only_provider_owned_package_names(self) -> None:
        provider = FakeProvider()
        advisor = AdvisorRecommendation(recommended_capabilities=[AdvisorCapability(
            "optional.shellcheck",
            "Check shell scripts.",
            "optional",
            "The project generates shell helpers.",
            "medium",
        )])
        review = build_recommendation_review(
            self.config(), profile=self.profile(), provider=provider, advisor=advisor
        )
        self.assertEqual(
            review.capability_ids,
            (
                "base.tooling", "language.python", "database.sqlite",
                "sandbox.rootless-podman", "optional.shellcheck",
            ),
        )
        shellcheck = next(item for item in review.items if item.capability_id == "optional.shellcheck")
        self.assertEqual(shellcheck.origin, "ai-suggested")
        self.assertEqual(shellcheck.requirement, "optional")
        self.assertEqual(shellcheck.packages[0].package_name, "shellcheck")
        self.assertEqual(shellcheck.packages[0].availability, PackageAvailability.UNAVAILABLE)
        self.assertFalse(shellcheck.packages[0].installed)
        self.assertEqual([name for name, _ in provider.calls], ["resolve", "verify", "installed"])
        self.assertFalse(any("sudo" in value for _, values in provider.calls for value in values))

    def test_advisor_prose_cannot_inject_a_fake_provider_package_or_plan(self) -> None:
        provider = FakeProvider()
        fake_name = "definitely-not-a-real-package"
        advisor = AdvisorRecommendation(recommended_capabilities=[AdvisorCapability(
            "optional.shellcheck",
            "Check shell scripts.",
            "optional",
            f"A model mentioned {fake_name} as prose only.",
            "low",
        )])
        review = build_recommendation_review(
            self.config(), profile=self.profile(), provider=provider, advisor=advisor
        )
        queried = tuple(value for _, values in provider.calls for value in values)
        mapped = tuple(package.package_name for item in review.items for package in item.packages)
        self.assertNotIn(fake_name, queried)
        self.assertNotIn(fake_name, mapped)
        self.assertEqual([name for name, _ in provider.calls], ["resolve", "verify", "installed"])

    def test_required_baseline_cannot_be_removed_by_advisor_omission(self) -> None:
        review = build_recommendation_review(
            self.config(), profile=self.profile(), provider=FakeProvider(), advisor=AdvisorRecommendation()
        )
        self.assertIn("base.tooling", review.capability_ids)
        self.assertIn("language.python", review.capability_ids)
        self.assertTrue(all(
            item.requirement == "required"
            for item in review.items
            if item.capability_id in {"base.tooling", "language.python", "database.sqlite"}
        ))

    def test_unsupported_provider_is_reviewable_without_queries_or_arch_fallback(self) -> None:
        profile = HostProfile(
            os_id="fedora",
            os_id_like=("rhel",),
            pretty_name="Fedora Linux",
            version_id="42",
            architecture="x86_64",
            package_provider=None,
        )
        review = build_recommendation_review(self.config(), profile=profile, provider=None)
        self.assertIsNone(review.provider_id)
        self.assertTrue(review.warnings)
        self.assertTrue(all(not item.packages for item in review.items))
        self.assertNotIn("pacman", "\n".join(render_recommendation_review(review)).lower())

    def test_provider_mismatch_is_blocked_before_any_query(self) -> None:
        provider = FakeProvider()
        provider.provider_id = "arch"
        provider.documentation_label = "Wrong Arch provider"
        review = build_recommendation_review(self.config(), profile=self.profile(), provider=provider)
        self.assertIsNone(review.provider_id)
        self.assertEqual(provider.calls, [])
        self.assertIn("does not match", "\n".join(review.warnings))

    def test_beginner_review_distinguishes_installed_missing_and_unavailable(self) -> None:
        review = build_recommendation_review(
            self.config(), profile=self.profile(), provider=FakeProvider(), advisor=AdvisorRecommendation(
                recommended_capabilities=[AdvisorCapability(
                    "optional.shellcheck", "Check shell scripts.", "optional", "Useful for helpers.", "medium"
                )]
            )
        )
        text = "\n".join(render_recommendation_review(review))
        self.assertIn("already installed", text)
        self.assertIn("available but not installed", text)
        self.assertIn("unavailable from configured repositories", text)
        self.assertIn("No package or command was executed", text)

    def test_each_item_has_typed_provenance_confidence_and_provider_mapping(self) -> None:
        review = build_recommendation_review(
            self.config(),
            profile=self.profile(),
            provider=FakeProvider(),
            advisor=AdvisorRecommendation(
                recommended_capabilities=[AdvisorCapability(
                    "optional.shellcheck", "Check shell scripts.", "optional",
                    "Useful for generated helpers.", "medium",
                )],
                questions=["Are shell helpers part of the supported interface?"],
            ),
            user_capability_ids=("optional.shellcheck",),
        )
        baseline = next(item for item in review.items if item.capability_id == "language.python")
        suggested = next(item for item in review.items if item.capability_id == "optional.shellcheck")
        self.assertEqual(baseline.sources, (RecommendationSource.DETERMINISTIC,))
        self.assertEqual(baseline.confidence, "high")
        self.assertEqual(baseline.provider_id, "debian")
        self.assertEqual(
            suggested.sources,
            (RecommendationSource.AI_SUGGESTED, RecommendationSource.USER_REQUESTED),
        )
        self.assertEqual(suggested.confidence, "medium")
        self.assertEqual(
            suggested.unresolved_questions,
            ("Are shell helpers part of the supported interface?",),
        )

    def test_review_renders_explicit_p3_004_evidence_without_command_authority(self) -> None:
        review = build_recommendation_review(
            self.config(),
            profile=self.profile(),
            provider=FakeProvider(),
            advisor=AdvisorRecommendation(
                recommended_capabilities=[AdvisorCapability(
                    "optional.shellcheck", "Check shell scripts.", "optional",
                    "Useful for generated helpers.", "medium",
                )],
                risks=["Shell support scope is not confirmed."],
                questions=["Are shell helpers supported?"],
            ),
        )
        text = "\n".join(render_recommendation_review(review))
        for expected in (
            "Reason needed:",
            "Source: deterministic",
            "Source: ai-suggested",
            "Confidence: high",
            "Confidence: medium",
            "Provider mapping: debian -> git",
            "Verification: available",
            "Installed: yes",
            "Package source: official",
            "Unresolved question: Are shell helpers supported?",
            "Review-wide risk: Shell support scope is not confirmed.",
        ):
            self.assertIn(expected, text)
        self.assertNotIn("apt-get install", text)

    def test_manual_or_third_party_mapping_stays_unverified_and_out_of_queries(self) -> None:
        provider = ManualSourceProvider()
        review = build_recommendation_review(
            self.config(),
            profile=self.profile(),
            provider=provider,
            advisor=AdvisorRecommendation(recommended_capabilities=[AdvisorCapability(
                "optional.shellcheck", "Check shell scripts.", "optional",
                "Useful for generated helpers.", "low",
            )]),
        )
        shellcheck = next(item for item in review.items if item.capability_id == "optional.shellcheck")
        package = shellcheck.packages[0]
        self.assertEqual(package.source, PackageSource.MANUAL_REVIEW)
        self.assertEqual(package.availability, PackageAvailability.UNVERIFIED)
        self.assertIsNone(package.installed)
        queried_names = [values for name, values in provider.calls if name in {"verify", "installed"}]
        self.assertTrue(all("shellcheck" not in names for names in queried_names))
        text = "\n".join(render_recommendation_review(review))
        self.assertIn("Package source: manual-review", text)
        self.assertIn("manual review required; not an automatic install candidate", text)


if __name__ == "__main__":
    unittest.main()
