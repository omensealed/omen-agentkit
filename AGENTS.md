# Maintainer instructions — CLI AI Agent Starter Kit

## Purpose

Maintain a standard-library-only Python wizard that generates safe, useful **OpenAI Codex CLI** project workspaces with first-class CachyOS guidance. Preserve beginner usability, existing-file safety, Codex-owned OAuth, testability, and durable implementation notes.

## Read before changing code

Read these files in order:

1. `README.md`
2. `docs/ARCHITECTURE.md`
3. `docs/SECURITY-MODEL.md`
4. `docs/DEVELOPMENT.md`
5. `docs/IMPLEMENTATION-NOTES.md`

Inspect the relevant tests before modifying behavior. Treat `docs/IMPLEMENTATION-NOTES.md` as persistent project memory and append an entry for every meaningful implementation phase.

## Non-negotiable constraints

- This edition supports OpenAI Codex CLI only. Do not add alternate-agent branches, bridge files, flags, examples, or authentication paths without an explicit new architecture decision. Assessment-only local-model readiness checks are allowed only when they do not change generated Codex launch/auth configuration or `primary_agent`.
- Runtime code must use Python 3.11+ standard library only unless an approved decision documents why a dependency is unavoidable.
- Never ask for, read, copy, print, persist, or inspect OAuth tokens, API keys, cookies, browser profiles, or keyring data. Authorization belongs to the official `codex` command.
- Never run real Codex login, OpenAI network calls, GitHub publication, package-manager installation, or `sudo` in the automated test suite.
- Never execute model-suggested or answer-file custom commands without explicit user approval.
- Never silently replace an existing file. Preserve conflicts as proposals; when forced, create a backup first.
- Keep generated paths inside the chosen project root and retain the symlink/traversal protections.
- Package installation, GitHub repository creation, deployment, publication, destructive migrations, and remote pushes must remain explicit user actions.
- Generated `AGENTS.md` must require phase-based testing and updates to `docs/11-IMPLEMENTATION-NOTES.md`.
- Keep CachyOS commands reviewable before execution and prefer project-local, minimal toolchains.

## Verification

Run the complete source check before declaring work complete:

```bash
./scripts/check.sh
```

For focused iteration, use:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q agent_starter tests starter.py
bash -n install.sh uninstall.sh scripts/*.sh
```

Tests must use temporary directories, synthetic data, mocked subprocesses, and isolated `HOME`/XDG paths where appropriate.

## Change workflow

1. State the behavior being changed and identify security or compatibility implications.
2. Add or adjust a regression test before or with the implementation.
3. Make the smallest coherent change; avoid unrelated formatting or dependency churn.
4. Inspect at least one freshly generated project when templates, toolchains, launch behavior, or file contracts change.
5. Update user-facing docs, answer examples, version/changelog when applicable, and `docs/IMPLEMENTATION-NOTES.md`.
6. Run `./scripts/check.sh` and record the exact result in the implementation note.

## Generated-content review

For changes affecting templates or toolchains, inspect at least:

- one new Python/SQLite Codex project; and
- one existing-project renovation using a different built-in toolchain or database.

Confirm that:

- `AGENTS.md` and `FIRST_PROMPT.md` are consistent and Codex-specific;
- `.codex/config.toml` uses conservative workspace settings;
- the numbered docs agree with `.agent-starter/project.json`;
- setup commands are printed for review before installation;
- build, lint, test, check, run, and agent scripts have valid Bash syntax;
- the GitHub workflow matches the selected languages;
- no credentials or raw advisor transcript are persisted;
- implementation-note instructions are prominent and actionable.

## Definition of done

A change is complete only when implementation, regression tests, generated output, documentation, and implementation notes agree; all checks pass; and no credential, destructive-write, implicit-execution, or alternate-agent path has been introduced.
