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

from .models import AdvisorRecommendation, ProjectConfig


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
    list_of_strings = {"type": "array", "items": {"type": "string"}}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "summary",
            "languages",
            "database",
            "architecture",
            "toolchain_packages",
            "setup_commands",
            "build_commands",
            "test_commands",
            "lint_commands",
            "rationale",
            "risks",
            "questions",
        ],
        "properties": {
            "summary": {"type": "string"},
            "languages": list_of_strings,
            "database": {"type": "string"},
            "architecture": {"type": "string"},
            "toolchain_packages": list_of_strings,
            "setup_commands": list_of_strings,
            "build_commands": list_of_strings,
            "test_commands": list_of_strings,
            "lint_commands": list_of_strings,
            "rationale": list_of_strings,
            "risks": list_of_strings,
            "questions": list_of_strings,
        },
    }


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
            return AdvisorRecommendation.from_dict(data, source="codex", raw_output=raw)

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
