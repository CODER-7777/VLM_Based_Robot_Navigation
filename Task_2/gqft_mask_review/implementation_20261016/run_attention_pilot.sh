#!/usr/bin/env bash
# Four matched 500-step runs. Only --dry-run avoids launching training.
set -euo pipefail

GQFT_PROJECT=/data/robotics/toshith/vivekananda/gqft_algorithm_sharing_vivekananda
GQFT_LAB="$GQFT_PROJECT/gqft_mask_review"
GQFT_SOURCE="$GQFT_LAB/source_20261016"
GQFT_PYTHON=/data/robotics/toshith/envs/agentvln/bin/python
GQFT_CHECKPOINT="$GQFT_PROJECT/runs/gqft_spatial_yaw_v1/best.pt"
GQFT_MANIFEST="$GQFT_PROJECT/results/hsgm_manifest_v1.json"
GQFT_ARCHIVE="$GQFT_LAB/source_20261016.tar.gz"
GQFT_DRY_RUN=false
if [[ "${1:-}" == --dry-run && $# == 1 ]]; then
  GQFT_DRY_RUN=true
elif [[ $# != 0 ]]; then
  printf 'Usage: bash run_attention_pilot.sh [--dry-run]\n' >&2
  exit 2
fi

export CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES=7 PYTHONDONTWRITEBYTECODE=1
GQFT_RUN_ROOT="$GQFT_LAB/pilots/$(date -u +%Y%m%dT%H%M%SZ)_$$"
GQFT_COMMON=(
  "$GQFT_PYTHON" -u -B -m step2.train_gqft
  --manifest "$GQFT_MANIFEST" --steps 500 --batch-size 6 --workers 2
  --queries 1 --max-history 30 --virtual-extension-px 270
  --seed 20260820 --warmup 50 --val-every 100 --checkpoint-every 100
  --min-stable-step 500 --init-checkpoint "$GQFT_CHECKPOINT"
  --reinitialize-motion-heads --predict-yaw --target-ground-plane sequence_floor
  --mask-coverage-rule receptive_field --mask-soft-floor 0.25 --mask-logit-strength 1
  --mask-hard-min-coverage 0 --mask-ground-near-m 0.5 --mask-ground-far-m 8 --allow-gpu
)

gqft_run_arm() {
  local arm="$1" spatial="$2" integration="$3"
  local -a command=("${GQFT_COMMON[@]}" --spatial-mask "$spatial"
                    --motion-integration "$integration" --out "$GQFT_RUN_ROOT/$arm")
  if "$GQFT_DRY_RUN"; then
    printf 'CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES=7 PYTHONDONTWRITEBYTECODE=1 '
    printf '%q ' "${command[@]}"
    printf '\n'
  else
    printf '\nStarting %s; log: %s/%s.log\n' "$arm" "$GQFT_RUN_ROOT" "$arm"
    "${command[@]}" 2>&1 | tee "$GQFT_RUN_ROOT/$arm.log"
  fi
}

if ! "$GQFT_DRY_RUN"; then
  [[ -x "$GQFT_PYTHON" && -f "$GQFT_ARCHIVE" && -f "$GQFT_CHECKPOINT" && -f "$GQFT_MANIFEST" ]]
  "$GQFT_PYTHON" -B - "$GQFT_ARCHIVE" <<'PY'
import hashlib, sys
from pathlib import Path
expected='3abcc4e92d3fa18926a646c147c7955928675aeafcc88bb50c8e5660de98729b'
if hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest()!=expected:
    raise SystemExit('Source archive hash mismatch; do not train this bundle')
PY
  if [[ ! -d "$GQFT_SOURCE" ]]; then
    tar --keep-old-files -xzf "$GQFT_ARCHIVE" -C "$GQFT_LAB"
  fi
  "$GQFT_PYTHON" -B - "$GQFT_SOURCE" "$GQFT_CHECKPOINT" <<'PY'
import hashlib, json, sys
from pathlib import Path
source, checkpoint=map(Path,sys.argv[1:])
for name,expected in json.loads((source/'SOURCE_MANIFEST.json').read_text()).items():
    if hashlib.sha256((source/name).read_bytes()).hexdigest()!=expected:
        raise SystemExit('Staged source mismatch: '+name)
if hashlib.sha256(checkpoint.read_bytes()).hexdigest()!='40729f0f537c28e5b07565aba01133bb594c7781cc59eedf90bc3fafa939ee8d':
    raise SystemExit('Starting checkpoint differs from the verified pilot checkpoint')
print('Source and starting checkpoint verified.',flush=True)
PY
  cd "$GQFT_SOURCE"
  mkdir -p "$GQFT_LAB/pilots"
  mkdir "$GQFT_RUN_ROOT"
  printf 'PILOT_OUTPUT=%s\n' "$GQFT_RUN_ROOT"
  nvidia-smi -i 7 --query-gpu=index,name,memory.used,memory.total --format=csv,noheader
fi

gqft_run_arm reference none keyframe
gqft_run_arm masked_only soft_confidence_ground keyframe
gqft_run_arm yaw_local_only none yaw_local
gqft_run_arm masked_yaw_local soft_confidence_ground yaw_local

if ! "$GQFT_DRY_RUN"; then
  printf '\nALL_FOUR_PILOTS_DONE output=%s\n' "$GQFT_RUN_ROOT"
fi
