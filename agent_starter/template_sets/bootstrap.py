"""Provider-specific, review-first generated development bootstrap."""

from __future__ import annotations

import shlex
import textwrap
from typing import Sequence

from ..config_schema import validate_package_identifier
from ..models import ProjectConfig
from ..platforms import arch_packages_for_capabilities, debian_packages_for_capabilities
from ..toolchains import capabilities_for


def _unique(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def _provider_extras(config: ProjectConfig, provider: str) -> tuple[str, ...]:
    values = config.arch_extra_packages if provider == "arch" else config.extra_packages_by_provider.get(provider, [])
    for index, package in enumerate(values):
        issue = validate_package_identifier(package, path=f"extra_packages_by_provider.{provider}[{index}]")
        if issue is not None:
            raise ValueError(issue.message)
    return _unique(values)


def _shell_array(values: Sequence[str]) -> str:
    return " ".join(shlex.quote(value) for value in values)


def render_bootstrap_script(config: ProjectConfig, setup_commands: Sequence[str]) -> str:
    """Render one standalone provider-detecting script with no default mutation."""

    capability_ids = capabilities_for(config.languages, config.database, github=config.github_actions)
    arch_packages = _unique((
        *arch_packages_for_capabilities(capability_ids),
        *_provider_extras(config, "arch"),
    ))
    debian_packages = _unique((
        *debian_packages_for_capabilities(capability_ids, flavor="debian"),
        *_provider_extras(config, "debian"),
    ))
    ubuntu_packages = _unique((
        *debian_packages_for_capabilities(capability_ids, flavor="ubuntu"),
        *_provider_extras(config, "ubuntu"),
    ))
    setup_lines = "\n".join(
        f"printf '%s\\n' {shlex.quote(command)}" for command in setup_commands
    ) or "printf '%s\\n' 'No project setup command has been finalized yet.'"
    rendered = fr"""
        #!/usr/bin/env bash
        set -euo pipefail

        ARCH_PACKAGES=({_shell_array(arch_packages)})
        DEBIAN_PACKAGES=({_shell_array(debian_packages)})
        UBUNTU_PACKAGES=({_shell_array(ubuntu_packages)})

        usage() {{
          printf '%s\n' 'Usage: bootstrap-dev.sh [--provider arch|debian|ubuntu] [--refresh | --install]'
          printf '%s\n' 'Default: detect the provider, query installed packages, and print reviewable argv without changing the host.'
        }}

        detect_provider() {{
          local os_id='' os_like='' key value count=0
          [[ -r /etc/os-release ]] || return 1
          while IFS='=' read -r key value; do
            ((count += 1))
            ((count <= 256)) || break
            case "$key" in
              ID|ID_LIKE)
                value="${{value:0:1024}}"
                if [[ "$value" == \"* && "$value" == *\" ]]; then
                  value="${{value:1:${{#value}}-2}}"
                fi
                value="${{value,,}}"
                if [[ "$key" == 'ID' ]]; then os_id="$value"; else os_like="$value"; fi
                ;;
            esac
          done < /etc/os-release
          case "$os_id" in
            ubuntu) printf '%s' ubuntu; return 0 ;;
            cachyos|arch) printf '%s' arch; return 0 ;;
            debian) printf '%s' debian; return 0 ;;
          esac
          case " $os_like " in
            *' ubuntu '*) printf '%s' ubuntu ;;
            *' arch '*) printf '%s' arch ;;
            *' debian '*) printf '%s' debian ;;
            *) return 1 ;;
          esac
        }}

        provider=''
        action='plan'
        while (($#)); do
          case "$1" in
            --provider)
              (($# >= 2)) || {{ printf '%s\n' 'Missing value after --provider.' >&2; exit 2; }}
              provider="$2"
              shift 2
              ;;
            --refresh|--install)
              [[ "$action" == 'plan' ]] || {{ printf '%s\n' 'Choose only one of --refresh or --install.' >&2; exit 2; }}
              action="${{1#--}}"
              shift
              ;;
            -h|--help) usage; exit 0 ;;
            *) printf 'Unknown option: %s\n' "$1" >&2; usage >&2; exit 2 ;;
          esac
        done

        if [[ -z "$provider" ]]; then
          provider="$(detect_provider)" || {{
            printf '%s\n' 'Could not detect CachyOS/Arch, Debian, or Ubuntu from bounded /etc/os-release fields.' >&2
            printf '%s\n' 'Review the host and rerun with --provider only when the matching package manager is intentional.' >&2
            exit 2
          }}
        else
          printf '%s\n' 'Explicit provider override selected; matching package-manager proof is still required.'
        fi

        case "$provider" in
          arch) manager='pacman'; query_manager='pacman'; PACKAGES=("${{ARCH_PACKAGES[@]}}") ;;
          debian) manager='apt-get'; query_manager='dpkg-query'; PACKAGES=("${{DEBIAN_PACKAGES[@]}}") ;;
          ubuntu) manager='apt-get'; query_manager='dpkg-query'; PACKAGES=("${{UBUNTU_PACKAGES[@]}}") ;;
          *) printf 'Unsupported provider: %s\n' "$provider" >&2; exit 2 ;;
        esac
        if ! command -v "$manager" >/dev/null 2>&1; then
          printf 'Provider %s requires %s, but it is unavailable. No package action was attempted.\n' "$provider" "$manager" >&2
          exit 2
        fi
        if ! command -v "$query_manager" >/dev/null 2>&1; then
          printf 'Provider %s requires %s for installed-state checks, but it is unavailable. No package action was attempted.\n' "$provider" "$query_manager" >&2
          exit 2
        fi

        is_installed() {{
          local package="$1" status=''
          if [[ "$provider" == 'arch' ]]; then
            pacman -Qq "$package" >/dev/null 2>&1
          else
            status="$(dpkg-query -W -f='${{Status}}' "$package" 2>/dev/null)" || return 1
            [[ "$status" == 'install ok installed' ]]
          fi
        }}

        print_argv() {{
          printf '  '
          printf '%q ' "$@"
          printf '\n'
        }}

        MISSING=()
        printf 'Provider: %s\n' "$provider"
        printf '%s\n' 'Installed-state check (read-only):'
        for package in "${{PACKAGES[@]}}"; do
          if is_installed "$package"; then
            printf '  installed: %s\n' "$package"
          else
            printf '  missing:   %s\n' "$package"
            MISSING+=("$package")
          fi
        done

        REFRESH_CMD=()
        if [[ "$provider" == 'arch' ]]; then
          INSTALL_CMD=(sudo pacman -S --needed "${{MISSING[@]}}")
        else
          REFRESH_CMD=(sudo apt-get update)
          INSTALL_CMD=(sudo apt-get install --yes "${{MISSING[@]}}")
        fi

        case "$action" in
          plan)
            printf '\n%s\n' 'Review-only host plan; no package command was run:'
            if ((${{#REFRESH_CMD[@]}})); then
              printf '%s\n' '  Optional APT index refresh, kept separate because it uses the network and changes local repository metadata:'
              print_argv "${{REFRESH_CMD[@]}}"
            fi
            if ((${{#MISSING[@]}})); then
              printf '%s\n' '  Install only packages not reported installed:'
              print_argv "${{INSTALL_CMD[@]}}"
            else
              printf '%s\n' '  All selected provider packages are already installed; no install command is needed.'
            fi
            printf '%s\n' 'No full-system upgrade is part of project bootstrap.'
            printf '%s\n' 'Use --refresh separately on Debian/Ubuntu only when APT indexes need refresh; use --install only after reviewing the missing list.'
            ;;
          refresh)
            if [[ "$provider" == 'arch' ]]; then
              printf '%s\n' '--refresh is only for Debian/Ubuntu APT indexes. No Arch system upgrade was run.' >&2
              exit 2
            fi
            printf '%s\n' 'Refreshing configured APT indexes only; this does not upgrade installed packages.'
            "${{REFRESH_CMD[@]}}"
            ;;
          install)
            if ((${{#MISSING[@]}} == 0)); then
              printf '%s\n' 'All selected provider packages are already installed; nothing to install.'
            else
              printf '%s\n' 'Installing only the reviewed missing packages; human sudo approval is required.'
              "${{INSTALL_CMD[@]}}"
            fi
            ;;
        esac

        printf '\n%s\n' 'Project-level setup commands to review/run after system packages:'
        {setup_lines}
    """
    return textwrap.dedent(rendered).strip() + "\n"
