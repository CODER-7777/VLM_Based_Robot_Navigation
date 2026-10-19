#!/bin/sh
# Run on the simulation server after IITK IT provisions HTTPS and allowed networks.
set -eu
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
config=${1:-"$base/config.production.json"}
if [ ! -f "$config" ]; then
    printf '%s\n' 'Fill config.production.json using config.production.example.json first.' >&2
    exit 1
fi
exec /usr/bin/python3 -B "$base/run_tmux.py" "$config"
