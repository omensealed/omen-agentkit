"""Deterministic maintainer performance/resource checks.

The checks generate only temporary representative workspaces. They do not
contact Codex, inspect package metadata, install software, or access a network.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from time import perf_counter
import tempfile
import tracemalloc

from .generator import generate_project
from .models import ProjectConfig, SandboxConfig


GENERATION_TIME_BUDGET_SECONDS = 10.0
GENERATION_PEAK_MEMORY_BUDGET_BYTES = 128 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class GenerationMeasurement:
    profile: str
    elapsed_seconds: float
    peak_bytes: int
    generated_files: int
    generation_ok: bool
    within_time_budget: bool
    within_memory_budget: bool

    @property
    def passed(self) -> bool:
        return self.generation_ok and self.within_time_budget and self.within_memory_budget

    def to_dict(self) -> dict[str, object]:
        return {
            "profile": self.profile,
            "elapsed_seconds": self.elapsed_seconds,
            "peak_bytes": self.peak_bytes,
            "generated_files": self.generated_files,
            "generation_ok": self.generation_ok,
            "within_time_budget": self.within_time_budget,
            "within_memory_budget": self.within_memory_budget,
            "passed": self.passed,
        }


@dataclass(frozen=True, slots=True)
class PerformanceResourceReport:
    schema_version: int
    time_budget_seconds: float
    peak_memory_budget_bytes: int
    measurements: tuple[GenerationMeasurement, ...]

    @property
    def passed(self) -> bool:
        return bool(self.measurements) and all(item.passed for item in self.measurements)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "budgets": {
                "generation_time_seconds_per_profile": self.time_budget_seconds,
                "generation_peak_bytes_per_profile": self.peak_memory_budget_bytes,
            },
            "measurements": [item.to_dict() for item in self.measurements],
            "passed": self.passed,
        }


def _measure(profile: str, config: ProjectConfig) -> GenerationMeasurement:
    already_tracing = tracemalloc.is_tracing()
    if already_tracing:
        baseline_current, _ = tracemalloc.get_traced_memory()
        tracemalloc.reset_peak()
    else:
        baseline_current = 0
        tracemalloc.start()
    started = perf_counter()
    try:
        report = generate_project(config)
        elapsed = perf_counter() - started
        _, peak = tracemalloc.get_traced_memory()
    finally:
        if not already_tracing:
            tracemalloc.stop()
    peak_delta = max(peak - baseline_current, 1)
    generated_files = len(report.created) + len(report.unchanged) + len(report.conflicts) + len(report.overwritten)
    return GenerationMeasurement(
        profile=profile,
        elapsed_seconds=round(elapsed, 6),
        peak_bytes=peak_delta,
        generated_files=generated_files,
        generation_ok=report.ok,
        within_time_budget=elapsed <= GENERATION_TIME_BUDGET_SECONDS,
        within_memory_budget=peak_delta <= GENERATION_PEAK_MEMORY_BUDGET_BYTES,
    )


def measure_representative_generation(base_root: Path) -> PerformanceResourceReport:
    """Measure fresh and renovation profiles under a caller-owned temporary root."""

    base = base_root.expanduser().resolve()
    base.mkdir(parents=True, exist_ok=True)
    fresh_root = base / "python-sqlite"
    renovation_root = base / "web-mariadb-renovation"
    renovation_root.mkdir()
    (renovation_root / "README.md").write_text("# Owner-maintained renovation\n", encoding="utf-8")

    profiles = (
        (
            "python-sqlite",
            ProjectConfig(
                project_name="Performance Python SQLite",
                project_slug="performance-python-sqlite",
                project_path=str(fresh_root),
                project_type="cli",
                languages=["python"],
                database="sqlite",
                git_enabled=False,
            ),
        ),
        (
            "web-mariadb-renovation",
            ProjectConfig(
                project_name="Performance Web Renovation",
                project_slug="performance-web-renovation",
                project_path=str(renovation_root),
                project_mode="existing",
                project_type="web",
                languages=["php", "javascript"],
                database="mariadb",
                github_actions=True,
                git_enabled=False,
                sandbox=SandboxConfig(enabled=True, mode="toolchain"),
            ),
        ),
    )
    measurements = tuple(_measure(profile, config) for profile, config in profiles)
    return PerformanceResourceReport(
        schema_version=1,
        time_budget_seconds=GENERATION_TIME_BUDGET_SECONDS,
        peak_memory_budget_bytes=GENERATION_PEAK_MEMORY_BUDGET_BYTES,
        measurements=measurements,
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="agentkit-performance-") as temp:
        report = measure_representative_generation(Path(temp))
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
