#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
export HOME="$TMP/home"
export XDG_DATA_HOME="$TMP/data"
export XDG_BIN_HOME="$TMP/bin"
mkdir -p "$HOME" "$XDG_DATA_HOME" "$XDG_BIN_HOME"

./install.sh >/dev/null
"$XDG_BIN_HOME/agent-starter" --version | grep -q "$(cat VERSION)"
test -f "$XDG_DATA_HOME/cli-ai-agent-starter-kit/starter.py"

./uninstall.sh >/dev/null
test ! -e "$XDG_BIN_HOME/agent-starter"
test ! -e "$XDG_DATA_HOME/cli-ai-agent-starter-kit"
printf '%s\n' 'Install/uninstall smoke test passed.'
