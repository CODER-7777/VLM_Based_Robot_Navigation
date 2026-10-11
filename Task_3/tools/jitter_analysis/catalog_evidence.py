"""Inventory project evidence and independently recalculate saved contact comparisons.

Skips installed environments, VCS internals and caches. An inventory is not a
claim to have watched every video frame or validated every training track.
"""
from __future__ import annotations
import argparse
from collections import Counter
import csv
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import torch
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator

import record
from analyze import band_rms, load_run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    entries, json_errors, log_flags = [], [], []
    excludes = {'.git', '.venv', '__pycache__', '.aws', '.codex', '.agents', '.pytest_cache'}
    for base, dirs, files in os.walk(record.ROOT):
        dirs[:] = sorted(d for d in dirs if d not in excludes and
                          not (Path(base) / d).resolve().is_relative_to(args.out.resolve()))
        for name in sorted(files):
            path = Path(base) / name
            if not path.is_file():
                continue
            row = dict(path=str(path.relative_to(record.ROOT)), bytes=path.stat().st_size,
                       suffix=path.suffix.lower())
            if path.suffix in {'.md', '.py', '.json', '.yaml', '.xml', '.csv', '.log', '.TXT'}:
                data = path.read_bytes()
                row['sha256'] = hashlib.sha256(data).hexdigest()
                if path.suffix == '.json':
                    try:
                        json.loads(data)
                    except (ValueError, UnicodeDecodeError) as exc:
                        json_errors.append(dict(path=row['path'], error=str(exc)))
                if path.suffix in {'.log', '.TXT'}:
                    flagged = [line[:400] for line in data.decode(errors='replace').splitlines()
                               if any(x in line for x in ['WARNING', 'Traceback (most recent', 'RuntimeError:', 'CUDA error:'])]
                    if flagged:
                        log_flags.append(dict(path=row['path'], flagged_lines=len(flagged), examples=flagged[:3]))
            entries.append(row)
    record.write_json(args.out / 'inventory.json', entries)
    record.write_json(args.out / 'inventory_summary.json', dict(
        files=len(entries), bytes=sum(r['bytes'] for r in entries),
        by_suffix=dict(Counter(r['suffix'] for r in entries)),
        by_top_directory=dict(Counter(r['path'].split('/')[0] for r in entries)),
        excluded_directories=sorted(excludes), json_errors=json_errors, flagged_logs=log_flags))

    checkpoints = []
    for path in [record.DEFAULT_MODEL, *sorted((record.ROOT / 'xterra_mjlab/evaluation_runs').glob('*/latest.pt'))]:
        data = torch.load(path, map_location='cpu', weights_only=False)
        arguments = data.get('arguments', {})
        if not isinstance(arguments, dict):
            arguments = vars(arguments)
        checkpoints.append(dict(path=str(path.relative_to(record.ROOT)), sha256=record.sha256(path),
                                update=data.get('update'), learning_rate=data.get('learning_rate'),
                                arguments=arguments,
                                model_finite=all(bool(torch.isfinite(v).all()) for v in data['model_state_dict'].values())))
    (args.out / 'checkpoints.json').write_text(json.dumps(checkpoints, indent=2, default=str) + '\n')

    logs = []
    for path in sorted((record.ROOT / 'xterra_mjlab/evaluation_runs').glob('*/events.out.tfevents.*')):
        event = EventAccumulator(str(path), size_guidance={'scalars': 0}).Reload()
        tags = event.Tags().get('scalars', [])
        terms = {}
        for tag in tags:
            if any(k in tag for k in ['action_rate', 'second_difference', 'saturation', 'target_rate', 'track_linear', 'track_angular']):
                values = event.Scalars(tag)
                v = np.array([r.value for r in values])
                terms[tag] = dict(records=len(v), first_step=values[0].step, last_step=values[-1].step,
                                  finite=bool(np.isfinite(v).all()), first50_mean=float(v[:50].mean()),
                                  last50_mean=float(v[-50:].mean()))
        logs.append(dict(path=str(path.relative_to(record.ROOT)), scalar_tag_count=len(tags), terms=terms))
    record.write_json(args.out / 'training_logs.json', logs)

    # Read numeric traces, independently of the historical summary files.
    oldroot = record.ROOT / 'tools/results/control_loop_audit_20261006_v2/validation'
    comparisons = []
    for path in sorted(oldroot.glob('*/*/trace.npz')):
        m, s, d = load_run(path.parent)
        if m.get('diagnostic_case') not in ('legacy', 'legacy_impratio10', 'fresh', 'fresh_impratio10'):
            continue
        mask = (d['time'] >= 5 - 1e-8) & (d['time'] < 11 - 1e-8)
        qb = band_rms(np.degrees(d['q'][mask]), 200)
        ever_platform = np.zeros(4, dtype=bool)
        longest = hold = 0.
        for i in range(len(d['time'])):
            ever_platform |= d['foot_platform_force'][i] > 1
            row = {key: d[key][i] for key in ['foot_pos', 'tilt_deg', 'base_clearance']}
            hold = hold + m['dt'] if record.top_reached(row, ever_platform) else 0.
            longest = max(longest, hold)
        comparisons.append(dict(path=str(path.parent.relative_to(record.ROOT)), outcome=s['outcome'],
                                recorded_traversal=s['outcome'] == 'traversed',
                                independently_verified_traversal=longest >= .5 - 1e-8,
                                max_hold_s=longest, q_band_deg=None if qb is None else float(qb.mean()),
                                target_min=m['target_min'], target_max=m['target_max']))
    record.write_json(args.out / 'historical_raw_recheck.json', comparisons)
    print(json.dumps(dict(files=len(entries), json_errors=len(json_errors),
                          checkpoints=len(checkpoints), training_logs=len(logs), rechecked_runs=len(comparisons))))


if __name__ == '__main__':
    main()
