from __future__ import annotations

import unittest

from agent_starter.agents import AgentError, advisor_schema, extract_json, get_adapter


class AgentHelpersTests(unittest.TestCase):
    def test_extract_plain_and_fenced_json(self) -> None:
        self.assertEqual(extract_json('{"summary":"ok"}')["summary"], "ok")
        fenced = 'noise\n```json\n{"summary":"fine"}\n```\nmore'
        self.assertEqual(extract_json(fenced)["summary"], "fine")

    def test_extract_json_rejects_non_json(self) -> None:
        with self.assertRaises(AgentError):
            extract_json("not structured")

    def test_schema_and_codex_aliases(self) -> None:
        schema = advisor_schema()
        self.assertEqual(schema["type"], "object")
        self.assertEqual(get_adapter().key, "codex")
        self.assertEqual(get_adapter("openai").key, "codex")
        with self.assertRaises(AgentError):
            get_adapter("unsupported")


if __name__ == "__main__":
    unittest.main()
