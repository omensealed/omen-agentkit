from __future__ import annotations

import unittest

from agent_starter.platforms import (
    ArgvPlan,
    ArchCapabilityRecord,
    ArchProvider,
    CapabilityRequest,
    CommandResult,
    DetectionConfidence,
    SupportLevel,
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
    detect_platform,
    parse_os_release,
)


class FakeProvider:
    provider_id = "test"
    package_manager_id = "test-pkg"
    documentation_label = "Test Linux (test-pkg)"
    shell_executable = "/bin/sh"

    def detection_confidence(self, profile: HostProfile) -> DetectionConfidence:
        return DetectionConfidence.CONFIRMED

    def query_installed(self, package_names: object) -> tuple[PackageState, ...]:
        return (PackageState("python", True),)

    def verify_available(self, package_names: object) -> tuple[PackageVerification, ...]:
        return (PackageVerification("python", PackageAvailability.AVAILABLE),)

    def resolve_capabilities(self, requests: object) -> tuple[PackageResolution, ...]:
        return (PackageResolution("python", "python"),)

    def update_plan(self, profile: HostProfile) -> ArgvPlan:
        return ArgvPlan("Update", ("test-pkg", "update"), "Review repository metadata update", True)

    def install_plan(self, packages: object) -> ArgvPlan:
        return ArgvPlan("Install", ("test-pkg", "install", "python"), "Review package install", True, True)

    def rootless_podman_checks(self, profile: HostProfile) -> tuple[PrerequisiteCheck, ...]:
        return ()

    def executable_name(self, capability_id: str) -> str:
        return capability_id


class PlatformContractTests(unittest.TestCase):
    def make_profile(self) -> HostProfile:
        return HostProfile(
            os_id="cachyos",
            os_id_like=("arch",),
            pretty_name="CachyOS",
            version_id="rolling",
            architecture="x86_64",
            package_provider="arch",
            executables=(ExecutableFact("python3", True, "3.14.6"),),
            rootless_podman=RootlessPodmanStatus(
                executable_available=True,
                rootless_usable=None,
                checks=(PrerequisiteCheck("subuid", PrerequisiteStatus.UNKNOWN, "Not checked."),),
            ),
            selected_languages=("python",),
            selected_targets=("linux",),
        )

    def test_advisor_profile_is_an_explicit_redacted_allowlist(self) -> None:
        payload = self.make_profile().to_advisor_dict()
        self.assertEqual(
            set(payload),
            {
                "os_id", "os_id_like", "pretty_name", "version_id", "architecture",
                "package_provider", "executables", "rootless_podman", "selected_languages",
                "selected_targets",
            },
        )
        serialized = repr(payload).lower()
        for forbidden in ("username", "hostname", "home_path", "ip_address", "environment", "token", "cookie", "ssh"):
            self.assertNotIn(forbidden, serialized)

    def test_provider_protocol_covers_reviewable_platform_operations(self) -> None:
        provider = FakeProvider()
        self.assertIsInstance(provider, PlatformProvider)
        profile = self.make_profile()
        self.assertEqual(provider.detection_confidence(profile), DetectionConfidence.CONFIRMED)
        self.assertEqual(provider.query_installed(("python",))[0].installed, True)
        self.assertEqual(provider.verify_available(("python",))[0].availability, PackageAvailability.AVAILABLE)
        self.assertEqual(provider.resolve_capabilities((CapabilityRequest("python"),))[0].package_name, "python")
        self.assertEqual(provider.executable_name("python"), "python")

    def test_process_plans_are_argv_only_and_expose_authority(self) -> None:
        plan = FakeProvider().install_plan(())
        self.assertEqual(plan.argv, ("test-pkg", "install", "python"))
        self.assertTrue(plan.requires_network)
        self.assertTrue(plan.requires_privilege)
        self.assertFalse(hasattr(plan, "shell_command"))
        with self.assertRaises(ValueError):
            ArgvPlan("Bad", (), "No executable")
        with self.assertRaises(ValueError):
            ArgvPlan("Bad", ("tool", "bad\x00argument"), "Malformed")

    def test_package_and_host_values_reject_shell_or_identity_shaped_inputs(self) -> None:
        with self.assertRaises(ValueError):
            PackageResolution("python", "python;curl")
        with self.assertRaises(ValueError):
            ExecutableFact("/home/person/tool", True)
        with self.assertRaises(TypeError):
            CapabilityRequest("python", required="false")  # type: ignore[arg-type]


class PlatformDetectionTests(unittest.TestCase):
    @staticmethod
    def lookup(*available: str):
        names = set(available)
        return lambda name: f"/usr/bin/{name}" if name in names else None

    def test_os_release_parser_handles_quotes_escapes_and_malformed_lines(self) -> None:
        parsed = parse_os_release(
            'ID=ubuntu\nID_LIKE="debian linux"\nPRETTY_NAME="Ubuntu \\"LTS\\""\nBROKEN\n'
        )
        self.assertEqual(parsed.values["ID"], "ubuntu")
        self.assertEqual(parsed.values["ID_LIKE"], "debian linux")
        self.assertEqual(parsed.values["PRETTY_NAME"], 'Ubuntu "LTS"')
        self.assertEqual(parsed.issues[0].code, "malformed_os_release_line")

    def test_supported_families_require_matching_metadata_and_executable(self) -> None:
        fixtures = (
            ('ID=cachyos\nID_LIKE=arch\nPRETTY_NAME="CachyOS"\n', "pacman", "arch"),
            ('ID=debian\nPRETTY_NAME="Debian GNU/Linux"\n', "apt-get", "debian"),
            ('ID=ubuntu\nID_LIKE=debian\nPRETTY_NAME="Ubuntu"\n', "apt-get", "ubuntu"),
        )
        for text, manager, expected in fixtures:
            with self.subTest(expected):
                result = detect_platform(
                    text, architecture="x86_64", executable_lookup=self.lookup(manager)
                )
                self.assertEqual(result.profile.package_provider, expected)
                self.assertEqual(result.package_manager, manager)
                self.assertEqual(result.support, SupportLevel.SUPPORTED)
                self.assertEqual(result.confidence, DetectionConfidence.CONFIRMED)

    def test_matching_os_without_package_manager_is_partial(self) -> None:
        result = detect_platform(
            "ID=arch\nPRETTY_NAME=Arch\n", architecture="aarch64", executable_lookup=self.lookup()
        )
        self.assertEqual(result.profile.package_provider, "arch")
        self.assertEqual(result.support, SupportLevel.PARTIAL)
        self.assertEqual(result.confidence, DetectionConfidence.PARTIAL)
        self.assertEqual(result.issues[-1].code, "package_manager_missing")

    def test_executable_presence_never_overrides_contradictory_os_metadata(self) -> None:
        queried: list[str] = []

        def lookup(name: str) -> str | None:
            queried.append(name)
            return "/usr/bin/apt-get"

        result = detect_platform(
            'ID=fedora\nPRETTY_NAME="Fedora Linux"\n',
            architecture="x86_64",
            executable_lookup=lookup,
        )
        self.assertIsNone(result.profile.package_provider)
        self.assertEqual(result.support, SupportLevel.UNSUPPORTED)
        self.assertEqual(result.confidence, DetectionConfidence.CONTRADICTED)
        self.assertEqual(queried, [])
        self.assertEqual(result.issues[-1].code, "unsupported_platform")

    def test_missing_metadata_is_unknown_not_executable_inference(self) -> None:
        result = detect_platform(
            None, architecture="x86_64", executable_lookup=self.lookup("pacman", "apt-get")
        )
        self.assertIsNone(result.profile.package_provider)
        self.assertEqual(result.support, SupportLevel.UNKNOWN)
        self.assertEqual(result.confidence, DetectionConfidence.UNKNOWN)
        self.assertEqual(result.profile.executables, ())

    def test_override_requires_proof_and_keeps_contradiction_visible(self) -> None:
        text = 'ID=cachyos\nID_LIKE=arch\nPRETTY_NAME="CachyOS"\n'
        accepted = detect_platform(
            text,
            architecture="x86_64",
            executable_lookup=self.lookup("pacman", "apt-get"),
            override="debian",
        )
        self.assertEqual(accepted.detected_provider, "arch")
        self.assertEqual(accepted.profile.package_provider, "debian")
        self.assertEqual(accepted.confidence, DetectionConfidence.CONTRADICTED)
        self.assertEqual(accepted.support, SupportLevel.PARTIAL)
        self.assertEqual(accepted.issues[-1].code, "provider_override_contradicts_os")

        rejected = detect_platform(
            text,
            architecture="x86_64",
            executable_lookup=self.lookup("pacman"),
            override="debian",
        )
        self.assertIsNone(rejected.profile.package_provider)
        self.assertTrue(rejected.has_errors)
        self.assertEqual(rejected.issues[-1].code, "override_proof_failed")


class ArchProviderTests(unittest.TestCase):
    @staticmethod
    def profile(*, pacman: bool = True, os_id: str = "cachyos") -> HostProfile:
        return HostProfile(
            os_id=os_id,
            os_id_like=("arch",) if os_id == "cachyos" else (),
            pretty_name="CachyOS" if os_id == "cachyos" else "Other Linux",
            version_id="rolling",
            architecture="x86_64",
            package_provider="arch",
            executables=(ExecutableFact("pacman", pacman),),
        )

    def test_arch_provider_matches_protocol_and_preserved_capabilities(self) -> None:
        provider = ArchProvider(runner=lambda argv: CommandResult(2))
        self.assertIsInstance(provider, PlatformProvider)
        self.assertEqual(provider.detection_confidence(self.profile()), DetectionConfidence.CONFIRMED)
        self.assertEqual(provider.executable_name("language.python"), "python3")
        resolutions = provider.resolve_capabilities((
            CapabilityRequest("base.tooling"),
            CapabilityRequest("language.python"),
            CapabilityRequest("database.sqlite"),
        ))
        self.assertEqual(
            [item.package_name for item in resolutions],
            ["git", "curl", "jq", "ripgrep", "fd", "unzip", "base-devel", "python", "python-pip", "sqlite"],
        )
        self.assertTrue(all(item.source is PackageSource.OFFICIAL for item in resolutions))
        with self.assertRaisesRegex(ValueError, "Unsupported required"):
            provider.resolve_capabilities((CapabilityRequest("unknown.required"),))
        self.assertEqual(provider.resolve_capabilities((CapabilityRequest("unknown.optional", required=False),)), ())

    def test_read_only_pacman_queries_are_argv_and_status_is_structured(self) -> None:
        calls: list[tuple[str, ...]] = []

        def runner(argv: tuple[str, ...]) -> CommandResult:
            calls.append(argv)
            package = argv[-1]
            return CommandResult({"python": 0, "missing": 1}.get(package, 2))

        provider = ArchProvider(runner=runner)
        states = provider.query_installed(("python", "missing", "broken"))
        self.assertEqual([item.installed for item in states], [True, False, None])
        verified = provider.verify_available(("python", "missing", "broken"))
        self.assertEqual(
            [item.availability for item in verified],
            [PackageAvailability.AVAILABLE, PackageAvailability.UNAVAILABLE, PackageAvailability.UNVERIFIED],
        )
        self.assertEqual(calls[:3], [
            ("pacman", "-Qq", "python"),
            ("pacman", "-Qq", "missing"),
            ("pacman", "-Qq", "broken"),
        ])
        self.assertEqual(calls[3], ("pacman", "-Si", "python"))
        self.assertTrue(all(call[0] == "pacman" and call[1] in {"-Qq", "-Si"} for call in calls))
        with self.assertRaises(TypeError):
            provider.query_installed("python")  # type: ignore[arg-type]

    def test_update_and_install_are_review_only_verified_argv_plans(self) -> None:
        provider = ArchProvider(runner=lambda argv: CommandResult(2))
        update = provider.update_plan(self.profile())
        self.assertEqual(update.argv, ("sudo", "pacman", "-Syu"))
        self.assertIn("never embed", update.purpose)
        self.assertTrue(update.requires_network)
        self.assertTrue(update.requires_privilege)

        packages = (
            PackageResolution("language.python", "python", PackageAvailability.AVAILABLE),
            PackageResolution("language.python", "python-pip", PackageAvailability.AVAILABLE),
        )
        install = provider.install_plan(packages)
        self.assertEqual(install.argv, ("sudo", "pacman", "-S", "--needed", "python", "python-pip"))
        with self.assertRaisesRegex(ValueError, "verified available"):
            provider.install_plan((PackageResolution("language.python", "python"),))

    def test_aur_capability_is_manual_unverified_and_never_installable(self) -> None:
        manual = ArchCapabilityRecord(
            "editor.manual",
            ("example-aur-bin",),
            "example-editor",
            PackageSource.MANUAL_REVIEW,
            "AUR-only suggestion: inspect the PKGBUILD and source manually; no helper is enabled.",
        )
        provider = ArchProvider(runner=lambda argv: CommandResult(2), catalog={manual.capability_id: manual})
        resolution = provider.resolve_capabilities((CapabilityRequest("editor.manual"),))[0]
        self.assertEqual(resolution.availability, PackageAvailability.UNVERIFIED)
        self.assertEqual(resolution.source, PackageSource.MANUAL_REVIEW)
        self.assertFalse(resolution.installable)
        self.assertIn("AUR", resolution.explanation)
        with self.assertRaisesRegex(ValueError, "manual/AUR review"):
            provider.install_plan((resolution,))

    def test_rootless_podman_check_does_not_probe_or_install(self) -> None:
        calls: list[tuple[str, ...]] = []
        provider = ArchProvider(runner=lambda argv: calls.append(argv) or CommandResult(0))
        checks = provider.rootless_podman_checks(self.profile())
        self.assertEqual(checks[0].code, "podman-executable")
        self.assertEqual(checks[0].status, PrerequisiteStatus.ACTION_REQUIRED)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
