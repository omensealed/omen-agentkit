"""Local workspace readiness, publication review, and mirror planning commands."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from ..agents import get_adapter
from ..generator import validate_project
from ..models import ProjectConfig
from .project_runtime import load_generated_config
from .sandbox_orchestration import _podman_image_id, sandbox_preflight_state


AI_LOCAL_IGNORE_PATTERNS: tuple[str, ...] = (
    "AGENTS.md",
    "FIRST_PROMPT.md",
    "FIRST_RUN_AUTONOMOUS.md",
    ".agents/",
    ".codex/",
    ".agent-starter/",
    "docs/09-PROGRESS.md",
    "docs/11-IMPLEMENTATION-NOTES.md",
    "docs/14-AGENT-HANDOFF.md",
    "docs/AI-STACK-RECOMMENDATION.md",
    "docs/agent-prompts/",
    ".codex/*.jsonl",
    ".codex/sessions/",
    ".agent-starter/proposals/",
    ".agent-starter/backups/",
    "NEXT_PROMPT.md",
    "LOCAL_MODEL_HANDOFF.md",
)


@dataclass(slots=True)
class GitReadiness:
    summary: str
    is_repo: bool
    dirty: bool
    has_origin: bool


def _git_status_summary(root: Path) -> tuple[str, bool]:
    readiness = _git_readiness(root)
    return readiness.summary, readiness.is_repo


def _git_readiness(root: Path) -> GitReadiness:
    if shutil.which("git") is None:
        return GitReadiness("git not installed", False, True, False)
    try:
        inside = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return GitReadiness(f"git unavailable: {exc}", False, True, False)
    if inside.returncode != 0:
        return GitReadiness("not a Git repository", False, True, False)
    try:
        branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
        origin = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return GitReadiness(f"git status unavailable: {exc}", True, True, False)
    name = (branch.stdout or "").strip() or "detached/unknown"
    dirty = bool((status.stdout or "").strip()) if status.returncode == 0 else True
    has_origin = origin.returncode == 0 and bool((origin.stdout or "").strip())
    suffix = "with uncommitted changes" if dirty else "clean"
    remote = "origin remote configured" if has_origin else "no origin remote"
    return GitReadiness(f"repository on {name}, {suffix}, {remote}", True, dirty, has_origin)


def _ignored_ai_artifacts_summary(root: Path) -> tuple[str, bool]:
    gitignore = root / ".gitignore"
    if not gitignore.is_file():
        return "missing .gitignore", False
    text = gitignore.read_text(encoding="utf-8", errors="replace")
    missing = [pattern for pattern in AI_LOCAL_IGNORE_PATTERNS if pattern not in text]
    if missing:
        return "missing AI-local ignore pattern(s): " + ", ".join(missing), False
    return "AI-local notes, prompts, sessions, skill metadata, and proposals are ignored", True


def _codex_status_summary() -> tuple[str, bool]:
    adapter = get_adapter()
    if not adapter.exists():
        return f"{adapter.display_name} is not installed", False
    version = adapter.version()
    status = adapter.auth_status()
    if status is True:
        return f"{version}; authorized account reported", True
    if status is False:
        return f"{version}; not authorized", False
    return f"{version}; authorization status unavailable", False


def _podman_rootless_summary(root: Path) -> tuple[str, bool | None]:
    if shutil.which("podman") is None:
        return "podman missing", None
    try:
        result = subprocess.run(
            ["podman", "info", "--format", "{{.Host.Security.Rootless}}"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"unknown: {exc}", None
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        return f"unknown: {detail}", None
    value = (result.stdout or "").strip().lower()
    if value == "true":
        return "yes", True
    if value == "false":
        return "no", False
    return "unknown", None


def _xdg_runtime_summary() -> tuple[str, bool | None]:
    value = os.environ.get("XDG_RUNTIME_DIR")
    if not value:
        return "unknown: XDG_RUNTIME_DIR is not set", None
    path = Path(value)
    if not path.exists():
        return f"no: {path} does not exist", False
    if not path.is_dir():
        return f"no: {path} is not a directory", False
    if not os.access(path, os.W_OK):
        return f"no: {path} is not writable", False
    return f"yes: {path}", True


def _sandbox_status_lines(root: Path, config: ProjectConfig) -> list[str]:
    if not config.sandbox.enabled or config.sandbox.mode in {"none", "files-only"}:
        return ["[info] Sandbox: inactive/not generated"]
    sandbox_json_path = root / ".agent-starter" / "sandbox" / "sandbox.json"
    image = ""
    if sandbox_json_path.is_file():
        try:
            sandbox_data = json.loads(sandbox_json_path.read_text(encoding="utf-8"))
            image = str(sandbox_data.get("image") or "")
        except (OSError, json.JSONDecodeError):
            image = ""
    state, reason, stamp = sandbox_preflight_state(root)
    image_exists = "unknown"
    image_id = ""
    if image and shutil.which("podman") is not None:
        try:
            exists = subprocess.run(["podman", "image", "exists", image], cwd=root, check=False, timeout=15)
            image_exists = "yes" if exists.returncode == 0 else "no"
        except (OSError, subprocess.TimeoutExpired):
            image_exists = "unknown"
        image_id = _podman_image_id(root, image)
    rootless, _ = _podman_rootless_summary(root)
    runtime, _ = _xdg_runtime_summary()
    created = str(stamp.get("created_at") or "never") if stamp else "never"
    lines = [
        f"[info] Sandbox mode: {config.sandbox.mode}",
        f"[info] Sandbox engine: {config.sandbox.engine}",
        f"[{'ok' if state == 'valid' else 'warn'}] Sandbox preflight: {state}",
        f"[info] Sandbox preflight reason: {reason}",
        f"[info] Last preflight: {created}",
        f"[info] Sandbox image: {image or 'unknown'}",
        f"[info] Sandbox image exists: {image_exists}",
    ]
    if image_id:
        lines.append(f"[info] Sandbox image id: {image_id}")
    lines.extend(
        [
            f"[info] Rootless Podman: {rootless}",
            f"[info] XDG_RUNTIME_DIR writable: {runtime}",
        ]
    )
    if state == "valid":
        lines.append("[info] Sandbox next step: use scripts/sandbox/check for project verification when Codex approval policy permits it.")
    else:
        lines.append("[info] Sandbox next step: run `agent-starter sandbox preflight .` from a normal host terminal.")
    return lines


def command_status(args: argparse.Namespace) -> int:
    root = Path(args.project).expanduser().resolve()
    print(f"Workspace status: {root}")
    try:
        config = load_generated_config(root)
    except ValueError as exc:
        print(f"[fail] Metadata: {exc}")
        print("Next action: generate or validate a starter workspace before launching Codex.")
        return 2
    print(f"[ok] Metadata: {config.project_name} ({config.project_mode}, {config.project_type})")
    print(f"[ok] Agent contract: {config.primary_agent}")
    validation = validate_project(root)
    if validation.ok:
        print(f"[ok] Generated files: {len(validation.checked)} required file(s) present")
    else:
        print("[fail] Generated files:")
        for error in validation.errors:
            print(f"  - {error}")
    for warning in validation.warnings:
        print(f"[warn] {warning}")
    codex_text, codex_ok = _codex_status_summary()
    print(f"[{'ok' if codex_ok else 'warn'}] Codex: {codex_text}")
    git_text, git_ok = _git_status_summary(root)
    print(f"[{'ok' if git_ok else 'warn'}] Git: {git_text}")
    github_workflow = root / ".github" / "workflows" / "ci.yml"
    print("[info] GitHub Actions: workflow present" if github_workflow.is_file() else "[info] GitHub Actions: deferred/not generated")
    ignore_text, ignore_ok = _ignored_ai_artifacts_summary(root)
    print(f"[{'ok' if ignore_ok else 'warn'}] AI-local artifacts: {ignore_text}")
    for line in _sandbox_status_lines(root, config):
        print(line)
    if not validation.ok:
        print("Next action: restore or merge missing generated files, then run `agent-starter validate`.")
        return 2
    if not codex_ok:
        print("Next action: run `./scripts/setup-agent.sh` or `agent-starter auth --status` before launching Codex.")
    elif not git_ok:
        print("Next action: run local checks, then initialize Git only if you want local history.")
    else:
        print("Next action: read `START_HERE.md`, then follow `NEXT_STEPS.md` and run `./scripts/check.sh`.")
    return 0


def _github_workflow_summary(root: Path) -> tuple[str, bool]:
    workflow = root / ".github" / "workflows" / "ci.yml"
    if not workflow.is_file():
        return "GitHub Actions deferred/not generated", True
    text = workflow.read_text(encoding="utf-8", errors="replace")
    if "./scripts/check.sh" not in text:
        return "workflow present but does not call ./scripts/check.sh", False
    return "workflow present and calls ./scripts/check.sh", True


def _run_local_check(root: Path, *, skip: bool) -> tuple[str, bool]:
    check = root / "scripts" / "check.sh"
    if skip:
        return "skipped by --skip-check", True
    if not check.is_file():
        return "missing scripts/check.sh", False
    try:
        result = subprocess.run([str(check)], cwd=root, text=True, capture_output=True, check=False, timeout=600)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"could not complete ./scripts/check.sh: {exc}", False
    if result.returncode == 0:
        return "./scripts/check.sh passed", True
    detail = (result.stderr or result.stdout).strip().splitlines()
    suffix = f": {detail[-1][:200]}" if detail else ""
    return f"./scripts/check.sh failed with exit {result.returncode}{suffix}", False


def command_github_ready(args: argparse.Namespace) -> int:
    root = Path(args.project).expanduser().resolve()
    print(f"GitHub readiness: {root}")
    try:
        config = load_generated_config(root)
    except ValueError as exc:
        print(f"[fail] Metadata: {exc}")
        print("Recommendation: do not create a GitHub repository yet.")
        return 2
    print(f"[ok] Metadata: {config.project_name}")
    validation = validate_project(root)
    if validation.ok:
        print(f"[ok] Generated files: {len(validation.checked)} required file(s) present")
    else:
        print("[fail] Generated files:")
        for error in validation.errors:
            print(f"  - {error}")
    check_text, check_ok = _run_local_check(root, skip=args.skip_check)
    print(f"[{'ok' if check_ok else 'fail'}] Local check: {check_text}")
    git = _git_readiness(root)
    print(f"[{'ok' if git.is_repo and not git.dirty else 'fail'}] Git: {git.summary}")
    ignore_text, ignore_ok = _ignored_ai_artifacts_summary(root)
    print(f"[{'ok' if ignore_ok else 'fail'}] AI-local artifacts: {ignore_text}")
    workflow_text, workflow_ok = _github_workflow_summary(root)
    print(f"[{'ok' if workflow_ok else 'warn'}] GitHub Actions: {workflow_text}")
    ready = validation.ok and check_ok and git.is_repo and not git.dirty and ignore_ok and workflow_ok
    if ready:
        if git.has_origin:
            print("Recommendation: local baseline is ready; review the origin remote before any manual push.")
        elif (root / ".github" / "workflows" / "ci.yml").is_file():
            print("Recommendation: local baseline and CI workflow are ready to review before creating a remote.")
        else:
            print("Recommendation: local baseline is ready for a GitHub remote if you want one; GitHub Actions remain optional.")
        return 0
    print("Recommendation: do not create a GitHub repository, enable CI, or push yet. Fix the failed items locally first.")
    return 2


def _looks_like_remote_rsync_target(value: str) -> bool:
    return ":" in value and not value.startswith("/") and not value.startswith("./") and not value.startswith("../")


def _validate_rsync_target(root: Path, target: str) -> None:
    if not target.strip():
        raise ValueError("rsync target is required.")
    if _looks_like_remote_rsync_target(target):
        return
    destination = Path(target).expanduser().resolve()
    try:
        destination.relative_to(root)
    except ValueError:
        return
    raise ValueError("Refusing to mirror into a path inside the project root.")


def _rsync_command(root: Path, target: str, *, delete: bool) -> list[str]:
    command = [
        "rsync",
        "-a",
        "--human-readable",
        "--itemize-changes",
        "--exclude-from",
        str(root / ".agent-starter" / "rsync-excludes"),
    ]
    if delete:
        command.append("--delete")
    command.extend([str(root) + "/", target])
    return command


def command_rsync_plan(args: argparse.Namespace) -> int:
    root = Path(args.project).expanduser().resolve()
    try:
        config = load_generated_config(root)
        _validate_rsync_target(root, args.target)
    except ValueError as exc:
        print(f"[fail] {exc}")
        return 2
    excludes = root / ".agent-starter" / "rsync-excludes"
    if not excludes.is_file():
        print(f"[fail] Missing exclude file: {excludes}")
        return 2
    command = _rsync_command(root, args.target, delete=args.delete)
    print(f"Rsync mirror plan: {config.project_name}")
    print(f"Source:  {root}/")
    print(f"Target:  {args.target}")
    print(f"Excludes: {excludes}")
    print("Command:")
    print("  " + shlex.join(command))
    print("")
    print("This mirrors source and durable docs while excluding local runtime artifacts, prompt drafts, credentials, caches, databases, starter proposals/backups, and .git history.")
    if args.delete:
        print("[warning] --delete will remove target files that are not present in the source mirror.")
    if not args.run:
        print("Plan only. Re-run with --run to execute after reviewing the command and target.")
        return 0
    if shutil.which("rsync") is None:
        print("[fail] rsync is not installed or not on PATH.")
        return 3
    result = subprocess.run(command, cwd=root, check=False)
    return result.returncode


def register_readiness_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    status = subparsers.add_parser("status", help="Summarize generated workspace readiness without changing anything.")
    status.add_argument("project", nargs="?", default=".")
    status.set_defaults(func=command_status)

    github_ready = subparsers.add_parser(
        "github-ready",
        help="Check local readiness before creating a GitHub remote, enabling CI, or pushing.",
    )
    github_ready.add_argument("project", nargs="?", default=".")
    github_ready.add_argument("--skip-check", action="store_true", help="Do not run ./scripts/check.sh.")
    github_ready.set_defaults(func=command_github_ready)

    rsync_plan = subparsers.add_parser("rsync-plan", help="Plan or explicitly run a local/SSH rsync source mirror.")
    rsync_plan.add_argument("project", help="Generated project to mirror.")
    rsync_plan.add_argument("target", help="Local path or rsync SSH target such as host:/path/project-copy.")
    rsync_plan.add_argument("--delete", action="store_true", help="Delete target files that are absent from the source mirror.")
    rsync_plan.add_argument("--run", action="store_true", help="Execute the reviewed rsync command.")
    rsync_plan.set_defaults(func=command_rsync_plan)
