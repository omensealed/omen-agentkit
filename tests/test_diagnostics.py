from __future__ import annotations

import subprocess
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agent_starter.config_schema import ConfigValidationError, ValidationIssue
from agent_starter.diagnostics import (
    DiagnosticResult,
    DiagnosticLog,
    DIAGNOSTIC_LOG_LIMIT,
    DiagnosticSeverity,
    default_diagnostic_log_root,
    diagnostic_from_exception,
)
from agent_starter.task_composer import TaskValidationError


class DiagnosticTests(unittest.TestCase):
    def test_stable_result_shape_and_severity(self) -> None:
        result = DiagnosticResult(
            code="review_needed",
            severity=DiagnosticSeverity.WARNING,
            title="Review needed",
            explanation="One choice needs review.",
            project_changed=False,
            safe_next_action="Review the choice before continuing.",
            technical_details="field=example",
        )
        self.assertEqual(
            list(result.to_dict()),
            [
                "code",
                "severity",
                "title",
                "explanation",
                "project_changed",
                "safe_next_action",
                "technical_details",
            ],
        )
        self.assertEqual(result.to_dict()["severity"], "warning")
        self.assertIs(result.to_dict()["project_changed"], False)

    def test_validation_exception_uses_structured_issue_and_safe_remedy(self) -> None:
        error = ConfigValidationError([
            ValidationIssue(
                "network_access",
                "invalid_boolean",
                "Use a JSON boolean.",
                "Choose true or false without quotation marks.",
            )
        ])
        result = diagnostic_from_exception(error, operation="preview_config")
        self.assertEqual(result.code, "configuration_invalid")
        self.assertEqual(result.title, "Review the project settings")
        self.assertEqual(result.explanation, "network_access: Use a JSON boolean.")
        self.assertEqual(result.safe_next_action, "Choose true or false without quotation marks.")
        self.assertEqual(result.technical_details, "operation=preview_config; field=network_access; issue=invalid_boolean")
        self.assertFalse(result.project_changed)

    def test_known_backend_exceptions_map_without_tracebacks_or_secret_values(self) -> None:
        cases = (
            (TaskValidationError("password=do-not-show"), "task_invalid"),
            (FileNotFoundError("/secret/private/project.json"), "file_not_found"),
            (PermissionError("token=do-not-show"), "permission_denied"),
            (subprocess.TimeoutExpired(["codex", "secret"], 5), "operation_timed_out"),
            (OSError("api_key=do-not-show"), "system_io_error"),
            (RuntimeError("unexpected password=do-not-show"), "unexpected_backend_error"),
        )
        for error, code in cases:
            with self.subTest(error=type(error).__name__):
                result = diagnostic_from_exception(error, operation="test_operation", project_changed=True)
                encoded = str(result.to_dict())
                self.assertEqual(result.code, code)
                self.assertTrue(result.project_changed)
                self.assertNotIn("do-not-show", encoded)
                self.assertNotIn("Traceback", encoded)
                self.assertTrue(result.safe_next_action)

    def test_private_bounded_log_redacts_again_and_refuses_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "state" / "diagnostics"
            logger = DiagnosticLog(root)
            unsafe = DiagnosticResult(
                code="test_failure",
                severity=DiagnosticSeverity.ERROR,
                title="password=do-not-log",
                explanation="Authorization: Bearer do-not-log",
                project_changed=False,
                safe_next_action="Remove api_key=do-not-log.",
                technical_details="/private/path cookie=do-not-log",
            )
            self.assertTrue(logger.write(unsafe))
            path = root / "gui-diagnostics.jsonl"
            content = path.read_text(encoding="utf-8")
            record = json.loads(content)
            self.assertNotIn("do-not-log", content)
            self.assertNotIn("/private/path", content)
            self.assertEqual(record["diagnostic"]["code"], "test_failure")
            self.assertFalse(record["diagnostic"]["project_changed"])
            self.assertEqual(os.stat(root).st_mode & 0o777, 0o700)
            self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)

            path.unlink()
            outside = Path(temp) / "outside.log"
            outside.write_text("outside", encoding="utf-8")
            path.symlink_to(outside)
            self.assertFalse(logger.write(unsafe))
            self.assertEqual(outside.read_text(encoding="utf-8"), "outside")

            path.unlink()
            path.write_bytes(b"x" * DIAGNOSTIC_LOG_LIMIT)
            self.assertTrue(logger.write(unsafe))
            self.assertLess(path.stat().st_size, DIAGNOSTIC_LOG_LIMIT)

            path.unlink()
            root.rmdir()
            outside_directory = Path(temp) / "outside-directory"
            outside_directory.mkdir()
            root.symlink_to(outside_directory, target_is_directory=True)
            self.assertFalse(logger.write(unsafe))
            self.assertEqual(list(outside_directory.iterdir()), [])

    def test_default_log_root_requires_absolute_xdg_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp, mock.patch.dict(
            os.environ, {"XDG_STATE_HOME": temp}, clear=False
        ):
            self.assertEqual(
                default_diagnostic_log_root(),
                Path(temp) / "omen-agentkit" / "diagnostics",
            )
        with mock.patch.dict(os.environ, {"XDG_STATE_HOME": "relative-state"}, clear=False):
            self.assertIsNone(default_diagnostic_log_root())


if __name__ == "__main__":
    unittest.main()
