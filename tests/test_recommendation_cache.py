from __future__ import annotations

import json
import stat
import tempfile
import unittest
from pathlib import Path

from agent_starter.models import AdvisorCapability, AdvisorRecommendation, ProjectConfig
from agent_starter.platforms import HostProfile
from agent_starter.recommendation_cache import (
    RecommendationCache,
    RecommendationCacheError,
    recommendation_cache_key,
)


class RecommendationCacheTests(unittest.TestCase):
    def config(self) -> ProjectConfig:
        return ProjectConfig(
            project_name="Cache Project",
            project_type="cli",
            description="Build a local task CLI.",
            goals=["Reliable local workflow"],
            target_platforms=["linux"],
            languages=["python"],
            database="sqlite",
            stack_strategy="ai",
        )

    def profile(self, *, version: str = "12", provider: str = "debian") -> HostProfile:
        return HostProfile(
            os_id="debian" if provider == "debian" else "ubuntu",
            os_id_like=(),
            pretty_name="Synthetic Linux",
            version_id=version,
            architecture="x86_64",
            package_provider=provider,
        )

    def recommendation(self) -> AdvisorRecommendation:
        return AdvisorRecommendation(
            summary="Use a small Python CLI.",
            languages=["python"],
            database="sqlite",
            recommended_capabilities=[AdvisorCapability(
                "language.python", "Run Python.", "required", "Matches the CLI.", "high"
            )],
            architecture_notes=["Keep one small package."],
            questions=["Is a single-user workflow sufficient?"],
            risks=["Packaging target is not finalized."],
            source="codex",
            raw_output='{"terminal":"noise"}',
        )

    def test_round_trip_stores_only_strict_structured_recommendation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            cache = RecommendationCache(Path(temp))
            key = recommendation_cache_key(self.config(), self.profile())
            cache.store(key, self.recommendation())
            record = cache.load(key)
            self.assertIsNotNone(record)
            assert record is not None
            self.assertEqual(record.recommendation.summary, "Use a small Python CLI.")
            self.assertEqual(record.recommendation.source, "codex-cache")
            self.assertEqual(record.recommendation.raw_output, "")
            self.assertEqual(record.recommendation.review_label, "Cached AI-reviewed structured recommendation")

            raw = next(Path(temp).glob("*.json")).read_text(encoding="utf-8")
            self.assertNotIn("terminal", raw)
            self.assertNotIn("pretty_name", raw)
            self.assertNotIn("Synthetic Linux", raw)
            self.assertNotIn("description", raw)
            self.assertNotIn("Build a local task CLI", raw)
            self.assertEqual(stat.S_IMODE(Path(temp).stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(next(Path(temp).glob("*.json")).stat().st_mode), 0o600)

    def test_key_invalidates_on_os_provider_or_project_stack_change(self) -> None:
        config = self.config()
        original = recommendation_cache_key(config, self.profile())
        self.assertNotEqual(original, recommendation_cache_key(config, self.profile(version="13")))
        self.assertNotEqual(original, recommendation_cache_key(config, self.profile(provider="ubuntu")))
        changed_language = self.config()
        changed_language.languages = ["rust"]
        self.assertNotEqual(original, recommendation_cache_key(changed_language, self.profile()))
        changed_database = self.config()
        changed_database.database = "postgresql"
        self.assertNotEqual(original, recommendation_cache_key(changed_database, self.profile()))

    def test_malformed_or_command_bearing_cache_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            cache = RecommendationCache(Path(temp))
            key = recommendation_cache_key(self.config(), self.profile())
            path = Path(temp) / f"{key}.json"
            path.write_text(json.dumps({
                "schema_version": 1,
                "key": key,
                "created_at": "2026-07-14T00:00:00+00:00",
                "recommendation": {
                    "summary": "Unsafe cached data",
                    "languages": ["python"],
                    "database": "sqlite",
                    "recommended_capabilities": [],
                    "architecture_notes": [],
                    "questions": [],
                    "risks": [],
                    "setup_commands": ["sudo anything"],
                },
            }), encoding="utf-8")
            with self.assertRaises(RecommendationCacheError):
                cache.load(key)

    def test_symlinked_cache_entry_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "target.json"
            target.write_text("{}", encoding="utf-8")
            key = recommendation_cache_key(self.config(), self.profile())
            (root / f"{key}.json").symlink_to(target)
            with self.assertRaises(RecommendationCacheError):
                RecommendationCache(root).load(key)


if __name__ == "__main__":
    unittest.main()
