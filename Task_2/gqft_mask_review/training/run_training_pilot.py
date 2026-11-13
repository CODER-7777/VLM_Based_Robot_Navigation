"""Run a single-GPU, three-arm GQFT pilot from an isolated server snapshot.

Copy this file into a prepared run directory containing source/, preflight.json,
source_manifest.json and solver_validation.json. Outputs never leave that run.
No package installation, flow regeneration or locked-test access is performed.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import traceback

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
SOURCE = ROOT/'source'


def save(name, data):
    destination = ROOT/name
    temporary = destination.with_suffix(destination.suffix+'.tmp')
    temporary.write_text(json.dumps(data, indent=2)+'\n')
    temporary.replace(destination)


def stamp():
    return datetime.now(timezone.utc).isoformat()


def main():
    lock = ROOT/'training_started.lock'
    with lock.open('x') as f:
        f.write(f'{os.getpid()} {stamp()}\n')
    status = {'status': 'preparing', 'pid': os.getpid(), 'started_utc': stamp(),
              'gpu_physical': 4, 'steps_per_arm': 500, 'completed_arms': []}
    save('training_status.json', status)
    try:
        preflight = json.loads((ROOT/'preflight.json').read_text())
        validation = json.loads((ROOT/'solver_validation.json').read_text())
        assert preflight['gpu_physical'] == 4
        assert validation['protocol']['canvas'] == [960, 810]
        assert validation['protocol']['queries'] == 1
        assert len(validation['windows']) == 104
        assert validation['cutoff_selected_on'] == 'train'
        assert len(validation['train_selection']) == 5
        assert not validation['validation_sensitivity_not_for_selection']
        cutoff = validation['chosen_cutoff_m']
        checkpoint = PROJECT/'runs/gqft_spatial_yaw_v1/best.pt'
        assert hashlib.sha256(checkpoint.read_bytes()).hexdigest() == preflight['checkpoint_sha256']
        manifest = json.loads((ROOT/'source_manifest.json').read_text())
        for row in manifest['files']:
            assert hashlib.sha256((SOURCE/row['path']).read_bytes()).hexdigest() == row['sha256']
        cache = ROOT/'cache'
        cache.mkdir(exist_ok=True)
        env = os.environ.copy()
        env.update(CUDA_DEVICE_ORDER='PCI_BUS_ID', CUDA_VISIBLE_DEVICES='4',
                   PYTHONDONTWRITEBYTECODE='1', OMP_NUM_THREADS='2', OPENBLAS_NUM_THREADS='2',
                   XDG_CACHE_HOME=str(cache), TORCH_HOME=str(cache/'torch'),
                   CUDA_CACHE_PATH=str(cache/'cuda'))
        common = [sys.executable, '-B', '-m', 'step2.train_gqft',
                  '--manifest', str(PROJECT/'results/hsgm_manifest_v1.json'),
                  '--sequences-root', '/data/robotics/toshith/rgbd_vo_dataset/hsgm_sequences',
                  '--steps', '500', '--batch-size', '4', '--workers', '2', '--queries', '1',
                  '--max-history', '30', '--virtual-extension-px', '270',
                  '--lr', '0.0002', '--weight-decay', '0.01', '--warmup', '50',
                  '--log-every', '20', '--val-every', '100', '--val-batches', '100',
                  '--checkpoint-every', '500', '--min-stable-step', '500',
                  '--seed', '20260820', '--init-checkpoint', str(checkpoint),
                  '--reinitialize-motion-heads', '--predict-yaw',
                  '--spatial-pooling', 'attention_max', '--spatial-mask', 'none',
                  '--motion-integration', 'yaw_local', '--target-ground-plane', 'sequence_floor',
                  '--allow-gpu']
        arms = [('yaw_local_reference', ['--motion-prior', 'none']),
                ('solver_residual', ['--motion-prior', 'ground_solver',
                                     '--ground-max-floor-m', str(cutoff)]),
                ('solver_learned_weights', ['--motion-prior', 'ground_solver',
                                            '--ground-max-floor-m', str(cutoff),
                                            '--ground-learned-weights'])]
        save('training_plan.json', {
            'purpose': '500-step feasibility pilot; one matched seed, not a final benchmark',
            'gpu': 4, 'selected_cutoff_m': cutoff, 'selection_split': 'train',
            'source_manifest': 'source_manifest.json', 'initialization': str(checkpoint),
            'checkpoint_sha256': preflight['checkpoint_sha256'],
            'steps_per_arm': 500, 'batch_size': 4, 'seed': 20260820,
            'labels': 'sequence_floor', 'spatial_mask': 'none', 'flips': False,
            'precision': 'CUDA bfloat16 training; solver internal float32',
            'scope': 'Existing CNN/Transformer and new modules may train; SEA-RAFT frozen/cached',
            'checkpoint_policy': 'best.pt and last.pt per arm; no numbered checkpoint accumulation',
            'reference_head_rule': 'Reset delta/logvar; retain pretrained yaw head',
            'solver_head_rule': 'Reset translation/logvar/yaw residual heads; zero residual output initialization',
            'matched_validation': '104 windows, reference 30, input histories 4/8/12/16/20/24/30, anchor (480,809)',
            'arms': [{'name': name, 'command': common+['--out', str(ROOT/name)]+extra}
                     for name, extra in arms]})
        for name, extra in arms:
            if shutil.disk_usage(ROOT).free < 1536*1024**2:
                raise RuntimeError('Less than 1.5 GiB free; stopping before starting another arm')
            output = ROOT/name
            output.mkdir(exist_ok=False)
            status.update(status='training', current_arm=name, current_log=str(output/'train.log'), updated_utc=stamp())
            save('training_status.json', status)
            command = common+['--out', str(output)]+extra
            with (output/'train.log').open('x') as log:
                result = subprocess.run(command, cwd=SOURCE, env=env, stdin=subprocess.DEVNULL,
                                        stdout=log, stderr=subprocess.STDOUT)
            if result.returncode:
                raise RuntimeError(f'{name} training exited {result.returncode}; inspect {output}/train.log')
            status.update(status='validating', updated_utc=stamp())
            save('training_status.json', status)
            command = [sys.executable, '-B', '-m', 'step2.evaluate_gqft',
                       '--checkpoint', str(output/'best.pt'),
                       '--manifest', str(PROJECT/'results/hsgm_manifest_v1.json'),
                       '--sequences-root', '/data/robotics/toshith/rgbd_vo_dataset/hsgm_sequences',
                       '--split', 'val', '--histories', '4,8,12,16,20,24,30',
                       '--queries', '1', '--batch-size', '4', '--workers', '0',
                       '--target-ground-plane', 'sequence_floor', '--device', 'cuda',
                       '--out', str(output/'fixed_validation.json')]
            with (output/'fixed_validation.log').open('x') as log:
                result = subprocess.run(command, cwd=SOURCE, env=env, stdin=subprocess.DEVNULL,
                                        stdout=log, stderr=subprocess.STDOUT)
            if result.returncode:
                raise RuntimeError(f'{name} validation exited {result.returncode}')
            status['completed_arms'].append(name)
            save(name+'/checkpoint_hashes.json', {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                                for p in [output/'best.pt', output/'last.pt']})
        status.update(status='completed', current_arm=None, finished_utc=stamp())
        save('training_status.json', status)
    except Exception:
        status.update(status='failed', error=traceback.format_exc(), finished_utc=stamp())
        save('training_status.json', status)
        raise


if __name__ == '__main__':
    main()
