# Omen AgentKit 0.5.5 corrective release candidate evidence

## Scope

This local unpublished corrective candidate fixes the GUI task-composer bridge-readiness race reported after v0.5.4.
The task selector now waits for pywebview's supported readiness event, retains an already-ready fallback, and shows a
bounded loading/error state. It does not change task definitions, validation, approvals, generation, or Codex launch.

The prior behavior failed closed by leaving the selector empty; no project write, command, launch, or release was
created by that failure. Version 0.5.5 is aligned in all four source owners and Unreleased is empty.

## Expected artifacts

- `cli_ai_agent_starter_kit-0.5.5-py3-none-any.whl`
- `cli_ai_agent_starter_kit-0.5.5.tar.gz`
- `SHA256SUMS`
- `release.spdx.json`

Artifact digests are generated beside the exact candidate and are intentionally not hard-coded into source. The wheel
and sdist must pass isolated no-index import, CLI help, generation, validation, and GUI asset-discovery smoke before any
publication decision.

## Compatibility and safety

Compatibility shims remain required through 0.5.5 and the following minor stable release. The standard-library runtime,
Sol model policy, schema migration, safe writes, approval gates, sandbox/network restrictions, OAuth ownership, and
deployment stop boundary remain unchanged. The GUI error path renders no raw bridge exception or traceback.

## Release boundary

Use a new immutable `v0.5.5`, verification-only dispatch, and separate publication dispatch. The workflow must fail
closed on any ref/version/dirtiness/checksum/smoke mismatch; no local or remote release was created by candidate
preparation. Only the separately authorized publication job may create and publish the exact verified assets.
