# CLI AI Agent Starter Kit — Codex Edition

A standard-library-only Python wizard that turns a project idea—or an existing codebase—into a documented, test-oriented workspace for **OpenAI Codex CLI**. It is designed for beginners using CachyOS while keeping the generated workflow useful on other Linux systems.

The kit asks the project questions that are easy to skip during vibe coding: what is being built, which languages fit, whether persistence is needed, which database is appropriate, what Codex must be able to test, what security boundaries apply, and whether Git/GitHub automation should be included. It then writes the project memory Codex needs before implementation begins.

## What it creates

A generated workspace can include:

- a canonical `AGENTS.md` contract for Codex;
- `FIRST_PROMPT.md`, ready to start the first implementation phase;
- `NEXT_STEPS.md`, a beginner-safe local sequence for the first run after generation;
- numbered `docs/*.md` files covering requirements, architecture, stack, CachyOS setup, testing, security, UX, phases, decisions, progress, implementation notes, release, operations, handoff, and open questions;
- `.codex/config.toml` with conservative project defaults;
- `START_AGENT.sh` plus Codex setup/status helpers;
- build, run, lint, test, and aggregate check scripts appropriate to the selected toolchains;
- optional repo-local `$agentkit` Codex skill files under `.agents/skills/agentkit/`;
- optional rootless Podman sandbox files for containerized build/test work and, when explicitly selected, Codex inside a project-scoped container;
- optional local Git initialization and deferred GitHub Actions workflow;
- safe handling for existing repositories through proposals and timestamped backups instead of silent replacement.

The generated `docs/11-IMPLEMENTATION-NOTES.md` is the durable work journal. `AGENTS.md` instructs Codex to update it after every meaningful phase so a later session can recover the exact state of the project.

## Fast start on CachyOS

The starter itself requires Python 3.11 or newer and Bash. Run it directly from the extracted directory:

```bash
./agent-starter doctor
./agent-starter new
```

For a user-level installation:

```bash
./install.sh
agent-starter doctor
agent-starter new
```

The installer writes only beneath the user data and binary directories, normally `~/.local/share/cli-ai-agent-starter-kit` and `~/.local/bin/agent-starter`. It does not use `sudo`.

## The guided workflow

The interactive wizard walks through:

1. **Project identity and scope** — new or existing project, current stage, type, description, goals, non-goals, users, platforms, and packaging targets.
2. **Codex readiness** — detect Codex, optionally run the official installer, and authorize the user through Codex’s own login flow.
3. **Technology choice** — manually choose languages and persistence, or ask Codex for a read-only structured recommendation and review it before accepting anything.
4. **Data and security** — database type, network access, accounts, personal data, payments, existing schemas, and project-specific risks.
5. **Quality workflow** — tests, browser testing, build/lint commands, local Git, and deferred GitHub Actions/repository setup after local checks prove useful.
6. **CachyOS and sandboxing** — generate reviewable `pacman` package guidance and optional rootless Podman project sandbox files; no package installation or Podman command runs during generation.
7. **Handoff** — validate the generated workspace and optionally launch Codex with `FIRST_PROMPT.md`.

The local fallback recommendation remains available when Codex is absent or cannot return valid structured advice.

## Codex authorization and account ownership

Authorization is delegated to the official Codex CLI. The starter kit never asks for, reads, copies, logs, or stores OAuth tokens, API keys, browser cookies, or keyring data.

Useful commands:

```bash
agent-starter auth --status
agent-starter auth
agent-starter auth --device-auth
agent-starter auth --relogin
```

When Codex is missing, the starter prints the official installer command. Running it requires explicit approval:

```bash
agent-starter auth --install
```

A generated project also includes:

```bash
./scripts/setup-agent.sh
./scripts/agent-status.sh
```

Browser OAuth is the default. Device-code authorization is available when the local browser flow is inconvenient.

## Useful commands

```bash
# Interactive wizard; also the default when no subcommand is supplied
agent-starter new

# Add the workflow to a specified directory
agent-starter new --path /path/to/project

# Generate without launching Codex
agent-starter new --no-launch

# Preview intended writes
agent-starter new --dry-run

# Write an editable JSON answers example
agent-starter example-answers --output answers.json

# Deterministic generation from reviewed answers
agent-starter generate --answers answers.json

# Permit explicitly supplied custom commands after manual review
agent-starter generate --answers answers.json --allow-custom-commands

# Validate a generated workspace
agent-starter validate /path/to/project --verbose

# Summarize readiness and the next local action
agent-starter status /path/to/project

# Check local readiness before creating a GitHub remote, enabling CI, or pushing
agent-starter github-ready /path/to/project

# Review a local/SSH source mirror command without running it
agent-starter rsync-plan /path/to/project /path/to/project-mirror

# Inspect the host, CachyOS tools, and Codex status
agent-starter doctor

# Launch Codex interactively with the prepared first prompt
agent-starter launch /path/to/project

# Run the first prompt as a one-shot Codex task
agent-starter launch /path/to/project --kickoff

# Generate a copy/paste prompt for the next Codex session
agent-starter prompt /path/to/project --request "Add import support"

# From inside a generated project, turn a short Codex skill request into a full prompt file
agent-starter idea-prompt --from-codex --arguments "implement Add SQLite save/load support"

# Install or update the repo-local $agentkit Codex skill
agent-starter codex install-agentkit-skill /path/to/project
agent-starter codex skill-status /path/to/project

# Check generated rootless Podman sandbox readiness without installing anything
agent-starter sandbox doctor /path/to/project

# Add task-specific guidance
agent-starter prompt /path/to/project --template bug --request "Fix CSV import crash"

# Ask guided questions before generating that continuation prompt
agent-starter prompt /path/to/project --interactive

# Save that continuation prompt for review
agent-starter prompt /path/to/project --request "Add import support" --output NEXT_PROMPT.md

# Assess local Ollama models before attempting a local-model handoff
agent-starter ollama-check /path/to/project --request "Continue the import feature"

# Show built-in language/database package mappings
agent-starter toolchains
```

## Existing-project safety

The generator treats existing source code as user data:

- it refuses unsafe roots such as `/` and the home directory itself;
- generated paths are constrained to the selected project root;
- writes through symlinked parent directories are rejected;
- new files are written atomically;
- identical files are left unchanged;
- conflicting files are preserved and generated alternatives go under `.agent-starter/proposals/`;
- `--force` first creates timestamped copies under `.agent-starter/backups/`;
- Git initialization never creates a commit or pushes a remote;
- GitHub Actions are deferred by default for new projects so beginners can prove local setup and tests first;
- GitHub repository creation is opt-in and never pushes code automatically.
- local AI/runtime artifacts such as Codex logs, session JSONL files, saved prompt drafts, local-model handoff drafts, and starter proposals/backups are ignored by the generated `.gitignore` so GitHub stays focused on the project source and durable docs.

Answers files are also checked for common credential patterns. Custom executable commands require `--allow-custom-commands` so downloaded or copied JSON cannot silently become code execution.

## Generated project routine

After generation, the normal project loop is:

```bash
cd /path/to/project
less NEXT_STEPS.md
./scripts/doctor.sh
./scripts/bootstrap-dev.sh             # prints/reviews the plan
./scripts/bootstrap-dev.sh --install   # explicit CachyOS package install
./scripts/check.sh
agent-starter status .
./START_AGENT.sh
```

GitHub can stay off until the project has a useful local baseline. Enable a workflow or create a remote only after `./scripts/check.sh` and Phase 0 documentation make the project worth publishing or backing up remotely.
Run `agent-starter github-ready /path/to/project` before creating a remote, enabling GitHub Actions, or pushing; it checks validation, local checks, Git cleanliness, CI posture, and ignored AI-local artifacts without contacting GitHub.
For a local or SSH source mirror, `agent-starter rsync-plan /path/to/project /path/to/project-mirror` prints the exact `rsync` command and uses `.agent-starter/rsync-excludes`; it only executes when `--run` is supplied.

Inside the Codex session, `AGENTS.md` requires the agent to inspect the project docs, work one phase at a time, run the available tests, and append an implementation note before ending the phase. The helper below creates a note skeleton:

```bash
./scripts/new-implementation-note.sh codex "Phase objective"
```

For later work, the starter can generate a focused continuation prompt that tells Codex what to read, how to preserve the project contract, which safety boundaries apply, and how to report completion:

```bash
agent-starter prompt /path/to/project --request "Implement the next planned feature"
```

For a guided beginner flow, use `agent-starter prompt /path/to/project --interactive`; it asks about task type, recent changes, affected surfaces, risk, and verification before printing the same Codex-safe continuation prompt.
Named templates are available with `--template feature`, `--template bug`, `--template cleanup`, `--template docs`, `--template test-baseline`, and `--template release-prep`.

Generated projects can also include a repo-local Agent Kit Codex skill. Inside Codex, `$agentkit` is a skill invocation, not a custom slash command:

```text
$agentkit implement Add your feature idea here
$agentkit fix Describe the bug here
$agentkit plan Describe the project change here
```

The skill does not send keystrokes, run a daemon, modify `~/.codex/config.toml`, contact OpenAI or GitHub by itself, or bypass approvals. It tells Codex to run the local prompt builder, `agent-starter idea-prompt`, read the generated file under `docs/agent-prompts/`, and treat that generated prompt as the task brief. Use `agent-starter codex skill-status`, `update-agentkit-skill`, and `uninstall-agentkit-skill` to inspect or manage the versioned skill sidecar. Restart Codex if a newly installed or updated skill does not appear immediately.

## Optional rootless Podman sandbox

New local projects can include a rootless Podman sandbox. The default sandbox mode keeps Codex on the host and runs project build/test/toolchain commands in a project container. An explicit Codex-inside-container mode generates project-scoped Codex launch scripts and a project-specific Codex home volume.

Generated sandbox files live under `.agent-starter/sandbox/` and `scripts/sandbox/`. They do not mount host `~/.codex`, `~/.ssh`, browser profiles, GitHub credentials, production configs, or the host home directory by default. Container auth uses `scripts/sandbox/codex-login` only when the user deliberately runs it. The starter recommends handoff summaries instead of copying raw Codex sessions or auth files into containers.

Useful generated commands:

```bash
scripts/sandbox/doctor
scripts/sandbox/build
scripts/sandbox/check
scripts/sandbox/shell
scripts/sandbox/codex-login  # only when Codex-inside-container mode was explicitly selected
scripts/sandbox/codex
```

Rootless Podman reduces host filesystem risk, but it does not make untrusted code safe. It can still damage mounted project files and misuse network access when network is enabled. Do not use host `danger-full-access`, do not mount real secrets, and do not deploy, push, or rsync production targets without explicit approval.

If a user wants to attempt continuation with a local Ollama model, check the installed models first:

```bash
agent-starter ollama-check /path/to/project --request "Implement the next planned feature"
```

The check inspects `ollama list` and `ollama show <model> --json` locally, looks for confirmed context length and coding-model signals, and refuses to generate a local-model handoff prompt when the model is inadvisable unless the user passes `--override`. It does not rewrite Codex configuration or add an alternate launcher.

## Runtime requirements

- Python 3.11+
- Bash
- Linux for the complete generated shell workflow
- Git, curl, and CachyOS/Arch `pacman` for the intended local-development path
- OpenAI Codex CLI for AI advice and implementation work
- GitHub CLI only when repository creation is requested

The Python package has no third-party runtime dependencies.

## Development and tests

From the starter-kit source tree:

```bash
./scripts/check.sh
```

That command performs Python syntax checks, the unit/integration suite, shell syntax validation, CLI smoke checks, fresh-project generation and validation, generated-project checks, and an isolated install/uninstall test. It deliberately does not access a real OpenAI account, run OAuth, invoke network installers, use `sudo`, or publish a repository.

## Project layout

```text
agent_starter/
  agents.py       Codex CLI boundary and structured advisor call
  cli.py          commands, validation, authorization, launch, GitHub setup
  codex_skill.py  repo-local Agent Kit skill rendering/status/update helpers
  generator.py    safe rendering, writes, conflict handling, validation
  idea_prompts.py local prompt-file builder used by the $agentkit skill
  models.py       serializable project configuration
  templates.py    generated project files and documentation
  toolchains.py   language/database mappings for CachyOS and CI
  wizard.py       beginner-oriented interactive setup
docs/              maintainer documentation and implementation memory
examples/          reviewed Codex-only answer files
scripts/           source checks, generation smoke test, install smoke test
tests/             standard-library unittest suite
```

## License

MIT. See `LICENSE`.
