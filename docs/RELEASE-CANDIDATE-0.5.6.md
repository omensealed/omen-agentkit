# Omen AgentKit 0.5.6 corrective release candidate evidence

## Scope

This local unpublished corrective candidate prevents incomplete GUI task-composer answers from reaching the canonical
backend validator. Compose Task remains unavailable until the task schema is ready and every required answer for the
selected starting choice is nonblank. The interface explains that gate, marks required controls, and recomputes the
state after input, choice changes, and draft resume. A local guard reveals and focuses a missing guided decision before
compose or approval; backend validation remains authoritative and unchanged.

The prior behavior failed closed with a task validation error and performed no project write, command, approval,
launch, or release. Version 0.5.6 is aligned in all four source owners and Unreleased is empty. Immutable v0.5.5 and
its release assets remain unchanged.

## Expected artifacts

- `cli_ai_agent_starter_kit-0.5.6-py3-none-any.whl`
- `cli_ai_agent_starter_kit-0.5.6.tar.gz`
- `SHA256SUMS`
- `release.spdx.json`

Artifact digests are generated beside the exact candidate and are intentionally not hard-coded into source. The wheel
and sdist must pass isolated no-index import, CLI help, generation, validation, and GUI asset-discovery smoke before any
publication decision.

## Compatibility and safety

Compatibility shims remain required through 0.5.6 and the following minor stable release. Task definitions and packet
semantics, CLI behavior, partial-draft persistence, the standard-library runtime, Sol model policy, schema migration,
safe writes, approval gates, sandbox/network restrictions, OAuth ownership, and deployment stop boundary remain
unchanged. No raw bridge exception, traceback, or submitted answer is added to the new guidance path.

## Release boundary

Use a new immutable `v0.5.6`, verification-only dispatch, and separate publication dispatch. The workflow must fail
closed on any ref/version/dirtiness/checksum/smoke mismatch; no local or remote release was created by candidate
preparation. Only the separately authorized publication job may create and publish the exact verified assets.
