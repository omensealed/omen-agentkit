"""OpenAI Codex CLI process boundary.

Authentication is intentionally delegated to the official Codex CLI. This
module never reads, copies, prints, or persists OAuth tokens.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from .capabilities import CAPABILITY_CATALOG

from .models import AdvisorCapability, AdvisorRecommendation, ProjectConfig
from .toolchains import TOOLCHAINS


ADVISOR_LANGUAGES = tuple(toolchain.key for toolchain in TOOLCHAINS)
ADVISOR_DATABASES = ("none", "sqlite", "mariadb", "postgresql", "existing", "undecided")
ADVISOR_REQUIREMENTS = ("required", "optional")
ADVISOR_CONFIDENCE = ("high", "medium", "low")

_ADVISOR_PROSE_POLICIES = (
    (
        "credential request",
        re.compile(
            r"(?is)\b(?:paste|reveal|share|upload|send|print|read)\b.{0,100}"
            r"\b(?:password|api[ _-]?key|oauth[ _-]?token|access[ _-]?token|cookie|private[ _-]?key|secret)\b"
        ),
    ),
    (
        "prompt-injection content",
        re.compile(
            r"(?is)\b(?:ignore|disregard|override)\b.{0,100}"
            r"\b(?:previous|prior|system|developer)\b.{0,60}\b(?:instruction|instructions|prompt)\b"
        ),
    ),
    (
        "download-pipe command content",
        re.compile(r"(?is)\b(?:curl|wget)\b[^\n]{0,500}\|\s*(?:sh|bash|zsh|python|python3)\b"),
    ),
    (
        "privileged or destructive command content",
        re.compile(
            r"(?is)(?:\bsudo\b|\brm\s+-[a-z]*[rf][a-z]*\s+|\bmkfs(?:\.[a-z0-9]+)?\b|"
            r"\bdd\s+if=|\b(?:shutdown|reboot|poweroff)\b)"
        ),
    ),
    (
        "shell command syntax",
        re.compile(r"(?s)(?:\$\(|`|&&|\|\||(?:^|\s)[<>|](?:\s|$)|;\s*(?:sh|bash|sudo|rm|curl|wget)\b)"),
    ),
)


class AgentError(RuntimeError):
    """Raised when an agent command cannot complete a requested operation."""


class AgentAdapter(ABC):
    key: str
    display_name: str
    command: str
    install_command: str
    account_description: str

    def exists(self) -> bool:
        return shutil.which(self.command) is not None

    def version(self) -> str:
        if not self.exists():
            return "not installed"
        try:
            result = subprocess.run(
                [self.command, "--version"],
                text=True,
                capture_output=True,
                check=False,
                timeout=15,
            )
        except (OSError, subprocess.TimeoutExpired):
            return "installed (version unavailable)"
        text = (result.stdout or result.stderr).strip()
        return text.splitlines()[0] if text else "installed"

    def install(self) -> bool:
        """Run the vendor-published installer after caller confirmation."""

        result = subprocess.run(["bash", "-lc", self.install_command], check=False)
        for directory in (Path.home() / ".local" / "bin", Path.home() / "bin"):
            value = str(directory)
            paths = os.environ.get("PATH", "").split(os.pathsep)
            if value not in paths:
                os.environ["PATH"] = value + os.pathsep + os.environ.get("PATH", "")
        return result.returncode == 0 and self.exists()

    @abstractmethod
    def auth_status(self) -> bool | None:
        """Return True, False, or None when the CLI has no reliable status API."""

    @abstractmethod
    def login(self, *, device_auth: bool = False) -> bool:
        """Launch the official interactive account login flow."""

    @abstractmethod
    def advise(self, config: ProjectConfig, prompt: str) -> AdvisorRecommendation:
        """Ask the agent for a read-only structured stack recommendation."""

    @abstractmethod
    def launch_interactive(self, root: Path, prompt: str) -> int:
        """Launch a continuing interactive session with an initial prompt."""

    @abstractmethod
    def launch_kickoff(self, root: Path, prompt: str) -> int:
        """Run a one-shot kickoff task and return the process exit code."""


def _run_capture(command: list[str], *, cwd: Path | None = None, timeout: int = 60, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.setdefault("NO_COLOR", "1")
    return subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
        env=env,
    )


def extract_json(text: str) -> dict[str, Any]:
    """Extract one JSON object from agent output without accepting Python syntax."""

    cleaned = text.strip()
    if not cleaned:
        raise AgentError("The agent returned no recommendation output.")

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL | re.IGNORECASE)
    candidates = [fenced.group(1)] if fenced else []
    candidates.append(cleaned)

    first = cleaned.find("{")
    last = cleaned.rfind("}")
    if first >= 0 and last > first:
        candidates.append(cleaned[first : last + 1])

    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise AgentError("The agent response did not contain a valid JSON object.")


def advisor_schema() -> dict[str, Any]:
    def string_list(*, item_limit: int, count_limit: int) -> dict[str, Any]:
        return {
            "type": "array",
            "maxItems": count_limit,
            "items": {"type": "string", "minLength": 1, "maxLength": item_limit},
        }

    capability = {
        "type": "object",
        "additionalProperties": False,
        "required": ["capability_id", "purpose", "requirement", "rationale", "confidence"],
        "properties": {
            "capability_id": {"type": "string", "enum": list(CAPABILITY_CATALOG)},
            "purpose": {"type": "string", "minLength": 1, "maxLength": 500},
            "requirement": {"type": "string", "enum": list(ADVISOR_REQUIREMENTS)},
            "rationale": {"type": "string", "minLength": 1, "maxLength": 2000},
            "confidence": {"type": "string", "enum": list(ADVISOR_CONFIDENCE)},
        },
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "summary",
            "languages",
            "database",
            "recommended_capabilities",
            "architecture_notes",
            "risks",
            "questions",
        ],
        "properties": {
            "summary": {"type": "string", "minLength": 1, "maxLength": 2000},
            "languages": {
                "type": "array",
                "maxItems": 10,
                "uniqueItems": True,
                "items": {"type": "string", "enum": list(ADVISOR_LANGUAGES)},
            },
            "database": {"type": "string", "enum": list(ADVISOR_DATABASES)},
            "recommended_capabilities": {"type": "array", "maxItems": 30, "items": capability},
            "architecture_notes": string_list(item_limit=2000, count_limit=20),
            "risks": string_list(item_limit=2000, count_limit=20),
            "questions": string_list(item_limit=2000, count_limit=20),
        },
    }


def parse_advisor_response(
    data: dict[str, Any],
    *,
    source: str = "codex",
    raw_output: str = "",
) -> AdvisorRecommendation:
    """Strictly validate untrusted capability-first advisor JSON."""

    if not isinstance(data, dict):
        raise AgentError("Advisor response must be one JSON object.")
    required = set(advisor_schema()["required"])
    actual = set(data)
    unexpected = sorted(actual - required)
    missing = sorted(required - actual)
    if unexpected:
        raise AgentError(f"Advisor response has unexpected fields: {', '.join(unexpected)}.")
    if missing:
        raise AgentError(f"Advisor response is missing required fields: {', '.join(missing)}.")

    def text(value: Any, path: str, *, limit: int, allow_empty: bool = False) -> str:
        if not isinstance(value, str):
            raise AgentError(f"Advisor field {path} must be text.")
        if "\x00" in value or any(ord(character) < 32 and character not in "\n\t" for character in value):
            raise AgentError(f"Advisor field {path} contains unsupported control content.")
        cleaned = value.strip()
        if not allow_empty and not cleaned:
            raise AgentError(f"Advisor field {path} must not be empty.")
        if len(cleaned) > limit:
            raise AgentError(f"Advisor field {path} exceeds {limit} characters.")
        for policy_name, pattern in _ADVISOR_PROSE_POLICIES:
            if pattern.search(cleaned):
                raise AgentError(
                    f"Advisor field {path} contains prohibited {policy_name}; "
                    "discard this response and use a reviewed retry or deterministic fallback."
                )
        return cleaned

    def text_list(value: Any, path: str, *, count: int, item_limit: int) -> list[str]:
        if not isinstance(value, list):
            raise AgentError(f"Advisor field {path} must be a JSON list.")
        if len(value) > count:
            raise AgentError(f"Advisor field {path} exceeds {count} items.")
        return [text(item, f"{path}[{index}]", limit=item_limit) for index, item in enumerate(value)]

    summary = text(data["summary"], "summary", limit=2000)
    languages = text_list(data["languages"], "languages", count=10, item_limit=80)
    if len(set(languages)) != len(languages):
        raise AgentError("Advisor field languages must not contain duplicates.")
    for index, language in enumerate(languages):
        if language not in ADVISOR_LANGUAGES:
            raise AgentError(f"Advisor field languages[{index}] is unsupported.")
    database = text(data["database"], "database", limit=80)
    if database not in ADVISOR_DATABASES:
        raise AgentError("Advisor field database is unsupported.")

    raw_capabilities = data["recommended_capabilities"]
    if not isinstance(raw_capabilities, list):
        raise AgentError("Advisor field recommended_capabilities must be a JSON list.")
    if len(raw_capabilities) > 30:
        raise AgentError("Advisor field recommended_capabilities exceeds 30 items.")
    recommended: list[AdvisorCapability] = []
    seen: set[str] = set()
    capability_fields = {"capability_id", "purpose", "requirement", "rationale", "confidence"}
    for index, item in enumerate(raw_capabilities):
        path = f"recommended_capabilities[{index}]"
        if not isinstance(item, dict):
            raise AgentError(f"Advisor field {path} must be an object.")
        extra = sorted(set(item) - capability_fields)
        absent = sorted(capability_fields - set(item))
        if extra:
            raise AgentError(f"Advisor field {path} has unexpected fields: {', '.join(extra)}.")
        if absent:
            raise AgentError(f"Advisor field {path} is missing fields: {', '.join(absent)}.")
        capability_id = text(item["capability_id"], f"{path}.capability_id", limit=80)
        if capability_id not in CAPABILITY_CATALOG:
            raise AgentError(f"Advisor field {path}.capability_id is unknown.")
        if capability_id in seen:
            raise AgentError(f"Advisor field {path}.capability_id is duplicated.")
        seen.add(capability_id)
        requirement = text(item["requirement"], f"{path}.requirement", limit=20)
        if requirement not in ADVISOR_REQUIREMENTS:
            raise AgentError(f"Advisor field {path}.requirement must be required or optional.")
        confidence = text(item["confidence"], f"{path}.confidence", limit=20)
        if confidence not in ADVISOR_CONFIDENCE:
            raise AgentError(f"Advisor field {path}.confidence must be high, medium, or low.")
        recommended.append(AdvisorCapability(
            capability_id,
            text(item["purpose"], f"{path}.purpose", limit=500),
            requirement,
            text(item["rationale"], f"{path}.rationale", limit=2000),
            confidence,
        ))

    architecture_notes = text_list(data["architecture_notes"], "architecture_notes", count=20, item_limit=2000)
    risks = text_list(data["risks"], "risks", count=20, item_limit=2000)
    questions = text_list(data["questions"], "questions", count=20, item_limit=2000)
    return AdvisorRecommendation(
        summary=summary,
        languages=languages,
        database=database,
        architecture="\n".join(architecture_notes),
        recommended_capabilities=recommended,
        architecture_notes=architecture_notes,
        toolchain_capabilities=[item.capability_id for item in recommended],
        rationale=[item.rationale for item in recommended],
        risks=risks,
        questions=questions,
        source=source,
        raw_output=raw_output[:100_000],
    )


class CodexAdapter(AgentAdapter):
    key = "codex"
    display_name = "OpenAI Codex CLI"
    command = "codex"
    install_command = "curl -fsSL https://chatgpt.com/codex/install.sh | sh"
    account_description = "ChatGPT account OAuth managed by the official Codex CLI"

    def auth_status(self) -> bool | None:
        if not self.exists():
            return False
        try:
            result = _run_capture([self.command, "login", "status"], timeout=20)
        except (OSError, subprocess.TimeoutExpired):
            return None
        return result.returncode == 0

    def login(self, *, device_auth: bool = False) -> bool:
        if not self.exists():
            return False
        command = [self.command, "login"]
        if device_auth:
            command.append("--device-auth")
        result = subprocess.run(command, check=False)
        status = self.auth_status()
        return result.returncode == 0 and status is not False

    def advise(self, config: ProjectConfig, prompt: str) -> AdvisorRecommendation:
        if not self.exists():
            raise AgentError("Codex is not installed.")
        with tempfile.TemporaryDirectory(prefix="agent-starter-advisor-") as tmp:
            root = Path(tmp)
            schema_path = root / "schema.json"
            output_path = root / "recommendation.json"
            schema_path.write_text(json.dumps(advisor_schema(), indent=2), encoding="utf-8")
            command = [
                self.command,
                "exec",
                "--sandbox",
                "read-only",
                "--skip-git-repo-check",
                "--color",
                "never",
                "--cd",
                str(root),
                "--output-schema",
                str(schema_path),
                "--output-last-message",
                str(output_path),
                "-",
            ]
            try:
                result = _run_capture(command, cwd=root, timeout=300, input_text=prompt)
            except subprocess.TimeoutExpired as exc:
                raise AgentError("Codex stack advice timed out.") from exc
            raw = output_path.read_text(encoding="utf-8") if output_path.exists() else result.stdout
            if result.returncode != 0:
                detail = (result.stderr or result.stdout).strip()
                raise AgentError(f"Codex stack advice failed: {detail[:500]}")
            data = extract_json(raw)
            return parse_advisor_response(data, source="codex", raw_output=raw)

    def launch_interactive(self, root: Path, prompt: str) -> int:
        command = [self.command, "--cd", str(root), prompt]
        return subprocess.run(command, cwd=root, check=False).returncode

    def launch_kickoff(self, root: Path, prompt: str) -> int:
        command = [
            self.command,
            "exec",
            "--cd",
            str(root),
            "--sandbox",
            "workspace-write",
            prompt,
        ]
        return subprocess.run(command, cwd=root, check=False).returncode


ADAPTERS: dict[str, AgentAdapter] = {
    "codex": CodexAdapter(),
}


def get_adapter(name: str = "codex") -> AgentAdapter:
    """Return the Codex adapter, accepting only explicit Codex aliases."""

    normalized = name.strip().lower()
    aliases = {
        "openai": "codex",
        "openai-codex": "codex",
    }
    normalized = aliases.get(normalized, normalized)
    try:
        return ADAPTERS[normalized]
    except KeyError as exc:
        raise AgentError(f"Unsupported agent: {name}. This starter kit supports OpenAI Codex CLI only.") from exc
