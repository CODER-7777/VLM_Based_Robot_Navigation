#!/bin/sh
set -eu
studio_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec /usr/bin/python3 -B "$studio_root/checkpoint_walkthrough_studio/launch.py" "$@"
