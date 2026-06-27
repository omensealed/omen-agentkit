# Development

## Requirements

- Python 3.11+
- Bash
- Git for repository-oriented checks
- No third-party Python runtime packages

CachyOS is the primary user environment, but source tests should remain portable across normal Linux development hosts.

## Commands

```bash
./scripts/check.sh
python3 -m unittest discover -s tests -v
python3 -m compileall -q agent_starter tests starter.py
bash -n install.sh uninstall.sh scripts/*.sh
./scripts/smoke-test.sh
./scripts/install-smoke-test.sh
```

## Test strategy

Unit tests cover models, normalization, JSON extraction, Codex command construction, templates, security boundaries, conflict behavior, project validation, CLI answers, and wizard helpers. Generator tests use temporary directories and disable Git unless Git behavior is under examination.

Agent Kit skill and `idea-prompt` tests use temporary generated projects. They must not require Codex to be installed, must not read `~/.codex`, and must not use shell interpolation for user-provided idea text.

No automated test invokes Codex login/advice against a real account, network installers, `sudo`, `pacman`, GitHub publication, remote pushes, or production databases. Subprocess tests use mocks or isolated commands. Installation tests replace `HOME`, `XDG_DATA_HOME`, and `XDG_BIN_HOME` with a temporary tree.

The smoke test generates a fresh project, validates it, runs its generated checks, validates all shell scripts, and confirms expected Codex/project-memory files.

## Adding a toolchain

1. Add a focused `Toolchain` entry in `agent_starter/toolchains.py`.
2. Prefer official compiler/runtime packages available through CachyOS repositories.
3. Keep setup, build, test, lint, CI, and ignore behavior mutually consistent.
4. Add normalization and generation tests.
5. Generate and inspect a representative project.
6. Update the answer-file reference and implementation notes.

Do not add a framework merely because a toolchain supports one. The wizard should preserve the user’s vanilla/minimal-dependency preference.

## Changing generated files

`agent_starter/generator.py::REQUIRED_FILES`, `build_file_map`, templates, validation, tests, README examples, and `docs/TEMPLATE-CATALOG.md` form one file contract. Update them together.

Generated `AGENTS.md`, `FIRST_PROMPT.md`, numbered docs, scripts, and `.codex/config.toml` must tell one consistent story. Verify both a new project and an existing-project renovation after changing this contract.

Generated `.agents/skills/agentkit/SKILL.md` and `agentkit-skill.json` are part of the optional Codex skill contract. Keep `SKILL.md` concise and store Agent Kit-specific version data in the JSON sidecar.

## Release

1. Update `VERSION`, `agent_starter.__version__`, `ProjectConfig.kit_version`, and `pyproject.toml` together.
2. Update `CHANGELOG.md` and `docs/PROGRESS.md`.
3. Append a complete entry to `docs/IMPLEMENTATION-NOTES.md`.
4. Run `./scripts/check.sh` from a clean source tree.
5. Build the archive without caches, local Git metadata, generated workspaces, or credentials.
6. Extract the archive into a fresh temporary directory and run the full check again.
7. Publish a SHA-256 checksum beside the archive.
