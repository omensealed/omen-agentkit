"""Host-side sandbox preflight fingerprints, state, and orchestration."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from ..models import ProjectConfig
from .project_runtime import _run_project_command_logged, load_generated_config


SANDBOX_FINGERPRINT_INPUTS: tuple[str, ...] = (
    ".agent-starter/project.json",
    ".agent-starter/sandbox/Containerfile",
    ".agent-starter/sandbox/sandbox.json",
    "scripts/sandbox/doctor",
    "scripts/sandbox/preflight",
    "scripts/sandbox/build",
    "scripts/sandbox/check",
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sandbox_fingerprint(root: Path) -> tuple[str, dict[str, str]]:
    inputs: dict[str, str] = {}
    for relative in SANDBOX_FINGERPRINT_INPUTS:
        path = root / relative
        inputs[relative] = _sha256_file(path) if path.is_file() else "missing"
    combined = hashlib.sha256()
    for relative in SANDBOX_FINGERPRINT_INPUTS:
        combined.update(f"{inputs[relative]}  {relative}\n".encode("utf-8"))
    return combined.hexdigest(), inputs


def _podman_image_id(root: Path, image: str) -> str:
    if not image or shutil.which("podman") is None:
        return ""
    try:
        result = subprocess.run(
            ["podman", "image", "inspect", "--format", "{{.Id}}", image],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return (result.stdout or "").strip() if result.returncode == 0 else ""


def _write_sandbox_preflight_stamp(
    root: Path,
    config: ProjectConfig,
    *,
    status: str,
    run_check: bool,
    steps: Sequence[str],
    failed_step: str = "",
) -> Path:
    sandbox_dir = root / ".agent-starter" / "sandbox"
    sandbox_dir.mkdir(parents=True, exist_ok=True)
    sandbox_json_path = sandbox_dir / "sandbox.json"
    image = ""
    if sandbox_json_path.is_file():
        try:
            sandbox_data = json.loads(sandbox_json_path.read_text(encoding="utf-8"))
            image = str(sandbox_data.get("image") or "")
        except (OSError, json.JSONDecodeError):
            image = ""
    fingerprint, inputs = sandbox_fingerprint(root)
    stamp = sandbox_dir / "preflight.json"
    payload = {
        "schema_version": 1,
        "status": status,
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "project": config.project_slug or config.project_name,
        "mode": config.sandbox.mode,
        "engine": config.sandbox.engine,
        "image": image,
        "image_id": _podman_image_id(root, image),
        "run_check": run_check,
        "steps": list(steps),
        "failed_step": failed_step,
        "sandbox_fingerprint": fingerprint,
        "inputs": inputs,
        "note": "Host-side Agent Kit sandbox preflight completed before Codex launch. This file contains no credentials.",
    }
    temp = stamp.with_name(f".{stamp.name}.tmp")
    temp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(stamp)
    return stamp


def sandbox_preflight_state(root: Path) -> tuple[str, str, dict[str, Any]]:
    stamp_path = root / ".agent-starter" / "sandbox" / "preflight.json"
    if not stamp_path.is_file():
        return "missing", "preflight stamp is missing", {}
    try:
        stamp = json.loads(stamp_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return "failed", f"preflight stamp is unreadable: {exc}", {}
    if stamp.get("status") != "passed":
        failed = str(stamp.get("failed_step") or "last preflight did not pass")
        return "failed", failed, stamp
    current, inputs = sandbox_fingerprint(root)
    if stamp.get("sandbox_fingerprint") != current:
        old_inputs = stamp.get("inputs") if isinstance(stamp.get("inputs"), dict) else {}
        changed = [relative for relative, digest in inputs.items() if old_inputs.get(relative) != digest]
        reason = f"{changed[0]} changed after last preflight" if changed else "sandbox fingerprint changed"
        return "stale", reason, stamp
    return "valid", "preflight stamp is current", stamp


def sandbox_preflight(root: Path, *, run_check: bool = True) -> int:
    root = root.expanduser().resolve()
    try:
        config = load_generated_config(root)
    except ValueError as exc:
        print(f"[fail] {exc}")
        return 2
    if not config.sandbox.enabled or config.sandbox.mode in {"none", "files-only"}:
        print("Sandbox preflight skipped: this project does not have an active generated sandbox.")
        return 0

    required = [
        root / "scripts/sandbox/doctor",
        root / "scripts/sandbox/build",
    ]
    if run_check:
        required.append(root / "scripts/sandbox/check")
    missing = [path for path in required if not path.is_file()]
    if missing:
        for path in missing:
            print(f"[fail] Missing sandbox script: {path}")
        return 2

    print("Agent Kit sandbox preflight")
    print("Running host-side rootless Podman setup before Codex launch.")
    print("This does not run sudo, mount host Codex auth, mount SSH keys, or request Codex full permissions.")
    log_dir = root / ".agent-starter" / "logs"
    steps = [
        (root / "scripts/sandbox/doctor", "sandbox doctor", log_dir / "sandbox-preflight-doctor.log"),
        (root / "scripts/sandbox/build", "sandbox build", log_dir / "sandbox-build.log"),
    ]
    if run_check:
        steps.append((root / "scripts/sandbox/check", "sandbox check", log_dir / "sandbox-check.log"))
    for path, label, log_path in steps:
        code = _run_project_command_logged(root, [path], label=label, log_path=log_path)
        if code != 0:
            _write_sandbox_preflight_stamp(
                root,
                config,
                status="failed",
                run_check=run_check,
                steps=[step_label for _, step_label, _ in steps],
                failed_step=label,
            )
            print("Sandbox preflight failed. Fix the host rootless Podman environment before launching Codex,")
            print("or explicitly choose a non-sandbox workflow. Do not use Codex danger-full-access to make Podman work.")
            return code
    stamp = _write_sandbox_preflight_stamp(
        root,
        config,
        status="passed",
        run_check=run_check,
        steps=[label for _, label, _ in steps],
    )
    print("Sandbox preflight passed.")
    print(f"Wrote {stamp}")
    return 0
