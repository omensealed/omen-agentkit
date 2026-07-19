# Supply-chain policy

## Scope and authority

Omen AgentKit keeps an empty runtime dependency list and does not install packages during its trusted checks. Supply-chain
automation may propose pull requests, build temporary GitHub Actions artifacts, and attach evidence to GitHub-hosted builds.
Ordinary CI may not auto-merge or publish. The separately manual-and-tag-bound workflow in `docs/RELEASE-SAFETY.md` may
publish only its verified GitHub release assets; it cannot upload to a package index, push a container, deploy, access a
deployment credential, or run on untrusted pull-request code with write authority.

## Dependency and update review

Dependabot proposes weekly GitHub Actions updates and monthly Python metadata/development-extra updates, with at most two
open pull requests per ecosystem and grouped maintainer-tool proposals. These are review requests, not approval. A human
must inspect upstream release notes, the exact diff, compatibility, licenses, runtime changes, and required permissions.
There is no auto-merge configuration.

Every `uses:` reference remains pinned to a reviewed full commit SHA with its release version in a comment. The binding
action review process is in `docs/GITHUB-ACTIONS-UPDATE-POLICY.md`; the offline registry validator must reject an automated
pin change until the registry, evidence, tests, and documentation are reviewed together.

The source provider-container smoke uses reviewed Linux/amd64 digest references for Docker Official Images. Maintainers
must review public manifest metadata and upstream image provenance before changing either digest, record the date and
source in `agent_starter/deployment_ci.py`, and rerun the network-off provider matrix. Generated sandbox profiles retain
their explicit official Arch/Debian tags so users can knowingly rebuild current toolchains; they are never pulled during
generation or ordinary validation.

## Distribution evidence

`python3 -m agent_starter.release_artifacts <new-build-directory>` accepts exactly one regular wheel and one regular
`.tar.gz` source distribution. It refuses symlinked directories/artifacts, special files, ambiguous artifact counts,
oversized files, concurrent substitution, and existing evidence. It creates, without replacement:

- `SHA256SUMS`, covering the wheel and source distribution; and
- `release.spdx.json`, a deterministic SPDX 2.3 artifact SBOM carrying the same SHA-256 identities.

The source CI creates this evidence only after the trusted test job passes on a push to `main` or an explicit workflow
dispatch. It uploads a short-retention workflow artifact and requests GitHub-hosted SLSA provenance for exactly the two
subjects in `SHA256SUMS`. Only that job receives `id-token: write` and `attestations: write`; the workflow default remains
`contents: read`. Pull requests run dependency review but never receive attestation/write permissions. This is build
evidence, not release intent, and no release trigger or publication step exists in this phase.

## Host package sources

Generated host bootstrap plans use only provider-owned official Arch/CachyOS, Debian, or Ubuntu package-manager mappings
by default. They do not add PPAs, AUR helpers, third-party repositories, signing keys, package pins, or source-list edits.
Manual third-party capability records remain non-installable and require a separate human review of source, key,
pinning, removal, and project need. No package command runs during generation, validation, or plan display.

## Verification and rollback

Tests are synthetic and local. They do not execute GitHub Actions, attestations, publication, package installation, or
credential access. If a proposed update fails review, close or revise the pull request; do not weaken permissions, replace
immutable pins with tags, disable evidence validation, or add an unreviewed package source. Preserve prior artifacts and
evidence rather than overwriting them.

## Release boundary

`.github/workflows/release.yml` is manual-only and must be dispatched from the exact existing semantic tag repeated in
its input. Verification is default; publication requires the separate default-off boolean and a successful clean
version/changelog/test/build/exact-artifact-smoke/evidence job. Only the final `release`-environment job receives
`contents: write`; it has no checkout and revalidates the fixed-name downloaded candidate, checksums, exact tag ref, and
current tag-to-dispatch-commit binding before creating a draft and publishing it as the final operation. See
`docs/RELEASE-SAFETY.md` for preparation and failure handling.
