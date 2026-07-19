# Maintainer guide

This page routes maintainers to the canonical design and release owners. It does not restate their policies.

## Architecture and compatibility

- [Architecture](ARCHITECTURE.md) defines module ownership, data flow, trust boundaries, provider seams, schema decisions, and deployment boundaries.
- [Structure policy](STRUCTURE-POLICY.md) defines advisory source/generated modularity signals.
- [Template catalog](TEMPLATE-CATALOG.md) identifies generated-file ownership and compatibility surfaces.
- [Migration status](GPT-5.6-SOL-MIGRATION-STATUS.md) records the protected baseline, compatibility promises, task ledger, exact checks, and blockers.
- [Migration report](GPT-5.6-SOL-MIGRATION-REPORT.md) is the audience-facing v0.4.8 comparison, schema/model/provider guide, and deprecation timeline.

Keep `agent_starter.cli:main`, public commands/imports, schema-v1 loading, and safe conflict/proposal/backup behavior compatible unless a reviewed decision says otherwise.

## Providers and schemas

- [Supported hosts](SUPPORTED-HOSTS.md) owns the CachyOS/Arch, Debian, and Ubuntu support matrix and package-source rules.
- [Answers-file reference](ANSWER-FILE-REFERENCE.md) owns schema-v2 fields, model-policy selection, strict values, and v1 migration behavior.
- [OpenAI Codex integration](AGENT-INTEGRATION.md) owns authorization, launch, recommendation, task, and sandbox integration boundaries.

Provider intent is expressed as canonical capabilities. Preserved v1 `cachyos_packages` remain Arch-family extras and must never be reinterpreted as Debian/Ubuntu package names.

## Security and testing

Read the [security model](SECURITY-MODEL.md) before changing paths, writes, commands, credentials, sandboxing, networking, recommendations, or deployment evidence. The [security regression suite](SECURITY-REGRESSION-SUITE.md) is the focused invariant map.

The normal source gate is:

```bash
./scripts/check.sh
```

Focused commands and test strategy are in [development](DEVELOPMENT.md). In a maintainer workspace, append each meaningful phase and its exact results to the private local `docs/IMPLEMENTATION-NOTES.md` ledger and keep local `docs/PROGRESS.md` current when those files are present. They are intentionally ignored and are not public source-checkout dependencies. Do not install optional tooling merely to make a gate available.

## Release

Read [release safety](RELEASE-SAFETY.md), [supply-chain policy](SUPPLY-CHAIN-POLICY.md), and the [GitHub Actions update policy](GITHUB-ACTIONS-UPDATE-POLICY.md). Ordinary CI cannot publish. Release dispatch is manual, exact-tag-bound, clean-tree-gated, and separates verification from final protected publication authority.

The current corrective candidate evidence is in [0.5.2 release candidate](RELEASE-CANDIDATE-0.5.2.md). Accept burn-in only through the opt-in [user-submitted reporting guide](BURN-IN.md); add no telemetry or background reporting.

Never tag, publish, push, install, deploy, or contact production as an implied maintenance step.
