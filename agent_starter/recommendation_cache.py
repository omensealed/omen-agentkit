"""Safe structured recommendation cache with non-identifying keys."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
import secrets

from .agents import AgentError, parse_advisor_response
from .models import AdvisorRecommendation, ProjectConfig
from .platforms import HostProfile


CACHE_SCHEMA_VERSION = 1
CACHE_FILE_LIMIT = 256_000
CACHE_KEY_RE = re.compile(r"^[0-9a-f]{64}$")


class RecommendationCacheError(ValueError):
    """Raised when cache data or its filesystem boundary is unsafe."""


@dataclass(frozen=True, slots=True)
class CachedRecommendation:
    key: str
    created_at: str
    recommendation: AdvisorRecommendation


def _canonical_intent(config: ProjectConfig) -> dict[str, object]:
    """Return project intent only; no path, timestamps, commands, or advisor data."""

    return {
        "project_type": config.project_type,
        "description": config.description,
        "goals": list(config.goals),
        "non_goals": list(config.non_goals),
        "target_users": config.target_users,
        "target_platforms": list(config.target_platforms),
        "packaging_targets": list(config.packaging_targets),
        "network_access": config.network_access,
        "user_accounts": config.user_accounts,
        "handles_personal_data": config.handles_personal_data,
        "handles_payments": config.handles_payments,
        "security_notes": config.security_notes,
        "stack_strategy": config.stack_strategy,
        "languages": list(config.languages),
        "database": config.database,
        "sandbox": {
            "enabled": config.sandbox.enabled,
            "mode": config.sandbox.mode,
            "image_profile": config.sandbox.image_profile,
        },
        "github_actions": config.github_actions,
    }


def _host_fingerprint(profile: HostProfile) -> dict[str, object]:
    """Return only non-identifying invalidation fields from HostProfile."""

    return {
        "os_id": profile.os_id,
        "os_id_like": list(profile.os_id_like),
        "version_id": profile.version_id,
        "architecture": profile.architecture,
        "package_provider": profile.package_provider,
    }


def recommendation_cache_key(config: ProjectConfig, profile: HostProfile) -> str:
    canonical = json.dumps(
        {"intent": _canonical_intent(config), "host": _host_fingerprint(profile)},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _structured_payload(recommendation: AdvisorRecommendation) -> dict[str, object]:
    return {
        "summary": recommendation.summary,
        "languages": list(recommendation.languages),
        "database": recommendation.database,
        "recommended_capabilities": [
            {
                "capability_id": item.capability_id,
                "purpose": item.purpose,
                "requirement": item.requirement,
                "rationale": item.rationale,
                "confidence": item.confidence,
            }
            for item in recommendation.recommended_capabilities
        ],
        "architecture_notes": list(recommendation.architecture_notes),
        "questions": list(recommendation.questions),
        "risks": list(recommendation.risks),
    }


def default_recommendation_cache_root() -> Path:
    base = os.environ.get("XDG_CACHE_HOME")
    cache_home = Path(base).expanduser() if base else Path.home() / ".cache"
    return cache_home / "omen-agentkit" / "recommendations"


def get_recommendation_cache() -> "RecommendationCache":
    """Return the user-scoped recommendation cache.

    Keeping construction behind this function gives the interactive workflow one
    narrow boundary that tests can replace without touching the real user cache.
    """

    return RecommendationCache()


class RecommendationCache:
    """Read/write strict cached advisor data without executing anything."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root if root is not None else default_recommendation_cache_root()

    def _path(self, key: str) -> Path:
        if not isinstance(key, str) or not CACHE_KEY_RE.fullmatch(key):
            raise RecommendationCacheError("Recommendation cache key is malformed.")
        return self.root / f"{key}.json"

    def load(self, key: str) -> CachedRecommendation | None:
        path = self._path(key)
        if not path.exists() and not path.is_symlink():
            return None
        if path.is_symlink() or not path.is_file():
            raise RecommendationCacheError("Recommendation cache entry must be a regular non-symlink file.")
        try:
            if path.stat().st_size > CACHE_FILE_LIMIT:
                raise RecommendationCacheError("Recommendation cache entry exceeds the safe size limit.")
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise RecommendationCacheError(f"Recommendation cache entry could not be read: {exc}") from exc
        if not isinstance(data, dict) or set(data) != {"schema_version", "key", "created_at", "recommendation"}:
            raise RecommendationCacheError("Recommendation cache entry has an unknown structure.")
        if data.get("schema_version") != CACHE_SCHEMA_VERSION or data.get("key") != key:
            raise RecommendationCacheError("Recommendation cache entry version or key does not match.")
        created_at = data.get("created_at")
        payload = data.get("recommendation")
        if not isinstance(created_at, str) or not created_at or len(created_at) > 80:
            raise RecommendationCacheError("Recommendation cache timestamp is malformed.")
        if not isinstance(payload, dict):
            raise RecommendationCacheError("Cached recommendation must be a structured object.")
        try:
            recommendation = parse_advisor_response(payload, source="codex-cache", raw_output="")
        except AgentError as exc:
            raise RecommendationCacheError(f"Cached recommendation failed strict validation: {exc}") from exc
        return CachedRecommendation(key, created_at, recommendation)

    def store(self, key: str, recommendation: AdvisorRecommendation) -> CachedRecommendation:
        path = self._path(key)
        if recommendation.review_mode not in {"ai-reviewed", "ai-reviewed-cache"}:
            raise RecommendationCacheError("Only strictly parsed AI-reviewed recommendations may be cached.")
        payload = _structured_payload(recommendation)
        try:
            validated = parse_advisor_response(payload, source="codex-cache", raw_output="")
        except AgentError as exc:
            raise RecommendationCacheError(f"Recommendation is not safe to cache: {exc}") from exc
        created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        document = {
            "schema_version": CACHE_SCHEMA_VERSION,
            "key": key,
            "created_at": created_at,
            "recommendation": payload,
        }
        encoded = (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")
        if len(encoded) > CACHE_FILE_LIMIT:
            raise RecommendationCacheError("Recommendation is too large for the safe cache limit.")
        try:
            self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
            if self.root.is_symlink() or not self.root.is_dir():
                raise RecommendationCacheError("Recommendation cache root must be a non-symlink directory.")
            os.chmod(self.root, 0o700)
            if path.is_symlink():
                raise RecommendationCacheError("Refusing to replace a symlinked recommendation cache entry.")
            temporary = self.root / f".{key}.{secrets.token_hex(8)}.tmp"
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            descriptor = os.open(temporary, flags, 0o600)
            try:
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(encoded)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, path)
                os.chmod(path, 0o600)
            finally:
                if temporary.exists():
                    temporary.unlink()
        except RecommendationCacheError:
            raise
        except OSError as exc:
            raise RecommendationCacheError(f"Recommendation cache could not be written: {exc}") from exc
        return CachedRecommendation(key, created_at, validated)
