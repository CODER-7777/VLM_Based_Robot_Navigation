"""Audit preserved GQFT evidence only; no training or checkpoint inference."""
import csv
import hashlib
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAB = HERE.parent
os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ.setdefault('MPLCONFIGDIR', str(HERE/'matplotlib'))

import numpy as np
import torch
import torch.nn.functional as F


def main():
    torch.set_num_threads(2)
    root = LAB/'trained_episode_overlays/20261019T101035Z_431613/20261019T123632Z'
    val = LAB/'pilot_results/20261019T101035Z_431613/validation_20261019T104120Z'
    provenance = json.loads((root/'provenance.json').read_text())
    arms = list(provenance['checkpoints'])
    results, histories = {}, {}
    for arm in arms:
        payload = json.loads((val/f'{arm}.json').read_text())
        row = next(r for r in payload['histories'] if r['history'] == 24)
        close = row['signature_close_pairs']
        bad = round(close*row['signature_ambiguity'])
        assert abs(bad/max(close, 1)-row['signature_ambiguity']) < 1e-6
        results[arm] = dict(ade_px=row['ade_px'], fde_px=row['fde_px'],
            close_queries=close, ambiguous_queries=bad, eligible_queries=row['signature_cross_sequence_eligible'],
            conditional_ambiguity=row['signature_ambiguity'],
            ambiguous_fraction_of_all_eligible=bad/row['signature_cross_sequence_eligible'],
            one_close_query_fraction=1/close if close else None,
            selected_history=payload['shortest_sufficient_history'])
        histories[arm] = [{k: row[k] for k in ('history','ade_px','fde_px','signature_close_pairs','signature_ambiguity','nn_full_curve_gap_m_mean')}
                          for row in payload['histories']]
    entropy_rows, aggregate, source_hashes = [], {}, {}
    for leg in (0, 2, 3, 4):
        folder = root/f'leg{leg:02d}'
        predictions = json.loads((folder/'predictions.json').read_text())
        source_hashes[str(folder.relative_to(LAB))+'/predictions.json'] = hashlib.sha256((folder/'predictions.json').read_bytes()).hexdigest()
        with np.load(folder/'attention_maps.npz', allow_pickle=False) as arrays:
            for arm in arms:
                attention = arrays[f'{arm}__attention_weights'][:, 0].reshape(24, 60).astype(np.float64)
                assert np.allclose(attention.sum(1), 1, atol=1e-5)
                entropy = -(attention*np.log(np.maximum(attention, 1e-30))).sum(1)
                p = predictions['predictions'][arm]
                gt = np.asarray(predictions['reference_displacement_m'])
                error = np.linalg.norm(np.asarray(p['displacement_m'])-gt, axis=1)[1:]
                for t in range(24):
                    entropy_rows.append({'leg': leg, 'arm': arm, 'flow_pair': t,
                        'entropy_nats': float(entropy[t]), 'normalized_entropy': float(entropy[t]/np.log(60)),
                        'effective_attention_cells': float(np.exp(entropy[t])),
                        'maximum_cell_mass': float(attention[t].max()),
                        'pose_3d_error_m': float(error[t])})
                aggregate.setdefault(arm, []).append(predictions['metrics'][arm])
    entropy_summary = {}
    for arm in arms:
        rows = [r for r in entropy_rows if r['arm'] == arm]
        entropy_summary[arm] = {
            'frames': len(rows), 'mean_entropy_nats': float(np.mean([r['entropy_nats'] for r in rows])),
            'median_entropy_nats': float(np.median([r['entropy_nats'] for r in rows])),
            'mean_effective_attention_cells': float(np.mean([r['effective_attention_cells'] for r in rows])),
            'fraction_entropy_below_1p5_exploratory': float(np.mean([r['entropy_nats'] < 1.5 for r in rows])),
            'mean_maximum_cell_mass': float(np.mean([r['maximum_cell_mass'] for r in rows]))}
    episode_summary = {arm: {key: float(np.mean([r[key] for r in rows])) for key in rows[0]}
                       for arm, rows in aggregate.items()}
    with (HERE/'episode_attention_entropy.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(entropy_rows[0])); writer.writeheader(); writer.writerows(entropy_rows)
    cache = LAB/'ep629/leg00/20261013T170841_769161Z/probe/flow_searaft_160x90.npz'
    with np.load(cache, allow_pickle=False) as data:
        valid = torch.from_numpy(data['valid'].astype(np.float32))[:, None]
    coarse = F.adaptive_avg_pool2d(valid, (6,10)) >= .75
    rf_average = F.avg_pool2d(valid, 31, 16, 15, count_include_pad=False)
    any_valid = valid
    for _ in range(4): any_valid = F.max_pool2d(any_valid, 3, 2, 1)
    assert torch.equal(any_valid, F.max_pool2d(valid, 31, 16, 15))
    support = {'window': 'ep629 leg00 first 24 pairs', 'coarse_fraction_eligible': float(coarse.float().mean()),
        'rf_any_valid_fraction': float(any_valid.mean()),
        'coarse_rejected_with_any_valid_conv_path_fraction': float(((~coarse)&any_valid.bool()).float().mean()),
        'all_input_pairs_have_some_valid_flow': bool(valid.flatten(1).any(1).all()),
        'four_stage_max_pool_equals_31_kernel_support': True,
        'interpretation': 'Any-valid support along convolution paths only; excludes GroupNorm global dependency. Not a reliability score or a measured accuracy improvement.'}
    oracle = json.loads((LAB.parent/'gqft_algorithm_sharing_vivekananda/analysis/label_geometry_20261009/oracle_geometry.json').read_text())
    conflicts = [r for r in oracle['windows'] if abs(r['height_contract_error_m']) > .01]
    label = {'audited_split': 'val', 'windows': len(oracle['windows']), 'conflicting_windows': len(conflicts),
        'distinct_conflicting_sequences': len({r['sequence'] for r in conflicts}), 'conflicts': conflicts,
        'max_oracle_pixel_discrepancy': oracle['fixed_rig_oracle_max_h30_px'],
        'training_split_conflicts_audited_in_this_report': False,
        'note': 'A consistent target/projector pair is required; this does not establish that fixed 1.2m is the correct physical floor for every window.'}
    findings = {'date': '2026-11-04', 'training_performed': False, 'gpu_used': False,
        'new_checkpoint_inference_performed': False, 'historical_primary_precision': 'CUDA bfloat16 validation',
        'h24_validation': results, 'history_sweep': histories, 'episode_attention_entropy': entropy_summary,
        'episode_metrics': episode_summary, 'convolution_support_diagnostic': support, 'label_geometry': label,
        'embedding_audit_status': 'Not executed: terminal/full-state matrices were not preserved locally and the recorded server project directory is now absent.',
        'raw_state_retrieval_domain': {'input_flow_pairs':24,'reference_flow_pairs':30,'reference_curve_points':31,
            'unobserved_reference_flow_pairs_at_h24':6,'sequences':26,'windows':104,'cross_sequence_unique_pairs':5200},
        'source_sha256': source_hashes,
        'limits': ['96 flow pairs belong to four windows of one episode, not independent scenes.',
            'Entropy below 1.5 is exploratory, not a validated collapse threshold.',
            'Do not replace the official raw-cosine gate with a centered or pooled variant without separate validation.',
            'Missing embeddings prevent attribution to anisotropy, terminal-state semantics, or dimensional collapse.']}
    (HERE/'findings.json').write_text(json.dumps(findings, indent=2, allow_nan=False)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    labels = ['Reference','Soft mask','Yaw-local','Mask + yaw','Original yaw']
    colors = ['#00bcd4','#159447','#7c3aed','#ff8800','#4682b4']
    fig, axes = plt.subplots(1,3,figsize=(16,5))
    x=np.arange(len(arms))
    axes[0].bar(x,[results[a]['ade_px'] for a in arms],color=colors)
    axes[0].set(title='Fixed validation · history 24',ylabel='ADE (px) · lower is better')
    axes[1].bar(x,[results[a]['conditional_ambiguity'] for a in arms],color=colors)
    axes[1].axhline(.05,color='red',ls='--',label='Gate limit 0.05');axes[1].legend()
    for i,a in enumerate(arms):axes[1].text(i,results[a]['conditional_ambiguity']+.006,f"{results[a]['ambiguous_queries']}/{results[a]['close_queries']}",ha='center',fontsize=9)
    axes[1].set(title='Ambiguous / cosine-near queries',ylabel='Conditional ambiguity (fraction)',ylim=(0,.26))
    axes[2].bar(x,[entropy_summary[a]['mean_entropy_nats'] for a in arms],color=colors)
    axes[2].axhline(float(np.log(60)),color='gray',ls=':',label='Uniform: log(60)');axes[2].legend()
    axes[2].set(title='Separate episode-629 diagnostic',ylabel='Mean attention entropy (nats)',ylim=(0,4.4))
    for axis in axes:axis.set_xticks(x,labels,rotation=25,ha='right');axis.grid(axis='y',alpha=.2)
    fig.suptitle('GQFT diagnosis: path accuracy, embedding gate and attention concentration are different measurements')
    fig.tight_layout(rect=(0,0,1,.94));fig.savefig(HERE/'diagnostic_summary.png',dpi=150);plt.close(fig)
    print(json.dumps({k:findings[k] for k in ['h24_validation','episode_attention_entropy','convolution_support_diagnostic']},indent=2))


if __name__ == '__main__':
    main()
