#!/bin/sh
# Start/reuse every dashboard in tmux and open each browser page.
set -eu
task5_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec "$task5_root/dashboard_startup/start_all.sh" "$@"
