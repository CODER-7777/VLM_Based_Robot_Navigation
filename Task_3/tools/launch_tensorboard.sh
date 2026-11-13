#!/usr/bin/env bash
# Start TensorBoard for Task_3 results. Run it from any folder.
#
#   tools/launch_tensorboard.sh                         # training runs + SvanM2 evaluation runs
#   tools/launch_tensorboard.sh <folder>                # one evaluation or training folder
#   PORT=60061 tools/launch_tensorboard.sh              # choose the port
#
# Default folders:
#   xterra_mjlab/evaluation_runs   (earlier training and evaluation runs)
#   tools/results/svanm2_eval      (output of eval_svanm2_moe.sh)
#
# On a remote machine, run this on that machine and tunnel from your laptop:
#   ssh -N -L 6006:localhost:6006 USER@HOST
# then open http://localhost:6006
set -euo pipefail

TASK3="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TB="${TB:-$TASK3/xterra_mjlab/.venv/bin/tensorboard}"
PORT="${PORT:-6006}"

if [[ ! -x "$TB" ]]; then
  TB="$(command -v tensorboard || true)"
fi
if [[ -z "$TB" ]]; then
  echo "tensorboard not found: set TB=/path/to/tensorboard or install it in xterra_mjlab/.venv" >&2
  exit 2
fi

if [[ $# -ge 1 ]]; then
  LOGDIR_ARGS=(--logdir "$(cd "$1" && pwd)")
else
  LOGDIR_ARGS=(--logdir_spec "training:$TASK3/xterra_mjlab/evaluation_runs,evaluation:$TASK3/tools/results/svanm2_eval")
fi

echo "[tensorboard] port $PORT  (Ctrl+C to stop)"
exec "$TB" "${LOGDIR_ARGS[@]}" --port "$PORT"
