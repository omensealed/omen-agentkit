# Generated template catalog

## Root files

- `AGENTS.md`: canonical Codex project contract, safety limits, phase routine, testing requirements, and documentation-memory rules.
- `FIRST_PROMPT.md`: initial prompt containing the project brief, Phase 0 objective, required reading, and first deliverables.
- `NEXT_STEPS.md`: beginner-safe post-generation command sequence, placeholder-check explanation, Codex launch path, and local-first GitHub guidance.
- `README.md`: beginner-facing project setup, commands, current phase, and workflow.
- `START_AGENT.sh`: validates basic project files, runs sandbox preflight for active sandbox modes, and launches Codex with the prepared prompt.
- `.codex/config.toml`: conservative workspace sandbox, approval, and web-search defaults.
- `.agents/skills/agentkit/SKILL.md`: optional concise repo-local Codex skill for `$agentkit` prompt expansion.
- `.agents/skills/agentkit/agentkit-skill.json`: optional Agent Kit-managed skill version/install metadata.
- `.agent-starter/project.json`: normalized non-secret project configuration.
- `.agent-starter/manifest.json`: hashes/modes for generated managed files.
- `.agent-starter/rsync-excludes`: review-first local/SSH mirror excludes for `agent-starter rsync-plan`.
- `.agent-starter/sandbox/Containerfile`, `sandbox.json`, and `README.md`: optional rootless Podman project sandbox definition.
- `.gitignore`, license, language-specific starter metadata, and optional GitHub workflow as applicable. The generated `.gitignore` excludes local AI/runtime artifacts such as `AGENTS.md`, first prompts, implementation/progress/handoff notes, Codex skill metadata, prompt drafts, Codex logs, session JSONL files, local-model handoff drafts, starter runtime state, proposals, and backups while keeping end-user docs, scripts, and source files trackable.

## Documentation memory

- `docs/README.md`: documentation map and update rules.
- `docs/00-PROJECT-BRIEF.md`: users, goals, non-goals, platform, packaging, and status.
- `docs/01-REQUIREMENTS.md`: functional/nonfunctional requirements and acceptance criteria.
- `docs/02-ARCHITECTURE.md`: initial architecture hypothesis and boundaries.
- `docs/03-TECH-STACK.md`: selected languages, database, dependencies, and Codex recommendation rationale.
- `docs/04-DEVELOPMENT-ENVIRONMENT.md`: CachyOS prerequisites and local setup.
- `docs/05-TESTING.md`: test pyramid, commands, fixtures, and completion gates.
- `docs/06-SECURITY.md`: threat model, data handling, and secure-development checklist.
- `docs/07-UX-ACCESSIBILITY.md`: beginner experience, errors, accessibility, and platform conventions.
- `docs/08-IMPLEMENTATION-PLAN.md`: phased path from discovery to release.
- `docs/09-PROGRESS.md`: local AI-facing current phase, completed work, blockers, and next task.
- `docs/10-DECISIONS.md`: architecture decision records.
- `docs/11-IMPLEMENTATION-NOTES.md`: local append-only session/phase engineering journal.
- `docs/12-RELEASE-CHECKLIST.md`: quality, security, packaging, and documentation gates.
- `docs/13-OPERATIONS.md`: configuration, backup, migration, logging, and recovery planning.
- `docs/14-AGENT-HANDOFF.md`: local compact restart context for a fresh Codex session.
- `docs/15-OPEN-QUESTIONS.md`: unresolved product and engineering questions.
- `docs/AI-STACK-RECOMMENDATION.md`: reviewed Codex or deterministic fallback recommendation.
- `docs/12-SANDBOX.md`: optional rootless Podman security model and generated command guide when sandboxing is enabled.
- `docs/CACHYOS-PODMAN.md`: optional CachyOS/Arch rootless Podman troubleshooting guide, host/container/Codex flow table, and log locations when sandboxing is enabled.
- `docs/GODOT-SANDBOX.md`: optional Godot headless test hook and artifact guidance for Godot/game sandbox projects.
- `docs/agent-prompts/create-container-handoff.md`: optional no-secrets handoff prompt for moving from host Codex context to a container session.

## Scripts

- `scripts/doctor.sh`: non-mutating host/tool diagnosis.
- `scripts/bootstrap-dev.sh`: review-first CachyOS dependency setup.
- `scripts/build.sh`, `test.sh`, `lint.sh`, `check.sh`, `run.sh`: normalized local workflow.
- `scripts/setup-agent.sh`: official Codex install/login boundary.
- `scripts/agent-status.sh`: Codex version and login status.
- `scripts/new-implementation-note.sh`: appends a complete note skeleton.
- `scripts/sandbox/*`: optional rootless Podman doctor/preflight/status/build/shell/exec/check/logs/clean scripts, plus Codex, database, web, and game helpers when selected by project metadata. Project container wrappers use `--userns=keep-id` with runtime `id -u` / `id -g` so mounted `/workspace` files remain host-owned, use project-local home/cache directories under `.agent-starter/`, apply basic hardening flags, and default toolchain command networking to none unless `AGENTKIT_SANDBOX_NETWORK=default` is explicitly set. Host-side wrappers must not accidentally run nested Podman from inside the project container. Preflight writes a fingerprinted `.agent-starter/sandbox/preflight.json` plus logs under `.agent-starter/logs/`; status can validate that stamp even when `agent-starter` is not on `PATH`. Build reuses the project image by default; clean removes labeled project containers and can remove images/volumes only through explicit `--dry-run`, `--force`, `--image`, and `--volumes` controls.
- `scripts/sandbox/playtest-gui`: optional advanced game/Godot helper generated only when `sandbox.gui_passthrough` is true; it intentionally exposes selected host Wayland, GPU, PipeWire audio, and input/controller interfaces to the project container.
- `scripts/sandbox/headless-test`: optional game/Godot helper that prefers project-owned `scripts/godot-headless-test.sh` when present and otherwise falls back to `./scripts/check.sh` with an honest message that real visual/screenshot coverage still needs a project hook.
- `scripts/playtest-host`: optional host playtest helper for game projects where container GUI/audio/controller support is not enabled by default.

Template changes must update generator requirements, validation, tests, this catalog, and representative generated-project inspections together.

## Source-only optional GUI files

- `agent_starter/gui/app.py`: lazy `pywebview` desktop launcher for the optional GUI.
- `agent_starter/gui/bridge.py`: local JavaScript bridge over `ProjectConfig`, `generate_project()`, validation, and Codex status/launch boundaries.
- `agent_starter/gui/static/*`: local HTML, CSS, and JavaScript assets; no CDN or remote assets.
- `agent_starter/ui_schema.py`: shared beginner-facing page metadata and GUI payload conversion.
