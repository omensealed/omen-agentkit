from __future__ import annotations

import json
import unittest

from agent_starter.doctor import (
    CodexDoctorState,
    DoctorStatus,
    build_doctor_report,
    provider_for_detection,
    render_doctor_text,
)
from agent_starter.platforms import (
    CommandResult,
    SupportLevel,
    detect_platform,
)


class DoctorReportTests(unittest.TestCase):
    @staticmethod
    def lookup(*available: str):
        names = set(available)
        return lambda name: f"/synthetic/{name}" if name in names else None

    def test_status_values_and_codex_evidence_are_bounded(self) -> None:
        self.assertEqual(
            {status.value for status in DoctorStatus},
            {"pass", "action-needed", "optional", "blocked", "unverified"},
        )
        with self.assertRaises(ValueError):
            CodexDoctorState(installed=True, version="codex\nforged", authorized=True)

    def test_ubuntu_report_is_provider_appropriate_and_json_safe(self) -> None:
        detection = detect_platform(
            'ID=ubuntu\nID_LIKE=debian\nPRETTY_NAME="Ubuntu 24.04"\nVERSION_ID=24.04\n',
            architecture="x86_64",
            executable_lookup=self.lookup("apt-get"),
        )

        def runner(argv: tuple[str, ...]) -> CommandResult:
            self.assertEqual(argv[0], "dpkg-query")
            return CommandResult(0, "install ok installed")

        provider = provider_for_detection(detection, runner=runner)
        report = build_doctor_report(
            kit_version="test",
            python_version="3.11.9",
            detection=detection,
            provider=provider,
            executable_lookup=self.lookup("bash", "git", "curl"),
            codex=CodexDoctorState(installed=False, version="not installed", authorized=False),
        )
        payload = report.to_dict()
        encoded = json.dumps(payload)
        self.assertEqual(
            set(payload),
            {
                "schema_version", "overall_status", "starter_kit_version", "python_version",
                "host", "provider", "findings",
            },
        )
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["provider"]["id"], "ubuntu")
        self.assertIn("apt-get", encoded)
        self.assertNotIn("pacman", encoded)
        self.assertNotIn("/synthetic", encoded)
        base = next(item for item in payload["findings"] if item["code"] == "base-tooling")
        self.assertEqual(
            set(base),
            {"code", "status", "title", "capability_id", "explanation", "remedy", "evidence"},
        )
        self.assertEqual(base["status"], "pass")
        self.assertEqual(base["capability_id"], "base.tooling")
        self.assertIn("generated workflows", base["explanation"])
        codex = next(item for item in payload["findings"] if item["code"] == "codex-cli")
        self.assertEqual(codex["status"], "action-needed")
        podman = next(item for item in payload["findings"] if item["code"] == "rootless-podman")
        self.assertEqual(podman["status"], "optional")
        self.assertEqual(report.exit_code, 0)

    def test_blocked_and_unverified_states_are_structured(self) -> None:
        unsupported = detect_platform(
            'ID=fedora\nPRETTY_NAME="Fedora"\n',
            architecture="x86_64",
            executable_lookup=self.lookup(),
        )
        report = build_doctor_report(
            kit_version="test",
            python_version="3.11.9",
            detection=unsupported,
            provider=None,
            executable_lookup=self.lookup("bash", "git", "curl"),
            codex=CodexDoctorState(installed=True, version="codex test", authorized=None),
        )
        self.assertEqual(unsupported.support, SupportLevel.UNSUPPORTED)
        self.assertEqual(report.overall_status, DoctorStatus.BLOCKED)
        self.assertEqual(report.exit_code, 2)
        self.assertTrue(any(item.status is DoctorStatus.UNVERIFIED for item in report.findings))
        rendered = render_doctor_text(report)
        self.assertIn("[BLOCKED]", rendered)
        self.assertIn("[UNVERIFIED]", rendered)

    def test_debian_package_query_failure_is_unverified_not_installed(self) -> None:
        detection = detect_platform(
            'ID=debian\nPRETTY_NAME="Debian GNU/Linux"\n',
            architecture="x86_64",
            executable_lookup=self.lookup("apt-get"),
        )
        provider = provider_for_detection(detection, runner=lambda argv: CommandResult(2, stderr="synthetic"))
        report = build_doctor_report(
            kit_version="test",
            python_version="3.11.9",
            detection=detection,
            provider=provider,
            executable_lookup=self.lookup("bash", "git", "curl", "podman"),
            codex=CodexDoctorState(installed=True, version="codex test", authorized=True),
        )
        base = next(item for item in report.findings if item.code == "base-tooling")
        self.assertEqual(base.status, DoctorStatus.UNVERIFIED)
        self.assertNotIn("pacman", render_doctor_text(report))

    def test_arch_uses_only_read_only_package_queries(self) -> None:
        calls: list[tuple[str, ...]] = []
        detection = detect_platform(
            'ID=cachyos\nID_LIKE=arch\nPRETTY_NAME="CachyOS"\n',
            architecture="x86_64",
            executable_lookup=self.lookup("pacman"),
        )
        provider = provider_for_detection(
            detection,
            runner=lambda argv: calls.append(argv) or CommandResult(0),
        )
        build_doctor_report(
            kit_version="test",
            python_version="3.11.9",
            detection=detection,
            provider=provider,
            executable_lookup=self.lookup("bash", "git", "curl"),
            codex=CodexDoctorState(installed=True, version="codex test", authorized=True),
        )
        self.assertTrue(calls)
        self.assertTrue(all(argv[:2] == ("pacman", "-Qq") for argv in calls))

    def test_missing_package_manager_skips_provider_query(self) -> None:
        calls: list[tuple[str, ...]] = []
        detection = detect_platform(
            'ID=debian\nPRETTY_NAME="Debian"\n',
            architecture="x86_64",
            executable_lookup=self.lookup(),
        )
        provider = provider_for_detection(
            detection,
            runner=lambda argv: calls.append(argv) or CommandResult(0),
        )
        report = build_doctor_report(
            kit_version="test",
            python_version="3.11.9",
            detection=detection,
            provider=provider,
            executable_lookup=self.lookup("bash", "git", "curl"),
            codex=CodexDoctorState(installed=True, version="codex test", authorized=True),
        )
        self.assertEqual(calls, [])
        base = next(item for item in report.findings if item.code == "base-tooling")
        self.assertEqual(base.status, DoctorStatus.UNVERIFIED)


if __name__ == "__main__":
    unittest.main()
