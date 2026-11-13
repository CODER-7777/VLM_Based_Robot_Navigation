"""Verify soft-attention results and describe effect size with sequence-block resampling."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import numpy as np

LAB=Path(__file__).resolve().parent
RUN=LAB/'soft_attention/20261015_gpu2_v1'
OLD=LAB/'isolations/20261015_gpu2_pooling_v2'
PLAN=json.loads((LAB/'soft_attention_plan.json').read_text())
POLICIES=PLAN['policies']
reports,rows={},{}
cpu=json.loads((RUN/'cpu_verification.json').read_text())
assert cpu['passed']
source_hash=hashlib.sha256((LAB/'probe_soft_attention.py').read_bytes()).hexdigest()
plan_hash=hashlib.sha256((LAB/'soft_attention_plan.json').read_bytes()).hexdigest()
assert cpu['runner_sha256']==source_hash and cpu['plan_sha256']==plan_hash
checks=[]
metric_keys=('mean_ground_error_m','endpoint_ground_error_m','mean_3d_error_m',
             'endpoint_3d_error_m','mean_pixel_error_px','last_valid_pixel_error_px')
for mode,count in (('validation',104),('episodes',4)):
    reports[mode]=json.loads((RUN/mode/'report.json').read_text())
    rows[mode]=[json.loads(line) for line in (RUN/mode/'windows.jsonl').read_text().splitlines()]
    previous=[json.loads(line) for line in (OLD/mode/'windows.jsonl').read_text().splitlines()]
    protocol=reports[mode]['protocol']
    assert len(rows[mode])==len(previous)==count
    assert protocol['script_sha256']==source_hash and protocol['plan_sha256']==plan_hash
    assert protocol['plan']==PLAN and json.loads((RUN/mode/'predeclared_plan.json').read_text())==PLAN
    assert protocol['cuda_visible_devices']=='2' and not protocol['trained'] and not protocol['test_accessed']
    for r,old in zip(rows[mode],previous):
        if mode=='validation':
            assert (r['sequence'],r['start'])==(old['sequence'],old['start'])
        else:
            assert (r['episode_id'],r['leg'],r['start'])==(old['episode_id'],old['leg'],old['start'])
            assert r['saved_original_prediction_max_abs']==0
        assert r['original_encoder_max_abs']==0
        assert r['support']['input_preprocessing_max_abs_change']==0
        assert r['support']['cnn_feature_preprocessing_max_abs_change']==0
        for policy in POLICIES:
            m=r['metrics'][policy]
            assert m['pixel_points']==24
            assert r['attention_diagnostics'][policy]['max_pool_max_abs_change']==0
            assert r['attention_diagnostics'][policy]['weight_sum_max_error']<=1e-6
            if policy in ('original','attention_only'):
                for key in metric_keys:
                    assert m[key]==old['metrics'][policy][key]
        for policy in POLICIES:
            for key in metric_keys:
                value=np.mean([r['metrics'][policy][key] for r in rows[mode]])
                assert np.isclose(value,reports[mode]['summary']['policies'][policy][key],rtol=1e-12,atol=1e-12)
    checks.append(mode+'_counts_identity_domains_and_aggregates')
checks += ['same_plan_and_executed_source_hashes','bit_exact_original_and_hard_control_metrics_from_prior_run',
           'bit_exact_saved_original_episode_displacements','zero_max_pool_and_cnn_input_changes','normalized_attention',
           'gpu2_only_no_training_or_test_access','nine_cpu_semantic_checks_passed']

sequences=sorted(set(r['sequence'] for r in rows['validation']))
assert len(sequences)==26 and set(Counter(r['sequence'] for r in rows['validation']).values())=={4}
rng=np.random.default_rng(20261015)
indices=rng.integers(0,len(sequences),size=(20000,len(sequences)))
uncertainty={'method':'Percentile bootstrap of 26 sequence mean paired differences, preserving each sequence\'s four overlapping windows; 20000 draws; seed20261015.',
             'scope':'Exploratory within-one-scene sensitivity; sequences are not independent scenes. Interval is not a locked-test or cross-scene generalization estimate.',
             'candidate_order_predeclared':POLICIES,'policies':{}}
for policy in ('soft_coarse_attention','soft_rf_attention'):
    deltas=np.array([np.mean([r['metrics'][policy]['mean_ground_error_m']-r['metrics']['original']['mean_ground_error_m']
                              for r in rows['validation'] if r['sequence']==s]) for s in sequences])
    draws=deltas[indices].mean(1)
    uncertainty['policies'][policy]={'sequence_count':26,'mean_ground_error_delta_m':float(deltas.mean()),
        'bootstrap_95_percentile_interval_m':np.quantile(draws,[.025,.975]).tolist(),
        'sequences_ground_better_than_original':int((deltas<0).sum()),
        'sequence_deltas_m':dict(zip(sequences,deltas.tolist()))}
(RUN/'sequence_sensitivity.json').write_text(json.dumps(uncertainty,indent=2)+'\n')
v=reports['validation']['summary']['policies']
e=reports['episodes']['summary']['policies']
screen=reports['validation']['summary']['screening']
assert screen['passes_predeclared_screen']
gain=lambda policy:100*(1-v[policy]['mean_ground_error_m']/v['original']['mean_ground_error_m'])
labels={'original':'Original','attention_only':'Hard attention only','soft_coarse_attention':'Soft coarse (control)','soft_rf_attention':'Soft CNN support (primary)'}
lines=['# Soft attention with original max pooling — GPU 2', '',
'Completed 15 October 2026 with the existing frozen Attention+Yaw checkpoint. This is an analysis-only policy trial, not a new trained checkpoint. No training, production-model change, SEA-RAFT regeneration or locked-test access occurred.', '',
'## Fixed policy, declared before running', '',
'The primary candidate is **soft CNN-support attention**; coarse-cell soft weighting is a control. Both keep the original max-pooling vector exactly and reuse the original CNN inputs/features. Reliability is supplied validity density, not semantic segmentation or an additional confidence threshold.', '',
'```text', 'reliability[i] = 0.25 + 0.75 * valid_coverage[i]',
'soft_attention[i] = original_attention[i] * reliability[i]',
'soft_attention /= sum(soft_attention)', 'max_pooling = original_max_pooling', '```', '',
'Coverage for the primary is the 31×31 convolution footprint, stride 16, padding 15 with outside-image padding excluded. The coarse control uses the previous adaptive 6×10 grid coverage. GroupNorm still adds global feature dependence. No cell is hard rejected by the soft rule. Spatially constant reliability cancels, and an explicit bypass preserves original behavior bit for bit for all-valid/all-invalid frames.', '',
'Floor 0.25 was fixed before inference. No floor sweep, confidence tuning or retrospective change of primary candidate was performed. [Predeclared plan](soft_attention_plan.json).', '',
'## Validation: 104 paired windows', '',
'Same scene `D7G3Y4RVNrH`, 26 sequences × four overlapping windows; reference history 30; evaluated causal prefix 24; stride 5; anchor `(480,809)`; seed 20260820; original `sequence_floor` labels; float32; no augmentation. All 2,496 post-origin target-valid points are scored for every policy.', '',
'| Policy | Ground mean cm ↓ | Ground endpoint cm ↓ | Mean 3-D error cm ↓ | Pixel mean px ↓ | Pixel endpoint px ↓ |',
'| --- | ---: | ---: | ---: | ---: | ---: |']
for p in POLICIES:
    m=v[p]
    lines.append(f"| {labels[p]} | {m['mean_ground_error_m']*100:.6f} | {m['endpoint_ground_error_m']*100:.6f} | {m['mean_3d_error_m']*100:.6f} | {m['mean_pixel_error_px']:.6f} | {m['last_valid_pixel_error_px']:.6f} |")
lines += ['',f"The primary reduces ground mean by **{gain('soft_rf_attention'):.3f}%**, only **{(v['original']['mean_ground_error_m']-v['soft_rf_attention']['mean_ground_error_m'])*1000:.3f} mm**. The coarse control reduces it by **{gain('soft_coarse_attention'):.3f}%**, or **{(v['original']['mean_ground_error_m']-v['soft_coarse_attention']['mean_ground_error_m'])*1000:.3f} mm**. Both avoid the hard attention-only regression and add zero depth or prefix failures.", '',
'The primary passes the predeclared numerical screen: lower aggregate ground mean, no aggregate endpoint/3-D/pixel regression and no added depth/prefix failures. That screen has no minimum effect-size requirement, so passing it does not establish a practically useful improvement.', '',
'![Validation comparison](soft_attention/20261015_gpu2_v1/validation/soft_attention_comparison.png)', '',
'## Consistency and uncertainty', '',
'| Soft policy | Windows improved | Sequences improved | Mean ground change mm (negative better) | Sequence-bootstrap 95% interval mm |',
'| --- | ---: | ---: | ---: | --- |']
for p in ('soft_coarse_attention','soft_rf_attention'):
    u=uncertainty['policies'][p]
    lo,hi=np.array(u['bootstrap_95_percentile_interval_m'])*1000
    lines.append(f"| {labels[p]} | {v[p]['windows_ground_better_than_original']}/104 | {u['sequences_ground_better_than_original']}/26 | {u['mean_ground_error_delta_m']*1000:.3f} | [{lo:.3f}, {hi:.3f}] |")
lines += ['', 'Both intervals include zero. These are exploratory resamples of **sequence means**, not independent-window confidence claims; all sequences still belong to one scene. No reliable cross-scene gain or multi-seed benefit is established.', '',
'| Motion family | Windows | Original cm | Soft coarse cm | Soft CNN support cm |',
'| --- | ---: | ---: | ---: | ---: |']
families={'0':'Straight','1':'Constant arc','2':'Gradual turn','3':'S-curve','4':'Random smooth','5':'Stop-go','6':'Straight-then-turn','7':'MPPI-like'}
for family,s in reports['validation']['summary']['by_motion_family'].items():
    numbers=[s['policies'][p]['mean_ground_error_m']*100 for p in ('original','soft_coarse_attention','soft_rf_attention')]
    lines.append(f"| {family}: {families[family]} | {s['window_count']} | {numbers[0]:.5f} | {numbers[1]:.5f} | {numbers[2]:.5f} |")
lines += ['', 'The primary slightly regresses on straight, gradual-turn, random-smooth and stop-go families while improving the other four. The stop-go mean rises from 2.97785 to 3.00101 cm. Aggregate improvements therefore do not mean every motion family benefits.', '',
'## Episode 629: diagnostic only', '',
'The same first 24 flow pairs from legs 0, 2, 3 and 4 were evaluated after the fixed policy was declared. All 96 post-origin reference points are scored. These windows do not select the policy.', '',
'| Policy | Ground mean cm ↓ | Ground endpoint cm ↓ | Pixel mean px ↓ |',
'| --- | ---: | ---: | ---: |']
for p in POLICIES:
    m=e[p]
    lines.append(f"| {labels[p]} | {m['mean_ground_error_m']*100:.5f} | {m['endpoint_ground_error_m']*100:.5f} | {m['mean_pixel_error_px']:.5f} |")
lines += ['', 'Both soft variants improve aggregate episode ground mean slightly and improve two of the four windows individually. Neither reproduces the severe joint-hard-mask regression. Full per-leg predictions and attention-change diagnostics are in the episode JSONL.', '',
'## Training decision', '',
'**Do not launch a large training run based on these small frozen-weight gains.** Keep the original reference. The candidate is eligible for planning a **small, matched mask-aware training pilot**, because its fixed-policy screen passes without the hard-mask failure; training may allow the attention/CNN to adapt to the pooling change. That adaptation benefit remains a hypothesis.', '',
'Before a pilot: add an explicit differentiable soft-attention mode to the trainable model/config with a default-off compatibility check; retain original max pooling; test gradients/checkpoint round trips; fix one architecture, initialization, labels, seed, batch, histories and budget for both unmasked/soft runs. Keep the separate ground-label experiment independent. A no-yaw pair is a new experiment, not a direct continuation of this yaw-checkpoint probe.', '',
'The existing `--spatial-mask validity` flag is **hard joint masking**, not this soft attention rule. These analysis scripts do not make soft training available through that flag. No production training code was changed or training launched in this trial. The primary remains CNN-support weighting despite the coarse control showing a larger observed gain; switching primaries after seeing these results would be a new declared experiment.', '',
'## Verification and artifacts', '',
'Nine CPU semantic checks passed. GPU original and hard attention-only scores reproduce the previous isolation run exactly across all windows. Max pooling, original tokens and CNN inputs/features remain bit-identical; soft weights are finite and normalized; recorded original episode displacements match exactly.', '',
'- [Runner](probe_soft_attention.py) and [CPU verification](verify_soft_attention.py).',
'- [Validation report](soft_attention/20261015_gpu2_v1/validation/report.json), [104 window records](soft_attention/20261015_gpu2_v1/validation/windows.jsonl).',
'- [Episode report](soft_attention/20261015_gpu2_v1/episodes/report.json), [four window records](soft_attention/20261015_gpu2_v1/episodes/windows.jsonl).',
'- [Sequence sensitivity](soft_attention/20261015_gpu2_v1/sequence_sensitivity.json), [CPU verification output](soft_attention/20261015_gpu2_v1/cpu_verification.json), [artifact verification](soft_attention/20261015_gpu2_v1/verification.json).', '',
'Reproduce on ISL from the GQFT project root after uploading the runner and plan alongside the unchanged `isolate_masking.py`:', '',
'```bash', 'CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES=2 PYTHONDONTWRITEBYTECODE=1 \\',
'  /data/robotics/toshith/envs/agentvln/bin/python -B \\',
'  gqft_mask_review/probe_soft_attention.py --mode validation --device cuda', '',
'CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES=2 PYTHONDONTWRITEBYTECODE=1 \\',
'  /data/robotics/toshith/envs/agentvln/bin/python -B \\',
'  gqft_mask_review/probe_soft_attention.py --mode episodes --device cuda', '```', '',
'Default outputs use fresh UTC timestamps. Only GPU 2 was used in this run. The working existing `agentvln` environment was reused without package changes.', '',
f'Executed runner SHA-256: `{source_hash}`.', '',f'Predeclared plan SHA-256: `{plan_hash}`.', '']
(LAB/'SOFT_ATTENTION_RESULTS.md').write_text('\n'.join(lines))
artifacts={str(p.relative_to(LAB)):hashlib.sha256(p.read_bytes()).hexdigest() for p in RUN.rglob('*') if p.is_file() and p.name!='verification.json'}
verification={'passed':True,'checks':checks,'script_sha256':source_hash,'plan_sha256':plan_hash,'artifact_sha256':artifacts}
(RUN/'verification.json').write_text(json.dumps(verification,indent=2)+'\n')
print(json.dumps({'report':str(LAB/'SOFT_ATTENTION_RESULTS.md'),'checks':checks,'primary_screen_passed':screen['passes_predeclared_screen'],
                  'primary_ground_gain_percent':gain('soft_rf_attention'),'sequence_sensitivity':{p:{k:u[k] for k in ('mean_ground_error_delta_m','bootstrap_95_percentile_interval_m')} for p,u in uncertainty['policies'].items()}},indent=2))
