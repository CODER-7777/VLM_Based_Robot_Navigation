"""Summarize preserved pilot logs and matched validation, without inference."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ARMS = ('reference', 'masked_only', 'yaw_local_only', 'masked_yaw_local')
LABELS = {'reference': 'Reference (attention + yaw auxiliary)',
          'masked_only': 'Soft masking only',
          'yaw_local_only': 'Yaw-local integration only',
          'masked_yaw_local': 'Soft masking + yaw-local integration',
          'pretrained_yaw': 'Original pretrained attention + yaw'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('evaluation_dir', type=Path)
    args = parser.parse_args()
    root = args.evaluation_dir
    provenance = json.loads((root/'provenance.json').read_text())
    # Check that mask/integration and output location are the only arm differences.
    for field, permitted in [('args', {'spatial_mask', 'motion_integration', 'out'}),
                             ('model_config', {'spatial_mask', 'motion_integration'})]:
        reference_settings = provenance['arms']['reference']['checkpoints']['best.pt'][field]
        for arm in ARMS:
            settings = provenance['arms'][arm]['checkpoints']['best.pt'][field]
            assert {k: v for k, v in settings.items() if k not in permitted} == {
                k: v for k, v in reference_settings.items() if k not in permitted}, (arm, field)
    results = {arm: json.loads((root/f'{arm}.json').read_text())
               for arm in (*ARMS, 'pretrained_yaw')}
    records = []
    for arm, payload in results.items():
        assert payload['split'] == 'val' and payload['reference_history'] == 30
        assert payload['fixed_reference_tasks']
        for row in payload['histories']:
            assert row['queries'] == row['signature_samples'] == 104
            assert row['signature_sequences'] == 26
            assert row['visible_points'] == 104*(row['history']+1)
            assert row.get('empty_mask_frames', 0) == 0
            records.append({'arm': arm, 'history': row['history'],
                            'ade_px': row['ade_px'], 'fde_px': row['fde_px'],
                            'ambiguity': row['signature_ambiguity'],
                            'close_pairs': row['signature_close_pairs'],
                            'retrieval_gap_m': row['nn_full_curve_gap_m_mean']})
    with (root/'comparison.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    h24 = {arm: next(x for x in payload['histories'] if x['history'] == 24)
           for arm, payload in results.items()}
    reference = h24['reference']['ade_px']
    best = min(ARMS, key=lambda arm: h24[arm]['ade_px'])
    text = [
        '# Completed four-arm GQFT pilot — 19 October 2026', '',
        f"Server run: `{provenance['pilot']}`.", '',
        'All four arms completed 500 steps with a 500-step finite streak. '
        'Both best and last checkpoints are at step 500. Staged source hashes '
        'were verified before evaluation. Evaluation used physical GPU 7.', '',
        '## Training-time validation', '',
        'These are mixed-history training validation scores (260 queries). '
        'They are separate from the fixed-window results below.', '',
        '| Arm | ADE (px) | FDE (px) |', '| --- | ---: | ---: |',
    ]
    for arm in ARMS:
        row = provenance['arms'][arm]['validation'][-1]
        text.append(f"| {LABELS[arm]} | {row['ade_px']:.4f} | {row['fde_px']:.4f} |")
    text += ['', '## Matched validation at history 24', '',
             'All models see the same 104 reference windows from 26 validation '
             'sequences, with one extended anchor query per window. Reference '
             'horizon is 30 flow pairs; only model inputs are truncated. Pixel '
             'ADE includes the origin and all reference-valid points (2,600 at '
             'history 24), independent of the predicted stopping gate. Labels '
             'use sequence_floor, seed 20260820, virtual extension 270 px. '
             'Precision is the existing evaluator’s CUDA bfloat16 autocast.', '',
             '| Arm | ADE (px) | FDE (px) | ADE change vs pilot reference | Selected history* |',
             '| --- | ---: | ---: | ---: | ---: |']
    for arm, payload in results.items():
        row = h24[arm]
        delta = 100*(row['ade_px']/reference-1)
        selected = payload['shortest_sufficient_history']
        text.append(f"| {LABELS[arm]} | {row['ade_px']:.4f} | {row['fde_px']:.4f} | "
                    f"{delta:+.2f}% | {selected if selected is not None else 'none'} |")
    text += ['', '*Selected among 4, 8, 12, 16, 20, 24 and 30. The gate uses '
             'cross-sequence embedding retrieval of full 31-point reference '
             'curves: retrieval gap within 2% of the best equal/longer history '
             'and ambiguity ≤0.05 among cosine-near pairs (cosine ≥0.995; '
             'different curves >0.10 m apart). These are sequences, not '
             'necessarily different houses. This is not proof of unambiguous '
             'motion in all environments.', '',
             '## Interpretation and next step', '',
             f'The lowest fixed-history-24 pilot ADE belongs to **{LABELS[best]}**. '
             'Use the fixed-window table when judging long-horizon motion; '
             'a mixed-history average can hide a regression there.', '',
             f"Masking alone increases H24 ADE by {100*(h24['masked_only']['ade_px']/reference-1):.2f}%. "
             f"Adding masking to yaw-local increases ADE by "
             f"{100*(h24['masked_yaw_local']['ade_px']/h24['yaw_local_only']['ade_px']-1):.2f}%. "
             'The pilot therefore supplies no accuracy evidence for adopting this '
             'masking configuration. Yaw-local alone has a useful path-error '
             'signal, but both yaw-local arms fail history selection at every '
             'tested history. At H24 their ambiguities are '
             f"{h24['yaw_local_only']['signature_ambiguity']:.4f} and "
             f"{h24['masked_yaw_local']['signature_ambiguity']:.4f}, versus the 0.05 limit.", '',
             'This is one seed and 500 steps, with newly initialized motion '
             'and uncertainty heads in every pilot arm. The original pretrained '
             'checkpoint retained its trained heads and has a different training '
             'budget, so it is an operational reference rather than a matched '
             'training arm. A lower score is descriptive; no statistical or '
             'test-set improvement has been established.', '',
             'Recommendation: retain the original checkpoint as the working '
             'reference and defer a long combined mask/yaw run. First inspect '
             'the yaw-local nearest-neighbour ambiguity cases and per-sequence '
             'trajectory errors. Reproduce the reference/yaw-only comparison '
             'with matched seeds before increasing the budget. '
             'For a follow-up, hold the same initialization, labels, windows '
             'and budget across arms; use fresh output folders and at least '
             'three matched seeds. Preserve the four saved checkpoints. '
             'Keep the locked test untouched until the model and history '
             'are fixed on validation. No additional training was launched '
             'during this review.', '',
             'The soft mask floors reliability at 0.25, retains original max '
             'pooling and has no hard attention cutoff in this pilot. '
             'Reported feature coverage of 1.0 means all feature cells remain '
             'eligible; it does not mean their confidence/ground weights are '
             'all one. No empty-mask frames were observed.', '',
             '## Evidence', '',
             '- [Checkpoint/configuration/source provenance](provenance.json)',
             '- [All histories and metrics](comparison.csv)',
             '- Per-arm JSON and logs in this directory preserve complete evaluator output.',
             '- Copied training metrics/configurations are in the parent run folder.', '']
    (root/'REPORT.md').write_text('\n'.join(text))
    print('\n'.join(text))


if __name__ == '__main__':
    main()
