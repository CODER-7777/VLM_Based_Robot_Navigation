#!/usr/bin/env bash
# Validation only: identical 30-pair tasks across all requested histories/arms.
set -euo pipefail
PROJECT=/data/robotics/toshith/vivekananda/gqft_algorithm_sharing_vivekananda
LAB="$PROJECT/gqft_mask_review"
SOURCE="$LAB/source_20261016"
PYTHON=/data/robotics/toshith/envs/agentvln/bin/python
RUN="${1:?Supply the completed pilot directory basename}"
[[ "$RUN" =~ ^[0-9]{8}T[0-9]{6}Z_[0-9]+$ ]]
PILOT="$LAB/pilots/$RUN"
OUT="$PILOT/validation_$(date -u +%Y%m%dT%H%M%SZ)"
export CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES=7 PYTHONDONTWRITEBYTECODE=1
cd "$SOURCE"
mkdir "$OUT"
"$PYTHON" -B - "$SOURCE" "$PILOT" "$OUT" <<'PY'
from pathlib import Path
import hashlib, json, math, sys, torch
source, pilot, out = map(Path, sys.argv[1:])
for name, expected in json.loads((source/'SOURCE_MANIFEST.json').read_text()).items():
    assert hashlib.sha256((source/name).read_bytes()).hexdigest() == expected, name
arms = {}
for name in ('reference', 'masked_only', 'yaw_local_only', 'masked_yaw_local'):
    arm = pilot/name
    entries = [json.loads(x) for x in (arm/'metrics.jsonl').read_text().splitlines() if x.strip()]
    train = [x for x in entries if x.get('kind') == 'train']
    val = [x for x in entries if x.get('kind') == 'val']
    assert train[-1]['step'] == val[-1]['step'] == 500
    assert train[-1]['finite_streak'] == 500
    assert all(math.isfinite(v) for x in train+val for v in x.values() if isinstance(v, float))
    checkpoints = {}
    for filename in ('best.pt', 'last.pt'):
        path = arm/filename
        checkpoint = torch.load(path, map_location='cpu', weights_only=False)
        assert checkpoint['step'] == 500, (name, filename, checkpoint['step'])
        checkpoints[filename] = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                                 'bytes': path.stat().st_size, 'step': checkpoint['step'],
                                 'model_config': checkpoint['model_config'],
                                 'args': checkpoint['args']}
    arms[name] = {'checkpoints': checkpoints, 'validation': val, 'last_train': train[-1],
                  'run_config': json.loads((arm/'run_config.json').read_text())}
payload = {'pilot': str(pilot), 'source': str(source), 'source_manifest_verified': True,
           'torch': torch.__version__, 'physical_gpu': 7, 'logical_device': 'cuda:0',
           'gpu_name': torch.cuda.get_device_name(0), 'arms': arms,
           'evaluation': {'split': 'val', 'histories': [4,8,12,16,20,24,30],
                          'reference_history': 30, 'queries': 1, 'batch_size': 8,
                          'precision': 'CUDA autocast bfloat16 (existing evaluator)',
                          'target_ground_plane': 'sequence_floor', 'origin_included': True,
                          'selection': 'best.pt selected by training-time validation',
                          'test_evaluated': False}}
(out/'provenance.json').write_text(json.dumps(payload, indent=2)+'\n')
print('CHECKPOINTS_AND_SOURCE_VERIFIED', flush=True)
PY
for ARM in reference masked_only yaw_local_only masked_yaw_local pretrained_yaw
do
  CHECKPOINT="$PILOT/$ARM/best.pt"
  if [[ "$ARM" == pretrained_yaw ]]; then
    CHECKPOINT="$PROJECT/runs/gqft_spatial_yaw_v1/best.pt"
  fi
  "$PYTHON" -u -B -m step2.evaluate_gqft \
    --checkpoint "$CHECKPOINT" --manifest "$PROJECT/results/hsgm_manifest_v1.json" \
    --sequences-root /data/robotics/toshith/rgbd_vo_dataset/hsgm_sequences \
    --split val --histories 4,8,12,16,20,24,30 --queries 1 --batch-size 8 --workers 2 \
    --signature-samples 512 --target-ground-plane sequence_floor --device cuda \
    --out "$OUT/$ARM.json" 2>&1 | tee "$OUT/$ARM.log"
done
printf 'PILOT_VALIDATION_DONE output=%s\n' "$OUT"
