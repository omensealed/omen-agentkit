# User guide

## 1. Run without installing

Extract the archive, open a terminal in its directory, and inspect the host:

```bash
./agent-starter doctor
```

`doctor` changes nothing. It reports Python, Git, Bash, curl, `pacman`, and Codex availability/login status.

Start the guided setup:

```bash
./agent-starter new
```

Running `./agent-starter` with no subcommand does the same thing.

## 2. Optional user-level install

```bash
./install.sh
agent-starter --version
```

This installs beneath your user data/bin directories and does not require root. `./uninstall.sh` removes only those installed starter-kit files.

## 3. Describe the project

The wizard asks whether this is a new project or an existing codebase, then collects:

- project type, stage, plain-language description, goals, and first-release exclusions;
- intended users, target platforms, and packaging targets;
- whether Codex should recommend the stack or the user wants to select it;
- implementation languages and whether to minimize dependencies;
- database/persistence needs, including SQLite, MariaDB, PostgreSQL, an existing database, no database, or an undecided choice;
- network, account, personal-data, payment, and security constraints;
- test layers, browser testing, local Git, and optional later GitHub Actions/repository setup;
- whether to generate optional rootless Podman sandbox files for containerized project checks;
- initial license choice, including MIT, Apache-2.0, BSD-3-Clause, GPL-3.0-or-later, AGPL-3.0-or-later, MPL-2.0, or undecided; the wizard shows a short permissive/copyleft guide before this choice;
- extra trusted CachyOS packages and unresolved questions.

Never enter a database password, OAuth token, API key, cookie, private key, or production secret. The kit does not need them.

## 4. Use Codex stack advice safely

When selected, the kit asks Codex for a structured recommendation from a temporary directory using a read-only sandbox. You see the proposed languages, database, architecture, rationale, risks, and questions before deciding what to accept.

The model’s commands are advisory text. They become generated executable commands only through the explicit reviewed custom-command path. When Codex is unavailable or its response is invalid, the wizard uses conservative built-in advice instead.

## 5. Review generated files

For an existing repository, conflicts do not overwrite current files. Review alternatives under:

```text
.agent-starter/proposals/
```

Only use `--force` after reviewing the result. Forced replacement stores original content under:

```text
.agent-starter/backups/
```

Read `AGENTS.md`, `FIRST_PROMPT.md`, `docs/00-PROJECT-BRIEF.md`, `docs/08-IMPLEMENTATION-PLAN.md`, and `docs/11-IMPLEMENTATION-NOTES.md` before the first Codex session.

Generated projects keep local AI/runtime artifacts out of GitHub by default. Codex logs, session JSONL files, saved prompt drafts, local-model handoff drafts, starter runtime state, proposals, and backups are ignored by `.gitignore`; durable project docs, scripts, and source files remain trackable.

The wizard recommends a local-first path. Local Git can be initialized immediately, but GitHub Actions default to off so you can run `./scripts/check.sh`, complete Phase 0, and decide later whether a remote repository or CI workflow is worth adding.

## 6. Prepare CachyOS

Inside the generated project:

```bash
./scripts/doctor.sh
./scripts/bootstrap-dev.sh
```

The first bootstrap invocation prints the proposed packages and commands. After checking them:

```bash
./scripts/bootstrap-dev.sh --install
```

That second command may invoke `sudo pacman`; the starter never supplies or stores the password. Project-specific setup remains separate from system package installation.

Run the local quality gate:

```bash
./scripts/check.sh
```

## 7. Use the optional Podman sandbox

If you enabled the rootless Podman sandbox, inspect it before relying on it:

```bash
agent-starter sandbox doctor .
scripts/sandbox/doctor
scripts/sandbox/build
scripts/sandbox/check
```

The default `toolchain` sandbox mode keeps Codex on the host editing the local project files and runs project build/test/toolchain work in a container against the mounted `/workspace`. If the sandbox was requested and `doctor`, `build`, or `check` fails, do not treat host checks as equivalent unless you deliberately approve a temporary host-only fallback. If you explicitly selected Codex-inside-container mode, use:

```bash
scripts/sandbox/codex-login
scripts/sandbox/codex
scripts/sandbox/resume
```

`codex-login` is an explicit user action and stores Codex state in a project-specific container home volume. The generated sandbox does not mount host `~/.codex`, `~/.ssh`, browser profiles, production configs, or the host home directory by default. Prefer `docs/agent-prompts/create-container-handoff.md` to create a no-secrets handoff summary instead of copying raw session transcripts.

Rootless Podman reduces host filesystem risk, but container commands can still change mounted project files and can misuse network access when networking is available. Do not use host full-access as the default answer to permission friction, and do not deploy, push, rsync production targets, or mount real secrets without explicit approval.

## 8. Authorize Codex

From the installed starter:

```bash
agent-starter auth --status
agent-starter auth
```

Use device-code login when browser opening is unsuitable:

```bash
agent-starter auth --device-auth
```

From a generated project, the equivalent helpers are:

```bash
./scripts/setup-agent.sh
./scripts/agent-status.sh
```

All account interaction belongs to the official Codex CLI. Confirm in that flow that you selected the intended ChatGPT account.

## 9. Start implementation

Launch from the generated project:

```bash
less NEXT_STEPS.md
agent-starter status .
./START_AGENT.sh
```

Or use the installed starter:

```bash
agent-starter launch /path/to/project
```

`NEXT_STEPS.md` explains the local checks, placeholder scripts, GitHub pause, and Codex setup path. `agent-starter status`
summarizes generated-file validation, Codex readiness, Git/GitHub state, ignored AI-local artifacts, and the next
recommended local action. Codex receives `FIRST_PROMPT.md` as its initial instruction. A noninteractive first pass is also available:

```bash
agent-starter launch /path/to/project --kickoff
```

The initial prompt tells Codex to inspect the existing repository, verify the project hypothesis, establish or repair the test baseline, update project docs, work the first safe phase, and record an implementation note.

## 10. Continue safely

At every meaningful phase:

1. Read `AGENTS.md`, current progress, recent implementation notes, decisions, and handoff.
2. Update the plan before making broad changes.
3. Keep changes phase-sized and avoid unrelated rewrites.
4. Run the closest tests during work and `./scripts/check.sh` before ending the phase.
5. Update requirements, architecture, security, and operations docs when behavior changes.
6. Append a complete entry to `docs/11-IMPLEMENTATION-NOTES.md`.
7. Refresh `docs/09-PROGRESS.md` and `docs/14-AGENT-HANDOFF.md` with the exact next step.

A note skeleton can be appended with:

```bash
./scripts/new-implementation-note.sh codex "Implement phase name"
```

When you know what you want next but are unsure how to prompt Codex, generate a continuation prompt from the project metadata and documented workflow:

```bash
agent-starter prompt /path/to/project --request "Add CSV import"
```

For a guided prompt builder:

```bash
agent-starter prompt /path/to/project --interactive
```

For task-specific guidance:

```bash
agent-starter prompt /path/to/project --template bug --request "Fix CSV import crash"
```

The prompt is printed to the terminal for copy/paste into Codex. To save it for review:

```bash
agent-starter prompt /path/to/project --request "Add CSV import" --output NEXT_PROMPT.md
```

The generated prompt tells Codex to read the project instructions and current progress, inspect the actual code, work in a small tested phase, update the implementation notes and handoff, and avoid privileged, destructive, credential, publish, deploy, and remote-push actions without explicit approval. Interactive mode asks about task type, recent changes, affected surfaces, risk, and expected verification. Named templates are `feature`, `bug`, `cleanup`, `docs`, `test-baseline`, and `release-prep`.

## 11. Check GitHub readiness

Before creating a GitHub remote, enabling GitHub Actions, or pushing, run:

```bash
agent-starter github-ready /path/to/project
```

The command validates the generated workspace, runs `./scripts/check.sh` unless `--skip-check` is supplied, checks local Git cleanliness, verifies AI-local artifact ignores, and inspects the CI workflow when one exists. It does not contact GitHub, create a repository, push, install packages, or deploy anything.

## 12. Plan a local mirror

To review a local or SSH source mirror command without running it:

```bash
agent-starter rsync-plan /path/to/project /path/to/project-mirror
```

The plan uses `.agent-starter/rsync-excludes` to skip credentials, local databases, caches, Codex session files, prompt drafts, starter proposals/backups, and `.git` history. Add `--run` only after reviewing the command and target. Add `--delete` only when target-side deletion is intended.

## 13. Check a local Ollama handoff

Codex remains the default and supported agent path. If you want to experiment with a local Ollama model for a later focused task, check whether the installed model is a plausible handoff target first:

```bash
agent-starter ollama-check /path/to/project --request "Add CSV import"
```

The command inspects only local Ollama metadata:

- `ollama list` for installed model names;
- `ollama show <model> --json` for confirmed context length when Ollama exposes it;
- model-name signals such as code-focused and large general-model families.

Only models with strong coding signals and confirmed large context are treated as suitable. Borderline or inadvisable models do not get a handoff prompt unless you explicitly accept the warning:

```bash
agent-starter ollama-check /path/to/project --model llama3.2:3b --override
```

This command does not edit `.codex/config.toml`, switch the generated project away from Codex, install Ollama models, pull models, or run a model against the project. It produces a warning-rich handoff prompt only after the readiness gate passes or is manually overridden.

The reference baseline for this warning is Codex's recommended model for complex coding work, currently `gpt-5.5` in the Codex manual. The Ollama check is a conservative local metadata assessment, not a guarantee that a local model will match Codex quality.
