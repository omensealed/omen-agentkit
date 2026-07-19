from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agent_starter.agents import parse_advisor_response
from agent_starter.doctor import CodexDoctorState, build_doctor_report, provider_for_detection
from agent_starter.models import ProjectConfig
from agent_starter.platforms import (
    CommandResult,
    HostProfile,
    PackageAvailability,
    PackageResolution,
    PackageState,
    PackageVerification,
    detect_platform,
)
from agent_starter.recommendation import build_recommendation_review
from agent_starter.recommendation_cache import RecommendationCache, recommendation_cache_key


class _CountingProvider:
    provider_id = "debian"
    package_manager_id = "apt-get"
    documentation_label = "Bounded test provider"
    shell_executable = "/bin/sh"

    def __init__(self) -> None:
        self.resolve_calls = 0
        self.verify_calls: list[tuple[str, ...]] = []
        self.installed_calls: list[tuple[str, ...]] = []

    def resolve_capabilities(self, requests: object) -> tuple[PackageResolution, ...]:
        self.resolve_calls += 1
        typed = tuple(requests)  # type: ignore[arg-type]
        return tuple(
            PackageResolution(item.capability_id, "shared-package")
            for item in typed
        )

    def verify_available(self, package_names: object) -> tuple[PackageVerification, ...]:
        names = tuple(package_names)  # type: ignore[arg-type]
        self.verify_calls.append(names)
        return tuple(PackageVerification(name, PackageAvailability.AVAILABLE) for name in names)

    def query_installed(self, package_names: object) -> tuple[PackageState, ...]:
        names = tuple(package_names)  # type: ignore[arg-type]
        self.installed_calls.append(names)
        return tuple(PackageState(name, False) for name in names)


class PerformanceResourceTests(unittest.TestCase):
    def test_representative_generation_stays_within_resource_budgets(self) -> None:
        from agent_starter.performance_checks import measure_representative_generation

        with tempfile.TemporaryDirectory() as temp:
            report = measure_representative_generation(Path(temp))
        self.assertEqual(report.schema_version, 1)
        self.assertEqual([item.profile for item in report.measurements], ["python-sqlite", "web-mariadb-renovation"])
        self.assertTrue(report.passed, report.to_dict())
        self.assertTrue(all(item.generated_files >= 45 for item in report.measurements))
        self.assertTrue(all(item.elapsed_seconds > 0 for item in report.measurements))
        self.assertTrue(all(item.peak_bytes > 0 for item in report.measurements))

    def test_gui_help_import_does_not_load_bridge_or_pywebview(self) -> None:
        source = """
import contextlib
import io
import json
import sys
import agent_starter.gui.app as app
before = sorted(name for name in sys.modules if name == 'webview' or name.startswith('agent_starter.gui.bridge'))
with contextlib.redirect_stdout(io.StringIO()):
    code = app.main(['--help'])
after = sorted(name for name in sys.modules if name == 'webview' or name.startswith('agent_starter.gui.bridge'))
print(json.dumps({'code': code, 'before': before, 'after': after}))
"""
        completed = subprocess.run(
            [sys.executable, "-c", source],
            cwd=Path(__file__).resolve().parents[1],
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload, {"code": 0, "before": [], "after": []})

    def test_valid_recommendation_cache_loads_without_codex_or_package_queries(self) -> None:
        profile = HostProfile(
            os_id="debian",
            os_id_like=(),
            pretty_name="Debian",
            version_id="12",
            architecture="x86_64",
            package_provider="debian",
        )
        config = ProjectConfig(project_name="Cached", project_type="cli", languages=["python"], database="sqlite")
        recommendation = parse_advisor_response({
            "summary": "Use a small Python CLI.",
            "languages": ["python"],
            "database": "sqlite",
            "recommended_capabilities": [],
            "architecture_notes": [],
            "questions": [],
            "risks": [],
        })
        with tempfile.TemporaryDirectory() as temp:
            cache = RecommendationCache(Path(temp))
            key = recommendation_cache_key(config, profile)
            cache.store(key, recommendation)
            with mock.patch("agent_starter.agents.subprocess.run") as codex_process:
                first = cache.load(key)
                second = cache.load(key)
            codex_process.assert_not_called()
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertEqual(first.recommendation, second.recommendation)  # type: ignore[union-attr]

    def test_recommendation_batches_and_deduplicates_package_metadata_queries(self) -> None:
        provider = _CountingProvider()
        profile = HostProfile(
            os_id="debian",
            os_id_like=(),
            pretty_name="Debian",
            version_id="12",
            architecture="x86_64",
            package_provider="debian",
        )
        review = build_recommendation_review(
            ProjectConfig(project_name="Bounded", languages=["python"], database="sqlite"),
            profile=profile,
            provider=provider,  # type: ignore[arg-type]
        )
        self.assertTrue(review.items)
        self.assertEqual(provider.resolve_calls, 1)
        self.assertEqual(provider.verify_calls, [("shared-package",)])
        self.assertEqual(provider.installed_calls, [("shared-package",)])

    def test_doctor_queries_only_the_fixed_base_tooling_set(self) -> None:
        lookups: list[str] = []
        calls: list[tuple[str, ...]] = []

        def lookup(name: str) -> str | None:
            lookups.append(name)
            return f"/synthetic/{name}" if name in {"apt-get", "bash", "git", "curl"} else None

        detection = detect_platform(
            'ID=debian\nPRETTY_NAME="Debian"\n',
            architecture="x86_64",
            executable_lookup=lookup,
        )
        lookups.clear()
        provider = provider_for_detection(
            detection,
            runner=lambda argv: calls.append(argv) or CommandResult(0, "install ok installed"),
        )
        build_doctor_report(
            kit_version="test",
            python_version="3.11",
            detection=detection,
            provider=provider,
            executable_lookup=lookup,
            codex=CodexDoctorState(True, "codex test", True),
        )
        self.assertEqual(lookups, ["bash", "git", "curl", "podman"])
        self.assertEqual(len(calls), 7)
        self.assertTrue(all(argv[:3] == ("dpkg-query", "-W", "-f=${Status}") for argv in calls))
        self.assertEqual(
            {argv[-1] for argv in calls},
            {"git", "curl", "jq", "ripgrep", "fd-find", "unzip", "build-essential"},
        )
        self.assertFalse(any(argv[:2] in {("dpkg", "-l"), ("apt", "list")} for argv in calls))


if __name__ == "__main__":
    unittest.main()
