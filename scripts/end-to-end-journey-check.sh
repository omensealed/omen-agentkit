#!/usr/bin/env bash
set -euo pipefail

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"

./scripts/install-smoke-test.sh
python3 -m unittest tests.test_end_to_end_journeys -v
