#!/usr/bin/env bash
set -euo pipefail
task_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ssh -o BatchMode=yes -o ConnectTimeout=15 guest-isl@172.26.186.222 \
  'cd /data/robotics/toshith/rxr_author/refined && /data/robotics/toshith/envs/kitchen3d/bin/python kitchen_product_replacements/launch_products.py'
python3 "$task_dir/../toaster_home_tour/evidence/start_local_tunnels.py"
xdg-open 'http://localhost:8767/?object=range_kettle'
