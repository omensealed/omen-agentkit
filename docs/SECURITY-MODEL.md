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
