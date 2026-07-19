#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PYTHON=${PYTHON:-python3}
DATA_HOME=${XDG_DATA_HOME:-"$HOME/.local/share"}
BIN_HOME=${XDG_BIN_HOME:-"$HOME/.local/bin"}
DEST="$DATA_HOME/cli-ai-agent-starter-kit"
LAUNCHER="$BIN_HOME/agent-starter"
OWNER_MARKER=".agent-starter-install-owner"
OWNER_VALUE="cli-ai-agent-starter-kit"
DEST_OWNER="$DEST/$OWNER_MARKER"

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

owned_launcher() {
  [[ -f "$LAUNCHER" && ! -L "$LAUNCHER" ]] || return 1
  grep -q 'Installed by CLI AI Agent Starter Kit' "$LAUNCHER"
}

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  printf '%s\n' 'Python 3.11 or newer is required.' >&2
  exit 1
fi

if ! "$PYTHON" - <<'PY'
import sys
raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
PY
then
  printf 'Found %s, but Python 3.11 or newer is required.\n' "$($PYTHON --version 2>&1)" >&2
  exit 1
fi

if [[ -e "$DEST" || -L "$DEST" ]]; then
  if ! recognized_data_install; then
    printf 'Refusing to replace an unrecognized data path: %s\n' "$DEST" >&2
    exit 2
  fi
fi
if [[ -e "$LAUNCHER" || -L "$LAUNCHER" ]]; then
  if ! owned_launcher; then
    printf 'Refusing to replace an unrecognized launcher: %s\n' "$LAUNCHER" >&2
    exit 2
  fi
fi

mkdir -p "$DATA_HOME" "$BIN_HOME"
STAGE="$DATA_HOME/.cli-ai-agent-starter-kit.new.$$"
OLD="$DATA_HOME/.cli-ai-agent-starter-kit.old.$$"
trap 'rm -rf "$STAGE" "$OLD"' EXIT
rm -rf "$STAGE" "$OLD"
mkdir -p "$STAGE"

cp -a \
  "$ROOT/agent_starter" \
  "$ROOT/docs" \
  "$ROOT/examples" \
  "$ROOT/README.md" \
  "$ROOT/LICENSE" \
  "$ROOT/VERSION" \
  "$ROOT/starter.py" \
  "$ROOT/uninstall.sh" \
  "$STAGE/"
printf '%s\n' "$OWNER_VALUE" >"$STAGE/$OWNER_MARKER"

if [[ -e "$DEST" ]]; then
  mv "$DEST" "$OLD"
fi
mv "$STAGE" "$DEST"
rm -rf "$OLD"

TMP_LAUNCHER="$BIN_HOME/.agent-starter.new.$$"
cat >"$TMP_LAUNCHER" <<EOF
#!/usr/bin/env bash
# Installed by CLI AI Agent Starter Kit. OAuth remains owned by OpenAI Codex CLI.
exec ${PYTHON@Q} ${DEST@Q}/starter.py "\$@"
EOF
chmod 0755 "$TMP_LAUNCHER"
mv "$TMP_LAUNCHER" "$LAUNCHER"

printf 'Installed CLI AI Agent Starter Kit %s\n' "$(cat "$ROOT/VERSION")"
printf '  Program: %s\n' "$LAUNCHER"
printf '  Data:    %s\n' "$DEST"
if [[ ":$PATH:" != *":$BIN_HOME:"* ]]; then
  printf '\n%s is not currently on PATH. Add this to your shell profile:\n' "$BIN_HOME"
  printf '  export PATH=%q:\$PATH\n' "$BIN_HOME"
fi
printf '\nRun: agent-starter doctor\n'
