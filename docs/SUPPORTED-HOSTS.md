# Supported Linux host matrix

AgentKit supports three package-provider identities across four representative host families. Detection reads bounded `ID` and `ID_LIKE` values from `/etc/os-release` before checking for the matching package-manager executable.

| Host family | Provider identity | Required proof | Official rootless Podman packages |
|---|---|---|---|
| CachyOS | `arch` | `pacman` | `podman`, `passt`, `fuse-overlayfs` |
| Arch Linux | `arch` | `pacman` | `podman`, `passt`, `fuse-overlayfs` |
| Debian | `debian` | `apt-get` and `dpkg-query` | `podman`, `uidmap`, `slirp4netns`, `fuse-overlayfs` |
| Ubuntu | `ubuntu` | `apt-get` and `dpkg-query` | `podman`, `uidmap`, `slirp4netns`, `fuse-overlayfs` |

Executable presence never overrides contradictory or unsupported OS metadata. Fedora and other unsupported families receive an actionable error and no package-manager probe. A reviewed `--platform-provider arch|debian|ubuntu` or generated-bootstrap `--provider` override still has to prove the matching manager exists, and any contradiction remains visible.

## Package and repository policy

Provider-neutral configuration stores capability IDs, not package names. Each provider owns its official-package mapping. Migrated v1 `cachyos_packages` remain Arch-only; provider extras never cross into another provider's plan.

- CachyOS/Arch plans use configured official pacman repositories. AUR suggestions remain manual, unverified, and non-installable by AgentKit.
- Debian/Ubuntu plans use already configured official APT sources. AgentKit does not add PPAs, signing keys, source entries, or pinning.
- Default bootstrap is read-only and prints a plan. `--install` is explicit. Debian/Ubuntu index refresh is a separate `--refresh`; no full-system upgrade is part of bootstrap.
- Advisor or saved command text is printed for review and never becomes a package-manager or shell command automatically.

## Matrix verification

`tests/test_provider_matrix.py` uses checked-in CachyOS, Arch, Debian, Ubuntu, and unsupported Fedora fixtures plus `tests/fixtures/provider-package-plans.json`. Normal checks generate and validate representative Debian and Ubuntu projects without installing packages or requiring containers.

The optional container check is disabled by default. The source CI preloads the official Arch and Debian base images
in an explicit step; a local runner may enable the check only when those images are already present:

```bash
AGENTKIT_RUN_CONTAINER_MATRIX=1 AGENTKIT_CONTAINER_RUNTIME=podman \
  python3 -m unittest tests.test_provider_matrix.PreloadedContainerMatrixTests -v
```

Set the runtime to `docker` only on a reviewed Docker-based CI runner. The check generates and validates one
representative project per provider on the Python runner, then mounts it read-only and invokes only the default
bootstrap plan inside the matching container. Container execution uses `--pull=never`, `--network=none`, dropped
capabilities, and no-new-privileges. It verifies provider proof and review-only output; it does not install, refresh, or
update packages. Missing preloaded images are skipped rather than pulled implicitly.
