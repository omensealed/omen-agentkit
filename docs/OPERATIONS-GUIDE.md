# Operations guide

AgentKit currently supports reviewable local deployment evidence, not deployment execution. There is no `deployment apply` command and no production-ready target adapter. Free-form instructions such as “deploy it” do not grant authority.

## Plans and local evidence

Generated `docs/16-DEPLOYMENT.md` is the project-specific operations owner. The source [user guide](USER-GUIDE.md#13-create-an-immutable-deployment-plan) explains the local flow:

```bash
agent-starter deployment plan /path/to/project --profile deployment-target.json --format text
agent-starter deployment check /path/to/project --plan deployment-plan.json --format text
agent-starter deployment build /path/to/project --plan deployment-plan.json --source public --format text
```

These commands parse reviewed project-local inputs, bind evidence by digest, inspect bounded local state, and may create a deterministic local artifact. They do not run project/profile commands, contact a target, authenticate, push, publish, or apply. Their results do not authorize deployment; a passing report is evidence only.

## Rollback and rehearsal

A plan must declare health and rollback intent. The current static-site staging rehearsal is a disposable in-memory maintainer test: it rejects production and stale evidence, injects failure coverage, and proves restoration of the prior digest. It has no CLI, filesystem target, remote target, or production path. See [architecture](ARCHITECTURE.md) for module ownership and the [security model](SECURITY-MODEL.md) for the exact trust boundary.

## Secret references

Deployment configuration stores reference names only. Environment-file and SSH-agent checks inspect bounded metadata; they do not open secret files or list keys. External keyring, CI-store, and target-manager references remain unverified. Never place a secret value in answers, plans, logs, artifacts, prompts, or audit records.

## Audit and release boundary

Use `agent-starter audit-context /path/to/project` for advisory generated-context structure review. Keep deployment plan/check/build digests, clean source identity, health/rollback declarations, and redacted events as local review evidence. Audit metadata must remain bounded and secret-free.

Production apply would require a separately reviewed adapter and operation, exact target identity, human target-tool authentication, current digest-bound evidence, explicit local confirmation, rollback, and redacted audit metadata. Those requirements are modeled fail-closed but are not implemented as an executable route. Publication is governed separately by [release safety](RELEASE-SAFETY.md) and [supply-chain policy](SUPPLY-CHAIN-POLICY.md).
