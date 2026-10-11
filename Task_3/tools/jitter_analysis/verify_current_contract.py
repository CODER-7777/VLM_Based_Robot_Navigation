"""Recheck contact sensitivity under today's limits, with fixed contact time constants.

Fresh scripted CPU simulations, not hardware data or keyboard-session replays.
No runtime file, checkpoint, target limit, gain, or transmission is changed.
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path

import mujoco
import numpy as np

import record
from analyze import band_rms, load_run


def measure(path):
    m, s, d = load_run(path)
    axis = m['test_axis']
    # Fixed full window for flat comparisons; contact-aligned stair diagnostics
    # carry their duration and must not be ranked as matched fixed-state tests.
    lo, hi = (5., 11.) if m['terrain'] == 'flat' else (
        s['first_stair_contact_s'] or 5., (s['first_stair_contact_s'] or 5.) + 6.)
    mask = (d['time'] >= lo - 1e-8) & (d['time'] < hi - 1e-8)
    ticks = mask & d['policy_tick']
    qb = band_rms(np.degrees(d['q'][mask]), 200)
    tb = band_rms(np.degrees(d['target'][ticks]), 50, 8, 20)
    ax = 0 if axis == 'x' else 1
    row = dict(run=path.name, checkpoint=m['test_checkpoint'], terrain=m['terrain'],
               axis=axis, case=m['test_case'], start=m['test_start'],
               outcome=s['outcome'], end_s=s['last_recorded_time_s'],
               first_contact_s=s['first_stair_contact_s'], window_start=lo,
               window_seconds=float(mask.sum() * .005), complete_window=bool(mask.sum() == 1200),
               q_band_deg=None if qb is None else float(qb.mean()),
               target_band_deg=None if tb is None else float(tb.mean()),
               max_base_x=float(d['base_pos'][:, 0].max()),
               max_tilt_all=float(d['tilt_deg'].max()),
               warnings=s['warnings'], path=str(path.relative_to(record.ROOT)))
    if mask.any():
        row.update(mean_speed=float(d['base_velocity_body'][mask, ax].mean()),
                   speed_rmse=float(np.sqrt(np.mean((d['base_velocity_body'][mask, ax]
                                                    - d['command'][mask, ax])**2))),
                   heading_change_deg=float(np.degrees(np.unwrap(d['yaw_rad'][mask])[-1]
                                                       - np.unwrap(d['yaw_rad'][mask])[0])),
                   target_clipped_fraction=float((np.abs(d['target_removed'][mask]) > 1e-6).mean()),
                   torque_clipped_any_fraction=float((np.abs(d['torque_raw'][mask])
                       > np.asarray(m['torque_limits']) + 1e-5).any(axis=1).mean()))
    record.write_json(path / 'verification_metrics.json', row)
    return row


def run_case(out, checkpoint, label, terrain, axis, case, start, seconds):
    old_init = record.ObservedController.__init__
    old_physics = record.ObservedController.physics_step
    old_command = record.command_at
    substeps = 5 if case == 'fixed_contact_sub5' else 1

    def init(ctrl, *args, **kwargs):
        old_init(ctrl, *args, **kwargs)
        if case == 'impratio10':
            ctrl.model.opt.impratio = 10.
        if case.startswith('fixed_contact'):
            # Freeze the positive time-constant floor at the baseline 5 ms
            # timestep BEFORE changing resolution; unlike the old tier-1 grid.
            positive = ctrl.model.geom_solref[:, 0] > 0
            ctrl.model.geom_solref[positive, 0] = np.maximum(
                ctrl.model.geom_solref[positive, 0], 2 * ctrl.model.opt.timestep)

    def physics(ctrl):
        dt = float(ctrl.model.opt.timestep)
        ctrl.model.opt.timestep = dt / substeps
        try:
            old_physics(ctrl)  # Recompute PD only once per 5 ms, then hold torque.
            for _ in range(substeps - 1):
                mujoco.mj_step(ctrl.model, ctrl.data)
        finally:
            ctrl.model.opt.timestep = dt

    def command(t, vx, stand, ramp):
        value = vx * np.clip((t - stand) / ramp, 0., 1.)
        return np.array([value if axis == 'x' else 0., value if axis == 'y' else 0., 0.])

    record.ObservedController.__init__ = init
    record.ObservedController.physics_step = physics
    record.command_at = command
    try:
        path = record.record_run(checkpoint, out / f'{label}_{terrain}_{axis}_{case}_s{start}',
                                 terrain=terrain, sensors='viewer', device='cpu', seconds=seconds,
                                 y_offset=start * .03, yaw_offset=start * .02)
    finally:
        record.ObservedController.__init__ = old_init
        record.ObservedController.physics_step = old_physics
        record.command_at = old_command
    m = json.loads((path / 'manifest.json').read_text())
    m.update(test_checkpoint=label, test_axis=axis, test_case=case, test_start=start,
             impratio=10 if case == 'impratio10' else 100, physics_substeps=substeps,
             physics_dt=.005 / substeps, pd_dt=.005, policy_dt=.02,
             sampling='State/target sampled at 200 Hz; substep contact forces are LAST solve, not interval averages.',
             intervention_source_sha256=record.sha256(__file__))
    record.write_json(path / 'manifest.json', m)
    return measure(path)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--terrain', choices=['flat', 'stairs'], default='flat')
    p.add_argument('--cases', nargs='+', default=['baseline', 'impratio10', 'fixed_contact', 'fixed_contact_sub5'],
                   choices=['baseline', 'impratio10', 'fixed_contact', 'fixed_contact_sub5'])
    p.add_argument('--starts', nargs='+', type=int, default=[0])
    p.add_argument('--checkpoints', nargs='+', default=['original90000', 'newest91000'],
                   choices=['original90000', 'newest91000'])
    a = p.parse_args()
    a.out = a.out.resolve()
    a.out.mkdir(parents=True, exist_ok=False)
    checkpoints = dict(original90000=record.DEFAULT_MODEL,
                       newest91000=record.ROOT / 'xterra_mjlab/evaluation_runs/moe_swing013_latest/latest.pt')
    protected = [record.SIM / 'controller.py', record.SIM / 'scene.xml',
                 Path(record.__file__), Path(__file__), *checkpoints.values()]
    before = {str(f): record.sha256(f) for f in protected}
    shutil.copy2(__file__, a.out / Path(__file__).name)
    record.write_json(a.out / 'protocol.json', dict(
        protected_hashes=before, cases=a.cases, starts=a.starts, checkpoints=a.checkpoints,
        terrain=a.terrain, command_m_s=.3, policy_hz=50, pd_hz=200,
        target_min=record.original.TARGET_MIN.tolist(), target_max=record.original.TARGET_MAX.tolist(),
        bounds='Current controller, NOT the wider October 7 contract.',
        sensing='legacy, held constant within every pair; substeps change the age of legacy derived sensors',
        caveat='Deterministic offsets are sensitivity cases, not independently trained seeds.'))
    rows = []
    try:
        for label in a.checkpoints:
            for axis in (['x', 'y'] if a.terrain == 'flat' else ['x']):
                for start in a.starts:
                    for case in a.cases:
                        rows.append(run_case(a.out, checkpoints[label], label, a.terrain, axis, case, start,
                                             12. if a.terrain == 'flat' else 40.))
                        record.write_json(a.out / 'results.json', rows)
    finally:
        after = {str(f): record.sha256(f) for f in protected}
        record.write_json(a.out / 'integrity.json', dict(before=before, after=after, unchanged=before == after))
        assert before == after, 'Protected source/weights changed during experiment'
    keys = list(dict.fromkeys(k for row in rows for k in row))
    with (a.out / 'results.csv').open('w') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == '__main__':
    main()
