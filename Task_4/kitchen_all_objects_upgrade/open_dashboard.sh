#!/usr/bin/env bash
# Run on the local computer; the tunnel continues as a background user service.
set -euo pipefail
ISL_DESTINATION=${ISL_DESTINATION:-guest-isl@172.26.186.222}
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
ssh -o ConnectTimeout=15 "$ISL_DESTINATION" \
  '/data/robotics/toshith/envs/kitchen3d/bin/python /data/robotics/toshith/rxr_author/refined/toaster_home_tour/launch_home_tour.py'
exec python3 "$SCRIPT_DIR/../toaster_home_tour/evidence/start_local_tunnels.py"
