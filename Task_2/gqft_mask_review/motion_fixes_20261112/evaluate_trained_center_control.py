"""Same-scene follow-up: frozen central-floor intervention on trained hybrids.

This is the historical 104-window H24 task contract in float32. It is not an
independent replication of the preceding full-sequence validation experiment.
"""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import torch


@torch.inference_mode()
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source',type=Path,required=True)
    ap.add_argument('--project',type=Path,required=True)
    ap.add_argument('--pilot',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--device',choices=['cpu','cuda'],default='cpu')
    args=ap.parse_args();sys.path.insert(0,str(args.source))
    from tools.evaluate_ground_solver import build_loader,score
    from step2.checkpoint import load_gqft_checkpoint
    from step2.motion_controls import configure_solver_control
    spec=SimpleNamespace(manifest=str(args.project/'results/hsgm_manifest_v1.json'),
        sequences_root='/data/robotics/toshith/rgbd_vo_dataset/hsgm_sequences',reference_history=30,
        history=24,queries=1,seed=20260820,virtual_extension_px=270,target_ground_plane='sequence_floor',
        batch_size=4,workers=0)
    loader,camera=build_loader(spec,'val',0)
    results={}
    for arm in ['yaw_local_reference','solver_residual','solver_learned_weights']:
        path=args.pilot/arm/'best.pt'
        model,checkpoint=load_gqft_checkpoint(path,args.device)
        assert model.camera==camera and model.config.canvas_height==810
        for variant in (['unchanged'] if arm=='yaw_local_reference' else ['unchanged','center']):
            override=configure_solver_control(model,variant='center',center_ratio=.5) if variant=='center' else None
            measured,rows=score(model,loader,args.device)
            assert len(rows)==104
            results[arm+'__'+variant]={'metrics':measured,'windows':rows,'override':override,
                'checkpoint_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'checkpoint_step':checkpoint['step'],
                'training_config':asdict(model.config)}
            print('RESULT',arm,variant,json.dumps(measured),flush=True)
    payload={'protocol':{'validation_windows':104,'sequences':26,'reference_history':30,'observed_history':24,
        'query':[480,809],'canvas':[960,810],'precision':'float32','labels':'sequence_floor',
        'selection_scope':'Same-scene follow-up diagnostic; no locked-test access or independent replication',
        'training_performed':False,'center_ratio_predeclared':.5},'results':results}
    args.out.write_text(json.dumps(payload,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':main()
