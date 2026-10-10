#!/usr/bin/env bash
# Run locally. Reuse working tunnels and forward only missing dashboard ports.
set -euo pipefail
ISL_DESTINATION=${ISL_DESTINATION:-guest-isl@172.26.186.222}
forward_args=()
for pair in 8767:8774 8778:8778 8776:8776; do
  local_port=${pair%%:*}
  remote_port=${pair##*:}
  if ! python3 - "$local_port" <<'PY'
import json,sys
from urllib.request import urlopen
port=int(sys.argv[1]);path='/scene-info' if port in (8767, 8776) else '/state'
try:
    with urlopen(f'http://127.0.0.1:{port}{path}',timeout=3) as response:
        data=json.load(response)
    field='scene_glb' if port==8767 else 'c2w_raw_gl'
    sys.exit(0 if field in data else 1)
except Exception:
    sys.exit(1)
PY
  then
    forward_args+=(-L "127.0.0.1:$local_port:127.0.0.1:$remote_port")
  fi
done
echo 'Repaired kitchen editor: http://localhost:8767/'
echo 'Habitat Home Tour POV dashboard: http://localhost:8776/'
echo 'Updated Gaussian RGB-D: http://localhost:8778/'
echo 'Gaussian before/after: http://localhost:8778/corner-comparisons'
if (( ${#forward_args[@]} == 0 )); then
  echo 'Both dashboards are already reachable; existing tunnels preserved.'
  exit 0
fi
echo 'Connecting to ISL. Keep this terminal open while viewing.'
exec ssh -N -o ConnectTimeout=15 -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=30 -o ServerAliveCountMax=3 \
  "${forward_args[@]}" "$ISL_DESTINATION"
