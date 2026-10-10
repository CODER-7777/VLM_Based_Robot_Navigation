#!/usr/bin/env bash
# Run on your local computer. The tunnel stays in the background.
set -euo pipefail
ISL_DESTINATION=${ISL_DESTINATION:-guest-isl@172.26.186.222}
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
ssh -o ConnectTimeout=15 "$ISL_DESTINATION" \
  '/data/robotics/toshith/envs/kitchen3d/bin/python /data/robotics/toshith/rxr_author/refined/toaster_home_tour/launch_home_tour.py'
echo 'PBR home tour: http://localhost:8767/'
echo 'Comparisons: http://localhost:8767/comparisons'
echo 'Rotate repaired models: http://localhost:8767/models'
exec python3 "$SCRIPT_DIR/evidence/start_local_tunnels.py"
