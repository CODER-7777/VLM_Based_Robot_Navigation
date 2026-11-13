"""Render the four trained pilot arms on the exact saved episode-629 windows."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import html
import json
import os
from pathlib import Path
import sys

import numpy as np

ARMS = ('reference', 'masked_only', 'yaw_local_only', 'masked_yaw_local', 'pretrained_yaw')
LABELS = {'reference': 'Trained reference', 'masked_only': 'Trained soft mask',
          'yaw_local_only': 'Trained yaw-local', 'masked_yaw_local': 'Trained mask + yaw-local',
          'pretrained_yaw': 'Original pretrained yaw'}
COLORS = {'reference': '#00bcd4', 'masked_only': '#159447', 'yaw_local_only': '#7c3aed',
          'masked_yaw_local': '#ff8800', 'pretrained_yaw': '#4682b4'}
CASES = {0: '20261013T170841_769161Z', 2: '20261013T165039_654952Z',
         3: '20261013T165054_373912Z', 4: '20261013T165108_948717Z'}
GT_COLOR = '#ee00bb'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def reference(poses, pitch):
    # Same verified world-x/z/yaw convention as tools/review_episode_mask.py.
    delta = poses[:, :2] - poses[0, :2]
    yaw = poses[0, 2]
    forward = delta @ np.array([np.cos(yaw), np.sin(yaw)])
    left = delta @ np.array([np.sin(yaw), -np.cos(yaw)])
    p = np.deg2rad(pitch)
    camera = np.column_stack([-left, -np.sin(p)*forward, np.cos(p)*forward])
    return np.column_stack([forward, left]), camera


def ground(displacement, pitch):
    p = np.deg2rad(pitch)
    return np.column_stack([-np.sin(p)*displacement[:, 1]+np.cos(p)*displacement[:, 2],
                            -displacement[:, 0]])


def project(displacement, query, camera, canvas):
    from step2.geometry import canonical_ground_normal_camera, query_ground_anchor
    anchor, valid = query_ground_anchor(np.asarray(query)[None], camera.intrinsics,
                     canonical_ground_normal_camera(camera.pitch_down_deg), camera.camera_height_m)
    points = anchor[0] + displacement
    depth = points[:, 2] > 1e-4
    z = np.maximum(points[:, 2], 1e-4)
    uv = np.column_stack([camera.fx*points[:, 0]/z+camera.cx,
                          camera.fy*points[:, 1]/z+camera.cy])
    inside = (bool(valid[0]) & depth & (uv[:, 0] >= 0) & (uv[:, 0] < camera.width)
              & (uv[:, 1] >= 0) & (uv[:, 1] < canvas))
    return uv, np.logical_and.accumulate(inside), depth


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--project', type=Path, required=True)
    ap.add_argument('--pilot', default='20261019T101035Z_431613')
    args = ap.parse_args()
    project_root = args.project.resolve()
    lab = project_root/'gqft_mask_review'
    source = lab/'source_20261016'
    sys.path.insert(0, str(source))
    pilot = lab/'pilots'/args.pilot
    out = lab/'trained_episode_overlays'/args.pilot/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out.mkdir(parents=True, exist_ok=False)
    os.environ['MPLCONFIGDIR'] = str(out/'matplotlib')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import PowerNorm
    import torch
    from step2.checkpoint import load_gqft_checkpoint
    from step2.episode_contract import pack_normalized_flow

    assert os.environ.get('CUDA_VISIBLE_DEVICES') == '7', 'Use the approved physical GPU 7'
    torch.set_num_threads(2)
    device = torch.device('cuda:0')
    torch.cuda.set_device(0)
    for name, sha in json.loads((source/'SOURCE_MANIFEST.json').read_text()).items():
        assert digest(source/name) == sha, name
    print(f'OUTPUT={out}', flush=True)
    windows = {}
    poses_path = Path('/data/robotics/toshith/flowvo_compare/poses/b10_A_drivefix_idx3_20260829_114756.npz')
    with np.load(poses_path, allow_pickle=False) as poses_file:
        assert int(poses_file['episode_id']) == 629
        physical = json.loads(str(poses_file['physical'].item()))
        poses = poses_file['pose'].copy()
        starts = poses_file['leg_start'].copy()
    for leg, timestamp in CASES.items():
        folder = project_root/'analysis/masked_attention_v1/episodes/ep629'/f'leg{leg:02d}'/timestamp
        metadata = json.loads((folder/'episode_inputs.json').read_text())
        assert metadata['episode_id'] == 629 and metadata['leg'] == leg and metadata['history'] == 24
        begin = metadata['window_start_episode_frame']
        assert begin == int(starts[leg]) and metadata['window_start_within_leg'] == 0
        end = int(starts[leg+1]) if leg+1 < len(starts) else len(poses)
        assert begin+24 < end and len(metadata['frames']) == 25
        cache = folder/'flow_searaft_160x90.npz'
        with np.load(cache, allow_pickle=False) as data:
            features = pack_normalized_flow(data['flow'], data['confidence'], data['valid'])
        assert features.shape == (24, 4, 90, 160)
        rgb = plt.imread(metadata['frames'][0])
        windows[leg] = dict(metadata=metadata, features=features, rgb=rgb,
                            poses=poses[begin:begin+25], predictions={}, maps={},
                            cache_sha256=digest(cache))

    provenance = {'episode': 629, 'legs': list(CASES), 'history': 24, 'pilot': str(pilot),
                  'source': str(source), 'source_manifest_verified': True,
                  'physical_gpu': 7, 'gpu': torch.cuda.get_device_name(0), 'precision': 'float32',
                  'scope': 'First 24 recorded pairs of each leg; diagnostic, not full-leg benchmark',
                  'projection': 'Fixed-rig ground-anchor projection in first-frame camera; no fitted scale/rotation',
                  'checkpoints': {}, 'poses_file': str(poses_path), 'poses_sha256': digest(poses_path)}
    camera, canvas, query_px = None, None, None
    for arm in ARMS:
        ckpt_path = (project_root/'runs/gqft_spatial_yaw_v1/best.pt' if arm == 'pretrained_yaw'
                     else pilot/arm/'best.pt')
        model, checkpoint = load_gqft_checkpoint(ckpt_path, device)
        if camera is None:
            camera, canvas = model.camera, model.config.canvas_height
            query_px = [camera.cx, canvas-1.0]
            assert physical['resolution'] == [camera.height, camera.width]
            expected_fx = camera.width/(2*np.tan(np.deg2rad(physical['hfov_deg'])/2))
            assert np.isclose(expected_fx, camera.fx)
            assert np.isclose(physical['camera_position_agent'][1], camera.camera_height_m)
            assert np.isclose(-physical['camera_orientation_deg'][0], camera.pitch_down_deg)
            assert np.allclose(physical['camera_position_agent'][::2], [0, 0])
        assert camera == model.camera and canvas == model.config.canvas_height
        provenance['checkpoints'][arm] = dict(path=str(ckpt_path), sha256=digest(ckpt_path),
                  step=checkpoint.get('step'), config=asdict(model.config), color=COLORS[arm], label=LABELS[arm])
        for leg, w in windows.items():
            flow = torch.from_numpy(w['features'])[None].to(device)
            mask = torch.ones((1, 24), dtype=torch.bool, device=device)
            query = torch.tensor([[query_px]], device=device)
            with torch.inference_mode():
                result = model(flow, mask, query, query/query.new_tensor([camera.width-1, camera.height-1]))
                _, diagnostics = model.flow_encoder(flow[0], return_diagnostics=True)
            displacement = result['displacement'][0].float().cpu().numpy()
            uv = result['uv_px'][0, 0].float().cpu().numpy()
            assert displacement.shape == (25, 3) and np.isfinite(displacement).all() and np.isfinite(uv).all()
            analytic_uv, prefix, depth = project(displacement, query_px, camera, canvas)
            assert np.allclose(uv, analytic_uv, atol=.02, rtol=1e-4)
            w['predictions'][arm] = {'displacement_m': displacement, 'uv_px': uv,
                                     'prefix': prefix, 'positive_depth': depth,
                                     'ground': ground(displacement, camera.pitch_down_deg)}
            w['maps'][arm] = {key: value.float().cpu().numpy() for key, value in diagnostics.items()}
            print(f'INFERRED arm={arm} leg={leg:02d}', flush=True)
        del model
    provenance['camera'] = asdict(camera)
    provenance['query_px'] = query_px
    report = {}

    def draw(axis, w, arm=None, zoom=False, title=None):
        axis.imshow(w['rgb'])
        gt = w['gt_uv']
        axis.plot(gt[:, 0], gt[:, 1], '-o', color=GT_COLOR, lw=2.8, ms=2.8, label='Recorded ground truth')
        if arm:
            p = w['predictions'][arm]
            uv = np.where(p['positive_depth'][:, None], p['uv_px'], np.nan)
            axis.plot(uv[:, 0], uv[:, 1], ':', color=COLORS[arm], lw=2.2, label='Prediction after canvas exit')
            shown = np.where(p['prefix'][:, None], uv, np.nan)
            axis.plot(shown[:, 0], shown[:, 1], '-o', color=COLORS[arm], lw=2.3, ms=2.5,
                      label=LABELS[arm])
            if p['positive_depth'][-1]:
                axis.scatter(*uv[-1], color=COLORS[arm], s=65, marker='X', edgecolor='white', linewidth=.6, zorder=5)
            m = w['metrics'][arm]
            axis.text(.02, .025, f"Ground mean {100*m['mean_ground_error_m']:.1f} cm | end {100*m['endpoint_ground_error_m']:.1f} cm\n"
                      f"Pixel mean {m['mean_pixel_error_px']:.1f} px | accepted {m['accepted_prefix_points']}/25 poses",
                      transform=axis.transAxes, fontsize=8, color='white',
                      bbox=dict(facecolor='black', alpha=.75, edgecolor='none'))
        axis.scatter(*gt[-1], color=GT_COLOR, s=60, marker='X', edgecolor='white', linewidth=.6, zorder=5)
        axis.scatter(*gt[0], c='white', s=30, marker='s', edgecolor='black', zorder=6)
        for idx in (8, 16, 24):
            axis.annotate(str(idx), gt[idx], xytext=(5, 0), textcoords='offset points', color=GT_COLOR,
                          fontsize=8, bbox=dict(facecolor='white', alpha=.6, edgecolor='none', pad=.4))
        axis.axhline(camera.height, color='gray', linestyle=':', lw=1)
        axis.axhline(canvas, color='black', linestyle=':', lw=1)
        if zoom:
            tracks = [gt] + [p['uv_px'][p['positive_depth']] for p in w['predictions'].values()]
            points = np.concatenate(tracks)
            finite = points[np.isfinite(points).all(1)]
            lo = np.maximum(finite.min(0)-[55, 35], [0, 0])
            hi = np.minimum(finite.max(0)+[55, 35], [camera.width, canvas+15])
            axis.set_xlim(lo[0], hi[0]); axis.set_ylim(hi[1], lo[1])
        else:
            axis.set_xlim(0, camera.width); axis.set_ylim(canvas+15, 0)
        axis.set_title(title or (LABELS[arm] if arm else 'Ground truth only'), fontsize=11)
        axis.set_aspect('equal', adjustable='box')
        axis.set_xlabel('u (px)', fontsize=8); axis.set_ylabel('v (px)', fontsize=8)
        axis.legend(loc='upper left', fontsize=7, framealpha=.85)

    for leg, w in windows.items():
        folder = out/f'leg{leg:02d}'
        folder.mkdir()
        w['gt_ground'], gt_displacement = reference(w['poses'], camera.pitch_down_deg)
        w['gt_uv'], gt_prefix, _ = project(gt_displacement, query_px, camera, canvas)
        domain = gt_prefix.copy(); domain[0] = False
        assert int(domain.sum()) == 24
        w['metrics'] = {}
        saved = {}
        for arm, p in w['predictions'].items():
            ground_error = np.linalg.norm(p['ground']-w['gt_ground'], axis=1)
            pixel_error = np.linalg.norm(p['uv_px']-w['gt_uv'], axis=1)
            w['metrics'][arm] = {'mean_ground_error_m': float(ground_error[1:].mean()),
                                'endpoint_ground_error_m': float(ground_error[-1]),
                                'mean_pixel_error_px': float(pixel_error[domain].mean()),
                                'endpoint_pixel_error_px': float(pixel_error[-1]),
                                'accepted_prefix_points': int(p['prefix'].sum())}
            saved[arm] = {k: v.tolist() for k, v in p.items()}
            w['maps'][arm]['ground_error_m'] = ground_error
            fig, axis = plt.subplots(figsize=(10, 8))
            draw(axis, w, arm)
            fig.suptitle(f'Episode 629 · leg {leg:02d} · first 24 flow pairs · {LABELS[arm]}')
            fig.tight_layout()
            fig.savefig(folder/f'{arm}_overlay.png', dpi=160)
            plt.close(fig)
        for zoom, name in [(False, 'comparison'), (True, 'comparison_zoom')]:
            fig, axes = plt.subplots(2, 3, figsize=(18, 11))
            for axis, arm in zip(axes.flat, (None, *ARMS)):
                draw(axis, w, arm, zoom=zoom)
            fig.suptitle(f'Episode 629 · leg {leg:02d} · frames {w["metadata"]["window_start_episode_frame"]}–'
                         f'{w["metadata"]["window_start_episode_frame"]+24} · SAME input and ground truth', fontsize=15)
            fig.text(.5, .012, 'Magenta = recorded ground truth · X = endpoint · square = start · dotted prediction = beyond analytic prefix\n'
                     '24-pair diagnostic window; white region below RGB is the existing extended canvas; no fitted scale or alignment.',
                     ha='center', fontsize=9)
            fig.tight_layout(rect=(0, .055, 1, .96))
            fig.savefig(folder/f'{name}.png', dpi=150); plt.close(fig)
        fig, axes = plt.subplots(1, 2, figsize=(13, 5))
        gt = w['gt_ground']
        axes[0].plot(gt[:, 1], gt[:, 0], '-o', color=GT_COLOR, label='Recorded ground truth', lw=3, ms=3)
        for arm, p in w['predictions'].items():
            xy = p['ground']
            axes[0].plot(xy[:, 1], xy[:, 0], '-o', color=COLORS[arm], label=LABELS[arm], ms=2)
            axes[0].scatter(xy[-1, 1], xy[-1, 0], color=COLORS[arm], marker='X', s=65)
            axes[1].plot(range(1, 25), w['maps'][arm]['ground_error_m'][1:]*100,
                         color=COLORS[arm], label=LABELS[arm])
        axes[0].set(xlabel='Left (m)', ylabel='Forward (m)', title='Ground path in metres (no perspective distortion)')
        axes[0].set_aspect('equal', adjustable='datalim')
        axes[1].set(xlabel='Pose after start', ylabel='Ground error (cm)', title='Position error versus recorded poses')
        for ax in axes: ax.grid(alpha=.2); ax.legend(fontsize=8)
        fig.suptitle(f'Episode 629, leg {leg:02d} · trained checkpoints')
        fig.tight_layout(); fig.savefig(folder/'ground_paths.png', dpi=150); plt.close(fig)
        selected = (0, 12, 23)
        maximum = max(float(w['maps'][arm]['attention_weights'][list(selected)].max()) for arm in ARMS)
        norm = PowerNorm(.35, vmin=0, vmax=maximum)
        fig, axes = plt.subplots(3, 6, figsize=(20, 8))
        for row, t in enumerate(selected):
            rgb = plt.imread(w['metadata']['frames'][t])
            for col, arm in enumerate((None, *ARMS)):
                axis = axes[row, col]; axis.imshow(rgb)
                if arm:
                    heat = axis.imshow(w['maps'][arm]['attention_weights'][t, 0], cmap='magma', norm=norm,
                                       extent=(0, camera.width, camera.height, 0), alpha=.7, interpolation='nearest')
                axis.set_title(f'{LABELS[arm] if arm else "Raw source"} · pair {t}', fontsize=9)
                axis.axis('off')
        fig.suptitle('Learned attention: shared color scale · different trained weights, not a frozen causal comparison')
        fig.subplots_adjust(bottom=.1, top=.93, left=.01, right=.99, wspace=.03)
        fig.colorbar(heat, ax=list(axes.flat), orientation='horizontal', fraction=.025, pad=.03)
        fig.savefig(folder/'attention_comparison.png', dpi=150); plt.close(fig)
        fig, axes = plt.subplots(3, 4, figsize=(15, 8))
        for row, t in enumerate(selected):
            rgb = plt.imread(w['metadata']['frames'][t])
            maps = w['maps']['masked_only']
            arrays = (None, w['features'][t, 3], maps['feature_reliability'][t, 0], maps['ground_prior_coverage'][t, 0])
            for col, (array, title) in enumerate(zip(arrays, ['Raw source', 'Valid flow support', 'Soft reliability (0.25–1)', 'Hypothetical ground-ray prior'])):
                ax=axes[row, col]; ax.imshow(rgb)
                if array is not None:
                    heat=ax.imshow(array, extent=(0,camera.width,camera.height,0), vmin=0, vmax=1,
                                   cmap='viridis', alpha=.75, interpolation='nearest')
                ax.set_title(f'{title} · pair {t}', fontsize=9); ax.axis('off')
        fig.suptitle('Soft masking downweights cells; it does not cut out objects or remove every dark cell')
        fig.subplots_adjust(bottom=.1,top=.93,left=.01,right=.99,wspace=.03)
        fig.colorbar(heat,ax=list(axes.flat),orientation='horizontal',fraction=.025,pad=.03)
        fig.savefig(folder/'mask_reliability.png',dpi=150); plt.close(fig)
        payload = {'episode':629, 'leg':leg, 'history':24, 'inputs':w['metadata'],
                   'cache_sha256':w['cache_sha256'], 'metrics_origin_excluded':True,
                   'reference_displacement_m':gt_displacement.tolist(), 'reference_uv_px':w['gt_uv'].tolist(),
                   'metrics':w['metrics'], 'predictions':saved}
        (folder/'predictions.json').write_text(json.dumps(payload,indent=2,allow_nan=False)+'\n')
        np.savez_compressed(folder/'attention_maps.npz',**{f'{arm}__{key}':v for arm,d in w['maps'].items() for key,v in d.items()})
        report[str(leg)] = w['metrics']
        print(f'RENDERED leg={leg:02d}',flush=True)
    fig, axes = plt.subplots(4, 5, figsize=(20, 20))
    for row,(leg,w) in enumerate(windows.items()):
        for col,arm in enumerate(ARMS):
            draw(axes[row,col],w,arm,zoom=True,title=f'Leg {leg:02d} · {LABELS[arm]}')
    fig.suptitle('EPISODE 629 · newly trained checkpoints · magenta = recorded ground truth',fontsize=18)
    fig.tight_layout(rect=(0,0,1,.975));fig.savefig(out/'START_HERE_overview.png',dpi=140);plt.close(fig)
    (out/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    (out/'metrics.json').write_text(json.dumps(report,indent=2)+'\n')
    parts=['<!doctype html><meta charset="utf-8"><title>Episode 629 trained models</title>',
           '<style>body{font:16px system-ui;background:#15171b;color:#eee;margin:24px}img{width:100%;height:auto}a{color:#71d7ff}section{margin:35px 0}p{line-height:1.5}</style>',
           '<h1>Episode 629 — newly trained checkpoint comparisons</h1>',
           '<p>Magenta: recorded ground truth. Cyan: trained reference. Green: soft mask. Purple: yaw-local. Orange: mask + yaw-local. Steel: original pretrained yaw.</p>',
           '<p>Same first 24 flow pairs of legs 0, 2, 3, 4. These are short diagnostic windows, not full-leg results. No scale or rotation was fitted. All four new checkpoints are from step 500.</p>',
           '<p>Open the zoom comparisons first, then ground paths to judge metric motion. Dotted paths continue after the analytic canvas gate. The lower white area is the extended query canvas.</p>',
           '<p><a href="START_HERE_overview.png">All legs overview</a> · <a href="provenance.json">Checkpoint provenance</a></p>']
    for leg in CASES:
        parts.append(f'<section><h2>Leg {leg:02d}</h2>')
        for name,title in [('comparison_zoom','Camera overlay — zoom'),('comparison','Camera overlay — full view'),
                           ('ground_paths','Ground paths and errors'),('attention_comparison','Learned attention'),('mask_reliability','What the soft prior weights')]:
            path=f'leg{leg:02d}/{name}.png'
            parts.append(f'<h3>{html.escape(title)}</h3><a href="{path}"><img loading="lazy" src="{path}"></a>')
        parts.append('</section>')
    (out/'index.html').write_text('\n'.join(parts))
    (out/'README.md').write_text('# Episode 629 trained-checkpoint visual review\n\nOpen `index.html` or `START_HERE_overview.png`. '
        'Each leg folder includes a full and zoomed 6-panel camera comparison, individual model overlays, ground paths, '
        'attention heatmaps, reliability maps and exact prediction arrays. Magenta is recorded ground truth. '
        'All windows contain the same first 24 recorded flow pairs used by the earlier frozen-mask diagnostic; '
        'these are not complete legs. Checkpoint hashes/configurations are in provenance.json.\n')
    print(f'EPISODE_OVERLAYS_DONE {out}',flush=True)


if __name__ == '__main__':
    main()
