# Human start

This is the shortest path from an AgentKit checkout to a first reviewed Codex task. For the complete walkthrough, use the [user guide](USER-GUIDE.md).

## Install or run locally

AgentKit needs Python 3.11 or newer and Bash. It does not need `sudo`.

```bash
./agent-starter doctor
./agent-starter new --mode guided
```

To make `agent-starter` available from your user account, run `./install.sh`, then `agent-starter doctor`. The installer writes only to the user data and binary directories. It does not install system packages or authorize Codex.

## Create the first project

Run the guided flow above, review the proposed location and settings, and generate the workspace. Existing owner files are not silently replaced: conflicts become proposals unless you explicitly request replacement, in which case AgentKit creates a backup first.

In the generated project, read `START_HERE.md`, then run:

```bash
./scripts/check.sh
./scripts/agent-status.sh
```

Authorize through the official Codex CLI only when you are ready. AgentKit never asks for or reads OAuth tokens, API keys, browser data, or keyring contents.

## Prepare the first task

Use the generated `FIRST_PROMPT.md`, or create a smaller reviewed task:

```bash
agent-starter prompt /path/to/project --interactive
```

Review and approve the task contract before copying the prompt. Approval releases text only; it does not launch Codex, execute commands, push, publish, or deploy. The generated `AGENTS.md` is the binding project contract.

## Common repairs

- If host readiness is unclear, rerun `agent-starter doctor`. It performs provider-specific read-only checks and prints remedies; it does not install packages.
- If generation or a manual edit may have made the workspace inconsistent, run `agent-starter validate /path/to/project` and the project-local `./scripts/check.sh`.
- If an owner file conflicts, review the proposal reported by generation. Do not copy it over the owner file until the difference is understood. Forced replacement is a separate explicit action with a backup.
- If sandbox checks fail, run the generated `./scripts/sandbox/status` and `./scripts/sandbox/doctor` from a normal host terminal. Do not silently substitute unrestricted host execution.
- If Codex is missing or unauthorized, run `agent-starter auth --status` and follow its official-CLI remedy. Do not paste credentials into AgentKit.
- If an answers file is schema v1, preview with `agent-starter config migrate --input SOURCE`; write only to a separate path with `--output DESTINATION`.

For supported hosts and package-source boundaries, see [supported hosts](SUPPORTED-HOSTS.md). For every safety boundary, see the [security model](SECURITY-MODEL.md).
