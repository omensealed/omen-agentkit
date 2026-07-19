# Existing-project compatibility fixtures

Run the focused P8-002 gate from the source root:

```bash
./scripts/existing-project-fixture-check.sh
```

The checked-in catalog at `tests/fixtures/existing-projects/scenarios.json` names seven temporary renovation scenarios:

- a clean Git repository whose owner README is preserved and receives a proposal;
- a dirty Git repository whose uncommitted application change survives generation;
- conflicting README and deployment documentation preserved with separate proposals;
- a symlinked `docs` directory that is refused without writing outside the project;
- schema-v1 AgentKit metadata loaded with `cachyos_packages` retained only as Arch intent;
- a manually edited schema-v2 answers file whose custom test command requires explicit loader approval and is never executed;
- a large mixed-responsibility Python god-file reported by the read-only structure audit while remaining advisory and untouched during renovation.

Every scenario is reconstructed under a temporary directory from synthetic checked-in data. Git repositories use local synthetic identity and create no remote. The suite does not stash, reset, clean, commit user repositories, follow symlinks, force replacement, execute answer-file commands, or change owner source. Structure auditing imports or executes none of the fixture code.

This catalog is regression evidence, not permission to normalize real repositories. New existing-project cases must preserve owner data by default and assert proposals or backups explicitly when generated content differs.
