"""pywebview JavaScript bridge for the optional Agent Kit GUI."""

from __future__ import annotations

import webbrowser
from pathlib import Path
from typing import Any

from ..agents import get_adapter
from ..generator import generate_project, validate_project
from ..ui_schema import GUI_PAGES, config_from_gui_payload


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


class GuiBridge:
    """Small API exposed to local GUI JavaScript."""

    def pages(self) -> list[dict[str, object]]:
        return GUI_PAGES

    def preview_config(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            config = config_from_gui_payload(payload)
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}
        data = config.to_dict()
        data["advisor"]["raw_output"] = ""
        return {"ok": True, "config": data}

    def generate(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            config = config_from_gui_payload(payload)
            report = generate_project(config, force=False, dry_run=False)
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}
        result = _report_dict(report)
        result["next_steps_path"] = str(config.root / "NEXT_STEPS.md")
        result["first_prompt_path"] = str(config.root / "FIRST_PROMPT.md")
        return result

    def validate(self, project_path: str) -> dict[str, Any]:
        report = validate_project(Path(project_path))
        return {
            "ok": report.ok,
            "root": str(report.root),
            "errors": report.errors,
            "warnings": report.warnings,
            "checked": report.checked,
        }

    def codex_status(self) -> dict[str, Any]:
        adapter = get_adapter()
        exists = adapter.exists()
        status = adapter.auth_status() if exists else False
        return {
            "ok": exists and status is not False,
            "installed": exists,
            "version": adapter.version(),
            "authorized": status,
            "install_command": adapter.install_command,
        }

    def read_text_file(self, project_path: str, relative_path: str) -> dict[str, Any]:
        root = Path(project_path).expanduser().resolve()
        target = (root / relative_path).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            return {"ok": False, "error": "Requested file is outside the project root."}
        if not target.is_file():
            return {"ok": False, "error": f"File not found: {relative_path}"}
        return {"ok": True, "path": str(target), "text": target.read_text(encoding="utf-8", errors="replace")}

    def open_project_folder(self, project_path: str) -> dict[str, Any]:
        root = Path(project_path).expanduser().resolve()
        if not root.is_dir():
            return {"ok": False, "error": "Project folder does not exist."}
        webbrowser.open(root.as_uri())
        return {"ok": True, "path": str(root)}

    def close_window(self) -> dict[str, Any]:
        try:
            import webview  # type: ignore[import-not-found]
        except ImportError:
            return {"ok": False, "error": "pywebview is not available."}
        for window in list(getattr(webview, "windows", [])):
            window.destroy()
        return {"ok": True}

    def launch_codex(self, project_path: str) -> dict[str, Any]:
        from ..cli import launch_agent

        self.close_window()
        code = launch_agent(Path(project_path), kickoff=False)
        return {"ok": code == 0, "code": code}
