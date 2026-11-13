"""Validate downloaded paired results and write the local explanation/figures."""
from pathlib import Path
import hashlib
import json
import os
import math
import numpy as np

LAB = Path(__file__).resolve().parent
os.environ.setdefault('MPLCONFIGDIR', str(LAB/'.cache/matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

BASE = LAB/'isolations/20261015_gpu2_pooling_v2'
POLICIES = ('original','attention_only','max_only','both','rescue_both','rf_both')
NAMES = ('Original','Attention only','Max only','Both (current hard mask)',
         'Restore rejected / RF-valid cells','Replace mask with RF coverage')
reports, records = {}, {}
for mode, expected in (('episodes',4), ('validation',104)):
    reports[mode] = json.loads((BASE/mode/'report.json').read_text())
    records[mode] = [json.loads(line) for line in (BASE/mode/'windows.jsonl').read_text().splitlines()]
    assert len(records[mode]) == expected
    assert reports[mode]['protocol']['cuda_visible_devices'] == '2'
    assert reports[mode]['protocol']['origin_excluded']
    assert not reports[mode]['protocol']['trained'] and not reports[mode]['protocol']['test_accessed']
    for row in records[mode]:
        assert row['support']['input_preprocessing_max_abs_change'] == 0
        assert row['support']['cnn_feature_preprocessing_max_abs_change'] == 0
        assert row['encoder_equivalence'] == {'original_max_abs':0.,'joint_max_abs':0.}
        if mode == 'episodes':
            assert row['saved_prediction_equivalence'] == {'unmasked':0., 'masked':0.}
            probe = row['neighbour_experiment']
            assert probe['frozen_norm_neighbour_feature_l2_change'] > 0
            assert probe['frozen_norm_outside_footprint_feature_l2_change'] == 0
        for policy in POLICIES:
            assert row['metrics'][policy]['pixel_points'] == 24
    for policy in POLICIES:
        for key in ('mean_ground_error_m','endpoint_ground_error_m','mean_pixel_error_px'):
            calculated = np.mean([r['metrics'][policy][key] for r in records[mode]])
            assert np.isclose(calculated,reports[mode]['summary']['policies'][policy][key],rtol=1e-12,atol=1e-12)
assert hashlib.sha256((LAB/'isolate_masking.py').read_bytes()).hexdigest() == '1068665a21ea03eb90f5ff2f315f0a96b8547110bbcccb00eb985b5742b95dd7'

fig, axes = plt.subplots(2, 2, figsize=(12, 11))
with np.load(LAB/'inputs/ep629/b10_A_drivefix_idx3_20260829_114756.npz',allow_pickle=False) as archive:
    all_poses = archive['pose'].copy()
for axis, row in zip(axes.flat, records['episodes']):
    poses = all_poses[row['start']:row['start']+25]
    delta = poses[:,:2]-poses[0,:2]
    yaw = poses[0,2]
    gt = np.column_stack([delta@np.array([np.cos(yaw),np.sin(yaw)]),delta@np.array([np.sin(yaw),-np.cos(yaw)])])
    axis.plot(gt[:,1],gt[:,0],color='#235c37',label='Recorded reference',linewidth=2.5)
    for policy, colour, label in (('original','#2878b5','Original'),('both','#d94e43','Current hard mask'),('rescue_both','#ad7a18','Restore RF-valid cells')):
        d = np.asarray(row['predictions'][policy]['displacement_m'])
        forward = -.5*d[:,1] + np.cos(np.pi/6)*d[:,2]
        axis.plot(-d[:,0],forward,color=colour,label=label,linewidth=2)
        axis.scatter(-d[-1,0],forward[-1],color=colour,marker='X',s=65)
    values = [row['metrics'][p]['mean_ground_error_m']*100 for p in ('original','both','rescue_both')]
    axis.set(title=f"Leg {row['leg']} · mean error {values[0]:.1f} / {values[1]:.1f} / {values[2]:.1f} cm",
             xlabel='Left (m)',ylabel='Forward (m)')
    axis.grid(alpha=.2)
    axis.set_aspect('equal',adjustable='datalim')
    axis.legend(fontsize=8)
fig.suptitle('Same frozen weights and features: reinstating cells changes trajectory accuracy')
fig.tight_layout()
fig.savefig(BASE/'restored_cells_paths.png',dpi=160)
plt.close(fig)

first = records['episodes'][0]['neighbour_experiment']
probe = LAB/'ep629/leg00/20261013T170841_769161Z/probe'
with np.load(probe/'mask_maps.npz',allow_pickle=False) as archive:
    pixel = archive['pixel_mask'][first['frame'],0].astype(bool)
    attention = archive['unmasked_attention'][first['frame'],0]
h,w = pixel.shape
fh,fw = attention.shape
r,c = first['feature_row'],first['feature_column']
y0,y1 = math.floor(r*h/fh),math.ceil((r+1)*h/fh)
x0,x1 = math.floor(c*w/fw),math.ceil((c+1)*w/fw)
rfy0,rfy1 = max(0,16*r-15),min(h,16*r+16)
rfx0,rfx1 = max(0,16*c-15),min(w,16*c+16)
fig,axes = plt.subplots(1,3,figsize=(16,4.8))
axes[0].imshow(pixel,cmap='gray',vmin=0,vmax=1)
axes[0].add_patch(Rectangle((x0-.5,y0-.5),x1-x0,y1-y0,fill=False,edgecolor='magenta',linewidth=2,label='Adaptive mask cell'))
axes[0].add_patch(Rectangle((rfx0-.5,rfy0-.5),rfx1-rfx0,rfy1-rfy0,fill=False,edgecolor='cyan',linewidth=2,label='Convolution footprint'))
axes[0].set_title('White = valid input · black = rejected input')
axes[0].legend(fontsize=8,loc='upper left')
neighbours = np.zeros_like(pixel,dtype=bool)
neighbours[rfy0:rfy1,rfx0:rfx1] = True
neighbours[y0:y1,x0:x1] = False
neighbours &= pixel
axes[1].imshow(pixel,alpha=.35,cmap='gray',vmin=0,vmax=1)
overlay = np.zeros((*pixel.shape,4))
overlay[neighbours]=[.1,.8,.3,1]
axes[1].imshow(overlay)
axes[1].set_title(f'{int(neighbours.sum())} valid neighbours outside mask cell')
axes[2].imshow(attention,cmap='magma',vmin=0,vmax=attention.max())
axes[2].add_patch(Rectangle((c-.5,r-.5),1,1,fill=False,edgecolor='cyan',linewidth=2))
axes[2].set_title(f"Rejected cell held {first['original_attention_weight']*100:.1f}% of attention")
for ax in axes:
    ax.set_xticks([])
    ax.set_yticks([])
fig.suptitle('Episode 629 / leg 0 / flow frame 9: 74.2% mask coverage vs 88.0% convolution support')
fig.tight_layout()
fig.savefig(BASE/'neighbour_support.png',dpi=160)
plt.close(fig)

lines = ['# Masking isolation — completed on GPU 2', '',
'These are frozen-weight interventions, completed on 15 October 2026. No training, checkpoint modification, flow regeneration or locked-test evaluation was performed. The authoritative six-policy run is `20261015_gpu2_pooling_v2`; the earlier five-policy validation run is preserved in `v1`.', '',
'## What was isolated', '',
'The current hard mask changes two pooling branches at once. All six policies below reuse exactly the same CNN feature tensor, trained weights, camera, query and temporal history. Original and joint-mask encoder outputs match the production implementations **bit for bit**. Episode original/joint predictions also exactly reproduce all four saved probes.', '',
'Input preprocessing changed **zero** input values and **zero** feature values in all 108 windows: invalid flow/confidence values were already zero in these caches. The observed differences therefore come from the pooling interventions.', '',
'| Policy | Attention branch | Max branch | Eligibility rule |',
'| --- | --- | --- | --- |',
'| Original | Original | Original | No new spatial rejection |',
'| Attention only | Masked | Original | Adaptive-cell valid coverage ≥75% |',
'| Max only | Original | Masked | Same adaptive-cell rule |',
'| Both | Masked | Masked | Current hard mask |',
'| Restore cells | Masked | Masked | Current mask OR convolution-footprint coverage ≥75%; only restores cells |',
'| RF replacement | Masked | Masked | Convolution-footprint coverage ≥75% replaces current rule |', '',
'“RF” means the **local convolution footprint**, not a strictly local functional receptive field: GroupNorm introduces global spatial dependence.', '',
'## Matched validation: 104 windows', '',
'Scene `D7G3Y4RVNrH`; 26 sequences; 104 windows; stride 5; deterministic reference history 30, evaluated causal prefix 24; one repeated anchor `(480,809)`; seed 20260820; original `sequence_floor` labels; float32; no augmentation. All 2,496 target-valid post-origin points are scored for every policy. No threshold was tuned in this run.', '',
'| Intervention | Mean ground error cm ↓ | Endpoint ground error cm ↓ | Mean pixel error px ↓ | Depth failures / 2496 |',
'| --- | ---: | ---: | ---: | ---: |']
for p,n in zip(POLICIES,NAMES):
    s=reports['validation']['summary']['policies'][p]
    lines.append(f"| {n} | {s['mean_ground_error_m']*100:.3f} | {s['endpoint_ground_error_m']*100:.3f} | {s['mean_pixel_error_px']:,.3f} | {s['nonpositive_prediction_depth_points']} |")
v=reports['validation']['summary']['policies']
recovered=(v['both']['mean_ground_error_m']-v['rescue_both']['mean_ground_error_m'])/(v['both']['mean_ground_error_m']-v['original']['mean_ground_error_m'])*100
lines += ['', f'Reinstating only the rejected / RF-valid cells reverses **{recovered:.2f}% of the added aggregate ground error** relative to the original. This is a numerical recovery fraction for this fixed experiment, not a percentage attribution of physical causes.', '',
'The max-only intervention adds 6.664 cm mean ground error; attention-only adds 2.004 cm. The joint effect is larger than their sum: the error-level factorial interaction is +11.953 cm. This demonstrates a harmful interaction under this frozen checkpoint; it does not identify a unique internal Transformer mechanism.', '',
'The large joint-mask pixel mean includes **77 nonpositive-depth predictions**. The projector clamps Z to `1e-4`, so these values are numerical failure diagnostics rather than meaningful visible-image distances. Its median per-window pixel mean is 35.56 px; even its positive-depth-only pixel mean is 380.68 px. Ground error is the primary comparison. Positive-depth-only scores are supplementary and cannot replace the shared-domain score.', '',
'Restoring cells is still slightly worse than original on aggregate validation: 4.758 vs 4.492 cm ground mean; 12.850 vs 12.121 px pixel mean. It improves ground mean in 56/104 windows. RF replacement improves 60/104 but is also worse on aggregate. **Neither is an established replacement model.**', '',
'![Validation pooling ablation](isolations/20261015_gpu2_pooling_v2/validation/pooling_ablation.png)', '',
'## Episode 629: the same four saved windows', '',
'| Intervention | Mean ground error cm ↓ | Endpoint ground error cm ↓ | Mean pixel error px ↓ |',
'| --- | ---: | ---: | ---: |']
for p,n in zip(POLICIES,NAMES):
    s=reports['episodes']['summary']['policies'][p]
    lines.append(f"| {n} | {s['mean_ground_error_m']*100:.3f} | {s['endpoint_ground_error_m']*100:.3f} | {s['mean_pixel_error_px']:.3f} |")
lines += ['', 'Restoring cells improves these four diagnostic windows overall, including 3/4 windows individually, but this cannot override the validation aggregate. Each window contains the first 24 flow pairs from legs 0, 2, 3 and 4, with 24 post-origin points.', '',
'![Ground paths after selective restoration](isolations/20261015_gpu2_pooling_v2/restored_cells_paths.png)', '',
'## Direct test of neighbouring valid pixels', '',
'Four 3×3 stride-2 convolutions have a 31×31 local footprint and a 16-pixel centre spacing. The old mask instead averages 6×10 adaptive grid bins. These are different input regions.', '',
'For leg 0, flow frame 9, final feature row 5 / column 5:', '',
'- Adaptive-cell valid coverage: **74.17%**, so the 75% rule rejects it.',
'- Convolution-footprint valid coverage: **88.00%**.',
'- Original learned attention on this one cell: **82.09%**.',
'- **504 valid neighbouring pixels** lie within its convolution footprint but outside the adaptive mask bin.',
'- Perturb only their normalized flow by `du += 0.001`, `dv -= 0.001`: target-feature L2 changes by **0.14155** with baseline GroupNorm statistics frozen.',
'- Perturb the same number of valid pixels outside the footprint by the same amount: target-feature change is **exactly zero** with those same frozen statistics.', '',
'This controls GroupNorm statistics so the effect follows the local convolution path. Ordinary unfrozen GroupNorm also lets distant pixels affect this cell; those measurements are saved separately. All four episode windows show nonzero local-neighbour influence with zero outside-footprint control.', '',
'![Mask bin, convolution footprint, and valid neighbours](isolations/20261015_gpu2_pooling_v2/neighbour_support.png)', '',
'The intervention proves neighbouring valid flow affects a rejected cell. Restoring the identified class of cells proves their rejection caused most of the added error under this setup. It does **not** prove that every rejected cell is useful, or that neighbouring flow alone accounts for the entire recovery: each restored feature also contains coordinate, normalization and other learned information.', '',
'## Boundaries and next decision', '',
'The active production mask remains unchanged and defaults to `none`. Keep the unmasked checkpoint as the reference. Next isolate attention-only soft reliability / retained max against the same validation protocol, then decide whether matched mask-aware training is justified. Keep any supervision (`sequence_floor` vs `fixed_rig`) experiment separate. Do not select a variant using test or these four episode windows.', '',
'The 104 windows overlap and come from one validation scene; they are not 104 independent trials. This run holds the Attention+Yaw checkpoint fixed and does not isolate yaw itself. Float32 GPU results are not guaranteed bit-identical to a different PyTorch build, although the saved episode predictions match exactly in this environment.', '',
'## Files and reproduction', '',
'- [Runner](isolate_masking.py): strict loading; prepared shared features; two-by-two pooling intervention; selective rescue; RF replacement; local perturbation experiment; depth/prefix diagnostics.',
'- [CPU verification](verify_isolation.py): token equivalence, unchanged inputs/features, direct-neighbour control and finite missing-observation handling.',
'- [Validation machine-readable report](isolations/20261015_gpu2_pooling_v2/validation/report.json) and [104 per-window records](isolations/20261015_gpu2_pooling_v2/validation/windows.jsonl).',
'- [Episode report](isolations/20261015_gpu2_pooling_v2/episodes/report.json) and [four per-window records, predictions and neighbour tests](isolations/20261015_gpu2_pooling_v2/episodes/windows.jsonl).',
'- [Local verification and artifact hashes](isolations/20261015_gpu2_pooling_v2/verification.json).', '',
'On ISL, from `/data/robotics/toshith/vivekananda/gqft_algorithm_sharing_vivekananda`, after uploading `isolate_masking.py` to `gqft_mask_review/`:', '',
'```bash',
'CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES=2 PYTHONDONTWRITEBYTECODE=1 \\',
'  /data/robotics/toshith/envs/agentvln/bin/python -B \\',
'  gqft_mask_review/isolate_masking.py --mode validation --device cuda',
'',
'CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES=2 PYTHONDONTWRITEBYTECODE=1 \\',
'  /data/robotics/toshith/envs/agentvln/bin/python -B \\',
'  gqft_mask_review/isolate_masking.py --mode episodes --device cuda',
'```', '',
'Default outputs use fresh UTC timestamp directories, preserving prior results. GPU 2 is the latest authorized device for this experiment. GPU 7 was used only for the earlier episode probes; it was not used for this isolation run. The existing `agentvln` environment is reused without installing packages.', '',
'Checkpoint SHA-256: `40729f0f537c28e5b07565aba01133bb594c7781cc59eedf90bc3fafa939ee8d`.', '',
'Executed runner SHA-256: `1068665a21ea03eb90f5ff2f315f0a96b8547110bbcccb00eb985b5742b95dd7`. Local and server hashes match. Earlier `v1` predates the rescue/depth additions and is supplementary only.', '']
(LAB/'ISOLATION_RESULTS.md').write_text('\n'.join(lines))
artifacts={str(p.relative_to(LAB)):hashlib.sha256(p.read_bytes()).hexdigest() for p in BASE.rglob('*') if p.is_file() and p.name!='verification.json'}
verification={'passed':True,'checks':['104_validation_and_4_episode_windows','all_six_policy_aggregates_recomputed',
 '2496_validation_and_96_episode_shared_pixel_points','zero_input_and_feature_preprocessing_change',
 'bit_exact_production_encoder_equivalence','bit_exact_saved_episode_predictions','four_local_neighbour_positive_and_outside_zero_controls',
 'gpu2_only','no_training_or_test_access','executed_source_hash_matches_server'], 'artifact_sha256':artifacts}
(BASE/'verification.json').write_text(json.dumps(verification,indent=2)+'\n')
print(json.dumps({'report':str(LAB/'ISOLATION_RESULTS.md'),'checks':verification['checks']},indent=2))
