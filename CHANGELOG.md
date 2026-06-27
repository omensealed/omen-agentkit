# Changelog

## Unreleased

## 0.4.0 — 2026-06-27

- Added `agent-starter idea-prompt` for local prompt-file generation from short `$agentkit` requests.
- Added `agent-starter codex skill-status`, `install-agentkit-skill`, `update-agentkit-skill`, and `uninstall-agentkit-skill` for versioned repo-local Agent Kit Codex skill management.
- Generated projects can include `.agents/skills/agentkit/SKILL.md` and `agentkit-skill.json` by default, with answers-file opt-out through `codex_agentkit_skill: false`.
- Added optional rootless Podman sandbox generation with `agent-starter sandbox doctor`, generated `scripts/sandbox/*` helpers, sandbox-aware `$agentkit` prompts, project-scoped Codex-inside-container launch scripts when explicitly selected, and no-secrets container handoff guidance.

## 0.3.0 — 2026-06-24

- Added `agent-starter prompt` to generate copy/paste Codex continuation prompts for later project phases and feature requests.
- The generated continuation prompt reinforces project-memory reading order, phase-sized implementation, testing, documentation updates, and approval boundaries.
- Added `agent-starter ollama-check` to assess installed Ollama models before generating a warning-rich local-model handoff prompt.
- Ollama handoff prompts require confirmed strong model suitability or an explicit `--override`; the feature does not rewrite Codex configuration or add an alternate launcher.
- Added `Apache-2.0`, `BSD-3-Clause`, `GPL-3.0-or-later`, `AGPL-3.0-or-later`, and `MPL-2.0` as built-in generated project license options.
- Changed interactive and example defaults to defer GitHub Actions so new projects prove local setup/tests before adding CI or remote repository noise.
- Added generated `NEXT_STEPS.md` and completion-output guidance so beginners start with local checks, understand placeholder scripts, and pause GitHub until Phase 0 is useful.
- Added `agent-starter status` to summarize generated workspace readiness, Codex install/auth state, Git/GitHub state, AI-local artifact ignores, and the next recommended local action.
- Added `agent-starter github-ready` as a local-first gate before creating GitHub remotes, enabling CI, or pushing.
- Added `agent-starter prompt --interactive` to guide beginners through task type, recent changes, affected surfaces, risk, and verification before producing a Codex continuation prompt.
- Added `agent-starter prompt --template` options for feature, bug, cleanup, docs, test-baseline, and release-prep continuation work.
- Added generated `.agent-starter/rsync-excludes` and review-first `agent-starter rsync-plan` for local/SSH source mirrors that require explicit `--run` before execution.
- Updated source repository ignore rules so local `.agents/` and `.codex/` workspaces are not accidentally staged for GitHub publication.

## 0.2.0 — 2026-06-24

- Refactored the starter kit into an OpenAI Codex CLI–only workflow.
- Removed alternate-client selection, adapters, generated compatibility files, examples, launcher paths, authorization flags, and documentation.
- Simplified `auth`, `launch`, wizard setup, project metadata validation, and generated agent scripts around Codex.
- Added Codex-only regression coverage and refreshed all maintainer/user documentation.
- Kept OAuth under the official Codex CLI and retained the existing safe-write, CachyOS, testing, and implementation-note workflow.

## 0.1.0 — 2026-06-23

- Initial standard-library Python wizard and deterministic answers-file generator.
- Added CachyOS toolchain guidance, safe existing-project writes, generated project documentation, test scripts, CI, Git helpers, authorization delegation, and implementation-note requirements.
- Added source, generation, and isolated installation checks.
