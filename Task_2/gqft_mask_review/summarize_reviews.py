"""Summarize the preserved episode reviews; all generated files stay in this lab folder."""
from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path
import statistics

LAB = Path(__file__).resolve().parent
os.environ.setdefault('MPLCONFIGDIR', str(LAB / '.cache/matplotlib'))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    manifest = json.loads((LAB / 'import_manifest.json').read_text())
    for item in manifest['files']:
        path = LAB / item['destination']
        if hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            raise ValueError(f'Imported evidence changed: {path}')
    records = []
    keys = ('mean_ground_error_m', 'endpoint_ground_error_m',
            'mean_pixel_error_px', 'endpoint_pixel_error_px')
    for path in sorted((LAB / 'ep629').glob('leg*/*/review.json')):
        data = json.loads(path.read_text())
        if not data['metrics_origin_excluded']:
            raise ValueError('Reviews must use the same origin-excluded error convention')
        if data['history_flow_pairs'] != 24 or data['valid_post_origin_pixel_points'] != 24:
            raise ValueError('These pooled diagnostics require 24 scored poses per window')
        records.append({
            'episode': data['episode_id'], 'leg': data['leg'], 'history': data['history_flow_pairs'],
            'review_file': str(path.relative_to(LAB)), 'reference_endpoint_forward_left_m': data['reference_endpoint_forward_left_m'],
            'unmasked': data['metrics']['unmasked'], 'masked': data['metrics']['masked'],
            'mean_rejected_input_fraction': data['mean_rejected_input_fraction'],
            'mean_rejected_feature_fraction': data['mean_rejected_feature_fraction'],
            'mean_original_attention_on_rejected_cells': data['mean_original_attention_on_rejected_cells'],
            'max_original_attention_on_rejected_cells': data['max_original_attention_on_rejected_cells'],
        })
    if [(r['episode'], r['leg']) for r in records] != [(629, 0), (629, 2), (629, 3), (629, 4)]:
        raise ValueError('Expected exactly the four recorded episode-629 windows')
    aggregate = {}
    for key in keys:
        unmasked = statistics.mean(r['unmasked'][key] for r in records)
        masked = statistics.mean(r['masked'][key] for r in records)
        aggregate[key] = {'unmasked': unmasked, 'masked': masked,
                          'change_percent': 100 * (masked / unmasked - 1)}
    payload = {
        'scope': 'Four 24-pair windows of one recorded episode; frozen checkpoint; not a validation benchmark',
        'windows': len(records), 'scored_post_origin_pose_samples': 96,
        'aggregation': 'Equal-window means; equal 24-pose counts also make mean errors equal to pooled per-pose means. Endpoint errors are four-window means.',
        'positive_change_means': 'higher error, worse',
        'aggregate': aggregate, 'records': records,
        'conclusion': 'The current hard validity mask worsens pooled ground and pixel errors. Leg 2 improves endpoint error, while leg 3 has a severe forward-motion regression.',
    }
    (LAB / 'summary.json').write_text(json.dumps(payload, indent=2) + '\n')
    columns = ['episode', 'leg', 'history'] + [f'{variant}_{key}' for key in keys for variant in ('unmasked', 'masked')]
    with (LAB / 'summary.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for record in records:
            row = {key: record[key] for key in ('episode', 'leg', 'history')}
            for key in keys:
                for variant in ('unmasked', 'masked'):
                    row[f'{variant}_{key}'] = record[variant][key]
            writer.writerow(row)

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    colours = {'unmasked': '#2878b5', 'masked': '#e87524', 'reference': '#235c37'}
    for axis, key, scale, title, unit in [
        (axes[0, 0], 'mean_ground_error_m', 100, 'Average ground-position error', 'cm'),
        (axes[0, 1], 'endpoint_ground_error_m', 100, 'Ground endpoint error', 'cm'),
        (axes[1, 0], 'mean_pixel_error_px', 1, 'Average projected pixel error', 'px'),
    ]:
        for variant, offset in [('unmasked', -.18), ('masked', .18)]:
            values = [r[variant][key] * scale for r in records]
            bars = axis.bar([i + offset for i in range(len(records))], values, width=.34,
                            color=colours[variant], label=variant.capitalize())
            axis.bar_label(bars, labels=[f'{v:.1f}' for v in values], padding=3, fontsize=9)
        axis.set_title(title + ' · lower is better')
        axis.set_ylabel(unit)
        axis.set_ylim(0, axis.get_ylim()[1] * 1.15)
        axis.legend(fontsize=8)
    axis = axes[1, 1]
    for variant, offset in [('reference', -.25), ('unmasked', 0), ('masked', .25)]:
        values = [100 * (r['reference_endpoint_forward_left_m'][0] if variant == 'reference'
                         else r[variant]['endpoint_forward_left_m'][0]) for r in records]
        bars = axis.bar([i + offset for i in range(len(records))], values, width=.24,
                        color=colours[variant], label='Recorded reference' if variant == 'reference' else variant.capitalize())
        axis.bar_label(bars, labels=[f'{v:.1f}' for v in values], padding=3, fontsize=8)
    axis.set(title='Final forward component · compare with green', ylabel='cm')
    axis.set_ylim(0, axis.get_ylim()[1] * 1.15)
    axis.legend(fontsize=8)
    for axis in axes.flat:
        axis.set_xticks(range(len(records)), [f'Leg {r["leg"]}' for r in records])
        axis.set_axisbelow(True)
        axis.grid(axis='y', alpha=.2)
    fig.suptitle('Episode 629: hard masking is worse overall in these four saved windows', fontsize=14)
    fig.text(.5, .02,
             f'96 post-origin poses · mean ground error {aggregate["mean_ground_error_m"]["unmasked"]*100:.2f} → '
             f'{aggregate["mean_ground_error_m"]["masked"]*100:.2f} cm (+{aggregate["mean_ground_error_m"]["change_percent"]:.1f}%)\n'
             'Frozen weights; each window covers only its first 24 flow pairs. This is not a full-episode or validation score.',
             ha='center', fontsize=9)
    fig.tight_layout(rect=(0, .08, 1, .95))
    fig.savefig(LAB / 'summary.png', dpi=160)
    plt.close(fig)
    print(json.dumps({'lab': str(LAB), 'windows': len(records), 'aggregate': aggregate}, indent=2))


if __name__ == '__main__':
    main()
