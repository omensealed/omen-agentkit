#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PYTHON=${PYTHON:-python3}
DATA_HOME=${XDG_DATA_HOME:-"$HOME/.local/share"}
BIN_HOME=${XDG_BIN_HOME:-"$HOME/.local/bin"}
DEST="$DATA_HOME/cli-ai-agent-starter-kit"
LAUNCHER="$BIN_HOME/agent-starter"

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
