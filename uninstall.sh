#!/usr/bin/env bash
set -euo pipefail

DATA_HOME=${XDG_DATA_HOME:-"$HOME/.local/share"}
BIN_HOME=${XDG_BIN_HOME:-"$HOME/.local/bin"}
DEST="$DATA_HOME/cli-ai-agent-starter-kit"
LAUNCHER="$BIN_HOME/agent-starter"
OWNER_MARKER=".agent-starter-install-owner"
OWNER_VALUE="cli-ai-agent-starter-kit"
DEST_OWNER="$DEST/$OWNER_MARKER"
failures=0

owned_data_install() {
  local value=''
  [[ -d "$DEST" && ! -L "$DEST" && -f "$DEST_OWNER" && ! -L "$DEST_OWNER" ]] || return 1
  IFS= read -r value <"$DEST_OWNER" || true
  [[ "$value" == "$OWNER_VALUE" ]]
}

legacy_owned_data_install() {
  [[ -d "$DEST" && ! -L "$DEST" && ! -e "$DEST_OWNER" ]] || return 1
  [[ -d "$DEST/agent_starter" && ! -L "$DEST/agent_starter" ]] || return 1
  [[ -f "$DEST/starter.py" && ! -L "$DEST/starter.py" ]] || return 1
  [[ -f "$DEST/VERSION" && ! -L "$DEST/VERSION" ]] || return 1
  [[ -f "$DEST/uninstall.sh" && ! -L "$DEST/uninstall.sh" ]] || return 1
  grep -q 'from agent_starter.cli import main' "$DEST/starter.py" &&
    grep -q 'Generated projects and vendor CLI authorization were not touched' "$DEST/uninstall.sh"
}

recognized_data_install() {
  owned_data_install || legacy_owned_data_install
}

if [[ -f "$LAUNCHER" && ! -L "$LAUNCHER" ]] && grep -q 'Installed by CLI AI Agent Starter Kit' "$LAUNCHER"; then
  rm -f "$LAUNCHER"
  printf 'Removed %s\n' "$LAUNCHER"
elif [[ -e "$LAUNCHER" || -L "$LAUNCHER" ]]; then
  printf 'Refusing to remove an unrecognized launcher: %s\n' "$LAUNCHER" >&2
  failures=1
else
  printf 'Launcher was already absent: %s\n' "$LAUNCHER"
fi

if recognized_data_install; then
  rm -rf -- "$DEST"
  printf 'Removed %s\n' "$DEST"
elif [[ -e "$DEST" || -L "$DEST" ]]; then
  printf 'Refusing to remove an unrecognized data path: %s\n' "$DEST" >&2
  failures=1
else
  printf 'Installed data was already absent: %s\n' "$DEST"
fi

printf '%s\n' 'Generated projects and vendor CLI authorization were not touched.'
if ((failures)); then
  exit 2
fi
