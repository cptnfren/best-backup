#!/usr/bin/env bash
# Localsetup v2 - Automated tests. Thin wrapper; logic in automated_test.py.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENGINE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
exec python3 "$ENGINE_DIR/tests/automated_test.py"
