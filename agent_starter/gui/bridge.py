"""pywebview JavaScript bridge for the optional Agent Kit GUI."""

from __future__ import annotations

import hashlib
import json
import webbrowser
from pathlib import Path
import re
import tomllib
from typing import Any

from ..agents import get_adapter
from ..diagnostics import (
    DiagnosticLog,
    PathConfinementError,
    diagnostic_from_exception,
    diagnostic_from_status,
    safe_display_text,
)
from ..draft_sessions import DraftSessionError, get_draft_store
from ..generator import generate_project, validate_project
from ..model_policy import CodexModelPolicy, DEFAULT_CODEX_WORKSPACE_POLICY
from ..ui_schema import GUI_PAGES, config_from_gui_payload
from ..task_composer import (
    TASK_DEFINITIONS,
    TaskPacket,
    TaskValidationError,
    approve_task_contract,
    build_task_contract,
    compose_task_packet,
    render_task_contract,
    task_composer_schema,
)


GUI_TEXT_FILE_LIMIT = 1_000_000
_PREVIEW_ID_RE = re.compile(r"^[0-9a-f]{64}$")


class LaunchPolicyError(ValueError):
    """Raised when generated Codex settings no longer match reviewed project policy."""


def _report_dict(report: object) -> dict[str, Any]:
    return {
        "ok": bool(getattr(report, "ok", False)),
        "root": str(getattr(report, "root", "")),
        "created": list(getattr(report, "created", [])),
        "unchanged": list(getattr(report, "unchanged", [])),
        "overwritten": list(getattr(report, "overwritten", [])),
        "conflicts": list(getattr(report, "conflicts", [])),
        "proposals": list(getattr(report, "proposals", [])),
        "backups": list(getattr(report, "backups", [])),
        "warnings": list(getattr(report, "warnings", [])),
        "validation_errors": list(getattr(report, "validation_errors", [])),
        "validation_warnings": list(getattr(report, "validation_warnings", [])),
    }


def _task_packet_from_payload(payload: dict[str, Any]) -> TaskPacket:
    if not isinstance(payload, dict):
        raise TaskValidationError("Task composer payload must be an object.")
    return compose_task_packet(payload.get("kind", ""), payload.get("answers", {}))


def _read_launch_workspace_policy(root: Path, model_policy: CodexModelPolicy) -> dict[str, object]:
    lexical_path = root / ".codex" / "config.toml"
    if lexical_path.is_symlink() or lexical_path.parent.is_symlink():
        raise LaunchPolicyError("The project Codex configuration must not use a symlink.")
    config_path = lexical_path.resolve()
    try:
        config_path.relative_to(root)
    except ValueError as exc:
        raise PathConfinementError("Project Codex configuration leaves the project root.") from exc
    if not config_path.is_file() or config_path.is_symlink():
        raise LaunchPolicyError("The project Codex configuration is missing or symlinked.")
    if config_path.stat().st_size > GUI_TEXT_FILE_LIMIT:
        raise LaunchPolicyError("The project Codex configuration exceeds the review limit.")
    try:
        parsed = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise LaunchPolicyError("The project Codex configuration is not valid readable TOML.") from exc

    expected = DEFAULT_CODEX_WORKSPACE_POLICY
    workspace = parsed.get("sandbox_workspace_write")
    mismatches: list[str] = []
    if parsed.get("approval_policy") != expected.approval_policy:
        mismatches.append("approval_policy")
    if parsed.get("sandbox_mode") != expected.sandbox_mode:
        mismatches.append("sandbox_mode")
    if parsed.get("web_search") != expected.web_search:
        mismatches.append("web_search")
    if not isinstance(workspace, dict) or workspace.get("network_access") is not expected.command_network_access:
        mismatches.append("sandbox_workspace_write.network_access")

    selection = getattr(model_policy, "selection", "")
    if selection == "explicit":
        if parsed.get("model") != getattr(model_policy, "model_id", None):
            mismatches.append("model")
        if parsed.get("model_reasoning_effort") != getattr(model_policy, "reasoning_effort", None):
            mismatches.append("model_reasoning_effort")
    elif "model" in parsed or "model_reasoning_effort" in parsed:
        mismatches.append("inherited_model_settings")
    if mismatches:
        raise LaunchPolicyError(
            "The project Codex configuration differs from its reviewed project policy: "
            + ", ".join(mismatches)
            + "."
        )
    return expected.to_dict()


def _launch_preview_fingerprint(preview: dict[str, object]) -> str:
    encoded = json.dumps(preview, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class GuiBridge:
    """Small API exposed to local GUI JavaScript."""

    def __init__(self, *, diagnostic_logger: DiagnosticLog | None = None) -> None:
        self._diagnostic_logger = diagnostic_logger
        self._launch_preview_state: tuple[Path, str] | None = None

    def _failure(
        self,
        error: BaseException,
        *,
        operation: str,
        project_changed: bool = False,
    ) -> dict[str, Any]:
        diagnostic = diagnostic_from_exception(
            error,
            operation=operation,
            project_changed=project_changed,
        )
        if self._diagnostic_logger is not None:
            self._diagnostic_logger.write(diagnostic)
        return {"ok": False, "error": diagnostic.explanation, "diagnostic": diagnostic.to_dict()}

    def _status_failure(
        self,
        *,
        code: str,
        title: str,
        explanation: str,
        project_changed: bool,
        safe_next_action: str,
        operation: str,
        technical_details: str = "status=failed",
    ) -> dict[str, Any]:
        diagnostic = diagnostic_from_status(
            code=code,
            title=title,
            explanation=explanation,
            project_changed=project_changed,
            safe_next_action=safe_next_action,
            operation=operation,
            technical_details=technical_details,
        )
        if self._diagnostic_logger is not None:
            self._diagnostic_logger.write(diagnostic)
        return {"ok": False, "error": diagnostic.explanation, "diagnostic": diagnostic.to_dict()}

    def pages(self) -> list[dict[str, object]]:
        return GUI_PAGES

    def task_composer_schema(self) -> list[dict[str, object]]:
        return task_composer_schema()

    def save_draft(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            if not isinstance(payload, dict) or not set(payload).issubset({"draft_id", "project", "task"}):
                raise DraftSessionError("Draft save request has an unknown structure.")
            if "project" not in payload:
                raise DraftSessionError("Draft save request requires project form data.")
            draft_id = payload.get("draft_id")
            if draft_id is not None and not isinstance(draft_id, str):
                raise DraftSessionError("Draft identifier must be text.")
            session = get_draft_store().save(
                project=payload["project"],
                task=payload.get("task"),
                draft_id=draft_id,
            )
        except Exception as exc:
            return self._failure(exc, operation="save_draft")
        return {"ok": True, "draft": session.to_dict()}

    def list_drafts(self) -> dict[str, Any]:
        try:
            summaries = get_draft_store().list_summaries()
        except Exception as exc:
            return self._failure(exc, operation="list_drafts")
        return {"ok": True, "drafts": [summary.to_dict() for summary in summaries]}

    def load_draft(self, draft_id: str) -> dict[str, Any]:
        try:
            session = get_draft_store().load(draft_id)
            if session is None:
                raise DraftSessionError("Draft session was not found.")
        except Exception as exc:
            return self._failure(exc, operation="load_draft")
        return {"ok": True, "draft": session.to_dict()}

    def discard_draft(self, draft_id: str) -> dict[str, Any]:
        try:
            discarded = get_draft_store().discard(draft_id)
        except Exception as exc:
            return self._failure(exc, operation="discard_draft")
        return {"ok": True, "discarded": discarded, "draft_id": draft_id}

    def export_draft(self, draft_id: str, destination: str) -> dict[str, Any]:
        try:
            if not isinstance(destination, str) or not destination.strip():
                raise DraftSessionError("Choose a new export file path.")
            path = get_draft_store().export(draft_id, Path(destination))
        except Exception as exc:
            return self._failure(exc, operation="export_draft")
        return {"ok": True, "draft_id": draft_id, "path": str(path)}

    def compose_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            packet = _task_packet_from_payload(payload)
            definition = TASK_DEFINITIONS[packet.kind]
            contract = build_task_contract(packet)
        except Exception as exc:
            return self._failure(exc, operation="compose_task")
        return {
            "ok": True,
            "state": contract.state,
            "packet": packet.to_dict(),
            "contract": contract.to_dict(),
            "contract_text": render_task_contract(contract),
            "phase": f"{packet.kind.value} continuation",
            "template": definition.prompt_template,
        }

    def approve_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            packet = _task_packet_from_payload(payload)
            approved = approve_task_contract(build_task_contract(packet))
            definition = TASK_DEFINITIONS[packet.kind]
        except Exception as exc:
            return self._failure(exc, operation="approve_task")
        return {
            "ok": True,
            "state": approved.state,
            "contract": approved.contract.to_dict(),
            "request": approved.prompt,
            "phase": f"{packet.kind.value} continuation",
            "template": definition.prompt_template,
        }

    def preview_config(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            config = config_from_gui_payload(payload)
            data = config.to_dict()
            data["advisor"]["raw_output"] = ""
        except Exception as exc:
            return self._failure(exc, operation="preview_config")
        return {"ok": True, "config": data}

    def generate(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            config = config_from_gui_payload(payload)
        except Exception as exc:
            return self._failure(exc, operation="generate_config")
        project_changed = False

        def mark_mutated() -> None:
            nonlocal project_changed
            project_changed = True

        try:
            report = generate_project(
                config,
                force=False,
                dry_run=False,
                _mutation_observer=mark_mutated,
            )
        except Exception as exc:
            return self._failure(
                exc,
                operation="generate_project",
                project_changed=project_changed,
            )
        result = _report_dict(report)
        result["start_here_path"] = str(config.root / "START_HERE.md")
        result["next_steps_path"] = str(config.root / "NEXT_STEPS.md")
        result["first_prompt_path"] = str(config.root / "FIRST_PROMPT.md")
        if not result["ok"]:
            result.update(self._status_failure(
                code="generation_validation_failed",
                title="The generated workspace needs review",
                explanation="Generation completed, but the workspace did not pass validation.",
                project_changed=project_changed,
                safe_next_action="Review the listed validation errors before generating or launching again.",
                operation="generate_project",
                technical_details=f"validation_error_count={len(result['validation_errors'])}",
            ))
        return result

    def validate(self, project_path: str) -> dict[str, Any]:
        try:
            if not isinstance(project_path, str) or not project_path.strip():
                raise ValueError("Choose a project folder to validate.")
            report = validate_project(Path(project_path))
        except Exception as exc:
            return self._failure(exc, operation="validate_project")
        result = {
            "ok": report.ok,
            "root": str(report.root),
            "errors": report.errors,
            "warnings": report.warnings,
            "checked": report.checked,
        }
        if not report.ok:
            result.update(self._status_failure(
                code="project_validation_failed",
                title="The project needs attention",
                explanation="The selected workspace did not pass the starter validation checks.",
                project_changed=False,
                safe_next_action="Review the listed errors and rerun validation before launch.",
                operation="validate_project",
                technical_details=f"validation_error_count={len(report.errors)}",
            ))
        return result

    def codex_status(self) -> dict[str, Any]:
        try:
            adapter = get_adapter()
            exists = adapter.exists()
            status = adapter.auth_status() if exists else False
            version = safe_display_text(adapter.version())
            install_command = safe_display_text(adapter.install_command)
        except Exception as exc:
            return self._failure(exc, operation="codex_status")
        result = {
            "ok": exists and status is not False,
            "installed": exists,
            "version": version,
            "authorized": status,
            "install_command": install_command,
        }
        if not exists:
            result.update(self._status_failure(
                code="codex_not_installed",
                title="Codex is not installed",
                explanation="The supported Codex CLI was not found on the current PATH.",
                project_changed=False,
                safe_next_action="Review the displayed installation command or continue without launching Codex.",
                operation="codex_status",
            ))
        elif status is False:
            result.update(self._status_failure(
                code="codex_not_authorized",
                title="Codex authorization is required",
                explanation="The official Codex CLI reports that authorization is not currently available.",
                project_changed=False,
                safe_next_action="Use the official Codex CLI authorization flow when you are ready; the GUI will not request credentials.",
                operation="codex_status",
            ))
        return result

    def read_text_file(self, project_path: str, relative_path: str) -> dict[str, Any]:
        try:
            if not isinstance(project_path, str) or not project_path.strip():
                raise ValueError("Choose a project folder first.")
            if not isinstance(relative_path, str) or not relative_path.strip():
                raise ValueError("Choose a project-relative text file.")
            root = Path(project_path).expanduser().resolve()
            if not root.is_dir():
                raise FileNotFoundError("Selected project folder does not exist.")
            relative = Path(relative_path)
            if relative.is_absolute():
                raise PathConfinementError("Requested path must be relative to the project.")
            target = (root / relative).resolve()
            try:
                target.relative_to(root)
            except ValueError as exc:
                raise PathConfinementError("Requested path leaves the project root.") from exc
            if not target.is_file():
                raise FileNotFoundError("Requested project file does not exist.")
            if target.stat().st_size > GUI_TEXT_FILE_LIMIT:
                raise ValueError("Requested project text file exceeds the safe display limit.")
            text = target.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            return self._failure(exc, operation="read_text_file")
        return {"ok": True, "path": str(target), "text": text}

    def open_project_folder(self, project_path: str) -> dict[str, Any]:
        try:
            if not isinstance(project_path, str) or not project_path.strip():
                raise ValueError("Choose a project folder first.")
            root = Path(project_path).expanduser().resolve()
            if not root.is_dir():
                raise FileNotFoundError("Project folder does not exist.")
            opened = webbrowser.open(root.as_uri())
            if opened is False:
                return self._status_failure(
                    code="folder_open_failed",
                    title="The project folder could not be opened",
                    explanation="The desktop did not accept the request to open the selected folder.",
                    project_changed=False,
                    safe_next_action="Open the selected project folder manually in your file manager.",
                    operation="open_project_folder",
                )
        except Exception as exc:
            return self._failure(exc, operation="open_project_folder")
        return {"ok": True, "path": str(root)}

    def close_window(self) -> dict[str, Any]:
        try:
            import webview  # type: ignore[import-not-found]
            for window in list(getattr(webview, "windows", [])):
                window.destroy()
        except Exception as exc:
            return self._failure(exc, operation="close_window")
        return {"ok": True}

    def _build_launch_preview(self, root: Path) -> dict[str, Any]:
        try:
            report = validate_project(root)
        except Exception as exc:
            return self._failure(exc, operation="launch_preview")
        if not report.ok:
            result = self._status_failure(
                code="launch_validation_failed",
                title="Launch is blocked by project validation",
                explanation="The selected workspace did not pass validation, so Codex was not launched.",
                project_changed=False,
                safe_next_action="Review the listed validation errors, correct them, and request a new launch preview.",
                operation="launch_preview",
                technical_details=f"validation_error_count={len(report.errors)}",
            )
            result.update({
                "errors": report.errors,
                "warnings": report.warnings,
                "checked": report.checked,
            })
            return result
        try:
            from ..cli import load_generated_config

            config = load_generated_config(root)
            workspace_policy = _read_launch_workspace_policy(root, config.model_policy)
        except LaunchPolicyError as exc:
            return self._status_failure(
                code="launch_policy_invalid",
                title="Launch policy review is required",
                explanation=str(exc),
                project_changed=False,
                safe_next_action="Regenerate or explicitly review the project model and Codex configuration before launching.",
                operation="launch_preview",
                technical_details="policy_match=false",
            )
        except Exception as exc:
            return self._failure(exc, operation="launch_preview")

        policy = config.model_policy
        explicit = policy.selection == "explicit"
        preview: dict[str, object] = {
            "target_project": str(root),
            "model_policy": {
                "provider": policy.provider,
                "selection": policy.selection,
                "exact_model_id": policy.model_id if explicit else None,
                "display_label": policy.display_label if explicit else "Inherited global Codex policy",
                "reasoning_effort": policy.reasoning_effort if explicit else None,
                "allow_task_routing": policy.allow_task_routing,
                "fallback_behavior": policy.fallback_behavior,
            },
            "sandbox": {
                "project_enabled": config.sandbox.enabled,
                "project_mode": config.sandbox.mode if config.sandbox.enabled else "none",
                "execution_location": "project-container" if config.sandbox.codex_inside_container else "host",
                "codex_mode": workspace_policy["sandbox_mode"],
                "approval_policy": workspace_policy["approval_policy"],
                "agent_policy": config.agent_sandbox,
            },
            "network": {
                "project_requires_network": config.network_access,
                "command_network_access": "on" if workspace_policy["command_network_access"] else "off",
                "web_search": workspace_policy["web_search"],
            },
        }
        return {
            "ok": True,
            "preview": preview,
            "warnings": report.warnings,
            "checked": report.checked,
        }

    def launch_preview(self, project_path: str) -> dict[str, Any]:
        self._launch_preview_state = None
        try:
            if not isinstance(project_path, str) or not project_path.strip():
                raise ValueError("Choose a project folder before reviewing launch.")
            root = Path(project_path).expanduser().resolve()
        except Exception as exc:
            return self._failure(exc, operation="launch_preview")
        result = self._build_launch_preview(root)
        if not result.get("ok", False):
            return result
        preview_id = _launch_preview_fingerprint(result["preview"])
        self._launch_preview_state = (root, preview_id)
        result["preview_id"] = preview_id
        return result

    def launch_codex(self, project_path: str, preview_id: str = "") -> dict[str, Any]:
        try:
            if not isinstance(project_path, str) or not project_path.strip():
                raise ValueError("Choose a project folder before launching Codex.")
            root = Path(project_path).expanduser().resolve()
            if (
                not isinstance(preview_id, str)
                or not _PREVIEW_ID_RE.fullmatch(preview_id)
                or self._launch_preview_state != (root, preview_id)
            ):
                self._launch_preview_state = None
                return self._status_failure(
                    code="launch_preview_required",
                    title="Review launch settings before continuing",
                    explanation="Codex launch requires a current successful preview from this GUI session.",
                    project_changed=False,
                    safe_next_action="Choose Review launch, inspect every displayed setting, then confirm launch explicitly.",
                    operation="launch_codex",
                )
            current = self._build_launch_preview(root)
            if not current.get("ok", False):
                self._launch_preview_state = None
                return current
            current_id = _launch_preview_fingerprint(current["preview"])
            if current_id != preview_id:
                self._launch_preview_state = None
                return self._status_failure(
                    code="launch_preview_stale",
                    title="Launch settings changed after review",
                    explanation="The project launch settings no longer match the preview that was shown.",
                    project_changed=False,
                    safe_next_action="Request a new launch preview and review the current settings before continuing.",
                    operation="launch_codex",
                )
            self._launch_preview_state = None
            from ..cli import launch_agent

            close_result = self.close_window()
            if not close_result.get("ok", False):
                return close_result
            code = launch_agent(root, kickoff=False)
        except Exception as exc:
            return self._failure(exc, operation="launch_codex")
        if code != 0:
            result = self._status_failure(
                code="codex_launch_failed",
                title="Codex exited without completing successfully",
                explanation="The Codex process returned an unsuccessful status.",
                project_changed=True,
                safe_next_action="Inspect the project for partial changes before explicitly retrying.",
                operation="launch_codex",
                technical_details=f"exit_status={code}",
            )
            result["code"] = code
            result["preview"] = current["preview"]
            return result
        return {"ok": True, "code": code, "preview": current["preview"]}
