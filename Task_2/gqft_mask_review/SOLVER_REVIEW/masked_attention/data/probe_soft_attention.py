"""Predeclared soft-attention trial with untouched max pooling and frozen weights."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

import isolate_masking as base
import numpy as np
import torch

LAB, ROOT = base.LAB, base.ROOT
PLAN_PATH = LAB/'soft_attention_plan.json'
POLICIES = ('original', 'attention_only', 'soft_coarse_attention', 'soft_rf_attention')
FLOOR = .25


class SoftAttentionIntervention(base.PoolingIntervention):
    """Only attention changes. Retain the original max feature vector bit for bit."""
    def prepare(self, flow):
        super().prepare(flow)
        self.original_max = self.feat.amax((-2, -1))

    def attention_weights(self):
        if self.policy == 'original':
            return self.original_attention
        if self.policy == 'attention_only':
            observed = self.coarse.flatten(1).any(1)
            logits = self.logits.float().flatten(1).masked_fill(~self.coarse.flatten(1), -torch.inf)
            logits = torch.where(observed[:, None], logits, torch.zeros_like(logits))
            return logits.softmax(-1).reshape_as(self.logits).masked_fill(~self.coarse, 0).to(self.feat.dtype)
        if self.policy not in ('soft_coarse_attention', 'soft_rf_attention'):
            raise ValueError(f'Unknown policy {self.policy}')
        coverage = self.rf_coverage if self.policy == 'soft_rf_attention' else self.coarse_coverage
        reliability = FLOOR + (1-FLOOR)*coverage.clamp(0, 1)
        adjusted = self.original_attention.float()*reliability
        adjusted = adjusted/adjusted.sum((1,2,3), keepdim=True).clamp_min(torch.finfo(torch.float32).tiny)
        constant = reliability.flatten(1).amax(1) == reliability.flatten(1).amin(1)
        # Uniform reliability cancels analytically; bypass division to retain bit identity.
        return torch.where(constant[:,None,None,None], self.original_attention, adjusted).to(self.feat.dtype)

    def forward(self, flow, *, return_diagnostics=False):
        if flow.shape != self.flow.shape or flow.data_ptr() != self.flow.data_ptr():
            raise ValueError('Prepare exactly the tensor consumed by the model')
        weights = self.attention_weights()
        token = self.encoder.pool(torch.cat([(self.feat*weights).sum((-2,-1)), self.original_max], -1))
        if return_diagnostics:
            return token, {'attention_weights': weights, 'max_pooled': self.original_max}
        return token


def summarize(rows):
    result = {}
    means = ('mean_ground_error_m','endpoint_ground_error_m','mean_3d_error_m',
             'endpoint_3d_error_m','mean_pixel_error_px','last_valid_pixel_error_px')
    for policy in POLICIES:
        valid = [r['metrics'][policy] for r in rows]
        summary = {key:float(np.mean([x[key] for x in valid if x[key] is not None])) for key in means}
        for key in ('pixel_points','nonpositive_prediction_depth_points','rejected_prediction_prefix_points'):
            summary[key] = sum(x[key] for x in valid)
        summary['windows_ground_better_than_original'] = sum(r['metrics'][policy]['mean_ground_error_m'] < r['metrics']['original']['mean_ground_error_m'] for r in rows)
        summary['median_window_pixel_error_px'] = float(np.median([x['mean_pixel_error_px'] for x in valid if x['mean_pixel_error_px'] is not None]))
        summary['pooled_pixel_error_px'] = sum(x['pixel_error_sum_px'] for x in valid)/summary['pixel_points']
        summary['delta_from_original'] = {key:summary[key]-result['original'][key] for key in means} if policy != 'original' else {key:0. for key in means}
        result[policy] = summary
    return {'window_count':len(rows), 'policies':result}


def screening(summary, plan):
    original = summary['policies']['original']
    candidate = summary['policies'][plan['primary_candidate']]
    checks = {'mean_ground_strictly_better':candidate['mean_ground_error_m'] < original['mean_ground_error_m']}
    checks.update({key+'_no_regression':candidate[key] <= original[key] for key in plan['selection']['guardrails']})
    checks.update({key+'_no_increase':candidate[key] <= original[key] for key in ('nonpositive_prediction_depth_points','rejected_prediction_prefix_points')})
    return {'primary_candidate':plan['primary_candidate'], 'checks':checks, 'passes_predeclared_screen':all(checks.values()),
            'scope':'Screening on development validation only; no automatic training or production adoption.'}


def draw(summary, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    names = ['Original','Hard attention','Soft coarse','Soft CNN support']
    fig,axes = plt.subplots(1,3,figsize=(14,4.5))
    for ax,key,title in zip(axes,('mean_ground_error_m','endpoint_ground_error_m','mean_pixel_error_px'),
                            ('Mean ground error (cm)','Endpoint ground error (cm)','Mean pixel error (px)')):
        values = [summary['policies'][p][key]*(100 if key.endswith('_m') else 1) for p in POLICIES]
        ax.bar(names,values,color=['#2878b5','#c77646','#8c69a6','#23846b'])
        for i,value in enumerate(values):
            ax.text(i,value,f'{value:.3f}',ha='center',va='bottom',fontsize=9)
        ax.set_ylabel(title)
        ax.tick_params(axis='x',rotation=20)
        ax.grid(axis='y',alpha=.2)
    fig.suptitle(f"{summary['window_count']} paired windows · frozen weights · original max pooling retained")
    fig.tight_layout()
    fig.savefig(out/'soft_attention_comparison.png',dpi=160)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--mode',choices=('validation','episodes'),required=True)
    ap.add_argument('--device',choices=('cpu','cuda'),default='cpu')
    ap.add_argument('--out-dir',type=Path)
    ap.add_argument('--checkpoint',type=Path,default=ROOT/'runs/gqft_spatial_yaw_v1/best.pt')
    ap.add_argument('--manifest',type=Path,default=ROOT/'results/hsgm_manifest_v1.json')
    ap.add_argument('--probe-root',type=Path,default=ROOT/'analysis/masked_attention_v1/episodes/ep629')
    ap.add_argument('--poses-file',type=Path,default=Path('/data/robotics/toshith/flowvo_compare/poses/b10_A_drivefix_idx3_20260829_114756.npz'))
    args = ap.parse_args()
    plan = json.loads(PLAN_PATH.read_text())
    assert plan['policies'] == list(POLICIES) and plan['reliability_floor'] == FLOOR
    assert hashlib.sha256((LAB/'isolate_masking.py').read_bytes()).hexdigest() == plan['immutable_isolation_source_sha256']
    assert hashlib.sha256(args.checkpoint.read_bytes()).hexdigest() == plan['checkpoint_sha256']
    torch.set_num_threads(2)
    torch.manual_seed(plan['validation']['seed'])
    device = torch.device('cpu')
    if args.device == 'cuda':
        visible = os.environ.get('CUDA_VISIBLE_DEVICES','').strip()
        if visible != plan['gpu']:
            raise ValueError('This declared run requires explicitly authorized physical GPU 2')
        torch.cuda.set_device(0)
        device = torch.device('cuda:0')
        print(f'GPU_DEVICE physical={visible} logical=cuda:0 name={torch.cuda.get_device_name(0)}',flush=True)
    model,_ = base.load_gqft_checkpoint(args.checkpoint,'cpu')
    if model.config.spatial_pooling != 'attention_max' or model.config.spatial_mask != 'none':
        raise ValueError('Use matching unmasked trained attention architecture')
    model = model.eval().to(device)
    original_encoder = model.flow_encoder
    pool = SoftAttentionIntervention(original_encoder,.75)
    model.flow_encoder = pool
    h = plan['validation']['evaluated_history']
    protocol = {'created_utc':datetime.now(timezone.utc).isoformat(), 'mode':args.mode, 'plan':plan,
                'plan_sha256':hashlib.sha256(PLAN_PATH.read_bytes()).hexdigest(),
                'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'checkpoint':str(args.checkpoint.resolve()),'camera':asdict(model.camera),'model_config':asdict(model.config),
                'device':str(device),'cuda_visible_devices':os.environ.get('CUDA_VISIBLE_DEVICES') if device.type=='cuda' else None,
                'torch_version':str(torch.__version__),'numpy_version':str(np.__version__),
                'history':h,'origin_excluded':True,'trained':False,'test_accessed':False,
                'shared_domain':'Same target-valid post-origin points for all policies, regardless of prediction gate.'}
    out = args.out_dir or LAB/'soft_attention'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')/args.mode
    if not out.resolve().is_relative_to(LAB.resolve()):
        raise ValueError('Keep outputs within this lab')
    out.mkdir(parents=True,exist_ok=False)
    (out/'predeclared_plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    if args.mode == 'validation':
        dataset = base.FlowPathDataset(str(args.manifest),'val',max_history=30,deterministic_history=30,
                                       queries=1,seed=20260820,virtual_extension_px=270,target_ground_plane='sequence_floor')
        if len(dataset)!=104 or dataset.camera!=model.camera or model.config.canvas_height!=810:
            raise ValueError('Declared validation contract mismatch')
        windows = range(len(dataset))
        protocol.update(manifest=str(args.manifest.resolve()),manifest_sha256=hashlib.sha256(args.manifest.read_bytes()).hexdigest())
    else:
        windows = base.CASES
        protocol.update(poses_file=str(args.poses_file.resolve()),poses_sha256=hashlib.sha256(args.poses_file.read_bytes()).hexdigest())
    rows = []
    with torch.inference_mode():
        for index,case in enumerate(windows):
            saved = None
            if args.mode == 'validation':
                item = dataset[case]
                batch = base.collate_windows([item])
                flow = batch['flow'][:,:h].to(device)
                query,norm = batch['query_uv'].to(device),batch['query_norm'].to(device)
                gt = batch['displacement'][0,:h+1].numpy().astype(np.float64)
                gt_uv = batch['target_uv'][0,:,:h+1].numpy().astype(np.float64)*np.array([model.camera.width-1,model.camera.height-1])
                domain = batch['target_valid'][0,:,:h+1].numpy().copy()
                meta = json.loads((Path(dataset.root)/item['sequence']/'meta.json').read_text())
                row = {'sequence':item['sequence'],'start':item['start'],'motion_family':meta['shape_family']}
            else:
                folder = args.probe_root/case
                if not (folder/'probe.json').exists():
                    folder = folder/'probe'
                saved = json.loads((folder/'probe.json').read_text())
                inputs = json.loads((folder/'episode_inputs.json').read_text())
                if saved['checkpoint_sha256']!=plan['checkpoint_sha256'] or saved['history']!=h or saved['camera']!=asdict(model.camera):
                    raise ValueError('Recorded probe identity/history/camera mismatch')
                with np.load(folder/'flow_searaft_160x90.npz',allow_pickle=False) as cache:
                    packed = base.pack_normalized_flow(cache['flow'],cache['confidence'],cache['valid'])
                flow = torch.from_numpy(packed)[None].to(device)
                if flow.shape[1]!=h:
                    raise ValueError('Recorded flow count mismatch')
                query = flow.new_tensor([[saved['query_px']]])
                norm = query/query.new_tensor([model.camera.width-1,model.camera.height-1])
                begin,leg = inputs['window_start_episode_frame'],inputs['leg']
                with np.load(args.poses_file,allow_pickle=False) as archive:
                    starts = archive['leg_start']
                    end = int(starts[leg+1]) if leg+1<len(starts) else len(archive['pose'])
                    if int(archive['episode_id'])!=629 or int(starts[leg])+inputs['window_start_within_leg']!=begin or begin+h>=end:
                        raise ValueError('Recorded pose/leg mismatch')
                    physical = json.loads(str(archive['physical'].item()))
                    base.validate_camera(physical,model.camera)
                    if not np.allclose(physical['camera_position_agent'][::2],[0.,0.]):
                        raise ValueError('Unsupported horizontal camera offset')
                    _,gt = base.ground_reference(archive['pose'][begin:begin+h+1],model.camera.pitch_down_deg)
                uv,valid,_ = base.project_reference(gt,saved['query_px'],model.camera,model.config.canvas_height)
                gt_uv,domain = uv[None],valid[None]
                row = {'episode_id':629,'leg':leg,'start':begin,'probe':str(folder.resolve())}
            domain[:,0] = False
            flat = flow.reshape(-1,*flow.shape[2:])
            history = torch.ones((1,h),device=device,dtype=torch.bool)
            pool.prepare(flat)
            pool.policy = 'original'
            token_error = float((pool(flat)-original_encoder(flat)).abs().max())
            if token_error!=0:
                raise AssertionError('Original token not bit-identical')
            row.update(support=pool.support_summary(),original_encoder_max_abs=token_error,metrics={},attention_diagnostics={})
            if args.mode=='episodes':
                row['predictions'] = {}
            for policy in POLICIES:
                pool.policy = policy
                output = model(flow,history,query,norm)
                row['metrics'][policy] = base.metrics(output,gt,gt_uv,domain,model.camera,query)
                _,diagnostics = pool(flat,return_diagnostics=True)
                weights = diagnostics['attention_weights']
                max_error = float((diagnostics['max_pooled']-pool.feat.amax((-2,-1))).abs().max())
                norm_error = float((weights.flatten(1).sum(1)-1).abs().max())
                if max_error!=0 or not torch.isfinite(weights).all():
                    raise AssertionError('Max pooling changed or attention became nonfinite')
                if policy!='attention_only' and norm_error>1e-6:
                    raise AssertionError('Soft/original attention not normalized')
                row['attention_diagnostics'][policy] = {'max_pool_max_abs_change':max_error,'weight_sum_max_error':norm_error,
                    'mean_total_variation_from_original':float((weights-pool.original_attention).abs().sum((1,2,3)).mean()/2),
                    'mean_weight_on_coarse_rejected':float((weights*~pool.coarse).sum((1,2,3)).mean())}
                if args.mode=='episodes':
                    row['predictions'][policy] = {'displacement_m':output['displacement'][0].cpu().tolist(),'trajectory_px':output['uv_px'][0,0].cpu().tolist()}
                    if policy=='original':
                        difference = float(np.max(np.abs(output['displacement'][0].cpu().numpy()-np.asarray(saved['predictions']['unmasked']['displacement_m']))))
                        if difference>1e-5:
                            raise AssertionError('Saved original episode no longer reproduced')
                        row['saved_original_prediction_max_abs'] = difference
            rows.append(row)
            with (out/'windows.jsonl').open('a') as f:
                f.write(json.dumps(row,allow_nan=False)+'\n')
            if index%10==0 or index+1==len(windows):
                print(f'SOFT_ATTENTION {args.mode} {index+1}/{len(windows)}',flush=True)
    summary = summarize(rows)
    if args.mode=='validation':
        summary['screening'] = screening(summary,plan)
        families = sorted(set(r['motion_family'] for r in rows))
        summary['by_motion_family'] = {str(f):summarize([r for r in rows if r['motion_family']==f]) for f in families}
    summary['checks'] = {'original_encoder_max_abs':max(r['original_encoder_max_abs'] for r in rows),
                         'max_pooling_max_abs_change':max(d['max_pool_max_abs_change'] for r in rows for d in r['attention_diagnostics'].values()),
                         'cnn_feature_preprocessing_max_abs_change':max(r['support']['cnn_feature_preprocessing_max_abs_change'] for r in rows)}
    (out/'report.json').write_text(json.dumps({'protocol':protocol,'summary':summary},indent=2,allow_nan=False)+'\n')
    draw(summary,out)
    print(json.dumps({'output':str(out.resolve()),'summary':summary['policies'],'screening':summary.get('screening'),'checks':summary['checks']},indent=2),flush=True)


if __name__=='__main__':
    main()
