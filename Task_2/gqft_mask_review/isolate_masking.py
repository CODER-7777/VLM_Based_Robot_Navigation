"""Frozen-weight, paired pooling ablations and controlled CNN support experiment.

Run from either the local Task_2 lab or PROJECT/gqft_mask_review on ISL.
Never trains, modifies checkpoints, selects a test score, or regenerates flow.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import sys

LAB = Path(__file__).resolve().parent
ROOT = LAB.parent
if not (ROOT / 'step2/models/gqft.py').is_file():
    ROOT = LAB.parent / 'gqft_algorithm_sharing_vivekananda'
sys.path.insert(0, str(ROOT))
os.environ.setdefault('MPLCONFIGDIR', str(LAB / '.cache/matplotlib'))

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from step2.checkpoint import load_gqft_checkpoint
from step2.dataset import FlowPathDataset, collate_windows
from step2.episode_contract import pack_normalized_flow
from step2.models.gqft import GQFT
from step2.geometry import query_ground_anchor, canonical_ground_normal_camera
from tools.review_episode_mask import ground_reference, ground_prediction, project_reference
from tools.probe_episode_mask import validate_camera

POLICIES = ('original', 'attention_only', 'max_only', 'both', 'rescue_both', 'rf_both')
CASES = ('leg00/20261013T170841_769161Z', 'leg02/20261013T165039_654952Z',
         'leg03/20261013T165054_373912Z', 'leg04/20261013T165108_948717Z')


def augmented(flow):
    n, _, h, w = flow.shape
    yy, xx = torch.meshgrid(torch.linspace(-1, 1, h, device=flow.device, dtype=flow.dtype),
                            torch.linspace(-1, 1, w, device=flow.device, dtype=flow.dtype), indexing='ij')
    return torch.cat([flow, torch.stack([xx, yy])[None].expand(n, -1, -1, -1)], 1)


class PoolingIntervention(nn.Module):
    """Reuse one computed feature tensor; intervene only on the two pooling branches."""
    def __init__(self, encoder, threshold):
        super().__init__()
        self.encoder = encoder
        self.threshold = threshold
        self.policy = 'original'

    def prepare(self, flow):
        self.flow = flow
        self.pixel = (flow[:, 3:4] > .5) & torch.isfinite(flow).all(1, keepdim=True)
        cleaned = flow.masked_fill(~self.pixel, 0.)
        # Both pooling branches see exactly these same frozen CNN features.
        self.feat = self.encoder.net(augmented(flow))
        self.input_change = float((cleaned - flow).abs().max())
        clean_feat = self.encoder.net(augmented(cleaned))
        self.feature_change = float((clean_feat - self.feat).abs().max())
        fh, fw = self.feat.shape[-2:]
        self.coarse_coverage = F.adaptive_avg_pool2d(self.pixel.float(), (fh, fw))
        self.coarse = self.coarse_coverage >= self.threshold
        # Four 3x3 stride-2 convolutions: jump=16, local footprint=31, centre=16*i.
        # GroupNorm makes actual functional dependence global; this is CONV support.
        self.rf_coverage = F.avg_pool2d(self.pixel.float(), 31, 16, 15, count_include_pad=False)
        if self.rf_coverage.shape != self.coarse.shape:
            raise ValueError('Unexpected feature geometry for the four-convolution encoder')
        self.rf = self.rf_coverage >= self.threshold
        self.logits = self.encoder.attention(self.feat)
        self.original_attention = self.logits.flatten(1).softmax(-1).reshape_as(self.logits)

    def forward(self, flow, *, return_diagnostics=False):
        if flow.shape != self.flow.shape or flow.data_ptr() != self.flow.data_ptr():
            raise ValueError('Prepare exactly the flow tensor consumed by the model')
        mask = self.rf if self.policy == 'rf_both' else self.coarse
        if self.policy == 'rescue_both':
            mask = self.coarse | self.rf
        observed = mask.flatten(1).any(1)
        weights = self.original_attention
        max_pool = self.feat.amax((-2, -1))
        if self.policy in ('attention_only', 'both', 'rescue_both', 'rf_both'):
            logits = self.logits.float().flatten(1).masked_fill(~mask.flatten(1), -torch.inf)
            logits = torch.where(observed[:, None], logits, torch.zeros_like(logits))
            weights = logits.softmax(-1).reshape_as(self.logits).masked_fill(~mask, 0).to(self.feat.dtype)
        if self.policy in ('max_only', 'both', 'rescue_both', 'rf_both'):
            max_pool = self.feat.masked_fill(~mask, -torch.inf).amax((-2, -1))
            max_pool = torch.where(observed[:, None], max_pool, torch.zeros_like(max_pool))
        token = self.encoder.pool(torch.cat([(self.feat * weights).sum((-2, -1)), max_pool], -1))
        if self.policy in ('both', 'rescue_both', 'rf_both'):
            token = torch.where(observed[:, None], token, torch.zeros_like(token))
        return token

    def support_summary(self):
        rejected = ~self.coarse
        rescued = rejected & self.rf
        winners = self.feat.flatten(2).argmax(2)
        rejected_winners = rejected.flatten(1).gather(1, winners)
        return {
            'input_preprocessing_max_abs_change': self.input_change,
            'cnn_feature_preprocessing_max_abs_change': self.feature_change,
            'coarse_rejected_fraction': float(rejected.float().mean()),
            'rf_rejected_fraction': float((~self.rf).float().mean()),
            'coarse_rejected_but_rf_kept_cells': int(rescued.sum()),
            'coarse_rejected_cells': int(rejected.sum()),
            'mean_conv_valid_coverage_on_rejected': float(self.rf_coverage[rejected].mean()) if rejected.any() else None,
            'original_attention_on_coarse_rejected': float((self.original_attention * rejected).sum((1, 2, 3)).mean()),
            'original_attention_on_rf_rescued': float((self.original_attention * rescued).sum((1, 2, 3)).mean()),
            'channel_maxima_on_coarse_rejected_fraction': float(rejected_winners.float().mean()),
            'empty_coarse_frames': int((~self.coarse.flatten(1).any(1)).sum()),
            'empty_rf_frames': int((~self.rf.flatten(1).any(1)).sum()),
        }


def frozen_norm_forward(net, x, statistics=None):
    """Freeze baseline GroupNorm statistics to isolate LOCAL convolutional influence."""
    captured = []
    for index, block in enumerate(net):
        conv, norm, activation = block
        x = conv(x)
        grouped = x.reshape(x.shape[0], norm.num_groups, -1)
        if statistics is None:
            mean = grouped.mean(-1, keepdim=True)
            var = grouped.var(-1, unbiased=False, keepdim=True)
        else:
            mean, var = statistics[index]
        captured.append((mean, var))
        x = ((grouped - mean) * torch.rsqrt(var + norm.eps)).reshape_as(x)
        x = x * norm.weight[None, :, None, None] + norm.bias[None, :, None, None]
        x = activation(x)
    return x, captured


def neighbour_experiment(pool):
    """Perturb valid flow OUTSIDE the mask cell but INSIDE its convolution footprint."""
    t, _, h, w = pool.flow.shape
    fh, fw = pool.coarse.shape[-2:]
    candidates = []
    for frame, _, row, col in (~pool.coarse).nonzero().cpu().tolist():
        rf = torch.zeros((h, w), dtype=torch.bool, device=pool.flow.device)
        rf[max(0, 16*row-15):min(h, 16*row+16), max(0, 16*col-15):min(w, 16*col+16)] = True
        cell = torch.zeros_like(rf)
        cell[math.floor(row*h/fh):math.ceil((row+1)*h/fh),
             math.floor(col*w/fw):math.ceil((col+1)*w/fw)] = True
        neighbours = rf & ~cell & pool.pixel[frame, 0]
        outside = ~rf & pool.pixel[frame, 0]
        if neighbours.any() and int(outside.sum()) >= int(neighbours.sum()):
            candidates.append((float(pool.original_attention[frame, 0, row, col]), frame, row, col, neighbours, outside))
    if not candidates:
        return {'status': 'No eligible rejected cell with a matched outside-footprint control'}
    mass, frame, row, col, neighbours, outside = max(candidates, key=lambda x: x[0])
    original = pool.flow[frame:frame+1].clone()
    count = int(neighbours.sum())
    control = torch.zeros_like(outside)
    control.flatten()[outside.flatten().nonzero().flatten()[:count]] = True
    nearby = original.clone()
    distant = original.clone()
    for changed, domain in ((nearby, neighbours), (distant, control)):
        changed[0, 0, domain] += .001
        changed[0, 1, domain] -= .001
    baseline, stats = frozen_norm_forward(pool.encoder.net, augmented(original))
    near, _ = frozen_norm_forward(pool.encoder.net, augmented(nearby), stats)
    far, _ = frozen_norm_forward(pool.encoder.net, augmented(distant), stats)
    normal_base = pool.encoder.net(augmented(original))
    normal_near = pool.encoder.net(augmented(nearby))
    normal_far = pool.encoder.net(augmented(distant))
    target = lambda x: x[0, :, row, col]
    near_change = float(torch.linalg.vector_norm(target(near) - target(baseline)))
    far_change = float(torch.linalg.vector_norm(target(far) - target(baseline)))
    if far_change > 1e-6:
        raise AssertionError('Outside-footprint control influenced a cell with frozen GroupNorm statistics')
    return {
        'status': 'completed', 'frame': frame, 'feature_row': row, 'feature_column': col,
        'original_attention_weight': mass, 'adaptive_valid_coverage': float(pool.coarse_coverage[frame, 0, row, col]),
        'conv_footprint_valid_coverage': float(pool.rf_coverage[frame, 0, row, col]),
        'valid_neighbour_pixels_outside_adaptive_cell': count, 'matched_control_pixels': count,
        'du_change_normalized': .001, 'dv_change_normalized': -.001,
        'frozen_norm_neighbour_feature_l2_change': near_change,
        'frozen_norm_outside_footprint_feature_l2_change': far_change,
        'ordinary_norm_neighbour_feature_l2_change': float(torch.linalg.vector_norm(target(normal_near)-target(normal_base))),
        'ordinary_norm_outside_footprint_feature_l2_change': float(torch.linalg.vector_norm(target(normal_far)-target(normal_base))),
        'interpretation': 'Local neighbour influence is demonstrated if near > 0 and far = 0; does not alone prove those cues improve trajectory accuracy. Ordinary GroupNorm adds global dependence.',
    }


def metrics(output, gt_camera, gt_uv, pixel_domain, camera, query):
    pred = output['displacement'][0].cpu().numpy().astype(np.float64)
    pred_uv = output['uv_px'][0].cpu().numpy().astype(np.float64)
    gt_ground = ground_prediction(gt_camera, camera.pitch_down_deg)
    ground_err = np.linalg.norm(ground_prediction(pred, camera.pitch_down_deg) - gt_ground, axis=1)[1:]
    direct_err = np.linalg.norm(pred-gt_camera, axis=1)[1:]
    pixel_err = np.linalg.norm(pred_uv-gt_uv, axis=-1)
    selected = pixel_err[pixel_domain]
    last = [pixel_err[q, np.flatnonzero(domain)[-1]] for q, domain in enumerate(pixel_domain) if domain.any()]
    anchors, _ = query_ground_anchor(query[0].cpu().numpy(), camera.intrinsics,
                                     canonical_ground_normal_camera(camera.pitch_down_deg), camera.camera_height_m)
    positive = anchors[:, None, 2] + pred[None, :, 2] > 1e-4
    positive_domain = pixel_domain & positive
    positive_errors = pixel_err[positive_domain]
    return {
        'mean_ground_error_m': float(ground_err.mean()), 'endpoint_ground_error_m': float(ground_err[-1]),
        'mean_3d_error_m': float(direct_err.mean()), 'endpoint_3d_error_m': float(direct_err[-1]),
        'mean_pixel_error_px': float(selected.mean()) if selected.size else None,
        'last_valid_pixel_error_px': float(np.mean(last)) if last else None,
        'pixel_error_sum_px': float(selected.sum()), 'pixel_points': int(selected.size),
        'nonpositive_prediction_depth_points': int((pixel_domain & ~positive).sum()),
        'rejected_prediction_prefix_points': int((pixel_domain & ~output['analytic_valid'][0].cpu().numpy()).sum()),
        'positive_depth_pixel_error_sum_px': float(positive_errors.sum()),
        'positive_depth_pixel_points': int(positive_errors.size),
        'accepted_prefix_points': int(output['analytic_valid'][0].sum()),
    }


def aggregate(records):
    result = {}
    keys = ('mean_ground_error_m', 'endpoint_ground_error_m', 'mean_3d_error_m',
            'endpoint_3d_error_m', 'mean_pixel_error_px', 'last_valid_pixel_error_px')
    for policy in POLICIES:
        result[policy] = {key: float(np.mean([r['metrics'][policy][key] for r in records
                                            if r['metrics'][policy][key] is not None])) for key in keys}
        n = sum(r['metrics'][policy]['pixel_points'] for r in records)
        result[policy]['pooled_pixel_error_px'] = sum(r['metrics'][policy]['pixel_error_sum_px'] for r in records)/n if n else None
        positive_n = sum(r['metrics'][policy]['positive_depth_pixel_points'] for r in records)
        result[policy]['positive_depth_only_pixel_error_px'] = sum(r['metrics'][policy]['positive_depth_pixel_error_sum_px'] for r in records)/positive_n if positive_n else None
        result[policy]['nonpositive_prediction_depth_points'] = sum(r['metrics'][policy]['nonpositive_prediction_depth_points'] for r in records)
        result[policy]['rejected_prediction_prefix_points'] = sum(r['metrics'][policy]['rejected_prediction_prefix_points'] for r in records)
        result[policy]['pixel_points'] = n
        result[policy]['median_window_pixel_error_px'] = float(np.median([r['metrics'][policy]['mean_pixel_error_px'] for r in records if r['metrics'][policy]['mean_pixel_error_px'] is not None]))
        result[policy]['windows_ground_better_than_original'] = sum(r['metrics'][policy]['mean_ground_error_m'] < r['metrics']['original']['mean_ground_error_m'] for r in records)
    # Paired effects at original vs masked setting; nonlinear trajectory/error interactions explicit.
    effects = {}
    for key in ('mean_ground_error_m', 'endpoint_ground_error_m', 'mean_pixel_error_px'):
        a, b, c, d = [result[p][key] for p in ('original', 'attention_only', 'max_only', 'both')]
        effects[key] = {'attention_effect_with_original_max': b-a, 'max_effect_with_original_attention': c-a,
                        'joint_effect': d-a, 'interaction': d-b-c+a,
                        'rescue_both_minus_coarse_both': result['rescue_both'][key]-d,
                        'rf_both_minus_coarse_both': result['rf_both'][key]-d}
    return {'window_count': len(records), 'policies': result, 'paired_effects': effects}


def draw(summary, records, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    colours = ['#2878b5', '#ab6b2c', '#8064a2', '#d94e43', '#53a86c', '#23846b']
    for ax, key, label in zip(axes, ('mean_ground_error_m', 'endpoint_ground_error_m', 'mean_pixel_error_px'),
                              ('Mean ground error (cm)', 'Endpoint ground error (cm)', 'Mean pixel error (px)')):
        scale = 100 if key.endswith('_m') else 1
        values = [summary['policies'][p][key]*scale for p in POLICIES]
        ax.bar(POLICIES, values, color=colours)
        for i, value in enumerate(values):
            ax.text(i, value, f'{value:.2f}', ha='center', va='bottom', fontsize=9)
        ax.tick_params(axis='x', rotation=30)
        if key == 'mean_pixel_error_px' and max(values) > 10*min(values):
            ax.set_yscale('log')
        ax.set_ylabel(label)
        ax.grid(axis='y', alpha=.2)
    fig.suptitle(f'{len(records)} paired windows · same frozen checkpoint · origin excluded')
    fig.tight_layout()
    fig.savefig(out / 'pooling_ablation.png', dpi=160)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--device', choices=('cpu', 'cuda'), default='cpu')
    ap.add_argument('--mode', choices=('episodes', 'validation'), required=True)
    ap.add_argument('--checkpoint', type=Path, default=ROOT/'runs/gqft_spatial_yaw_v1/best.pt')
    ap.add_argument('--manifest', type=Path, default=ROOT/'results/hsgm_manifest_v1.json')
    ap.add_argument('--probe-root', type=Path, default=ROOT/'analysis/masked_attention_v1/episodes/ep629')
    ap.add_argument('--poses-file', type=Path, default=Path('/data/robotics/toshith/flowvo_compare/poses/b10_A_drivefix_idx3_20260829_114756.npz'))
    ap.add_argument('--history', type=int, default=24)
    ap.add_argument('--coverage', type=float, default=.75)
    ap.add_argument('--out-dir', type=Path)
    args = ap.parse_args()
    if not 0 < args.coverage <= 1:
        raise ValueError('coverage must be in (0,1]')
    torch.set_num_threads(2)
    torch.manual_seed(20260820)
    device = torch.device('cpu')
    if args.device == 'cuda':
        visible = os.environ.get('CUDA_VISIBLE_DEVICES', '').strip()
        if not visible or ',' in visible or visible == '-1':
            raise ValueError('Explicitly select exactly one authorized GPU')
        device = torch.device('cuda:0')
        torch.cuda.set_device(0)
        print(f'GPU_DEVICE physical={visible} logical=cuda:0 name={torch.cuda.get_device_name(0)}', flush=True)
    model, _ = load_gqft_checkpoint(args.checkpoint, 'cpu')
    if model.config.spatial_pooling != 'attention_max' or model.config.spatial_mask != 'none':
        raise ValueError('Use the matching unmasked trained attention architecture')
    if args.history < 2 or args.history > model.config.max_history:
        raise ValueError('History outside checkpoint limits')
    model = model.eval().to(device)
    reference = GQFT(replace(model.config, spatial_mask='validity', mask_min_coverage=args.coverage), model.camera).eval().to(device)
    reference.load_state_dict(model.state_dict(), strict=True)
    original_encoder = model.flow_encoder
    pool = PoolingIntervention(original_encoder, args.coverage)
    model.flow_encoder = pool
    out = args.out_dir or LAB/'isolations'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')/args.mode
    if not out.resolve().is_relative_to(LAB.resolve()):
        raise ValueError('Outputs must stay under this lab')
    out.mkdir(parents=True, exist_ok=False)
    protocol = {'mode': args.mode, 'history': args.history, 'origin_excluded': True,
                'checkpoint': str(args.checkpoint.resolve()), 'checkpoint_sha256': hashlib.sha256(args.checkpoint.read_bytes()).hexdigest(),
                'model_config': asdict(model.config), 'camera': asdict(model.camera), 'coverage': args.coverage,
                'device': str(device), 'cuda_visible_devices': os.environ.get('CUDA_VISIBLE_DEVICES') if device.type == 'cuda' else None,
                'dtype': 'float32', 'trained': False, 'test_accessed': False,
                'rf_rule': '31x31 convolution footprint, stride16, padding15, exclude outside-image padding; GroupNorm has additional global dependence',
                'policy_definition': {'original':'original attention + original max', 'attention_only':'coarse-masked attention + original max',
                 'max_only':'original attention + coarse-masked max', 'both':'coarse-masked attention + coarse-masked max',
                 'rescue_both':'joint coarse mask with ONLY coarse-rejected/RF-valid cells reinstated in both branches',
                 'rf_both':'convolution-footprint coverage masking for both branches'},
                'shared_domain': 'Pixel errors use identical target-valid post-origin points for all policies, irrespective of prediction prefix gate'}
    records = []
    if args.mode == 'validation':
        dataset = FlowPathDataset(str(args.manifest), 'val', max_history=30, deterministic_history=30,
                                  queries=1, seed=20260820, virtual_extension_px=270, target_ground_plane='sequence_floor')
        if dataset.camera != model.camera or model.config.canvas_height != 810:
            raise ValueError('Validation camera/canvas mismatch')
        protocol.update(manifest=str(args.manifest.resolve()), manifest_sha256=hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
                        split='val', reference_history=30, stride=5, queries=1, seed=20260820, target_ground_plane='sequence_floor')
        windows = range(len(dataset))
    else:
        windows = CASES
        protocol.update(episode_id=629, split='diagnostic recorded episode', poses_file=str(args.poses_file.resolve()),
                        poses_sha256=hashlib.sha256(args.poses_file.read_bytes()).hexdigest())
    with torch.inference_mode():
        for index, case in enumerate(windows):
            saved = None
            if args.mode == 'validation':
                item = dataset[case]
                batch = collate_windows([item])
                flow = batch['flow'][:, :args.history].to(device)
                query = batch['query_uv'].to(device)
                norm = batch['query_norm'].to(device)
                gt_camera = batch['displacement'][0, :args.history+1].numpy().astype(np.float64)
                gt_uv = batch['target_uv'][0, :, :args.history+1].numpy().astype(np.float64) * np.array([model.camera.width-1, model.camera.height-1])
                domain = batch['target_valid'][0, :, :args.history+1].numpy().copy()
                meta = json.loads((Path(dataset.root)/item['sequence']/'meta.json').read_text())
                record = {'sequence': item['sequence'], 'start': item['start'], 'motion_family': meta['shape_family']}
            else:
                probe_dir = args.probe_root/case
                if not (probe_dir/'probe.json').exists():
                    probe_dir = probe_dir/'probe'
                saved = json.loads((probe_dir/'probe.json').read_text())
                inputs = json.loads((probe_dir/'episode_inputs.json').read_text())
                if saved['checkpoint_sha256'] != protocol['checkpoint_sha256'] or saved['history'] != args.history:
                    raise ValueError('Saved episode checkpoint/history mismatch')
                if saved['camera'] != asdict(model.camera) or saved['mask_config']['mask_min_coverage'] != args.coverage:
                    raise ValueError('Saved episode camera/mask mismatch')
                with np.load(probe_dir/'flow_searaft_160x90.npz', allow_pickle=False) as cache:
                    packed = pack_normalized_flow(cache['flow'], cache['confidence'], cache['valid'])
                flow = torch.from_numpy(packed)[None].to(device)
                if flow.shape[1] != args.history:
                    raise ValueError('Unexpected episode flow count')
                query = flow.new_tensor([[saved['query_px']]])
                norm = query/query.new_tensor([model.camera.width-1, model.camera.height-1])
                begin, leg = inputs['window_start_episode_frame'], inputs['leg']
                with np.load(args.poses_file, allow_pickle=False) as poses:
                    if int(poses['episode_id']) != inputs['episode_id']:
                        raise ValueError('Episode pose identity mismatch')
                    starts = poses['leg_start']
                    end = int(starts[leg+1]) if leg+1 < len(starts) else len(poses['pose'])
                    if int(starts[leg])+inputs['window_start_within_leg'] != begin or begin+args.history >= end:
                        raise ValueError('Crossed leg boundary')
                    physical = json.loads(str(poses['physical'].item()))
                    validate_camera(physical, model.camera)
                    if not np.allclose(physical['camera_position_agent'][::2], [0., 0.]):
                        raise ValueError('Unsupported horizontal camera offset')
                    _, gt_camera = ground_reference(poses['pose'][begin:begin+args.history+1], model.camera.pitch_down_deg)
                gt_uv_one, valid, _ = project_reference(gt_camera, saved['query_px'], model.camera, model.config.canvas_height)
                gt_uv, domain = gt_uv_one[None], valid[None]
                record = {'episode_id': 629, 'leg': leg, 'start': begin, 'probe': str(probe_dir.resolve())}
            domain[:, 0] = False
            history = torch.ones((1, args.history), device=device, dtype=torch.bool)
            flat = flow.reshape(-1, *flow.shape[2:])
            pool.prepare(flat)
            if pool.input_change != 0 or pool.feature_change != 0:
                raise ValueError('Input masking changes features; this pooling-only isolation needs a separate preprocessing factor')
            # Prove wrapper reproduces the production unmasked token and joint intervention.
            pool.policy = 'original'
            original_token = original_encoder(flat)
            token_error = float((pool(flat)-original_token).abs().max())
            pool.policy = 'both'
            joint_token = reference.flow_encoder(flat)
            joint_error = float((pool(flat)-joint_token).abs().max())
            if max(token_error, joint_error) > 1e-6:
                raise AssertionError('Pooling wrapper does not reproduce existing encoder')
            record.update(support=pool.support_summary(), encoder_equivalence={'original_max_abs':token_error, 'joint_max_abs':joint_error})
            if args.mode == 'episodes':
                record['neighbour_experiment'] = neighbour_experiment(pool)
            record['metrics'] = {}
            record['predictions'] = {}
            for policy in POLICIES:
                pool.policy = policy
                output = model(flow, history, query, norm)
                record['metrics'][policy] = metrics(output, gt_camera, gt_uv, domain, model.camera, query)
                if args.mode == 'episodes':
                    record['predictions'][policy] = {'displacement_m': output['displacement'][0].cpu().tolist(),
                                                     'trajectory_px': output['uv_px'][0, 0].cpu().tolist()}
                if saved and policy in ('original', 'both'):
                    name = 'unmasked' if policy == 'original' else 'masked'
                    old = np.asarray(saved['predictions'][name]['displacement_m'])
                    difference = float(np.max(np.abs(output['displacement'][0].cpu().numpy()-old)))
                    record.setdefault('saved_prediction_equivalence', {})[name] = difference
                    if difference > 1e-5:
                        raise AssertionError('New experiment does not reproduce saved predictions')
            records.append(record)
            with (out/'windows.jsonl').open('a') as f:
                f.write(json.dumps(record, allow_nan=False)+'\n')
            if index % 10 == 0 or index+1 == len(windows):
                print(f'ABLATION {args.mode} {index+1}/{len(windows)}', flush=True)
    summary = aggregate(records)
    families = sorted(set(r.get('motion_family', 'episode629') for r in records))
    summary['by_motion_family'] = {family: aggregate([r for r in records if r.get('motion_family','episode629')==family]) for family in families}
    summary['checks'] = {'original_encoder_max_abs_error':max(r['encoder_equivalence']['original_max_abs'] for r in records),
                         'joint_encoder_max_abs_error':max(r['encoder_equivalence']['joint_max_abs'] for r in records),
                         'input_preprocessing_max_abs_change':max(r['support']['input_preprocessing_max_abs_change'] for r in records),
                         'cnn_feature_preprocessing_max_abs_change':max(r['support']['cnn_feature_preprocessing_max_abs_change'] for r in records)}
    (out/'report.json').write_text(json.dumps({'protocol':protocol, 'summary':summary}, indent=2, allow_nan=False)+'\n')
    draw(summary, records, out)
    print(json.dumps({'output':str(out.resolve()), 'summary':summary['policies'], 'checks':summary['checks']}, indent=2), flush=True)


if __name__ == '__main__':
    main()
