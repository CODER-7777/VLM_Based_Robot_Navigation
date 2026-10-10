#!/usr/bin/env bash
# Usage: [REFINED=1|INTERACTIVE=1] run.sh FOLDER INDEX [PORT]   e.g. run.sh 006 1  -> 1st episode of Downloads folder ...-006
set -euo pipefail
HERE=/data/robotics/toshith/rxr_author
NAV=/home/guest-isl/rishabh/NAVIDA
FOLDER=${1:?folder 001-006}; INDEX=${2:?1-based index}; PORT=${3:-8766}
read -r _ SHARD EP < <(awk -v f="$FOLDER" "\$1==f" "$HERE/episodes.tsv" | sed -n "${INDEX}p")
[[ -n "${EP:-}" ]] || { echo "No episode #$INDEX in folder $FOLDER ($(awk -v f="$FOLDER" "\$1==f" "$HERE/episodes.tsv" | wc -l) total)" >&2; exit 1; }
OUT="$HERE/out/$FOLDER/$EP"
SCENES=()
if [[ -n "${REFINED:-}${INTERACTIVE:-}" ]]; then
  # Only 2azQ1b91cZZ has a refined (Isaac-repaired) mesh; other scenes stay original.
  SCENE=$(zcat "$NAV/data/RxR_VLNCE_v0/val_unseen/val_unseen_guide.json.gz" | python3 -c 'import json,sys;ep=sys.argv[1];print(next(e["scene_id"] for e in json.load(sys.stdin)["episodes"] if str(e["episode_id"])==ep))' "$EP")
  [[ "$SCENE" == *2azQ1b91cZZ* ]] || { echo "Episode $EP is in $SCENE; no refined mesh for it (only 2azQ1b91cZZ). Run without REFINED=1." >&2; exit 1; }
  OUT="$HERE/out_refined/$FOLDER/$EP"; SCENES=(--scenes-dir "$HERE/scenes_v8")
  if [[ -n "${INTERACTIVE:-}" ]]; then
    # Doorless stage + each door/drawer as a clickable object (refined/export_parts.py).
    OUT="$HERE/out_interactive/$FOLDER/$EP"
    SCENES=(--scenes-dir "$HERE/scenes_interactive_v8" --parts-dir "$HERE/refined/parts_v8/parts")
  fi
fi
mkdir -p "$OUT"
echo "Folder $FOLDER #$INDEX -> $SHARD episode $EP  (outputs: $OUT)"
cd "$NAV"
PYTHONPATH="$NAV" MAGNUM_LOG=quiet HABITAT_SIM_LOG=quiet CUDA_VISIBLE_DEVICES=${GPU:-1} \
exec ${PYTHON:-/home/guest-isl/rishabh/VLA-paper/.navida-env/bin/python} "$HERE/author_pov_route.py" \
  --config config/vln_rxr.yaml --dataset data/RxR_VLNCE_v0/val_unseen/val_unseen_guide.json.gz \
  --episode-id "$EP" --port "$PORT" "${SCENES[@]}" \
  --output "$OUT/pov_route.json.gz" --challenge-output "$OUT/blocked.json.gz" \
  --baseline-output "$OUT/baseline.json.gz" --cases-dir "$OUT/cases" \
  --extracted-assets-dir "$HERE/extracted_mp3d_objects" --replica-cad-dir "$NAV/data/replica_cad"
