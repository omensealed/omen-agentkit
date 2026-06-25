#!/usr/bin/env bash
set -euo pipefail

DATA_HOME=${XDG_DATA_HOME:-"$HOME/.local/share"}
BIN_HOME=${XDG_BIN_HOME:-"$HOME/.local/bin"}
DEST="$DATA_HOME/cli-ai-agent-starter-kit"
LAUNCHER="$BIN_HOME/agent-starter"

if [[ -f "$LAUNCHER" ]] && grep -q 'Installed by CLI AI Agent Starter Kit' "$LAUNCHER"; then
  rm -f "$LAUNCHER"
  printf 'Removed %s\n' "$LAUNCHER"
elif [[ -e "$LAUNCHER" ]]; then
  printf 'Refusing to remove an unrecognized launcher: %s\n' "$LAUNCHER" >&2
else
  printf 'Launcher was already absent: %s\n' "$LAUNCHER"
fi

if [[ -d "$DEST" ]]; then
  rm -rf -- "$DEST"
  printf 'Removed %s\n' "$DEST"
else
  printf 'Installed data was already absent: %s\n' "$DEST"
fi

printf '%s\n' 'Generated projects and vendor CLI authorization were not touched.'
