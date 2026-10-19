#!/bin/sh
set -eu
launcher_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec /usr/bin/python3 -B "$launcher_dir/launch.py" all "$@"
