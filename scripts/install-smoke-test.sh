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

# unowned-data install refusal
mkdir -p "$XDG_DATA_HOME/cli-ai-agent-starter-kit"
printf '%s\n' 'preserve data' >"$XDG_DATA_HOME/cli-ai-agent-starter-kit/unowned-data"
if ./install.sh >/dev/null 2>&1; then
  printf '%s\n' 'installer replaced unowned data' >&2
  exit 1
else
  test "$?" -eq 2
fi
test -f "$XDG_DATA_HOME/cli-ai-agent-starter-kit/unowned-data"
rm -rf "$XDG_DATA_HOME/cli-ai-agent-starter-kit"

# unowned-launcher install refusal
printf '%s\n' 'preserve launcher' >"$XDG_BIN_HOME/agent-starter"
if ./install.sh >/dev/null 2>&1; then
  printf '%s\n' 'installer replaced unowned launcher' >&2
  exit 1
else
  test "$?" -eq 2
fi
grep -q 'preserve launcher' "$XDG_BIN_HOME/agent-starter"
rm -f "$XDG_BIN_HOME/agent-starter"

# symlink ownership refusal preserves external targets
mkdir -p "$TMP/external-data"
printf '%s\n' 'external data' >"$TMP/external-data/keep"
ln -s "$TMP/external-data" "$XDG_DATA_HOME/cli-ai-agent-starter-kit"
if ./install.sh >/dev/null 2>&1; then
  printf '%s\n' 'installer replaced symlinked data' >&2
  exit 1
else
  test "$?" -eq 2
fi
test -f "$TMP/external-data/keep"
rm -f "$XDG_DATA_HOME/cli-ai-agent-starter-kit"

./install.sh >/dev/null
"$XDG_BIN_HOME/agent-starter" --version | grep -q "$(cat VERSION)"
test -f "$XDG_DATA_HOME/cli-ai-agent-starter-kit/starter.py"
test -f "$XDG_DATA_HOME/cli-ai-agent-starter-kit/.agent-starter-install-owner"

# managed reinstall remains supported and removes stale managed payload
touch "$XDG_DATA_HOME/cli-ai-agent-starter-kit/stale-managed-file"
./install.sh >/dev/null
test ! -e "$XDG_DATA_HOME/cli-ai-agent-starter-kit/stale-managed-file"

./uninstall.sh >/dev/null
test ! -e "$XDG_BIN_HOME/agent-starter"
test ! -e "$XDG_DATA_HOME/cli-ai-agent-starter-kit"

# legacy managed adoption remains compatible with pre-marker installations
mkdir -p "$XDG_DATA_HOME/cli-ai-agent-starter-kit/agent_starter"
printf '%s\n' 'from agent_starter.cli import main' >"$XDG_DATA_HOME/cli-ai-agent-starter-kit/starter.py"
printf '%s\n' '0.4.8' >"$XDG_DATA_HOME/cli-ai-agent-starter-kit/VERSION"
printf '%s\n' 'Generated projects and vendor CLI authorization were not touched.' >"$XDG_DATA_HOME/cli-ai-agent-starter-kit/uninstall.sh"
./install.sh >/dev/null
test -f "$XDG_DATA_HOME/cli-ai-agent-starter-kit/.agent-starter-install-owner"
./uninstall.sh >/dev/null

# unowned-launcher and unowned-data uninstall refusal
printf '%s\n' 'preserve launcher' >"$XDG_BIN_HOME/agent-starter"
mkdir -p "$XDG_DATA_HOME/cli-ai-agent-starter-kit"
printf '%s\n' 'preserve data' >"$XDG_DATA_HOME/cli-ai-agent-starter-kit/unowned-data"
if ./uninstall.sh >"$TMP/uninstall-refusal.log" 2>&1; then
  printf '%s\n' 'uninstaller removed unowned paths' >&2
  exit 1
else
  test "$?" -eq 2
fi
grep -q 'Generated projects and vendor CLI authorization were not touched' "$TMP/uninstall-refusal.log"
test -f "$XDG_BIN_HOME/agent-starter"
test -f "$XDG_DATA_HOME/cli-ai-agent-starter-kit/unowned-data"
rm -f "$XDG_BIN_HOME/agent-starter"
rm -rf "$XDG_DATA_HOME/cli-ai-agent-starter-kit"

printf '%s\n' 'external launcher' >"$TMP/external-launcher"
ln -s "$TMP/external-launcher" "$XDG_BIN_HOME/agent-starter"
ln -s "$TMP/external-data" "$XDG_DATA_HOME/cli-ai-agent-starter-kit"
if ./uninstall.sh >/dev/null 2>&1; then
  printf '%s\n' 'uninstaller removed symlinked paths' >&2
  exit 1
else
  test "$?" -eq 2
fi
test -L "$XDG_BIN_HOME/agent-starter"
test -L "$XDG_DATA_HOME/cli-ai-agent-starter-kit"
grep -q 'external launcher' "$TMP/external-launcher"
test -f "$TMP/external-data/keep"
printf '%s\n' 'Install/uninstall smoke test passed.'
