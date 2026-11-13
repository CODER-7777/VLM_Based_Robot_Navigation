"""Continue the interrupted GPU-4 pilot, preserving completed and partial arms."""
from datetime import datetime, timezone
import argparse
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import traceback

ROOT = Path(__file__).resolve().parent


def save(data):
    tmp = ROOT/'training_status.json.tmp'
    tmp.write_text(json.dumps(data, indent=2)+'\n')
    tmp.replace(ROOT/'training_status.json')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', type=Path, default=ROOT/'source')
    parser.add_argument('--lock-name', default='resume_started.lock')
    parser.add_argument('--restart-invalid-learned-arm', action='store_true')
    args = parser.parse_args()
    source = args.source_dir.resolve()
    if not source.is_relative_to(ROOT.resolve()) or Path(args.lock_name).name != args.lock_name:
        raise ValueError('Source and lock must stay inside the run directory')
    with (ROOT/args.lock_name).open('x') as f:
        f.write(str(os.getpid()))
    status = json.loads((ROOT/'training_status.json').read_text())
    old = Path('/proc')/str(status['pid'])/'cmdline'
    if old.exists() and str(ROOT/'run_training_pilot.py').encode() in old.read_bytes().split(b'\0'):
        raise RuntimeError('Original controller is still alive')
    plan = json.loads((ROOT/'training_plan.json').read_text())
    if args.restart_invalid_learned_arm:
        import torch
        failed = ROOT/'solver_learned_weights'
        records = [json.loads(x[6:]) for x in (failed/'train.log').read_text().splitlines()
                   if x.startswith('TRAIN ')]
        if not records or any(math.isfinite(x['grad_norm']) for x in records):
            raise RuntimeError('Expected an invalid run with zero finite optimizer updates')
        for checkpoint in failed.glob('*.pt'):
            state = torch.load(checkpoint, map_location='cpu', weights_only=False)
            if state['optimizer']['state']:
                raise RuntimeError('Optimizer updates exist; refusing to discard resumable progress')
        status['completed_arms'] = [x for x in status['completed_arms'] if x != 'solver_learned_weights']
    status.update(pid=os.getpid(), status='restarting', gpu_physical=4,
                  resumed_utc=datetime.now(timezone.utc).isoformat(), active_source=str(source))
    status.pop('stop_reason', None)
    status.pop('stopped_utc', None)
    status.pop('error', None)
    save(status)
    env = os.environ.copy()
    env.update(CUDA_DEVICE_ORDER='PCI_BUS_ID', CUDA_VISIBLE_DEVICES='4',
               PYTHONDONTWRITEBYTECODE='1', OMP_NUM_THREADS='2', OPENBLAS_NUM_THREADS='2',
               XDG_CACHE_HOME=str(ROOT/'cache'), TORCH_HOME=str(ROOT/'cache/torch'),
               CUDA_CACHE_PATH=str(ROOT/'cache/cuda'))
    try:
        for arm in plan['arms']:
            name = arm['name']
            output = ROOT/name
            if name in status['completed_arms']:
                assert (output/'best.pt').exists() and (output/'fixed_validation.json').exists()
                continue
            if shutil.disk_usage(ROOT).free < 1536*1024**2:
                raise RuntimeError('Less than 1.5 GiB free')
            command = list(arm['command'])
            # This interruption had no solver checkpoint, so retain its logs and
            # restart that arm from the unchanged matched initialization.
            if output.exists():
                if (output/'last.pt').exists() and not (args.restart_invalid_learned_arm and name == 'solver_learned_weights'):
                    raise RuntimeError('Checkpoint found: configure exact checkpoint resume before continuing')
                archive = ROOT/'interrupted_before_resume'
                archive.mkdir(exist_ok=True)
                destination = archive/name
                if destination.exists():
                    destination = archive/(name+'_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
                output.rename(destination)
            output.mkdir()
            status.update(status='training', current_arm=name, current_log=str(output/'train.log'))
            save(status)
            with (output/'train.log').open('x') as log:
                subprocess.run(command, cwd=source, env=env,
                               stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, check=True)
            status.update(status='validating')
            save(status)
            project = ROOT.parents[2]
            command = [sys.executable, '-B', '-m', 'step2.evaluate_gqft',
                       '--checkpoint', str(output/'best.pt'),
                       '--manifest', str(project/'results/hsgm_manifest_v1.json'),
                       '--sequences-root', '/data/robotics/toshith/rgbd_vo_dataset/hsgm_sequences',
                       '--split', 'val', '--histories', '4,8,12,16,20,24,30',
                       '--queries', '1', '--batch-size', '4', '--workers', '0',
                       '--target-ground-plane', 'sequence_floor', '--device', 'cuda',
                       '--out', str(output/'fixed_validation.json')]
            with (output/'fixed_validation.log').open('x') as log:
                subprocess.run(command, cwd=source, env=env,
                               stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, check=True)
            status['completed_arms'].append(name)
            save(status)
        status.update(status='completed', current_arm=None, finished_utc=datetime.now(timezone.utc).isoformat())
        save(status)
    except Exception:
        status.update(status='failed', error=traceback.format_exc())
        save(status)
        raise


if __name__ == '__main__':
    main()
