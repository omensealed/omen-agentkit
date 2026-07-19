from __future__ import annotations

import unittest

from agent_starter.platforms import (
    ARCH_CAPABILITIES,
    CapabilityRequest,
    CommandResult,
    DEBIAN_CAPABILITIES,
    DebianCapabilityRecord,
    DebianFamilyProvider,
    DetectionConfidence,
    ExecutableFact,
    HostProfile,
    PackageAvailability,
    PackageResolution,
    PackageSource,
    PlatformProvider,
    PrerequisiteStatus,
)


class DebianFamilyProviderTests(unittest.TestCase):
    @staticmethod
    def profile(flavor: str, *, apt_get: bool = True) -> HostProfile:
        return HostProfile(
            os_id=flavor,
            os_id_like=("debian",) if flavor == "ubuntu" else (),
            pretty_name="Ubuntu" if flavor == "ubuntu" else "Debian GNU/Linux",
            version_id="24.04" if flavor == "ubuntu" else "12",
            architecture="x86_64",
            package_provider=flavor,
            executables=(ExecutableFact("apt-get", apt_get),),
        )

    def test_one_data_driven_provider_supports_debian_and_ubuntu(self) -> None:
        for flavor in ("debian", "ubuntu"):
            with self.subTest(flavor):
                provider = DebianFamilyProvider(flavor, runner=lambda argv: CommandResult(2))
                self.assertIsInstance(provider, PlatformProvider)
                self.assertEqual(provider.provider_id, flavor)
                self.assertIn(flavor.title(), provider.documentation_label)
                self.assertEqual(
                    provider.detection_confidence(self.profile(flavor)),
                    DetectionConfidence.CONFIRMED,
                )
                self.assertEqual(
                    provider.detection_confidence(self.profile(flavor, apt_get=False)),
                    DetectionConfidence.PARTIAL,
                )

    def test_capability_mapping_uses_debian_names_and_executable_aliases(self) -> None:
        provider = DebianFamilyProvider("debian", runner=lambda argv: CommandResult(2))
        resolutions = provider.resolve_capabilities((
            CapabilityRequest("base.tooling"),
            CapabilityRequest("language.python"),
            CapabilityRequest("database.sqlite"),
        ))
        self.assertEqual(
            [item.package_name for item in resolutions],
            [
                "git", "curl", "jq", "ripgrep", "fd-find", "unzip", "build-essential",
                "python3", "python3-venv", "python3-pip", "sqlite3",
            ],
        )
        self.assertEqual(provider.executable_aliases("base.tooling"), {"fd": "fdfind"})
        self.assertEqual(provider.executable_name("language.python"), "python3")
        self.assertTrue(all(item.source is PackageSource.OFFICIAL for item in resolutions))

    def test_default_catalog_covers_current_arch_capabilities_without_third_party_sources(self) -> None:
        self.assertEqual(set(DEBIAN_CAPABILITIES), set(ARCH_CAPABILITIES))
        self.assertTrue(all(
            record.source is PackageSource.OFFICIAL
            for record in DEBIAN_CAPABILITIES.values()
        ))

    def test_installed_and_available_queries_are_read_only_argv(self) -> None:
        calls: list[tuple[str, ...]] = []

        def runner(argv: tuple[str, ...]) -> CommandResult:
            calls.append(argv)
            package = argv[-1]
            if argv[0] == "dpkg-query":
                if package == "python3":
                    return CommandResult(0, "install ok installed")
                if package == "missing":
                    return CommandResult(1)
                return CommandResult(2, stderr="query failure")
            if package == "python3":
                return CommandResult(0, "python3:\n  Installed: 3.11\n  Candidate: 3.11\n")
            if package == "missing":
                return CommandResult(0, "missing:\n  Installed: (none)\n  Candidate: (none)\n")
            return CommandResult(100, stderr="cache unavailable")

        provider = DebianFamilyProvider("debian", runner=runner)
        installed = provider.query_installed(("python3", "missing", "broken"))
        self.assertEqual([item.installed for item in installed], [True, False, None])
        available = provider.verify_available(("python3", "missing", "broken"))
        self.assertEqual(
            [item.availability for item in available],
            [PackageAvailability.AVAILABLE, PackageAvailability.UNAVAILABLE, PackageAvailability.UNVERIFIED],
        )
        self.assertEqual(calls[0], ("dpkg-query", "-W", "-f=${Status}", "python3"))
        self.assertEqual(calls[3], ("apt-cache", "policy", "python3"))
        self.assertTrue(all(call[0] in {"dpkg-query", "apt-cache"} for call in calls))
        with self.assertRaises(TypeError):
            provider.verify_available("python3")  # type: ignore[arg-type]

    def test_refresh_and_install_plans_are_separate_and_never_upgrade(self) -> None:
        provider = DebianFamilyProvider("ubuntu", runner=lambda argv: CommandResult(2))
        refresh = provider.update_plan(self.profile("ubuntu"))
        self.assertEqual(refresh.argv, ("sudo", "apt-get", "update"))
        self.assertIn("does not upgrade", refresh.purpose)
        packages = (
            PackageResolution("language.python", "python3", PackageAvailability.AVAILABLE),
            PackageResolution("language.python", "python3-venv", PackageAvailability.AVAILABLE),
        )
        install = provider.install_plan(packages)
        self.assertEqual(
            install.argv,
            ("sudo", "apt-get", "install", "--yes", "python3", "python3-venv"),
        )
        combined = " ".join((*refresh.argv, *install.argv))
        self.assertNotIn("upgrade", combined)
        self.assertNotIn("dist-upgrade", combined)
        self.assertNotIn("add-apt-repository", combined)
        with self.assertRaisesRegex(ValueError, "verified available"):
            provider.install_plan((PackageResolution("language.python", "python3"),))

    def test_third_party_records_require_complete_manual_review_and_never_install(self) -> None:
        with self.assertRaisesRegex(ValueError, "source, key, pinning, and removal"):
            DebianCapabilityRecord(
                "vendor.incomplete",
                ("vendor-tool",),
                source=PackageSource.MANUAL_REVIEW,
                explanation="Third-party source needs review.",
            )
        manual = DebianCapabilityRecord(
            "vendor.reviewed-manually",
            ("vendor-tool",),
            "vendor-tool",
            source=PackageSource.MANUAL_REVIEW,
            explanation=(
                "Third-party source URL, signing key fingerprint/distribution, APT pinning, "
                "and repository/package removal instructions require separate human security review."
            ),
        )
        provider = DebianFamilyProvider(
            "debian", runner=lambda argv: CommandResult(2), catalog={manual.capability_id: manual}
        )
        resolution = provider.resolve_capabilities((CapabilityRequest(manual.capability_id),))[0]
        self.assertEqual(resolution.availability, PackageAvailability.UNVERIFIED)
        self.assertEqual(resolution.source, PackageSource.MANUAL_REVIEW)
        self.assertFalse(resolution.installable)
        with self.assertRaisesRegex(ValueError, "third-party review"):
            provider.install_plan((resolution,))

    def test_rootless_check_is_profile_only(self) -> None:
        calls: list[tuple[str, ...]] = []
        provider = DebianFamilyProvider("debian", runner=lambda argv: calls.append(argv) or CommandResult(0))
        checks = provider.rootless_podman_checks(self.profile("debian"))
        self.assertEqual(checks[0].status, PrerequisiteStatus.ACTION_REQUIRED)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
