# Security model

## Protected assets

- Existing source code and project documentation.
- User account authorization, OAuth artifacts, API keys, keyrings, browser state, and cookies.
- Local files outside the selected project root.
- System package-manager authority and `sudo` access.
- Git history, remotes, repositories, deployments, and production data.
- Integrity of generated commands, tests, project metadata, and implementation notes.

## Main threats and controls

### Existing-file destruction

Generated destinations are validated as safe relative paths. Filesystem root and the home directory itself are rejected as project roots. Parent-directory symlinks are rejected, writes are atomic, unchanged content is retained, conflicts become proposals, and forced replacements create timestamped backups first.

### Model-output command injection

Codex stack advice runs in an empty temporary directory with a read-only sandbox and a strict JSON output schema. Responses are parsed as data, normalized, displayed for review, and not automatically executed. Raw advisor output is removed from persisted project metadata.

Answers-file command arrays require `--allow-custom-commands`. Interactive setup and generated bootstrap scripts show commands before privileged execution.

### Credential capture

The kit never asks for tokens or passwords and rejects common credential-like answer strings. OAuth is executed by the official `codex` command; status checks use `codex login status` and never inspect its storage. Generated instructions prohibit secrets in prompts, source files, logs, tests, and repositories.

### Package-manager authority

CachyOS package names are validated. The default bootstrap mode prints the plan only. `sudo pacman` is reached only through an explicit `--install` action after the user reviews the generated script. Automated tests never invoke it.

### Codex overreach

Generated `.codex/config.toml` uses workspace-write sandboxing and on-request approval. Generated instructions prohibit unrelated paths, credential stores, permission-bypass options, destructive migrations, remote pushes, repository publication, deployment, and irreversible operations without human approval.

The optional repo-local `$agentkit` skill is a local prompt-building workflow only. It does not send keystrokes into an open terminal, run a daemon, add MCP/app-server/plugin automation, call OpenAI or GitHub, inspect Codex credentials, modify `~/.codex/config.toml`, start `codex login`, or bypass Codex approvals. Skill updates are managed through a versioned JSON sidecar and backed up before replacement.

### Rootless Podman project sandbox

Optional sandbox generation separates three layers:

- Codex's own sandbox: `read-only`, `workspace-write`, and other official Codex approval modes.
- Rootless Podman project container: container filesystem plus the project bind mount at `/workspace`.
- Host system: not mounted except for the selected project workspace and explicit local artifacts.

The generated sandbox does not mount host `~/.codex`, `~/.ssh`, browser profiles, GPG/SSH agents, GitHub credentials, production configs, or the host home directory by default. Codex-inside-container mode uses a project-specific Codex home volume and requires the user to run `scripts/sandbox/codex-login` deliberately. The scripts must not capture device codes or tokens and must not inspect Codex credential files.

Rootless Podman reduces host filesystem risk, but untrusted code can still modify mounted project files and can misuse network access if networking is available. Generated docs prohibit `--dangerously-bypass-approvals-and-sandbox`, host full-access as the default permission answer, production secret mounts, deployment, rsync to production, GitHub pushes, and remote resource creation without explicit approval.

Host Codex session/history import is not automatic. Generated projects prefer a no-secrets handoff summary in `docs/CODEX-HANDOFF.md` over copying raw session transcripts or auth files into the container.

### Local-model overreach

Ollama support is limited to a local readiness check and warning-rich handoff prompt. The starter inspects installed model metadata and refuses inadvisable handoff prompts unless the user passes `--override`. It never pulls models, installs packages, sends repository content to Ollama, executes local-model output, rewrites Codex configuration, or changes project metadata away from Codex.

### Repository and network side effects

Git initialization is local and creates no commit. GitHub Actions are deferred by default so local setup and tests can prove the project before CI noise is introduced. GitHub repository creation is optional, uses the official `gh` client, and does not push code. Network access, account handling, payments, and personal-data requirements are captured in the project security docs and phase plan.

## Residual risks

- Users can manually approve unsafe commands or weaken generated Codex settings.
- Third-party compilers, package repositories, GitHub Actions, and Codex itself remain external trust dependencies.
- A model can produce incorrect code even inside a sandbox; tests and human review remain necessary.
- Existing projects may contain their own malicious build scripts or instruction files; Codex and the user must inspect them before execution.
- Authorization status proves that Codex reports a session, not which human account is intended; the user must verify the account in the official login experience.
- Backups stored inside a project can still be deleted by later manual action; source control and external backups are recommended for valuable projects.
