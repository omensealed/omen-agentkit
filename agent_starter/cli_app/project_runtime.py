"""Shared generated-project metadata and command runtime boundaries."""

from __future__ import annotations

import json
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Sequence

from ..models import ProjectConfig


def _run_project_command(root: Path, command: Sequence[str], *, label: str, timeout: int = 1200) -> int:
    print(f"== {label} ==")
    print("  " + shlex.join(str(part) for part in command))
    try:
        result = subprocess.run(
            [str(part) for part in command],
            cwd=root,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"[fail] {label}: {exc}")
        return 2
    if result.returncode != 0:
        print(f"[fail] {label} exited with {result.returncode}")
    return result.returncode


def _run_project_command_logged(root: Path, command: Sequence[str], *, label: str, log_path: Path, timeout: int = 1200) -> int:
    print(f"== {label} ==")
    print("  " + shlex.join(str(part) for part in command))
    log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            [str(part) for part in command],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        message = f"[fail] {label}: {exc}\n"
        log_path.write_text(message, encoding="utf-8")
        print(message.rstrip())
        return 2
    output = (result.stdout or "") + (result.stderr or "")
    log_path.write_text(output, encoding="utf-8")
    if output:
        sys.stdout.write(output)
    if result.returncode != 0:
        print(f"[fail] {label} exited with {result.returncode}; see {log_path}")
    else:
        print(f"[ok] {label}; log: {log_path}")
    return result.returncode


def load_generated_config(root: Path) -> ProjectConfig:
    root = root.expanduser().resolve()
    config_path = root / ".agent-starter/project.json"
    if not config_path.is_file():
        raise ValueError(f"No generated project metadata found at {config_path}")
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        config = ProjectConfig.from_dict(data)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise ValueError(f"Could not load project metadata: {exc}") from exc
    if config.primary_agent != "codex":
        raise ValueError("This workspace metadata was not created for the Codex-only starter kit.")
    return config
