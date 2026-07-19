"""Generated release, operations, contribution, and security governance."""

from __future__ import annotations

from ..deployment import list_deployment_contracts
from ..deployment_ci import DEPLOYMENT_CI_POLICY
from ..deployment_secrets import list_secret_contracts
from ..models import ProjectConfig
from ..toolchains import DATABASE_COMMANDS
from .common import clean, inline_list


def render_release_checklist(config: ProjectConfig) -> str:
    return clean(
        f"""
        # Release checklist

        ## Product and quality

        - [ ] Release scope and acceptance criteria are explicit.
        - [ ] `./scripts/check.sh` passes from a clean checkout.
        - [ ] Core user journey and important failure paths are tested.
        - [ ] Known limitations are documented and acceptable.
        - [ ] Version, changelog, help/about output, and package metadata agree.

        ## Security and data

        - [ ] Secret and sensitive-file scan completed; no production data in artifacts.
        - [ ] Threat model and dependency review current.
        - [ ] Authentication/authorization/validation controls tested where applicable.
        - [ ] Database/file-format migration and rollback tested where applicable.
        - [ ] Logs and errors contain no credentials or unnecessary personal data.

        ## Packaging and operations

        - [ ] Target artifacts produced: {inline_list(config.packaging_targets)}.
        - [ ] Fresh install tested on a clean supported environment.
        - [ ] Upgrade and uninstall/cleanup behavior tested.
        - [ ] Backup/restore and recovery steps tested where durable data exists.
        - [ ] Checksums/signatures or release provenance generated where the distribution channel supports them.

        ## Documentation and handoff

        - [ ] README, setup, usage, configuration, troubleshooting, and operations docs current.
        - [ ] Progress, decisions, implementation notes, and agent handoff current.
        - [ ] GitHub Actions passes on the release commit when enabled.
        - [ ] Human reviewer approves publishing/deployment; agents do not publish autonomously.
        """
    )


def render_operations_doc(config: ProjectConfig) -> str:
    return clean(
        f"""
        # Operations and maintenance

        ## Development runbook

        ```bash
        ./scripts/doctor.sh
        ./scripts/check.sh
        ./scripts/run.sh
        ```

        Replace placeholder behavior with exact commands during Phase 0.

        ## Data operations

        Database mode: **{config.database}**

        {DATABASE_COMMANDS.get(config.database, DATABASE_COMMANDS['undecided'])}

        Before release, document schema initialization, migration, backup, restore verification, retention, corruption
        recovery, and rollback. Test these against disposable development data.

        ## Logging and diagnostics

        - Log operation identifiers and useful context, not secrets or full sensitive payloads.
        - Separate user-facing messages from diagnostic detail.
        - Bound log retention and file growth for long-running applications.
        - Add a documented diagnostic command or checklist that does not expose credentials.

        ## Dependency maintenance

        Review updates in small batches. Read release notes, inspect lockfile deltas, run the complete gate, and avoid
        combining major upgrades with feature work. Record compatibility changes and rollback steps.

        ## Incident checklist

        1. Stop further damage without destroying evidence.
        2. Preserve relevant redacted logs and exact versions.
        3. Revoke/rotate exposed credentials outside the repository.
        4. Restore from a verified backup or roll back through the documented path.
        5. Add a regression test and implementation-note entry.
        6. Update threat model, operations docs, and release criteria.
        """
    )


def render_deployment_doc(config: ProjectConfig) -> str:
    ci_policy = DEPLOYMENT_CI_POLICY
    target_rows = "\n".join(
        f"| `{contract.target.value}` | {contract.display_label} | {contract.artifact_kind} | {', '.join(operation.value for operation in contract.enabled_operations)} |"
        for contract in list_deployment_contracts()
    )
    secret_rows = "\n".join(
        f"| `{contract.mechanism}` | {contract.reference_convention} | {contract.existence_check} |"
        for contract in list_secret_contracts()
    )
    return clean(
        f"""
        # Deployment planning

        ## Authority and maturity

        No deployment target is selected or approved by generation. This is Stage A documentation only. The
        canonical deployment policy in `AGENTS.md` remains binding: a prompt, generated document, or successful local
        check grants no publication, push, remote-write, migration, credential, staging, or production authority.
        `agent-starter deployment plan` can now render a local digest-bound plan after fixed read-only source-state
        inspection. `agent-starter deployment check` verifies bounded local evidence from that immutable JSON plan.
        Neither command executes profile/project commands, accesses credentials, contacts a target, or writes remotely.
        `deployment build` adds deterministic local ZIP assembly for static-site and Linux-service-bundle plans only.
        The fail-closed apply-gate state model can explain missing or stale prerequisites, but no apply-capable target
        adapter, apply command, authentication adapter, or audit writer is available here.

        Packaging intent: {inline_list(config.packaging_targets)}

        ## Supported target contracts

        | Exact target ID | Display label | Artifact intent | Current operation |
        | --- | --- | --- | --- |
        {target_rows}

        These contracts do not imply generic cloud or Kubernetes support. Target IDs must be exact, and each future
        adapter needs its own tests and authority review.

        ## Create an immutable local plan

        Create a reviewed project-local JSON profile with exactly these fields. This illustrative static-site profile
        is not a selected default; change the exact target, environment, identifiers, effects, and evidence to match
        the project. Commands are argv data for display only and are never executed by `deployment plan`.

        ```json
        {{
          "schema_version": 1,
          "target": "static-site",
          "environment": "staging",
          "target_identifier": "docs-staging",
          "artifact_output": "dist/site.zip",
          "local_writes": ["dist/site.zip"],
          "remote_writes": [],
          "commands": [["./scripts/build.sh"]],
          "network_destinations": [],
          "credential_references": [],
          "health_checks": ["Inspect the staged artifact and require the expected page."],
          "rollback_steps": ["Restore the previously recorded artifact digest."]
        }}
        ```

        Render to standard output, or atomically create one new project-confined file:

        ```bash
        agent-starter deployment plan . --profile deployment-target.json --format text
        agent-starter deployment plan . --profile deployment-target.json --format json \\
          --output .agent-starter/deployment-plans/staging.json
        ```

        The plan records the project Git revision/state, target identity, artifact, every declared local/remote write,
        display-only argv, network destination, credential reference mechanism, health check, rollback step, its own
        output location, and the SHA-256 digest of canonical plan JSON. Existing output is never replaced. A dirty,
        unavailable, or parent-repository source state is recorded rather than hidden; later checks may block it.

        ## Run the local read-only check

        Save the JSON plan to a new project-confined file, then inspect local evidence without changing the project or
        target:

        ```bash
        agent-starter deployment check . \\
          --plan .agent-starter/deployment-plans/staging.json --format text
        agent-starter deployment check . \\
          --plan .agent-starter/deployment-plans/staging.json --format json
        ```

        The check validates the plan digest/schema, project identity and structure, source revision/dirty-state policy,
        a confined artifact SHA-256, declared health/rollback completeness, and whether remote effects require later
        evidence. It deliberately does not run project tests or build commands. Artifact reproducibility passes only
        when the local builder's embedded double-assembly provenance and every payload/SPDX checksum verify; one bare
        checksum remains insufficient. Target identity, credential-reference existence, backup readiness, and
        target-side least privilege remain `unverified` when proving them requires a later reviewed mechanism. Any
        unverified item keeps the report non-ready with exit status 1. Invalid/tampered input returns 2. A check report
        never authorizes apply.

        ## Assemble a deterministic local artifact

        For a static-site or Linux-service-bundle plan recorded from an exactly matching clean Git revision, select
        one dedicated reviewed build-output file or directory. The local builder does not run `scripts/build.sh` or any
        profile command; produce that input separately under explicit human review. The plan must declare a new `.zip`
        `artifact_output` in `local_writes`.

        ```bash
        agent-starter deployment build . \\
          --plan .agent-starter/deployment-plans/staging.json \\
          --source public --format text
        ```

        Assembly refuses the project root, traversal, symlinks, special files, credential-prone paths, more than 10,000
        files, more than 32 MiB of input, an existing output, and unsupported OCI/SSH targets. It creates the planned ZIP
        atomically after two equal in-memory assemblies. Normalized metadata, per-file SHA-256 values, the plan/source
        binding, display-only profile argv, AgentKit/Python/ZIP tool versions, and an SPDX-2.3 file inventory are embedded.
        Success performs one declared local artifact write only; it never triggers network access, push, target contact,
        remote write, staging/production change, or apply.

        ## Model the fail-closed apply gate

        The source apply-gate model requires all of these exact bindings before a future separate apply operation may
        even be considered: a reviewed apply-capable target adapter, current plan digest, complete passing check report,
        reproducible artifact and reviewed artifact digest, explicit environment and target identifier, human
        authentication through the target tool, exact typed confirmation from a separate local human-input boundary,
        available rollback, and a closed redacted local audit event. A plan, artifact, environment, or target change
        invalidates prior review and confirmation.

        Every current target remains blocked because no apply adapter is enabled or production-ready. The state model is
        pure evaluation: it runs no command, reads no credential, contacts no target or network, writes no audit log,
        and performs no apply. There is deliberately no `deployment apply` CLI command. Free-form prompt or model text
        cannot satisfy typed confirmation, authentication, adapter, check, rollback, or audit evidence.

        ## Rehearse disposable staging and rollback

        AgentKit includes one static-site disposable staging adapter for maintainer command-state tests only. It has no
        public rehearsal or apply CLI command and no generated-script entry point. The adapter stores only an artifact
        digest in memory, executes no profile or free-form command, opens no artifact or credential, and performs no
        filesystem, network, remote, hosting, or production change.

        A rehearsal accepts only an exact clean staging plan, its complete passing digest-bound check set, and the
        exact reviewed reproducible artifact digest. Wrong targets, production, dirty source, stale plan/artifact
        evidence, failed or missing tests/checks, and missing health or rollback declarations are rejected before the
        disposable state changes. Successful and injected partial-failure paths always restore the exact prior
        in-memory artifact state and emit closed redacted value-free audit metadata. This proves rollback state-machine
        behavior only; it does not prove a hosting provider, authentication, remote health check, or production apply.

        The static-site contract alone advertises this disposable rehearsal. It still does not enable `apply`, and
        production remains disabled for every target. A real staging adapter would require a separate architecture,
        threat-model, authentication, confinement, audit-persistence, and human-approval review.

        ## Environments and ownership

        | Environment | Exact target identity | Owner | Current state |
        | --- | --- | --- | --- |
        | Local development | Record before planning | Project maintainer | Local validation only |
        | Staging | Not configured | Assign a human operator before enablement | Disabled |
        | Production | Not configured | Assign a separate accountable human owner | Disabled |

        Never infer an environment from a hostname, branch, prompt, or cached plan. Record the exact environment and
        target identity and require a separate human review whenever either changes.

        ## Build artifact and provenance

        Before a later plan can be approved, record the source revision and dirty state, selected artifact kind,
        complete local inputs and outputs, reproducible build/check commands, tool versions, and artifact digest.
        A successful build must not trigger a push or apply.

        ## CI/CD identity and artifact provenance

        Deployment jobs remain absent and disabled in this generated workflow. A future reviewed adapter for a
        supported cloud target must use GitHub OIDC short-lived identity; long-lived static cloud credentials are not
        allowed. Keep the ordinary build/check workflow at `{ci_policy.build_permissions[0]}`. Grant
        `{ci_policy.future_deploy_permissions[1]}` only on that future deploy job, never at workflow scope.

        Pin every GitHub Action to a reviewed full 40-character commit SHA and retain the release version in a comment
        for human review. Use separate build and deploy jobs and separate environments. Use a protected production environment
        with required manual approval by an accountable human. The deploy job must consume the
        exact reviewed artifact from the build job and attach both a SHA-256 checksum and an artifact attestation bound
        to its source revision. A checksum or attestation does not grant apply authority, and neither may be generated
        by contacting a target from the current local-only deployment commands.

        ## Configuration and secret references

        Document configuration names, owning platform, expected scope, and reference names—never secret values.

        | Mechanism | Reference convention | Value-free existence behavior |
        | --- | --- | --- |
        {secret_rows}

        For `environment-file`, reference `name` means `.env.<name>` at the project root. `deployment check` uses file
        metadata plus quiet local Git-ignore status only: the reference must be a regular non-symlink file ignored by
        Git with owner-only mode `0600`. It never opens the file. For `ssh-agent`, the check verifies only that the
        `SSH_AUTH_SOCK` reference names a socket; it never lists or inspects keys. OS-keyring, CI-store, and target-store
        references remain `unverified` until a reviewed metadata-only adapter exists; the check never contacts them.

        Create, populate, rotate, revoke, and delete references outside AgentKit. Do not place values in answers JSON,
        target profiles, immutable plans, generated docs, prompts, logs, argv, artifacts, provenance, SBOMs, manifests,
        Git, or implementation notes. A missing/unsafe reference is reported by safe name and stable code only. Never
        print, prompt for, read, copy, hash, compare, transmit, or persist a value merely to prove existence.

        ## Data migration and backup

        State whether the target has durable data. Before any future apply, document compatible schema/file-format
        versions, a tested backup and restore procedure, migration ordering, retention, destructive effects, and the
        point at which rollback is no longer safe. Use disposable data for rehearsal; production data is out of scope.

        ## Health and smoke checks

        Define non-mutating readiness and post-change checks, expected results, time bounds, and failure thresholds.
        Identify who judges success. A missing or failing health check blocks any later apply gate.

        ## Rollback and recovery

        Name the prior artifact/configuration, exact recovery steps, backup dependency, responsible human, expected
        recovery time, and verification evidence. Rollback must be rehearsed in staging before production is considered.

        ## Monitoring, logs, and maintenance

        Record log and metric locations by reference, retention/redaction rules, alert owner, incident contact,
        routine maintenance owner, patch cadence, and end-of-life responsibility. Logs must not expose credentials,
        secret values, unnecessary personal data, raw prompts, or production payloads.

        Keep deployment decisions in `docs/10-DECISIONS.md`, current work in `docs/09-PROGRESS.md`, exact session
        evidence in `docs/11-IMPLEMENTATION-NOTES.md`, and unresolved ownership or target questions in
        `docs/15-OPEN-QUESTIONS.md`.
        """
    )


def render_contributing(config: ProjectConfig) -> str:
    return clean(
        f"""
        # Contributing to {config.project_name}

        Read `docs/AGENT-INDEX.md` first, then `AGENTS.md` and the matching task row's relevant files. Keep changes
        focused, add or update tests for behavior changes, run `./scripts/check.sh`, and update the implementation
        ledger and relevant documents.

        Do not include secrets, production data, generated databases, build outputs, or unrelated formatting changes.
        Open a decision record before changing architecture, persistent formats, public interfaces, or production dependencies.
        """
    )


def render_security_policy(config: ProjectConfig) -> str:
    return clean(
        f"""
        # Security policy

        Do not open a public issue containing a live exploit, credential, personal data, or production dump.
        Until a private reporting channel is configured, contact the repository owner privately and include the minimum
        reproduction needed. Never test against systems or data you do not own or have permission to assess.

        See `docs/06-SECURITY.md` for the project's working threat model and release gate.
        """
    )
