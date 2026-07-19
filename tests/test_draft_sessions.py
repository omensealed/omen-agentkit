from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agent_starter.draft_sessions import DRAFT_FILE_LIMIT, DraftSessionError, DraftStore, default_draft_root


class DraftSessionTests(unittest.TestCase):
    def project(self, root: Path) -> dict[str, object]:
        return {
            "entry_mode": "guided",
            "project_name": "Draft Project",
            "project_path": str(root / "project"),
            "description": "An incomplete beginner project.",
            "sandbox_enabled": True,
        }

    def task(self) -> dict[str, object]:
        return {
            "kind": "fix",
            "answers": {
                "steps": "Open the report.",
                "observed": "The page is blank.",
                "expected": "",
            },
        }

    def test_default_root_uses_user_local_xdg_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp, mock.patch.dict(
            os.environ, {"XDG_DATA_HOME": temp}, clear=False
        ):
            self.assertEqual(default_draft_root(), Path(temp) / "omen-agentkit" / "drafts")
        with mock.patch.dict(os.environ, {"XDG_DATA_HOME": "relative-data"}, clear=False):
            with self.assertRaises(DraftSessionError):
                default_draft_root()

    def test_partial_project_and_task_survive_store_restart_privately(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "data" / "drafts"
            stored = DraftStore(root).save(project=self.project(Path(temp)), task=self.task())
            loaded = DraftStore(root).load(stored.draft_id)
            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertEqual(loaded.project, stored.project)
            self.assertEqual(loaded.task, stored.task)
            self.assertEqual(loaded.selected_project, str(Path(temp) / "project"))
            self.assertTrue(loaded.updated_at.endswith("+00:00"))
            self.assertEqual(os.stat(root).st_mode & 0o777, 0o700)
            self.assertEqual(os.stat(root / f"{stored.draft_id}.json").st_mode & 0o777, 0o600)
            summary = DraftStore(root).list_summaries()[0]
            self.assertEqual(summary.draft_id, stored.draft_id)
            self.assertEqual(summary.selected_project, loaded.selected_project)
            self.assertEqual(summary.updated_at, loaded.updated_at)

    def test_drafts_reject_secrets_unknown_fields_malformed_files_and_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            store = DraftStore(base / "drafts")
            project = self.project(base)
            with self.assertRaises(DraftSessionError):
                store.save(project={**project, "description": "api_key=do-not-store"}, task=None)
            with self.assertRaises(DraftSessionError):
                store.save(project={**project, "unexpected": "value"}, task=None)
            with self.assertRaises(DraftSessionError):
                store.save(project=project, task={
                    "kind": "feature",
                    "answers": {"outcome": "password=do-not-store"},
                })
            with self.assertRaises(DraftSessionError):
                store.save(project=project, task={
                    "kind": "feature",
                    "answers": {"outcome": "Authorization: Bearer do-not-store"},
                })
            self.assertFalse((base / "drafts").exists())

            saved = store.save(project=project, task=self.task())
            path = store.root / f"{saved.draft_id}.json"
            path.write_text("{not json", encoding="utf-8")
            with self.assertRaises(DraftSessionError):
                store.load(saved.draft_id)

            path.write_bytes(b"x" * (DRAFT_FILE_LIMIT + 1))
            with self.assertRaises(DraftSessionError):
                store.load(saved.draft_id)

            path.unlink()
            outside = base / "outside.json"
            outside.write_text("outside", encoding="utf-8")
            path.symlink_to(outside)
            with self.assertRaises(DraftSessionError):
                store.load(saved.draft_id)
            with self.assertRaises(DraftSessionError):
                store.save(project=project, task=self.task(), draft_id=saved.draft_id)
            self.assertEqual(outside.read_text(encoding="utf-8"), "outside")

    def test_update_export_and_discard_are_explicit_atomic_operations(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            store = DraftStore(base / "drafts")
            first = store.save(project=self.project(base), task=self.task())
            updated_project = {**self.project(base), "description": "Updated draft."}
            updated = store.save(project=updated_project, task=None, draft_id=first.draft_id)
            self.assertEqual(updated.draft_id, first.draft_id)
            self.assertEqual(updated.project["description"], "Updated draft.")

            exported = base / "exports" / "draft.json"
            result = store.export(first.draft_id, exported)
            self.assertEqual(result, exported)
            exported_data = json.loads(exported.read_text(encoding="utf-8"))
            self.assertEqual(exported_data["draft_id"], first.draft_id)
            self.assertEqual(os.stat(exported).st_mode & 0o777, 0o600)
            with self.assertRaises(DraftSessionError):
                store.export(first.draft_id, exported)
            self.assertIsNotNone(store.load(first.draft_id))

            outside = base / "outside"
            outside.mkdir()
            linked_parent = base / "linked-export"
            linked_parent.symlink_to(outside, target_is_directory=True)
            with self.assertRaises(DraftSessionError):
                store.export(first.draft_id, linked_parent / "draft.json")
            self.assertFalse((outside / "draft.json").exists())

            self.assertTrue(store.discard(first.draft_id))
            self.assertFalse(store.discard(first.draft_id))
            self.assertIsNone(store.load(first.draft_id))


if __name__ == "__main__":
    unittest.main()
