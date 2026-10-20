#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")/step8_review"
exec python3 launch.py "$@"
