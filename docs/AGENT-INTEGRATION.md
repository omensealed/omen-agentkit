# OpenAI Codex integration

## Supported client

This edition integrates only with the official `codex` command. The adapter detects the executable, reports `codex --version`, checks authorization with `codex login status`, starts browser OAuth with `codex login`, and can request device-code authorization with `codex login --device-auth`.

The official installer command exposed by the starter is:

```bash
curl -fsSL https://chatgpt.com/codex/install.sh | sh
```

It is displayed first and executed only after explicit approval. Tests never run the installer or make account/network calls.

## Authorization boundary

The starter never proxies OAuth and never reads Codex credential storage. It launches the official CLI as a child process and uses only its exit status. This keeps account selection, browser authorization, token refresh, revocation, and secure storage inside Codex.

The relevant starter commands are:

```bash
agent-starter auth --status
agent-starter auth
agent-starter auth --device-auth
agent-starter auth --relogin
```

Generated workspaces expose the same boundary through `scripts/setup-agent.sh` and `scripts/agent-status.sh`.

## Read-only stack advisor

When the user asks Codex to recommend a stack, the adapter creates an empty temporary directory, supplies a strict JSON schema, and runs `codex exec` with a read-only sandbox. The response is parsed as JSON, normalized, shown to the user, and never accepted silently. Suggested commands remain text until the user reviews them.

If Codex is unavailable, unauthorized, times out, fails, or returns malformed output, the wizard falls back to deterministic local recommendations based on project type, constraints, and built-in toolchain mappings.

Raw model output is removed before project metadata is persisted.

## Project launch

Interactive launch passes the complete `FIRST_PROMPT.md` content to Codex while setting the generated project as the working directory. One-shot kickoff uses `codex exec` with workspace-write sandboxing. The generated `.codex/config.toml` requests on-demand approval and workspace-limited writes.

The starter does not use permission-bypass flags, auto-publish changes, push Git remotes, deploy software, or grant access outside the selected project.

## Continuation prompts

After the first session, `agent-starter prompt /path/to/project --request "..."` generates a copy/paste Codex prompt for the next focused phase or feature request. It loads only the generated project metadata, not raw credential stores or large project-document excerpts, and tells Codex to read the current project memory inside the sandbox before editing.

The prompt reinforces the Codex-only workflow, phase-sized changes, regression testing, `./scripts/check.sh`, implementation-note updates, handoff updates, and explicit approval requirements for privileged, destructive, credential, publish, deploy, remote-push, or external actions.

## Repo-local Agent Kit skill

Generated projects can include a concise Codex skill at `.agents/skills/agentkit/SKILL.md`. Users invoke it inside Codex with `$agentkit ...` or select it with `/skills`; it is not a custom slash command. The skill is intentionally instruction-only. It does not fake keyboard input, run a daemon, add MCP, modify `~/.codex/config.toml`, contact OpenAI/GitHub, or bypass approvals.

The skill turns a short request into a full implementation brief by telling Codex to run:

```bash
agent-starter idea-prompt --from-codex --arguments "<user request>" --json
```

Codex should pass the user request safely as an argument, read the returned `prompt_path`, and follow that generated prompt as the authoritative task brief. Prompt files are written under `docs/agent-prompts/`.

The skill is versioned by `.agents/skills/agentkit/agentkit-skill.json`, not nonstandard `SKILL.md` front matter. `agent-starter codex skill-status`, `update-agentkit-skill`, and `uninstall-agentkit-skill` inspect and manage only Agent Kit-managed files, with backups before replacement. Users may need to restart Codex if a newly installed or updated skill does not appear immediately.

## Rootless Podman sandbox workflow

Generated projects can optionally include rootless Podman files under `.agent-starter/sandbox/` and `scripts/sandbox/`. The default `toolchain` mode is host Codex editing the local project files, with project build/test/toolchain commands run through Podman against the mounted `/workspace`. Codex-inside-container mode is explicit and uses a project-specific Codex home volume rather than mounting host `~/.codex`.

The source command `agent-starter sandbox doctor /path/to/project` and generated `scripts/sandbox/doctor` check readiness without running `sudo` or installing packages. Missing CachyOS tools are printed as reviewable commands only.

When sandbox metadata exists, `agent-starter idea-prompt` adds sandbox-aware guidance: from the host project root, run `scripts/sandbox/doctor`, build the container, prefer `scripts/sandbox/check`, use database helper scripts such as `scripts/sandbox/db-up` when present, and do not silently replace a requested sandbox check with host checks. If Codex is already running inside the container, it should not run host-side `scripts/sandbox/*` launchers; it should run direct project commands such as `./scripts/check.sh`, `npm test`, or `python3 -m unittest` from `/workspace`. If `doctor`, `build`, or `check` fails on the host, Codex should record the exact failure and stop with `BLOCKED_ENVIRONMENT`, or ask the human whether a temporary host-only fallback is acceptable. Game projects get container-safe headless checks plus host playtesting guidance.

The sandbox workflow does not send keystrokes to a terminal, run Codex login automatically, copy host sessions, mount host SSH keys, create remotes, deploy, or bypass Codex approvals. For container migration, generated projects include `docs/agent-prompts/create-container-handoff.md`, which asks Codex to write a concise no-secrets `docs/CODEX-HANDOFF.md` instead of importing raw session transcripts.

## Ollama readiness check

`agent-starter ollama-check /path/to/project --request "..."` is an assessment and prompt-generation gate for users who want to experiment with a local Ollama model after the Codex workspace exists. It is not an alternate agent adapter, generated launcher, authentication path, or `.codex/config.toml` rewrite.

The command inspects local Ollama metadata with `ollama list` and `ollama show <model> --json`. It looks for confirmed context length and code-capable model signals, then classifies the selected model as suitable, borderline, or inadvisable. Only suitable models produce a local-model handoff prompt by default. Borderline or inadvisable models require `--override`, and the generated prompt keeps the warning in front of the user.

The check never pulls models, installs packages, sends project content to Ollama, executes model output, changes Codex authorization, or launches a local model against the repository.

The warning baseline is Codex's recommended model for complex coding work, currently `gpt-5.5` in the Codex manual. Ollama readiness remains a heuristic based on local metadata, so users should keep local-model tasks narrow even when the gate passes.
