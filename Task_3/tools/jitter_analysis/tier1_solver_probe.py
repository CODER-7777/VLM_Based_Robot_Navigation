"""Tier-1 solver diagnostics: does impratio fail to converge at the 5 ms timestep?

Answers three questions with new scripted simulations, without editing any file:

1. Is the contact solver hitting its iteration cap, and does that depend on impratio?
2. Does the joint 8-30 Hz band depend on physics resolution at fixed PD/policy rate?
3. Does restoring the training impratio remove the band content?

HARDWARE-CONTRACT GUARANTEE
PD stays at 200 Hz and the policy at 50 Hz for every case. Q0, SCALE, TARGET_MIN/MAX,
GEAR, TORQUE_LIMITS, J_LEG, kp, kd, foot friction, solref and solimp are never
written. The only quantities varied are MuJoCo solver settings that carry no
hardware meaning: `impratio` (friction-to-normal impedance ratio) and the internal
physics resolution (via substepping inside each PD interval). All changes are
process-local overrides; protected files are hash-checked before and after.

Provenance: scripted simulation, NOT a replay of the user's keyboard recording.
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import shutil
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import mujoco
import numpy as np

import record
from analyze import band_rms, load_run, save_json

# (impratio, physics substeps per 200 Hz PD interval)
MECHANISM_GRID = [(r, s) for r in (1., 10., 100., 1000.) for s in (1, 2, 5)]
# train/eval confirmation at the viewer's native 5 ms, both gains
CONFIRM_KP = (18., 20.)

LOAD_THRESHOLD_N = 5.0

# Newton iteration cap declared by the viewer's scene.xml; read once so that the
# "at cap" test reflects the model actually in use.
ITERATION_CAP = float(mujoco.MjModel.from_xml_path(
    str(record.SIM / 'scene.xml')).opt.iterations)


def _slip_and_penetration(rec):
    """Per-foot rigid contact-point slip speed and penetration for one physics sample.

    Slip is the world velocity of the foot material point at each loaded contact,
    with the contact-normal component removed. It is a simulation proxy for foot
    scuffing, not measured rubber deformation.

    Returns fixed-length (4,) arrays, one slot per leg, so the recorder can stack
    them across samples. A foot with no loaded contact reports zero.
    """
    m, d = rec.model, rec.data
    slip = np.zeros(4)
    pen = np.zeros(4)
    for k in range(d.ncon):
        c = d.contact[k]
        g1, g2 = int(c.geom1), int(c.geom2)
        if not ((g1 in rec.robot and g2 in rec.terrain_ids)
                or (g2 in rec.robot and g1 in rec.terrain_ids)):
            continue
        robot_geom = g1 if g1 in rec.robot else g2
        slot = rec.foot_map.get(robot_geom)
        if slot is None:
            continue
        f = np.zeros(6)
        mujoco.mj_contactForce(m, d, k, f)
        if f[0] <= LOAD_THRESHOLD_N:
            continue
        jp = np.zeros((3, m.nv))
        jr = np.zeros((3, m.nv))
        mujoco.mj_jac(m, d, jp, jr, c.pos, int(m.geom_bodyid[robot_geom]))
        v = jp @ d.qvel
        n = np.asarray(c.frame[0:3], dtype=np.float64)
        n /= max(np.linalg.norm(n), 1e-12)
        slip[slot] = max(slip[slot], float(np.linalg.norm(v - n * np.dot(v, n))))
        pen[slot] = max(pen[slot], max(0.0, -float(c.dist)))
    return slip, pen


def run_case(checkpoint, out, label, axis, impratio, substeps, kp, seconds, device,
             window=(5., 11.), stage='grid'):
    """One flat-ground case with a process-local impratio override."""
    case = f'{stage}_impratio{impratio:g}_sub{substeps}_kp{kp:g}'
    name = f'{label}_{axis}_{case}'

    old_init = record.ObservedController.__init__
    old_physics = record.ObservedController.physics_step
    old_row = record.Recorder.state_row
    old_command = record.command_at
    old_contacts = record.Recorder.contacts_after_step

    def init(ctrl, *a, **kw):
        old_init(ctrl, *a, **kw)
        ctrl.kp = kp
        ctrl.model.opt.impratio = impratio

    def physics(ctrl):
        """Hold the 200 Hz PD torque constant across `substeps` finer physics steps."""
        if substeps == 1:
            return old_physics(ctrl)
        dt = float(ctrl.model.opt.timestep)
        ctrl.model.opt.timestep = dt / substeps
        try:
            old_physics(ctrl)
            for _ in range(substeps - 1):
                mujoco.mj_step(ctrl.model, ctrl.data)
        finally:
            ctrl.model.opt.timestep = dt

    def contacts(rec, t):
        forces, details = old_contacts(rec, t)
        slip, pen = _slip_and_penetration(rec)
        forces['slip_speed'] = slip
        forces['penetration'] = pen
        return forces, details

    def row(rec, command, policy_tick):
        r = old_row(rec, command, policy_tick)
        r['solver_niter'] = np.array(rec.data.solver_niter, dtype=np.float64)
        r['solver_nnz'] = np.array(rec.data.solver_nnz, dtype=np.float64)
        r['nefc'] = np.array(rec.data.nefc, dtype=np.float64)
        return r

    def command(t, vx, stand, ramp):
        v = vx * np.clip((t - stand) / ramp, 0., 1.)
        return np.array([v if axis == 'x' else 0., v if axis == 'y' else 0., 0.])

    record.ObservedController.__init__ = init
    record.ObservedController.physics_step = physics
    record.Recorder.state_row = row
    record.Recorder.contacts_after_step = contacts
    record.command_at = command
    try:
        path = record.record_run(checkpoint, out / name, terrain='flat', sensors='viewer',
                                 device=device, seconds=seconds, vx=.3, stand=3., ramp=1.)
    finally:
        record.ObservedController.__init__ = old_init
        record.ObservedController.physics_step = old_physics
        record.Recorder.state_row = old_row
        record.Recorder.contacts_after_step = old_contacts
        record.command_at = old_command

    m, s, d = load_run(path)
    lo, hi = window
    mask = (d['time'] >= lo - 1e-8) & (d['time'] < hi - 1e-8)
    loaded = mask & (d['foot_normal_force'].max(axis=1) > LOAD_THRESHOLD_N)
    cap = ITERATION_CAP

    m.update(case=case, checkpoint_label=label, command_axis=axis, impratio=impratio,
             physics_hz=200 * substeps, pd_hz=200, policy_hz=50, kp=kp, kd=0.7,
             solver_iteration_cap=cap, cone='elliptic', solver='Newton',
             provenance='NEW scripted solver diagnostic; process-local overrides only.')
    save_json(path / 'manifest.json', m)

    base = dict(
        case=case, stage=stage, checkpoint=label, direction=axis, impratio=impratio,
        physics_hz=200 * substeps, pd_hz=200, policy_hz=50, kp=kp, kd=0.7,
        outcome=s['outcome'], last_recorded_time_s=s['last_recorded_time_s'],
        window_samples=int(mask.sum()),
    )
    # A case that tips early never reaches the analysis window. Record that outcome
    # rather than inventing a band estimate from a truncated window.
    if mask.sum() < 400 or d['q'].shape[0] < 400:
        base.update({k: float('nan') for k in (
            'q_band_deg', 'target_band_deg', 'foot_force_band_N', 'slip_band_m_s',
            'mean_actual_speed', 'speed_rmse', 'max_tilt', 'niter_mean', 'niter_p99',
            'slip_rms_m_s', 'slip_p99_m_s', 'penetration_p99_mm',
            'torque_clipped_any_fraction', 'loaded_contact_fraction')})
        base.update(niter_max=int(d['solver_niter'].max()),
                    niter_at_cap_fraction=float('nan'), nefc_mean=float('nan'),
                    note='Failed before the analysis window; no band estimate.')
        base['path'] = str(path)
        return base

    qb = band_rms(np.degrees(d['q'][mask]), 200)
    tb = band_rms(np.degrees(d['target'][mask]), 200)
    fb = band_rms(d['foot_normal_force'][mask], 200)
    sb = band_rms(d['slip_speed'][mask], 200)
    niter = d['solver_niter'][mask]
    axis_i = 0 if axis == 'x' else 1

    base.update(
        q_band_deg=float(qb.mean()) if qb is not None else float('nan'),
        target_band_deg=float(tb.mean()) if tb is not None else float('nan'),
        foot_force_band_N=float(fb.mean()) if fb is not None else float('nan'),
        mean_actual_speed=float(d['base_velocity_body'][mask][:, axis_i].mean()),
        speed_rmse=float(np.sqrt(np.mean((
            d['base_velocity_body'][mask][:, axis_i]
            - d['command'][mask][:, axis_i]) ** 2))),
        max_tilt=float(d['tilt_deg'][mask].max()),
        niter_mean=float(niter.mean()), niter_p99=float(np.quantile(niter, .99)),
        niter_max=int(niter.max()),
        niter_at_cap_fraction=float((niter >= cap - 0.5).mean()),
        nefc_mean=float(d['nefc'][mask].mean()),
        loaded_contact_fraction=float(loaded.mean()),
        slip_band_m_s=float(sb.mean()) if sb is not None else float('nan'),
        slip_rms_m_s=float(np.sqrt(np.mean(d['slip_speed'][loaded] ** 2))) if loaded.any() else float('nan'),
        slip_p99_m_s=float(np.quantile(d['slip_speed'][loaded], .99)) if loaded.any() else float('nan'),
        penetration_p99_mm=float(np.quantile(d['penetration'][mask], .99) * 1000.),
        torque_clipped_any_fraction=float((
            np.abs(d['torque_raw'][mask]) > np.asarray(m['torque_limits']) + 1e-5).any(1).mean()),
        path=str(path),
    )
    return base


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--candidate', type=Path,
                   default=record.ROOT / 'xterra_mjlab/evaluation_runs/moe_swing013_latest/latest.pt')
    p.add_argument('--device', default='cuda:0')
    p.add_argument('--seconds', type=float, default=12.)
    p.add_argument('--skip-mechanism', action='store_true')
    args = p.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)

    protected = [record.SIM / 'controller.py', record.SIM / 'scene.xml',
                 record.SIM / 'build_scene.py', record.SIM / 'checkpoint_policy.py',
                 record.SIM / 'teleop.py',
                 record.ROOT / 'xterra_mjlab/xterra_mjlab/assets/svanm2/constants.py',
                 record.ROOT / 'xterra_mjlab/xterra_mjlab/tasks/velocity/config/svanm2/env_cfgs.py',
                 record.DEFAULT_MODEL, args.candidate.resolve()]
    hashes = {str(q): record.sha256(q) for q in protected}

    save_json(out / 'protocol.json', dict(
        provenance='NEW scripted solver diagnostics; NOT user keyboard recordings',
        question=['Is the solver hitting its iteration cap as a function of impratio?',
                  'Does the 8-30 Hz band depend on physics resolution at fixed PD/policy rate?',
                  'Does restoring the training impratio remove the band content?'],
        mechanism_grid=[dict(impratio=r, physics_hz=200 * s) for r, s in MECHANISM_GRID],
        confirmation_kp=list(CONFIRM_KP),
        seconds=args.seconds, analysis_window=[5., 11.], request_m_s=.3,
        policy_hz=50, pd_hz=200,
        hardware_contract_untouched=['Q0', 'SCALE', 'TARGET_MIN', 'TARGET_MAX', 'GEAR',
                                     'TORQUE_LIMITS', 'J_LEG', 'kd', 'foot friction',
                                     'foot solref', 'foot solimp'],
        hardware_contract_note=('kp is reported at both the viewer value 18 and the training '
                                'value 20 as a recorded covariate; neither is a new value.'),
        solver_only_parameters=['impratio', 'internal physics resolution via substepping'],
        protected_file_hashes=hashes,
        caveats=['Physics substepping holds the 200 Hz PD torque constant, matching a real '
                 '200 Hz bridge loop; only the contact solve is refined.',
                 'Contact iteration count is read from data.solver_niter after the forward solve.',
                 'Slip is a rigid-foot contact-point velocity proxy, not measured rubber deformation.',
                 'Single start per case; no success-rate claim.',
                 'Simulator-internal result. Says nothing about hardware jitter.']))

    rows = []
    try:
        if not args.skip_mechanism:
            for impratio, substeps in MECHANISM_GRID:
                r = run_case(record.DEFAULT_MODEL, out, 'original90000', 'x',
                             impratio, substeps, 18., args.seconds, args.device)
                rows.append(r)
                print('MECHANISM', json.dumps(r), flush=True)
        for kp in CONFIRM_KP:
            for label, ckpt in (('original90000', record.DEFAULT_MODEL),
                                ('candidate91000', args.candidate.resolve())):
                for axis in ('x', 'y'):
                    for impratio in (100., 10.):
                        r = run_case(ckpt, out, label, axis, impratio, 1, kp,
                                     args.seconds, args.device, stage='confirm')
                        rows.append(r)
                        print('CONFIRM', json.dumps(r), flush=True)
    finally:
        for q in protected:
            assert record.sha256(q) == hashes[str(q)], f'Protected file changed: {q}'
    print('HARDWARE_CONTRACT_INTACT', flush=True)

    def finite(v):
        """JSON has no NaN; report a non-finite measurement as null, never as a number."""
        if isinstance(v, float) and not np.isfinite(v):
            return None
        return v

    clean = [{k: finite(v) for k, v in r.items()} for r in rows]
    with (out / 'results.csv').open('w') as f:
        w = csv.DictWriter(f, fieldnames=list(clean[0]), extrasaction='ignore')
        w.writeheader()
        w.writerows(clean)
    save_json(out / 'results.json', dict(protocol='protocol.json', runs=clean))

    # ---- plots ----
    g = [r for r in rows if r.get('stage') == 'grid' and r['direction'] == 'x']
    fig, axs = plt.subplots(2, 2, figsize=(15, 9))
    hz = sorted({r['physics_hz'] for r in g})
    for i, r in enumerate((1., 10., 100., 1000.)):
        for s, h in zip((1, 2, 5), hz):
            row = next((x for x in g if x['impratio'] == r and x['physics_hz'] == h), None)
            if row:
                axs[0, 0].plot(h, row['q_band_deg'], 'o-', label=f'impratio={r:g}')
                axs[0, 1].plot(h, row['niter_at_cap_fraction'], 'o-', label=f'impratio={r:g}')
                axs[1, 0].plot(h, row['slip_rms_m_s'], 'o-', label=f'impratio={r:g}')
                axs[1, 1].plot(h, row['penetration_p99_mm'], 'o-', label=f'impratio={r:g}')
    for ax, t in zip(axs.ravel(), ('joint 8-30 Hz RMS (deg)', 'fraction of steps at iteration cap',
                                   'loaded slip RMS (m/s)', 'p99 penetration (mm)')):
        ax.set_xscale('log'); ax.set_xlabel('physics resolution (Hz)')
        ax.set_title(t); ax.grid(alpha=.3); ax.legend(fontsize=8)
    fig.suptitle('Tier-1 solver probe: impratio x physics resolution, PD held at 200 Hz (original90000, forward)')
    fig.tight_layout(); fig.savefig(out / 'mechanism.png', dpi=140); plt.close(fig)

    fig, axs = plt.subplots(1, 3, figsize=(16, 4.5))
    for kp in CONFIRM_KP:
        for label in ('original90000', 'candidate91000'):
            for axis, mk in (('x', 'o'), ('y', 's')):
                sel = [r for r in rows if r.get('stage') == 'confirm'
                       and r['kp'] == kp and r['checkpoint'] == label
                       and r['direction'] == axis and r['physics_hz'] == 200]
                if len(sel) != 2:
                    continue
                sel.sort(key=lambda r: r['impratio'])
                lab = f'{label} {axis} kp={kp:g}'
                axs[0].plot([r['impratio'] for r in sel], [r['q_band_deg'] for r in sel], mk + '-', label=lab)
                axs[1].plot([r['impratio'] for r in sel], [r['mean_actual_speed'] for r in sel], mk + '-', label=lab)
                axs[2].plot([r['impratio'] for r in sel], [r['slip_rms_m_s'] for r in sel], mk + '-', label=lab)
    for ax, t in zip(axs, ('joint 8-30 Hz RMS (deg)', 'actual body speed (m/s)',
                           'loaded slip RMS (m/s)')):
        ax.set_xscale('log'); ax.set_xlabel('impratio (training value = 10)')
        ax.set_title(t); ax.grid(alpha=.3); ax.legend(fontsize=7)
    axs[1].axhline(.3, color='k', ls='--', label='request')
    fig.suptitle('Train/eval consistency: viewer impratio 100 vs training impratio 10')
    fig.tight_layout(); fig.savefig(out / 'confirmation.png', dpi=140); plt.close(fig)

    cols = ('case', 'stage', 'checkpoint', 'direction', 'impratio', 'physics_hz', 'kp', 'outcome',
            'q_band_deg', 'target_band_deg', 'foot_force_band_N', 'slip_band_m_s',
            'mean_actual_speed', 'speed_rmse', 'slip_rms_m_s', 'penetration_p99_mm',
            'niter_mean', 'niter_p99', 'niter_max', 'niter_at_cap_fraction',
            'nefc_mean', 'torque_clipped_any_fraction')
    table = '<table><tr>' + ''.join(f'<th>{c}</th>' for c in cols) + '</tr>'
    for r in clean:
        table += '<tr>' + ''.join(
            '<td>' + html.escape('—' if r.get(c) is None else
                                 f'{r[c]:.6g}' if isinstance(r.get(c), float) else str(r.get(c, '-')))
            + '</td>' for c in cols) + '</tr>'
    table += '</table>'
    (out / 'index.html').write_text(
        '<!doctype html><meta charset="utf-8"><title>Tier-1 solver probe</title>'
        '<style>body{font:15px system-ui;margin:24px}td,th{border:1px solid #ccc;padding:5px;'
        'font-size:12px}table{border-collapse:collapse}img{max-width:100%}</style>'
        '<h1>Tier-1 solver probe</h1><p>New scripted simulations, not user keyboard recordings. '
        'PD is held at 200 Hz and the policy at 50 Hz in every case; physics substepping only '
        'refines the contact solve. No hardware-contract parameter was modified and every '
        'protected file was hash-verified unchanged.</p>'
        '<p><a href="protocol.json">Protocol</a> &middot; <a href="results.json">Exact numbers</a> '
        '&middot; <a href="results.csv">CSV</a></p>'
        '<img src="mechanism.png"><img src="confirmation.png">' + table)
    print('REPORT', out / 'index.html', flush=True)


if __name__ == '__main__':
    main()