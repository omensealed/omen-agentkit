from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agent_starter.gui.bridge import GuiBridge
from agent_starter.ui_schema import GUI_PAGES, config_from_gui_payload


class GuiTests(unittest.TestCase):
    def payload(self, root: Path) -> dict[str, object]:
        return {
            "project_name": "GUI Test",
            "project_path": str(root),
            "project_mode": "new",
            "project_stage": "idea",
            "project_type": "cli",
            "description": "A GUI-generated project.",
            "languages": "python",
            "database": "sqlite",
            "target_platforms": "cachyos-linux",
            "codex_agentkit_skill": True,
            "sandbox_enabled": True,
            "sandbox_mode": "toolchain",
            "gui_passthrough": False,
            "git_enabled": False,
        }

    def test_gui_pages_cover_expected_flow(self) -> None:
        ids = [str(page["id"]) for page in GUI_PAGES]
        for expected in ("welcome", "project", "codex", "sandbox", "stack", "generate", "result"):
            self.assertIn(expected, ids)

    def test_config_from_gui_payload_builds_project_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            config = config_from_gui_payload(self.payload(root))
            self.assertEqual(config.project_name, "GUI Test")
            self.assertEqual(config.primary_agent, "codex")
            self.assertEqual(config.languages, ["python"])
            self.assertEqual(config.database, "sqlite")
            self.assertTrue(config.codex_agentkit_skill)
            self.assertTrue(config.sandbox.enabled)
            self.assertEqual(config.sandbox.mode, "toolchain")
            self.assertFalse(config.sandbox.gui_passthrough)

    def test_gui_payload_rejects_secret_like_text(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            payload = self.payload(Path(temp) / "project")
            payload["description"] = "api_key=sk-secret-value"
            with self.assertRaises(ValueError):
                config_from_gui_payload(payload)

    def test_bridge_generates_and_validates_without_display(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            bridge = GuiBridge()
            result = bridge.generate(self.payload(root))
            self.assertTrue(result["ok"], result)
            self.assertTrue((root / "AGENTS.md").is_file())
            self.assertTrue((root / ".agents/skills/agentkit/SKILL.md").is_file())
            validation = bridge.validate(str(root))
            self.assertTrue(validation["ok"], validation)

    def test_bridge_codex_status_does_not_start_login(self) -> None:
        adapter = mock.Mock()
        adapter.exists.return_value = True
        adapter.auth_status.return_value = False
        adapter.version.return_value = "codex test"
        adapter.install_command = "review installer"
        with mock.patch("agent_starter.gui.bridge.get_adapter", return_value=adapter):
            result = GuiBridge().codex_status()
        self.assertFalse(result["ok"])
        adapter.login.assert_not_called()

    def test_bridge_launch_codex_closes_window_first(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            bridge = GuiBridge()
            with (
                mock.patch.object(bridge, "close_window", return_value={"ok": True}) as close_window,
                mock.patch("agent_starter.cli.launch_agent", return_value=0) as launch_agent,
            ):
                result = bridge.launch_codex(str(root))
            self.assertTrue(result["ok"])
            close_window.assert_called_once_with()
            launch_agent.assert_called_once_with(root, kickoff=False)

    def test_gui_app_imports_without_pywebview(self) -> None:
        from agent_starter.gui import app

        self.assertEqual(app.static_path().name, "index.html")

    def test_pywebview_smoke_when_available(self) -> None:
        if importlib.util.find_spec("webview") is None:
            self.skipTest("pywebview is not installed")
        import agent_starter.gui.app as app

        self.assertTrue(app.static_path().is_file())


if __name__ == "__main__":
    unittest.main()
