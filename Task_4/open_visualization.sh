#!/usr/bin/env bash
# Keep this terminal open while using the ISL first-person kitchen dashboard.
set -euo pipefail

ISL_DESTINATION=${ISL_DESTINATION:-guest-isl@172.26.186.222}
VIS_LOCAL_PORT=${VIS_LOCAL_PORT:-8767}
VIS_REMOTE_PORT=${VIS_REMOTE_PORT:-8774}

if ! [[ "$VIS_LOCAL_PORT" =~ ^[0-9]+$ && "$VIS_REMOTE_PORT" =~ ^[0-9]+$ ]] ||
   (( VIS_LOCAL_PORT < 1 || VIS_LOCAL_PORT > 65535 || VIS_REMOTE_PORT < 1 || VIS_REMOTE_PORT > 65535 )); then
  echo "Ports must be integers from 1 to 65535." >&2
  exit 1
fi

VIS_URL="http://127.0.0.1:$VIS_LOCAL_PORT/"
if python3 - "$VIS_URL" <<'PY'
import sys
import urllib.request

try:
    with urllib.request.urlopen(sys.argv[1], timeout=3) as response:
        page = response.read().decode("utf-8", errors="replace")
    sys.exit(0 if any(title in page for title in ["Habitat first-person route author", "Repaired kitchen — all objects"]) else 1)
except Exception:
    sys.exit(1)
PY
then
  echo "The dashboard is already reachable: $VIS_URL"
  echo "Open that address in your browser. No additional tunnel is needed."
  exit 0
fi

echo "Connecting to $ISL_DESTINATION. Campus network or VPN may be needed."
echo "Once connected, open $VIS_URL in your browser."
echo "Keep this terminal open; Ctrl+C closes this tunnel."
echo "The existing dashboard on the server must also be running."
exec ssh -N \
  -o ConnectTimeout=15 \
  -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 \
  -L "127.0.0.1:$VIS_LOCAL_PORT:127.0.0.1:$VIS_REMOTE_PORT" \
  "$ISL_DESTINATION"
