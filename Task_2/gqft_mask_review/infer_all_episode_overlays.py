"""Frozen-checkpoint trajectories for every recorded flowvo episode and leg.

Writes only into a new project-local visualization run and project-local flow
cache. Camera/pose inputs remain read-only. No training or parameter selection.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time

import numpy as np

ARMS = ['yaw_local_reference', 'solver_residual', 'solver_learned_weights']
COLORS = {'yaw_local_reference': '#00bcd4', 'solver_residual': '#ff941f',
          'solver_learned_weights': '#8058ee', 'ground_truth': '#ed119a'}
LABELS = {'yaw_local_reference': 'Yaw-local reference', 'solver_residual': 'Solver + correction',
          'solver_learned_weights': 'Solver + learned weights'}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def save(path, payload):
    path = Path(path)
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(payload, separators=(',', ':'), allow_nan=False)+'\n')
    temporary.replace(path)


def ground(displacement, pitch):
    a = math.radians(pitch)
    return np.column_stack([-math.sin(a)*displacement[:, 1]+math.cos(a)*displacement[:, 2],
                            -displacement[:, 0]])


def reference(poses, pitch, heights=None):
    d = poses[:, :2]-poses[0, :2]
    yaw = poses[0, 2]
    forward = d @ [math.cos(yaw), math.sin(yaw)]
    left = d @ [math.sin(yaw), -math.cos(yaw)]
    a = math.radians(pitch)
    displacement=np.column_stack([-left, -math.sin(a)*forward, math.cos(a)*forward])
    if heights is not None:
        up=np.asarray(heights)-heights[0]
        displacement+=up[:,None]*np.array([0.,-math.cos(a),-math.sin(a)])
    return displacement


def rotate(vectors, angle, normal):
    return (vectors*math.cos(angle)+np.cross(normal, vectors)*math.sin(angle)
            +np.outer(vectors @ normal, normal)*(1-math.cos(angle)))


def stitch(model, features, window, device, context_mode='chunked'):
    import torch
    from step2.geometry import canonical_ground_normal_camera
    if context_mode == 'sliding':
        from step2.motion_controls import neural_local_steps, integrate_local_steps
        x = torch.from_numpy(features).to(device)
        local, dyaw = neural_local_steps(model, x, window=window, mode='sliding')
        xyz, yaw = integrate_local_steps(local, dyaw, model.camera.pitch_down_deg)
        return xyz.float().cpu().numpy(), yaw.float().cpu().numpy()
    if context_mode != 'chunked':
        raise ValueError('context_mode must be chunked or sliding')
    n = len(features)
    if n == 0:
        return np.zeros((1, 3)), np.zeros(1)
    query = torch.tensor([[[model.camera.cx, model.config.canvas_height-1.]]], device=device)
    qnorm = query/query.new_tensor([model.camera.width-1, model.camera.height-1])
    normal = canonical_ground_normal_camera(model.camera.pitch_down_deg)
    xyz, yaw = [np.zeros((1, 3))], [np.zeros(1)]
    base, heading = np.zeros(3), 0.
    for start in range(0, n, window):
        x = torch.from_numpy(features[start:start+window])[None].to(device)
        mask = torch.ones(1, x.shape[1], dtype=torch.bool, device=device)
        with torch.inference_mode():
            out = model(x, mask, query, qnorm)
        local = out['displacement'][0].float().cpu().numpy().astype(np.float64)
        psi = out['yaw'][0, :, 0].float().cpu().numpy().astype(np.float64)
        placed = base+rotate(local[1:], heading, normal)
        xyz.append(placed)
        yaw.append(heading+psi[1:])
        base, heading = placed[-1], heading+float(psi[-1])
    return np.concatenate(xyz), np.concatenate(yaw)


def project(displacement, camera, canvas):
    from step2.geometry import canonical_ground_normal_camera, query_ground_anchor
    q = np.array([[camera.cx, canvas-1.]])
    anchor, valid = query_ground_anchor(q, camera.intrinsics,
                                        canonical_ground_normal_camera(camera.pitch_down_deg), camera.camera_height_m)
    points = displacement+anchor[0]
    depth = points[:, 2] > 1e-4
    z = np.maximum(points[:, 2], 1e-4)
    uv = np.column_stack([camera.fx*points[:, 0]/z+camera.cx,
                          camera.fy*points[:, 1]/z+camera.cy])
    inside = (bool(valid[0]) & depth & (uv[:, 0] >= 0) & (uv[:, 0] < camera.width)
              & (uv[:, 1] >= 0) & (uv[:, 1] < canvas))
    return uv, depth, inside


def trajectory(displacement, yaw, camera, canvas):
    uv, depth, inside = project(displacement, camera, canvas)
    return {'displacement_m': displacement.tolist(), 'ground_m': ground(displacement, camera.pitch_down_deg).tolist(),
            'uv_px': uv.tolist(), 'positive_depth': depth.tolist(), 'in_canvas': inside.tolist(),
            'yaw_rad': yaw.tolist()}


def metrics(prediction, truth):
    err = np.linalg.norm(np.asarray(prediction['ground_m'])-truth['ground_m'], axis=1)
    d3 = np.linalg.norm(np.asarray(prediction['displacement_m'])-truth['displacement_m'], axis=1)
    domain = np.asarray(truth['in_canvas'], bool).copy(); domain[0] = False
    pixel = np.linalg.norm(np.asarray(prediction['uv_px'])-truth['uv_px'], axis=1)
    return {'mean_ground_error_m': float(err[1:].mean()) if len(err)>1 else None,
            'endpoint_ground_error_m': float(err[-1]), 'mean_3d_error_m': float(d3[1:].mean()) if len(d3)>1 else None,
            'mean_pixel_error_px': float(pixel[domain].mean()) if domain.any() else None,
            'pixel_reference_points': int(domain.sum()),
            'negative_depth_points': int((~np.asarray(prediction['positive_depth'], bool)).sum()),
            'ground_error_cm': (err*100).tolist()}


def cached_flow(cache, frames, engine, batch_size, device, on_progress):
    import cv2
    import torch
    if cache.exists():
        with np.load(cache, allow_pickle=False) as z:
            flow, conf, valid = z['flow'].copy(), z['confidence'].copy(), z['valid'].copy()
        if len(flow) != len(frames)-1:
            raise ValueError('Cached flow count does not match frames')
        on_progress(len(flow), len(flow))
        return flow, conf, valid
    all_flow, all_conf, all_valid = [], [], []
    begin, size = 0, batch_size
    started = time.time()
    while begin < len(frames)-1:
        end = min(begin+size, len(frames)-1)
        image0, image1 = [], []
        for i in range(begin, end):
            pair = [cv2.imread(str(frames[i])), cv2.imread(str(frames[i+1]))]
            if any(im is None or im.shape[:2] != (540, 960) for im in pair):
                raise ValueError(f'Unreadable/incompatible frame at {frames[i]}')
            image0.append(torch.from_numpy(cv2.cvtColor(pair[0], cv2.COLOR_BGR2RGB)).permute(2, 0, 1))
            image1.append(torch.from_numpy(cv2.cvtColor(pair[1], cv2.COLOR_BGR2RGB)).permute(2, 0, 1))
        try:
            x = torch.stack(image0).float().to(device)
            y = torch.stack(image1).float().to(device)
            flow, conf, valid, _, _ = engine._cs.infer_batch(engine.model, engine.args, x, y, (90, 160))
            all_flow.append(flow.permute(0, 2, 3, 1).cpu().half().numpy())
            all_conf.append(conf.cpu().half().numpy())
            all_valid.append(valid.cpu().numpy().astype(np.uint8))
        except torch.cuda.OutOfMemoryError:
            if size <= 1:
                raise
            del x, y
            torch.cuda.empty_cache()
            size = max(1, size//2)
            print('FLOW_BATCH_REDUCED',size,flush=True)
            continue
        begin = end
        if begin % max(8*size, 1) == 0 or begin == len(frames)-1:
            on_progress(begin, len(frames)-1)
            print(f'FLOW {begin}/{len(frames)-1} {begin/max(time.time()-started, .01):.1f} pairs/s',flush=True)
    arrays = (np.concatenate(all_flow), np.concatenate(all_conf), np.concatenate(all_valid))
    assert np.isfinite(arrays[0]).all() and np.isfinite(arrays[1]).all()
    tmp = str(cache)+'.tmp.npz'
    np.savez_compressed(tmp, flow=arrays[0], confidence=arrays[1], valid=arrays[2])
    os.replace(tmp, cache)
    return arrays


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--pilot', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--data-root', type=Path, default=Path('/data/robotics/toshith/flowvo_compare'))
    parser.add_argument('--device', default='cuda', choices=['cpu', 'cuda'])
    parser.add_argument('--flow-batch-size', type=int, default=8)
    parser.add_argument('--window', type=int, default=24)
    parser.add_argument('--context-mode', choices=('chunked','sliding'), default='chunked')
    parser.add_argument('--solver-control', choices=('unchanged','center','split'), default='unchanged')
    parser.add_argument('--center-ratio', type=float, default=.5)
    args = parser.parse_args()
    project, output = args.project.resolve(), args.out.resolve()
    if not output.is_relative_to(project) or output.is_relative_to(project/'baseline'):
        raise ValueError('Outputs must remain in the project lab')
    output.mkdir(parents=True, exist_ok=True)
    # Height-corrected recordings may keep the original episode stem. Namespace
    # their flow by data-root and pose bytes; never reuse the old-height flow.
    cache_root = project/'gqft_mask_review/full_episode_flow_cache_v2'
    cache_root.mkdir(exist_ok=True)
    for key, folder in [('XDG_CACHE_HOME','cache'),('HF_HOME','cache/hf'),('TORCH_HOME','cache/torch'),('CUDA_CACHE_PATH','cache/cuda')]:
        os.environ[key] = str(output/folder)
    sys.path.insert(0, str(args.source.resolve()))
    import cv2
    import torch
    from step2.checkpoint import load_gqft_checkpoint
    from step2.episode_contract import pack_normalized_flow
    from step2.geometry import canonical_ground_normal_camera
    if args.device=='cuda' and os.environ.get('CUDA_VISIBLE_DEVICES') != '4':
        raise ValueError('Only the user-approved physical GPU 4 may be used')
    cv2.setNumThreads(1); torch.set_num_threads(2)
    device = torch.device('cuda:0' if args.device=='cuda' else 'cpu')
    torch.backends.cuda.matmul.allow_tf32 = False
    models, checkpoints = {}, {}
    for arm in ARMS:
        path = args.pilot/arm/'best.pt'
        model, checkpoint = load_gqft_checkpoint(path, device)
        override=None
        if args.solver_control!='unchanged' and model.config.motion_prior=='ground_solver':
            from step2.motion_controls import configure_solver_control
            override=configure_solver_control(model,variant=args.solver_control,center_ratio=args.center_ratio)
        models[arm] = model
        checkpoints[arm] = {'path': str(path), 'sha256': sha(path), 'step': checkpoint.get('step'),
                            'config': asdict(model.config), 'runtime_override':override,
                            'color': COLORS[arm], 'label': LABELS[arm]}
    camera = models[ARMS[0]].camera; canvas = models[ARMS[0]].config.canvas_height
    assert all(m.camera==camera and m.config.canvas_height==canvas for m in models.values())
    assert args.window <= min(m.config.max_history for m in models.values())
    episodes = []
    for path in sorted((args.data_root/'poses').glob('b10_A_drivefix_idx*.npz')):
        frames = sorted((args.data_root/'frames'/path.stem).glob('*.png'))
        with np.load(path, allow_pickle=False) as z:
            poses = z['pose'].copy(); starts=z['leg_start'].copy()
            agent_y=z['agent_y'].copy() if 'agent_y' in z else None
            physical = json.loads(str(z['physical'].item()))
            episode = int(z['episode_id']); scene = str(z['scene'].item())
        assert len(frames)==len(poses) and len(frames)>1
        assert physical['resolution']==[camera.height,camera.width]
        assert math.isclose(physical['camera_position_agent'][1],camera.camera_height_m,abs_tol=1e-4)
        assert math.isclose(-physical['camera_orientation_deg'][0],camera.pitch_down_deg,abs_tol=1e-4)
        assert math.isclose(camera.width/(2*math.tan(math.radians(physical['hfov_deg'])/2)),camera.fx,rel_tol=1e-5)
        assert starts[0]==0 and np.all(np.diff(starts)>0) and starts[-1]<len(poses)
        episodes.append({'id':episode,'scene':scene,'poses_path':path,'frames':frames,
                         'poses':poses,'starts':starts,'physical':physical,'agent_y':agent_y})
    episodes.sort(key=lambda e:(e['id'] != 629,e['id']))
    manifest = {'created_utc':datetime.now(timezone.utc).isoformat(),'pilot':str(args.pilot),
                'camera':asdict(camera),'canvas_height':canvas,'window':args.window,
                'checkpoints':checkpoints,'colors':COLORS,'episodes':[],
                'expected_episode_count':len(episodes),'expected_leg_count':sum(len(e['starts']) for e in episodes),
                'total_frames':sum(len(e['frames']) for e in episodes),
                'scope':'Frozen full-recording diagnostics, no training, selection, fitted scale or ground-truth heading stitching',
                'context_mode':args.context_mode,
                'solver_control':args.solver_control,
                'experiment_note':('Frozen central-floor runtime control; checkpoint weights unchanged. '
                                   if args.solver_control=='center' else 'Frozen original solver rule. ')+
                                  ('Mesh-reconstructed 1.2m RGB counterfactual; not recovered logged elevation.'
                                   if any(e['agent_y'] is not None for e in episodes) else
                                   'Original RGB and pose recordings; height correction is separate.'),
                'integration':f'{args.context_mode} {args.window}-pair context; only predicted yaw integrates 3-D motion; leg views reset at each recorded leg; full-episode view runs continuously',
                'metrics':'Post-origin ground errors; pixel errors on pointwise reference-valid canvas points independent of predicted stopping',
                'time_protocol':'Consecutive recorded PNGs, no resampling; capture rate not reinterpreted as a benchmark',
                'runtime_source_sha256':{str(p.relative_to(args.source)):sha(p) for p in sorted(args.source.rglob('*.py'))},
                'physical_gpu':4 if args.device=='cuda' else None}
    save(output/'manifest.json',manifest)
    for p in ['/data/robotics/toshith/HSGM_public/integration','/data/robotics/toshith/SEA-RAFT/core',
              '/data/robotics/toshith/SEA-RAFT','/data/robotics/toshith/rgbd_vo_dataset']:
        sys.path.append(p)
    from flow_localizer import FlowEngine
    engine = FlowEngine(device)
    manifest['flow_frontend'] = {
        'weights': '/data/robotics/toshith/hf_cache_isl/searaft_spring540x960M.pth',
        'weights_sha256': sha('/data/robotics/toshith/hf_cache_isl/searaft_spring540x960M.pth'),
        'config_sha256': sha('/data/robotics/toshith/SEA-RAFT/config/eval/spring-M.json'),
        'iterations': engine.args.iters, 'batch_size_requested': args.flow_batch_size,
        'flow_units': 'du/W,dv/H', 'saved_dtype': 'float16 with uint8 validity',
        'recipe': 'Original forward/backward SEA-RAFT confidence and 0.75 downsampled validity'}
    save(output/'manifest.json',manifest)
    # Retain our package precedence after the external engine's import-time setup.
    sys.path.insert(0, str(args.source.resolve()))
    status = {'status':'running','completed_episodes':[],'expected_episodes':len(episodes)}
    for e in episodes:
        ep=e['id']; folder=output/f'ep{ep}';folder.mkdir(exist_ok=True)
        print(f'EPISODE {ep}: {len(e["frames"])} frames, {len(e["starts"])} legs',flush=True)
        def progress(done,total):
            status.update(current_episode=ep,stage='flow',flow_pairs_done=done,flow_pairs_total=total)
            save(output/'status.json',status)
        identity=hashlib.sha256((str(args.data_root.resolve())+sha(e['poses_path'])+
                                manifest['flow_frontend']['weights_sha256']).encode()).hexdigest()[:20]
        flow_cache=cache_root/(e['poses_path'].stem+'_'+identity+'.npz')
        flow, confidence, valid=cached_flow(flow_cache,e['frames'],engine,args.flow_batch_size,device,progress)
        features=pack_normalized_flow(flow,confidence,valid)
        record={'episode':ep,'scene':e['scene'],'poses_path':str(e['poses_path']),
                'poses_sha256':sha(e['poses_path']),'flow_cache_sha256':sha(flow_cache),
                'flow_cache_identity':identity,
                'frames':len(e['frames']),'vertical_reference':'mesh_reconstructed' if e['agent_y'] is not None else 'legacy_constant_renderer_height',
                'segments':[]}
        ranges=[('full',0,len(e['poses']))]+[(f'leg{i:02d}',int(a),int(e['starts'][i+1]) if i+1<len(e['starts']) else len(e['poses']))
                                               for i,a in enumerate(e['starts'])]
        for name,a,b in ranges:
            status.update(stage='trajectory',current_segment=name);save(output/'status.json',status)
            f=features[a:b-1]
            truth_disp=reference(e['poses'][a:b],camera.pitch_down_deg,
                                 e['agent_y'][a:b] if e['agent_y'] is not None else None)
            truth_yaw=-np.unwrap(e['poses'][a:b,2]-e['poses'][a,2])
            truth=trajectory(truth_disp,truth_yaw,camera,canvas)
            segment={'id':name,'start_frame':a,'end_frame_exclusive':b,'pairs':b-a-1,
                     'frame_start_name':e['frames'][a].name,'background':f'ep{ep}/{name}/keyframe.jpg',
                     'reference':truth,'predictions':{},'chunk_boundaries':list(range(args.window,b-a,args.window)),
                     'short_history_steps':min(1,b-a-1)}
            target=folder/name;target.mkdir(exist_ok=True)
            cv2.imwrite(str(target/'keyframe.jpg'),cv2.imread(str(e['frames'][a])),[cv2.IMWRITE_JPEG_QUALITY,86])
            for arm,model in models.items():
                xyz,yaw=stitch(model,f,args.window,device,args.context_mode)
                assert len(xyz)==b-a and np.isfinite(xyz).all() and np.isfinite(yaw).all()
                pred=trajectory(xyz,yaw,camera,canvas);pred['metrics']=metrics(pred,truth)
                segment['predictions'][arm]=pred
            record['segments'].append(segment)
        save(folder/'predictions.json',record)
        entry={'episode':ep,'scene':e['scene'],'frames':len(e['frames']),'legs':len(e['starts']),
               'data':f'ep{ep}/predictions.json','sha256':sha(folder/'predictions.json')}
        manifest['episodes'].append(entry);save(output/'manifest.json',manifest)
        status['completed_episodes'].append(ep);save(output/'status.json',status)
        print('EPISODE_DONE',ep,flush=True)
    status.update(status='completed',stage='finished');save(output/'status.json',status)
    print('ALL_EPISODES_DONE',output,flush=True)


if __name__=='__main__':
    main()
