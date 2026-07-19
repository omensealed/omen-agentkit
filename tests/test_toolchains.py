from __future__ import annotations

import unittest

from agent_starter.toolchains import (
    BASE_PACKAGES,
    DATABASE_PACKAGES,
    OPTIONAL_PACKAGES,
    capabilities_for,
    ci_setup_for,
    commands_for,
    fallback_recommendation,
    gitignore_for,
    normalize_language,
    packages_for,
    selected_toolchains,
    unique,
)


class ToolchainTests(unittest.TestCase):
    def test_aliases_and_deduplication(self) -> None:
        self.assertEqual(normalize_language("NodeJS"), "javascript")
        self.assertEqual(normalize_language("C++"), "cpp")
        self.assertEqual(unique(["git", "git", "curl"]), ["git", "curl"])
        self.assertEqual([item.key for item in selected_toolchains(["py", "rust"])], ["python", "rust"])

    def test_cachyos_packages_and_ignores(self) -> None:
        packages = packages_for(["python"], "sqlite", github=True)
        self.assertEqual(
            packages,
            ["git", "curl", "jq", "ripgrep", "fd", "unzip", "base-devel", "github-cli", "python", "python-pip", "sqlite"],
        )
        self.assertEqual(
            capabilities_for(["python"], "sqlite", github=True),
            ["base.tooling", "optional.github-cli", "language.python", "database.sqlite"],
        )
        self.assertIn("python", packages)
        self.assertIn("sqlite", packages)
        self.assertIn("github-cli", packages)
        ignores = gitignore_for(["python"], "sqlite")
        self.assertIn(".env", ignores)
        self.assertIn("*.sqlite", ignores)
        self.assertIn("AGENTS.md", ignores)
        self.assertIn("FIRST_PROMPT.md", ignores)
        self.assertIn(".agent-starter/", ignores)
        self.assertIn(".agents/", ignores)
        self.assertIn(".agent-starter/proposals/", ignores)
        self.assertIn(".codex/*.jsonl", ignores)
        self.assertIn(".codex/sessions/", ignores)
        self.assertIn("docs/09-PROGRESS.md", ignores)
        self.assertIn("docs/11-IMPLEMENTATION-NOTES.md", ignores)
        self.assertIn("docs/14-AGENT-HANDOFF.md", ignores)
        self.assertIn("docs/agent-prompts/", ignores)
        self.assertIn("NEXT_PROMPT.md", ignores)
        self.assertIn("LOCAL_MODEL_HANDOFF.md", ignores)

    def test_all_legacy_arch_package_views_remain_equivalent(self) -> None:
        self.assertEqual(BASE_PACKAGES, ("git", "curl", "jq", "ripgrep", "fd", "unzip", "base-devel"))
        self.assertEqual(OPTIONAL_PACKAGES, ("github-cli", "shellcheck"))
        self.assertEqual(DATABASE_PACKAGES, {
            "sqlite": ("sqlite",),
            "mariadb": ("mariadb",),
            "postgresql": ("postgresql",),
        })
        self.assertEqual(
            {item.key: item.packages for item in selected_toolchains(
                ["python", "javascript", "rust", "go", "php", "cpp", "java", "godot", "shell"]
            )},
            {
                "python": ("python", "python-pip"),
                "javascript": ("nodejs", "npm"),
                "rust": ("rustup",),
                "go": ("go",),
                "php": ("php", "composer"),
                "cpp": ("base-devel", "cmake", "ninja", "clang", "gdb"),
                "java": ("jdk-openjdk",),
                "godot": ("godot",),
                "shell": ("bash", "shellcheck"),
            },
        )

    def test_fallback_recommendations(self) -> None:
        languages, database, architecture = fallback_recommendation("game", ["browser"], True)
        self.assertEqual(languages, ["javascript"])
        self.assertEqual(database, "sqlite")
        self.assertIn("Canvas", architecture)

    def test_ci_snippets_are_normalized(self) -> None:
        snippet = ci_setup_for(["python"])[0]
        self.assertTrue(snippet.startswith("- name:"))
        self.assertIn("\n  uses:", snippet)

    def test_manifest_based_defaults_are_guarded(self) -> None:
        javascript_tests = commands_for(["javascript"], "test")
        php_setup = commands_for(["php"], "setup")
        self.assertTrue(any("package.json" in command for command in javascript_tests))
        self.assertTrue(any("composer.json" in command for command in php_setup))
        self.assertTrue(any("skipping" in command for command in javascript_tests))


if __name__ == "__main__":
    unittest.main()
