# End-to-end user journeys

Run the focused P8-001 gate from the source root:

```bash
./scripts/end-to-end-journey-check.sh
```

The runner first executes the existing isolated user-local install/reinstall/uninstall smoke with temporary `HOME` and XDG roots and no `sudo`. It then runs one complete temporary-project journey for each reviewed host family:

- CachyOS/Arch using the checked-in CachyOS `os-release` fixture and Arch provider;
- Debian using the checked-in Debian fixture and Debian provider;
- Ubuntu using the checked-in Ubuntu fixture and Ubuntu provider.

Each journey proves structured doctor output, deterministic and synthetic strictly parsed AI-assisted recommendations, provider-owned availability/installed-state review, creation and validation, generated local checks, feature/fix task contracts with explicit prompt approval, GPT-5.6-SOL/medium launch preview without launch, optional rootless-Podman project output without preflight, immutable local deployment plan/check/build evidence, and schema-v1 migration with Arch-only `cachyos_packages` preservation.

The host package runners are injected synthetic read-only boundaries. Install plans are inspected as argv data and are never executed. The advisor response is synthetic strict JSON and no Codex process is invoked. Deployment remains local plan/check/build only: advertised commands are not executed, targets are not contacted, and apply remains unauthorized. Sandbox output is inspected without running Podman. The only subprocesses are the repository-owned isolated installer smoke and generated local `scripts/check.sh` inside temporary workspaces.

This automated gate proves deterministic behavior for the three supported provider identities; it does not claim a real package install, real Codex authorization/session, container image pull, remote deployment, or production burn-in. P8-005 owns human release-candidate burn-in and user-submitted issue evidence.
