# Release safety

## Binding release intent

The source release workflow is manual-only. It has no push, pull-request, workflow-run, schedule, or ordinary-CI-success
trigger. The operator must select an existing `vMAJOR.MINOR.PATCH` tag in the workflow ref chooser, repeat that exact tag
as `release_tag`, and separately enable the default-off `publish` input. A branch dispatch, malformed/repeatedly mismatched
tag, dirty checkout, or moved tag fails closed.

Repository maintainers should protect release tags and configure the `release` environment with required human reviewers.
The workflow still requires manual tagged intent if that external environment protection is absent; environment review is
an additional repository control, not a substitute for source validation.

## Preparation contract

Before creating or pushing the tag:

1. Update `VERSION`, `pyproject.toml`, `agent_starter.__version__`, and `ProjectConfig.kit_version` together.
2. Move every intended entry from `## Unreleased` beneath exactly one dated `## X.Y.Z — YYYY-MM-DD` heading; finish by
   leaving `Unreleased` empty.
3. Update progress and implementation notes, run `./scripts/check.sh`, and review the complete clean diff.
4. Commit the reviewed source. Create and push the exact tag only as an explicit human release action.
5. In GitHub Actions, choose the exact tag—not a branch—and first consider a `publish: false` verification run.
6. For publication, repeat the manual dispatch with the same selected tag and explicitly choose `publish: true`.

Never clean, reset, stash, or discard protected work merely to satisfy the clean-source gate. Prepare a reviewed commit
normally. The verifier prints stable issue codes and safe remedies without changing source, tags, releases, or credentials.

Local candidate preparation and opt-in user reports follow [the burn-in policy](BURN-IN.md). A dirty-tree local artifact
may be useful for review, but it is not eligible for workflow verification or publication and must retain the
`dirty_release_source` failure. AgentKit adds no telemetry; maintainers act only on reports users deliberately submit.

## Verification and evidence job

The first job has `contents: read`, `id-token: write`, and `attestations: write`; checkout credentials are not persisted.
It verifies exact tag/ref/version/changelog/cleanliness, runs the complete trusted check, builds one wheel and one sdist,
creates no-replace SHA-256/SPDX evidence, and smoke-installs those exact artifacts into isolated no-index environments.
It uploads a fixed-name one-day candidate and creates provenance for the exact subjects in `SHA256SUMS`.

No publication job can start unless this job completes successfully. Test/build code never receives a write-capable token,
deployment credential, package-registry credential, or pull-request secret.

## Publication job

The second job is absent unless `publish: true`. It is the only job with `contents: write`, is bound to the `release`
environment, and uses no checkout or setup action. It downloads only the fixed-name candidate through the reviewed pinned
official action, rechecks `SHA256SUMS`, strictly rechecks tag syntax/ref, and asks GitHub whether the tag still resolves to
the dispatch commit before mutation.

The official GitHub CLI creates a draft release with exactly the wheel, sdist, checksums, and SPDX document, verifies the
existing tag, then publishes the draft as its final operation. An upload failure therefore leaves at most a reviewable
draft rather than silently claiming a complete public release. A rerun never overwrites an existing release automatically.
This workflow does not publish to PyPI, push a container, deploy, migrate data, inspect secrets, or expose a deployment
credential.

## Failure handling

- Validation/test/build/smoke/attestation failure: nothing is published; correct source through a new reviewed commit/tag.
- Candidate transfer/checksum failure: publication does not start.
- Draft asset failure: inspect the draft and workflow evidence; do not script deletion or overwrite as a retry shortcut.
- Tag movement or mismatch: stop, audit tag protection/history, and create new reviewed intent rather than bypassing checks.
- Published-release correction: use an explicit human incident decision; the workflow has no rollback/delete path.
