# Progress

## 0.4.3 patch release prep

- [x] Diagnose canary project host fallback after sandbox was requested.
- [x] Clarify `toolchain` mode as host Codex plus containerized command execution.
- [x] Strengthen generated prompts so sandbox failures block instead of silently falling back to host checks.
- [x] Run final full source check after version bump.
- [ ] Build and verify patch release archive/checksum locally.
- [ ] Tag and publish patch release if final archive check passes.

## 0.4.2 patch release prep

- [x] Remove noninteractive Podman TTY allocation from generated `scripts/sandbox/exec` and `scripts/sandbox/check`.
- [x] Preserve interactive `scripts/sandbox/shell` behavior.
- [x] Run final full source check after version bump.
- [x] Build and verify patch release archive/checksum locally.
- [x] Tag and publish patch release if final archive check passes.

## 0.4.1 patch release prep

- [x] Run manual rootless Podman smoke test on a disposable generated sandbox project.
- [x] Fix generated ephemeral sandbox command container-name collision found by smoke testing.
- [x] Run final full source check after version bump.
- [x] Build and verify patch release archive/checksum locally.
- [x] Tag and publish patch release if final archive check passes.

## 0.4.0 local release prep

- [x] Add repo-local `$agentkit` skill workflow and optional rootless Podman sandbox support.
- [x] Update source docs, answer-file reference, curated examples, tests, changelog, and implementation notes.
- [x] Run final full source check after version bump.
- [x] Build and verify release archive/checksum for local handoff.

## 0.2.0 Codex-only release

- [x] Remove alternate-agent adapters, choices, flags, examples, launcher paths, and generated compatibility files.
- [x] Use one official Codex authorization/status flow.
- [x] Keep Codex read-only stack advice with deterministic local fallback.
- [x] Generate Codex-specific `AGENTS.md`, `FIRST_PROMPT.md`, `.codex/config.toml`, and helper scripts.
- [x] Preserve language/database questions, CachyOS toolchain planning, testing, CI, security, UX, and implementation notes.
- [x] Add/refactor regression tests for the Codex-only contract.
- [x] Rewrite user and maintainer documentation.
- [x] Complete clean archive extraction and final full check.

## Stable capabilities

- [x] New-project and existing-project workflows.
- [x] Manual stack selection or reviewed Codex recommendation.
- [x] SQLite, MariaDB, PostgreSQL, existing, undecided, and no-database planning.
- [x] Safe atomic writes, conflict proposals, forced-write backups, and symlink/path protections.
- [x] Generated phase plan, progress log, decisions, implementation notes, handoff, security, test, release, and operations docs.
- [x] Optional local Git initialization, GitHub Actions, and explicitly authorized repository creation.
- [x] Source tests, generated-project smoke test, and isolated user installation test.
- [x] Copy/paste Codex continuation prompt generation for later project phases and feature requests.
- [x] Repo-local `$agentkit` Codex skill workflow with versioned sidecar metadata and local `idea-prompt` file generation.
- [x] Optional rootless Podman project sandbox generation for containerized toolchain checks and explicit Codex-inside-container workflows.
- [x] Assessment-only Ollama readiness gate with override-required local-model handoff prompt generation.
- [x] Local-first GitHub posture: local Git remains available while GitHub Actions are deferred by default.
- [x] Workspace status and GitHub readiness gates for local-first project management.

## Sandbox manager maturity plan

### Phase A — First-run clarity

- [x] Generate a root `NEXT_STEPS.md` with beginner-safe commands, explanation of placeholder checks, Codex launch steps, and local-first GitHub guidance.
- [x] Make final CLI generation output point directly at `NEXT_STEPS.md`.
- [x] Make placeholder `build`, `lint`, and `test` script output clearly say no real app harness exists yet for new projects.

### Phase B — Status and readiness

- [x] Add `agent-starter status /path/to/project` to summarize metadata, required files, Codex install/auth status, Git/GitHub state, ignored AI-local artifacts, and the next recommended action.
- [x] Add `agent-starter github-ready /path/to/project` to check local validation, dirty Git state, ignored AI artifacts, and CI-readiness before suggesting GitHub Actions or remote creation.

### Phase C — Guided continuation

- [x] Add an interactive mode for `agent-starter prompt` that asks what changed, whether this is a bug/feature/docs task, risk level, affected surfaces, and desired verification.
- [x] Add prompt templates for bug fix, feature, cleanup, docs, test-baseline, and release-prep work.

### Phase D — Local backup/mirror

- [x] Add review-first `rsync-plan` support for local or SSH backup targets.
- [x] Generate an `.agent-starter/rsync-excludes` file from the same safety posture as `.gitignore`.
- [x] Require explicit `--run` before executing `rsync`.

### Phase E — Release readiness

- [x] Decide the next release version and update `VERSION`, `agent_starter.__version__`, `ProjectConfig.kit_version`, and `pyproject.toml` together.
- [x] Inspect representative generated output after all Phase A-D changes: one new Python/SQLite project and one existing-project renovation.
- [x] Run `./scripts/check.sh` from this source tree after the final version/changelog updates.
- [x] Perform clean archive extraction verification and run the full check from the extracted archive.
- [x] Publish or hand off the archive and SHA-256 checksum only after release approval.
- [x] Create private GitHub repository `omensealed/omen-agentkit` and publish release `v0.3.0` with verified tarball and checksum assets.

## External acceptance

- [x] Local disposable project acceptance dry-run: generate, validate, status, GitHub readiness gate, continuation prompt, and plan-only rsync mirror.
- [ ] A user completes `codex login` with the intended ChatGPT account on CachyOS.
- [ ] A real generated project is carried through its first Codex implementation phase and implementation-note handoff.
