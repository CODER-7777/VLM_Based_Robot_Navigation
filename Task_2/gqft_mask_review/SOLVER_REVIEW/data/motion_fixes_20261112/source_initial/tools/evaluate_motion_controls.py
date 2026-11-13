"""Frozen validation of motion controls on full observed HSGM sequences.

This is a new 48-pair diagnostic protocol, not the historical H24 benchmark or
history gate. Constants are declared before validation; locked test is forbidden.
"""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import torch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from step2.checkpoint import load_gqft_checkpoint
from step2.dataset import FlowPathDataset,collate_windows
from step2.geometry import canonical_ground_normal_camera,project_displacements_torch
from step2.ground_solver import GroundPlaneSolver,planar_to_camera_increment
from step2.motion_controls import (DirectionalGroundSolver,neural_local_steps,
                                  integrate_local_steps,quality_fuse)
from step2.metrics import PathMetricAccumulator


@torch.inference_mode()
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--manifest',required=True)
    ap.add_argument('--checkpoint',required=True)
    ap.add_argument('--sequences-root',default=None)
    ap.add_argument('--split',choices=['train','val'],default='val')
    ap.add_argument('--device',choices=['cpu','cuda'],default='cpu')
    ap.add_argument('--history',type=int,default=48)
    ap.add_argument('--window',type=int,default=24)
    ap.add_argument('--floor-cutoff',type=float,default=1.)
    ap.add_argument('--center-ratio',type=float,default=.5)
    ap.add_argument('--far-near-m',type=float,default=3.)
    ap.add_argument('--far-far-m',type=float,default=8.)
    ap.add_argument('--quality-good-px',type=float,default=2.)
    ap.add_argument('--quality-bad-px',type=float,default=5.)
    ap.add_argument('--max-sequences',type=int,default=0)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    model,checkpoint=load_gqft_checkpoint(args.checkpoint,args.device)
    if model.config.motion_prior!='none' or model.config.motion_integration!='yaw_local':
        raise ValueError('Fallback needs the independent yaw-local reference, not a solver residual head')
    camera=model.camera;extension=model.config.canvas_height-camera.height
    data=FlowPathDataset(args.manifest,args.split,sequences_root=args.sequences_root,min_history=2,
                         max_history=args.history,deterministic_history=args.history,queries=1,
                         virtual_extension_px=extension,seed=20260820,target_ground_plane='sequence_floor')
    if data.camera!=camera:raise ValueError('Checkpoint/dataset camera mismatch')
    assert args.history>args.window,'Need a path longer than one context to test restart effects'
    methods=['neural_chunked','neural_sliding','solver_joint','solver_center','solver_split','quality_fused']
    metric={name:PathMetricAccumulator(camera) for name in methods}
    joint=GroundPlaneSolver(camera,max_floor_m=args.floor_cutoff).to(args.device)
    center=DirectionalGroundSolver(camera,variant='center',max_floor_m=args.floor_cutoff,
                                   center_ratio=args.center_ratio).to(args.device)
    split=DirectionalGroundSolver(camera,variant='split',max_floor_m=args.floor_cutoff,
                                  center_ratio=args.center_ratio,far_near_m=args.far_near_m,
                                  far_far_m=args.far_far_m).to(args.device)
    records=[];normal=torch.tensor(canonical_ground_normal_camera(camera.pitch_down_deg),device=args.device,dtype=torch.float32)
    count=min(len(data),args.max_sequences or len(data))
    for index in range(count):
        item=data[index];batch=collate_windows([item])
        batch={k:v.to(args.device) if torch.is_tensor(v) else v for k,v in batch.items()}
        features=batch['flow'][0]
        local={}
        for mode in ['chunked','sliding']:
            local['neural_'+mode]=neural_local_steps(model,features,window=args.window,mode=mode)
        geometry={}
        for name,solver in [('solver_joint',joint),('solver_center',center),('solver_split',split)]:
            motion,info=solver(features);geometry[name]=(motion,info)
            local[name]=(planar_to_camera_increment(motion,camera.pitch_down_deg),motion[:,2])
        fused_delta,fused_yaw,alpha=quality_fuse(*local['neural_sliding'],*geometry['solver_joint'],camera,
                                               good_px=args.quality_good_px,bad_px=args.quality_bad_px)
        local['quality_fused']=(fused_delta,fused_yaw)
        target=batch['displacement'][0];up=target@normal
        row={'sequence':item['sequence'],'start':item['start'],'pairs':len(features),
             'ground_truth_up_span_m':float(up.max()-up.min()),'methods':{},
             'mean_solver_fraction':float(alpha.mean()),'solver_rejected_fraction':float((alpha==0).float().mean())}
        for name,(delta,dyaw) in local.items():
            disp,yaw=integrate_local_steps(delta,dyaw,camera.pitch_down_deg)
            uv,valid=project_displacements_torch(disp[None],batch['query_uv'],camera,
                                                (camera.width,model.config.canvas_height))
            scale=uv.new_tensor([camera.width-1,camera.height-1])
            out={'uv_norm':uv/scale,'analytic_valid':valid,'valid_logits':valid.float()*20-10,
                 'pose_mask':torch.ones(1,len(disp),device=args.device,dtype=torch.bool)}
            metric[name].update(out,batch)
            difference=disp-target
            horizontal=difference-(difference*normal).sum(-1,keepdim=True)*normal
            e=torch.linalg.vector_norm(horizontal,dim=-1)
            yaw_diff=yaw-batch['target_yaw'][0,:,0]
            yaw_error=torch.atan2(yaw_diff.sin(),yaw_diff.cos()).abs()
            row['methods'][name]={'mean_ground_error_m':float(e[1:].mean()),
                'endpoint_ground_error_m':float(e[-1]),
                'mean_3d_error_m':float(torch.linalg.vector_norm(difference[1:],dim=-1).mean()),
                'endpoint_yaw_error_deg':float(torch.rad2deg(yaw_error[-1])),
                'displacement_m':disp.cpu().tolist(),'yaw_rad':yaw.cpu().tolist()}
        records.append(row)
        print('SEQUENCE',index+1,count,item['sequence'],json.dumps({k:round(v['mean_ground_error_m'],4) for k,v in row['methods'].items()}),flush=True)
    summary={}
    for name in methods:
        summary[name]={**metric[name].compute()}
        for key in ['mean_ground_error_m','endpoint_ground_error_m','mean_3d_error_m','endpoint_yaw_error_deg']:
            summary[name][key]=float(np.mean([r['methods'][name][key] for r in records]))
    subsets={}
    for label,predicate in [('approximately_planar',lambda r:r['ground_truth_up_span_m']<=.1),
                             ('height_changing',lambda r:r['ground_truth_up_span_m']>.1)]:
        rows=[r for r in records if predicate(r)]
        subsets[label]={'sequences':len(rows),'ground_mean_m':{k:float(np.mean([r['methods'][k]['mean_ground_error_m'] for r in rows])) if rows else None for k in methods}}
    comparisons={}
    for candidate,reference in [('solver_center','solver_joint'),('solver_split','solver_center'),
                                ('neural_sliding','neural_chunked'),('quality_fused','neural_sliding')]:
        diff=np.array([r['methods'][candidate]['mean_ground_error_m']-r['methods'][reference]['mean_ground_error_m'] for r in records])
        rng=np.random.default_rng(20261112)
        samples=diff[rng.integers(len(diff),size=(10000,len(diff)))].mean(1)
        comparisons[candidate+'_vs_'+reference]={'mean_change_m':float(diff.mean()),
            'sequence_bootstrap_95_m':np.quantile(samples,[.025,.975]).tolist(),
            'sequences_improved':int((diff<0).sum()),'sequences':len(diff)}
    result={'protocol':{'split':args.split,'observed_pairs':args.history,'context':args.window,
              'queries':1,'canvas':[camera.width,model.config.canvas_height],'camera':asdict(camera),
              'precision':'float32','pixel_origin_included':True,'motion_origin_excluded':True,
              'validity':'Analytic canvas gate only; learned validity head is not compared',
              'benchmark_status':'Separate full-observed-sequence diagnostic; not the historical H24 benchmark/history gate',
              'constants':vars(args)|{'out':str(args.out)},'locked_test_accessed':False,
              'limits':'One validation scene; paired sequence bootstrap does not establish cross-scene generalization'},
            'checkpoint_sha256':hashlib.sha256(Path(args.checkpoint).read_bytes()).hexdigest(),
            'summary':summary,'subsets':subsets,'comparisons':comparisons,'sequences':records}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    tmp=args.out.with_suffix('.tmp');tmp.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');tmp.replace(args.out)
    print('SUMMARY',json.dumps(summary),flush=True)


if __name__=='__main__':main()
