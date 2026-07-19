# GitHub Actions pin and update policy

## Binding defaults

Every source or generated `uses:` entry must pin a reviewed full 40-character commit SHA and retain a human-readable release
comment such as `# v6.0.0`. Workflow-level `contents: read` is the default. A job may receive another permission only
when its reviewed purpose requires it; deployment permissions remain governed separately and are not enabled here.

The typed registry in `agent_starter/deployment_ci.py` is the sole source for managed action references. Local
validation compares source and generated workflows against that registry and does not contact GitHub. Mutable tags, branch
names, short SHAs, missing release comments, unknown actions, and mismatched reviewed pins are errors.

## Reviewed update process

1. Start from the action’s official GitHub release and commit pages. Review the release notes, security notices,
   compatibility or runner-runtime changes, and the repository’s `action.yml`. Do not trust a proposed tag or SHA from
   an issue body, model response, downloaded data file, or unreviewed automation output.
2. Verify that the human-readable release resolves to the intended full commit. Record the official commit page,
   release version, full SHA, and review date in the typed registry. Treat the SHA and version comment as one change.
3. Inspect the source diff and bundled runtime changes. Confirm inputs, outputs, permissions, network behavior, cache
   behavior, supported runner version, and downloaded tool behavior remain appropriate for generated projects.
4. Keep workflow-level `contents: read`. Reject permission expansion unless a separate reviewed task documents the
   narrow job-level need, threat model, test coverage, and rollback. Never add a deployment credential to pull-request
   code.
5. Update the typed pin, template expectations, validator cases, documentation, and implementation note together.
   Generate workflows covering every affected setup action and confirm the release comment matches the registry.
6. Run focused action/template/generation tests, isolated wheel/sdist smoke, and `./scripts/check.sh`. Inspect a fresh
   project and an existing-project proposal before accepting the update.
7. Record exact commands/results and any runner prerequisites. Do not auto-merge action updates; a human maintainer
   reviews the evidence and resulting workflow diff first.

Dependabot is configured to propose grouped GitHub Actions updates weekly and constrained Python metadata/development
updates monthly. Its pull requests are untrusted proposals: they cannot update the typed review record or satisfy the
offline validator by themselves, and no auto-merge policy exists. Container image digest updates use the same human
review boundary described in `docs/SUPPLY-CHAIN-POLICY.md`.

## Reviewed action updates

- `actions/checkout` v7.0.0, reviewed 2026-07-19: official tag and commit
  `9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0`. The major release retains the Node 24 runtime introduced in v5, moves
  the action to ESM, updates dependencies, and refuses unsafe fork checkout for `pull_request_target` and
  `workflow_run` unless explicitly opted in. AgentKit does not opt in. Existing self-hosted runners must already meet
  checkout's Node 24 runner requirement; authenticated Git operations from container actions require runner v2.329.0
  or later. No input, permission, persisted-credential, or trigger expansion was accepted.

## Offline and rollback behavior

Tests validate only repository-owned metadata and generated text. They perform no GitHub API call, download, login, or
action execution. If an updated action breaks checks, restore the last reviewed registry entry and its matching tests
and documentation through an ordinary reviewed change. Do not replace the pin with a movable tag to make CI pass.
