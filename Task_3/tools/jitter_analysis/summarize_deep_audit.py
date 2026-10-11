"""Plot and verify the saved October 10 CPU study; never runs a simulation."""
from __future__ import annotations
import argparse
import html
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from analyze import load_run, save_json
import record


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    out = args.out.resolve()
    flat = json.loads((out / 'flat/results.json').read_text())
    stairs = json.loads((out / 'stairs/results.json').read_text())
    checkpoints = ['original90000', 'newest91000']
    cases = ['baseline', 'impratio10', 'fixed_contact_sub5']
    labels = ['100 / 5 ms', '10 / 5 ms', '100 / 1 ms, fixed contact']
    colors = ['#aa4433', '#287b55', '#3e64ac']
    pairs = []
    baseline_equivalence = []
    for checkpoint in checkpoints:
        for axis in ['x', 'y']:
            select = {r['case']: r for r in flat if r['checkpoint'] == checkpoint and r['axis'] == axis}
            b, c = select['baseline'], select['impratio10']
            pairs.append(dict(checkpoint=checkpoint, axis=axis,
                              q_reduction_percent=100 * (1 - c['q_band_deg'] / b['q_band_deg']),
                              speed_change=c['mean_speed'] - b['mean_speed'],
                              rmse_change=c['speed_rmse'] - b['speed_rmse']))
            _, _, d = load_run(record.ROOT / b['path'])
            _, _, fixed = load_run(record.ROOT / select['fixed_contact']['path'])
            baseline_equivalence.append(dict(checkpoint=checkpoint, axis=axis,
                q_exact_equal=bool(np.array_equal(d['q'], fixed['q'])),
                target_exact_equal=bool(np.array_equal(d['target'], fixed['target']))))
    fig, axs = plt.subplots(2, 2, figsize=(13, 8))
    groups = [(c, a) for c in checkpoints for a in ['x', 'y']]
    for i, case in enumerate(cases):
        rows = [next(r for r in flat if (r['checkpoint'], r['axis']) == group and r['case'] == case)
                for group in groups]
        for ax, key in zip(axs.flat, ['q_band_deg', 'mean_speed', 'speed_rmse', 'target_band_deg']):
            ax.bar(np.arange(4) + (i - 1) * .25, [r[key] for r in rows], .24,
                   label=labels[i], color=colors[i])
    titles = ['Measured joint 8–30 Hz RMS (degrees)', 'Mean commanded-axis body speed (m/s)',
              'Commanded-axis tracking RMSE (m/s)', 'Policy target 8–20 Hz RMS (degrees)']
    for ax, title in zip(axs.flat, titles):
        ax.set_title(title)
        ax.set_xticks(np.arange(4), ['90k X', '90k Y', 'new 91k X', 'new 91k Y'])
        ax.grid(axis='y', alpha=.2)
    axs[0, 1].axhline(.3, color='k', linestyle='--', label='Requested 0.30 m/s')
    axs[0, 0].legend(fontsize=8)
    axs[0, 1].legend(fontsize=8)
    fig.suptitle('Current tighter targets; fixed 5–11 s windows; CPU; 50 Hz policy / 200 Hz PD')
    fig.tight_layout()
    fig.savefig(out / 'current_flat_comparison.png', dpi=155)
    plt.close(fig)

    verifications = []
    fig, axs = plt.subplots(2, 3, figsize=(15, 8), sharex=True, sharey=True)
    for ci, checkpoint in enumerate(checkpoints):
        for si, start in enumerate([-1, 0, 1]):
            ax = axs[ci, si]
            for case, label, color in zip(cases, labels, colors):
                row = next(r for r in stairs if r['checkpoint'] == checkpoint and
                           r['start'] == start and r['case'] == case)
                m, s, d = load_run(record.ROOT / row['path'])
                ax.plot(d['time'], d['base_pos'][:, 0], color=color,
                        label=f'{label}: {s["outcome"]}')
                # Recompute traversal directly from numeric fields, independently
                # of record.top_reached() and the saved outcome string.
                feet = d['foot_pos']
                loaded = np.maximum.accumulate(d['foot_platform_force'] > 1, axis=0).all(axis=1)
                good = ((feet[:, :, 0] > 3.622).all(axis=1)
                        & (np.abs(feet[:, :, 1] + 9.5) < 1.).all(axis=1)
                        & loaded & (d['tilt_deg'] < 30.) & (d['base_clearance'] > .18))
                longest = count = 0
                for value in good:
                    count = count + 1 if value else 0
                    longest = max(count, longest)
                verified = longest * m['dt'] >= .5 - 1e-8
                if verified != (s['outcome'] == 'traversed'):
                    raise AssertionError(f'Traversal disagreement: {row["path"]}')
                verifications.append(dict(run=row['run'], verified_traversal=verified,
                                          max_valid_hold_s=longest * m['dt'],
                                          all_feet_ever_loaded_platform=bool(loaded[-1])))
            ax.set_title(f'{checkpoint}, start {start:+d}')
            ax.axhline(3.6, color='gray', linestyle=':', label='Platform front (base x alone is insufficient)')
            ax.set_xlabel('Simulation time (s)')
            ax.set_ylabel('Base world x (m)')
            ax.grid(alpha=.2)
            ax.legend(fontsize=6.5)
    fig.suptitle('All 18 current-contract stair outcomes, including failures; no steering rescue')
    fig.tight_layout()
    fig.savefig(out / 'current_stair_progress.png', dpi=155)
    plt.close(fig)

    # One successful pair: check changes in targets, velocities, and contact
    # alongside body motion; avoid assigning causality from apparent lead/lag.
    fig, axs = plt.subplots(5, 1, figsize=(13, 11), sharex=True)
    for case, color in zip(cases[:2], colors[:2]):
        row = next(r for r in stairs if r['checkpoint'] == 'original90000' and r['start'] == 0 and r['case'] == case)
        m, s, d = load_run(record.ROOT / row['path'])
        t = d['time']
        axs[0].plot(t, d['base_pos'][:, 0], color=color, label=f'{case}: {s["outcome"]}')
        axs[1].plot(t, np.degrees(d['q'][:, 2]), color=color, alpha=.8)
        ticks = d['policy_tick']
        axs[2].step(t[ticks], np.degrees(d['target'][ticks, 2]), color=color, where='post', alpha=.8)
        axs[3].plot(t, d['torque_applied'][:, 1], color=color, alpha=.65)
        axs[4].plot(t, d['tilt_deg'], color=color)
    for ax, ylabel in zip(axs, ['Base world x (m)', 'FL calf angle (deg)', 'FL calf target (deg)',
                                'FL thigh torque (Nm)', 'Base tilt (deg)']):
        ax.set_ylabel(ylabel)
        ax.grid(alpha=.2)
    axs[0].legend()
    axs[-1].set_xlabel('Simulation time (s)')
    fig.suptitle('Original90000, center start: contact intervention in the full feedback loop')
    fig.tight_layout()
    fig.savefig(out / 'stair_pair_signals.png', dpi=155)
    plt.close(fig)

    save_json(out / 'verification.json', dict(flat_pairs=pairs,
        fixed_contact_baseline_equivalence=baseline_equivalence, stair_verifications=verifications,
        runs=34, devices=['cpu'], training_launched=False,
        caveat='Three deterministic starts per checkpoint; no hardware validation or independent training seeds.'))
    cols = ['checkpoint', 'terrain', 'axis', 'case', 'start', 'outcome', 'q_band_deg', 'mean_speed',
            'speed_rmse', 'window_seconds', 'complete_window']
    table = '<table><tr>' + ''.join(f'<th>{k}</th>' for k in cols) + '</tr>'
    for row in flat + stairs:
        table += '<tr>' + ''.join('<td>' + html.escape(str(round(row[k], 5) if isinstance(row.get(k), float)
                                                       else row.get(k))) + '</td>' for k in cols) + '</tr>'
    table += '</table>'
    (out / 'index.html').write_text(
        '<!doctype html><meta charset="utf-8"><title>October 10 jitter recheck</title>'
        '<style>body{font:16px system-ui;max-width:1300px;margin:24px auto;padding:0 20px}'
        'img{max-width:100%}table{border-collapse:collapse;font-size:12px}td,th{border:1px solid #ccc;padding:5px}</style>'
        '<h1>Current-contract jitter recheck — 34 CPU-only simulations</h1>'
        '<p>No training or GPU evaluation. Current tighter joint targets, kp=18, kd=0.7, fixed checkpoints.</p>'
        '<p>Impratio 10 reduced flat joint-band RMS by 63.5–70.5%. It enabled 3/6 stair cases versus 0/6 at 100. '
        'Original90000 sideways tracking worsened. A useful simulator mitigation, not a complete hardware jitter fix.</p>'
        '<p><a href="../../../notes/23_DEEP_JITTER_ANALYSIS_20261010.md">Detailed report</a> · '
        '<a href="verification.json">Raw-trace verification</a> · <a href="flat/results.csv">Flat CSV</a> · '
        '<a href="stairs/results.csv">Stair CSV</a> · <a href="catalog/inventory_summary.json">Inventory</a></p>'
        '<p>Flat windows are all 5–11 s. Stair band metrics use the first six seconds after contact, '
        'truncated at termination, and are not matched gait-phase comparisons. Read completion and speed with vibration.</p>'
        '<img src="current_flat_comparison.png"><img src="current_stair_progress.png">'
        '<img src="stair_pair_signals.png">' + table)
    print(json.dumps(dict(flat_pairs=pairs, verified_stair_completions=sum(r['verified_traversal'] for r in verifications))))


if __name__ == '__main__':
    main()
