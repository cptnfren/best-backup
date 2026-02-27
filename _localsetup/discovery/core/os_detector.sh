#!/bin/bash
# Localsetup v2 - OS detection. Thin wrapper; logic in os_detector.py.
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENGINE_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
exec python3 "$ENGINE_DIR/discovery/core/os_detector.py"
