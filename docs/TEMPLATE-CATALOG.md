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
- `.gitignore`, license, language-specific starter metadata, and optional GitHub workflow as applicable. The generated `.gitignore` excludes local AI/runtime artifacts such as Codex logs, session JSONL files, prompt drafts, local-model handoff drafts, starter proposals, and backups while keeping durable project docs trackable.

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
- `docs/09-PROGRESS.md`: current phase, completed work, blockers, and next task.
- `docs/10-DECISIONS.md`: architecture decision records.
- `docs/11-IMPLEMENTATION-NOTES.md`: append-only session/phase engineering journal.
- `docs/12-RELEASE-CHECKLIST.md`: quality, security, packaging, and documentation gates.
- `docs/13-OPERATIONS.md`: configuration, backup, migration, logging, and recovery planning.
- `docs/14-AGENT-HANDOFF.md`: compact restart context for a fresh Codex session.
- `docs/15-OPEN-QUESTIONS.md`: unresolved product and engineering questions.
- `docs/AI-STACK-RECOMMENDATION.md`: reviewed Codex or deterministic fallback recommendation.
- `docs/12-SANDBOX.md`: optional rootless Podman security model and generated command guide when sandboxing is enabled.
- `docs/agent-prompts/create-container-handoff.md`: optional no-secrets handoff prompt for moving from host Codex context to a container session.

## Scripts

- `scripts/doctor.sh`: non-mutating host/tool diagnosis.
- `scripts/bootstrap-dev.sh`: review-first CachyOS dependency setup.
- `scripts/build.sh`, `test.sh`, `lint.sh`, `check.sh`, `run.sh`: normalized local workflow.
- `scripts/setup-agent.sh`: official Codex install/login boundary.
- `scripts/agent-status.sh`: Codex version and login status.
- `scripts/new-implementation-note.sh`: appends a complete note skeleton.
- `scripts/sandbox/*`: optional rootless Podman doctor/build/shell/exec/check/logs/clean scripts, plus Codex, database, web, and game helpers when selected by project metadata. Host-side wrappers must not accidentally run nested Podman from inside the project container.
- `scripts/playtest-host`: optional host playtest helper for game projects where container GUI/audio/controller support is intentionally not promised.

Template changes must update generator requirements, validation, tests, this catalog, and representative generated-project inspections together.
