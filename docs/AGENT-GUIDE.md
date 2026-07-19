# Agent guide

This is the concise source-repository routing index for Codex. The root `AGENTS.md` is binding; this page does not replace it. In a generated project, use that project's `AGENTS.md` and `docs/AGENT-INDEX.md` instead.

## Contracts

- Preserve user changes, public commands/imports, standard-library runtime, strict schema behavior, and conflict/proposal/backup safety.
- Never inspect credentials or weaken approval, workspace-write, command-network, sandbox, path, symlink, or atomic-write controls.
- Add or adjust regression coverage with the smallest cohesive implementation change. Run focused tests, then `./scripts/check.sh` before completion.
- Update [implementation notes](IMPLEMENTATION-NOTES.md), [progress](PROGRESS.md), and the active phase ledger when behavior or contracts change.
- Planning, local checking, and deterministic local artifact building do not authorize remote apply, push, publication, database migration, or secret access.

## Read only what the task needs

| Task | Canonical source documentation |
| --- | --- |
| Architecture or module boundary | [Architecture](ARCHITECTURE.md), [structure policy](STRUCTURE-POLICY.md) |
| Answers, models, validation, migration | [Answers-file reference](ANSWER-FILE-REFERENCE.md), [migration status](GPT-5.6-SOL-MIGRATION-STATUS.md) |
| Providers, packages, sandbox images | [Supported hosts](SUPPORTED-HOSTS.md), [security model](SECURITY-MODEL.md) |
| Codex auth, launch, prompts, tasks | [Codex integration](AGENT-INTEGRATION.md), [user guide](USER-GUIDE.md) |
| Templates or generated contracts | [Template catalog](TEMPLATE-CATALOG.md), [architecture](ARCHITECTURE.md) |
| Tests or release | [Development](DEVELOPMENT.md), [release safety](RELEASE-SAFETY.md), [supply-chain policy](SUPPLY-CHAIN-POLICY.md) |
| Deployment or operations | [Operations guide](OPERATIONS-GUIDE.md), [security model](SECURITY-MODEL.md) |

Before editing, inspect `git status`, the current branch/revision, and the existing diff. Do not reset, clean, stash, or overwrite protected work. Stop when the authorized task is complete.
