"""CPU regression checks for directional cues, rolling context and height queries."""
import argparse
import json
import hashlib
import tempfile
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import torch

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'gqft_algorithm_sharing_vivekananda'))
from step2.geometry import CameraModel,canonical_ground_normal_camera
from step2.ground_solver import GroundPlaneSolver
from step2.motion_controls import (DirectionalGroundSolver,neural_local_steps,
                                  integrate_local_steps,quality_fuse,configure_solver_control)
from step2.models.gqft import GQFT,GQFTConfig
from audit_episode_heights import VerticalFloorIndex,mp3d_to_habitat
from render_corrected_frames import prepare


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=HERE/'cpu_verification.json')
    args=parser.parse_args();torch.set_num_threads(2)
    camera=CameraModel(width=960,height=540,fx=198.82250993908562,fy=198.82250993908562,
                       cx=480.,cy=270.,camera_height_m=1.2,pitch_down_deg=30.)
    checks={}
    def ok(name,value):
        checks[name]=bool(value);print(('PASS ' if value else 'FAIL ')+name,flush=True)
    base=GroundPlaneSolver(camera,max_floor_m=1.)
    def flow(motion):
        g=base.grid(90,160,'cpu');uv,_=base._project(motion,g['body'],g['R'])
        result=torch.zeros(len(motion),4,90,160)
        result[:,:2]=((uv-g['uv0'][None])/torch.tensor([960.,540.])).transpose(1,2).reshape(-1,2,90,160)
        result[:,2:]=1
        return result
    truth=torch.tensor([[.06,.015,.08],[.03,-.01,-.07]])
    center=DirectionalGroundSolver(camera,variant='center',max_floor_m=1.)
    est,_=center(flow(truth))
    ok('central_floor_joint_recovers_synthetic_motion',torch.allclose(est,truth,atol=3e-4))
    split=DirectionalGroundSolver(camera,variant='split',max_floor_m=1.)
    pure=torch.tensor([[0.,0.,.08],[0.,0.,-.06]])
    est,info=split(flow(pure))
    ok('far_ray_branch_recovers_pure_yaw',torch.allclose(est[:,2],pure[:,2],atol=2e-4))
    ok('pure_yaw_does_not_invent_translation',bool(est[:,:2].abs().max()<3e-4))
    empty,empty_info=split(torch.zeros(2,4,90,160))
    ok('empty_directional_support_finite_zero',torch.isfinite(empty).all() and empty.abs().max()==0)
    w=center.pixel_weights(flow(truth));g=center.grid(90,160,'cpu')
    outside=(g['body'][:,0]<=0)|(g['body'][:,1].abs()>.5*g['body'][:,0])
    ok('translation_excludes_noncentral_cells',bool(w[:,outside].eq(0).all()))
    axis=torch.tensor(canonical_ground_normal_camera(30),dtype=torch.float32)
    forward=torch.tensor([0.,-.5,np.sqrt(3)/2],dtype=torch.float32)
    class Toy:
        config=SimpleNamespace(max_history=30,predict_yaw=True,canvas_height=810)
        calls=[]
        def __init__(self):self.camera=camera;self.calls=[]
        def __call__(self,x,mask,q,qn):
            n=x.shape[1];self.calls.append(n)
            local=(.03*forward+.001*axis).expand(n,3)
            xyz,yaw=integrate_local_steps(local,torch.full((n,),.02),30)
            return {'delta_local':local[None], 'displacement':xyz[None], 'yaw':yaw[None,:,None]}
    features=torch.zeros(60,4,8,12);toy=Toy()
    local,yaw=neural_local_steps(toy,features,window=24,mode='sliding')
    ok('rolling_history_never_restarts_after_warmup',toy.calls==list(range(1,25))+[24]*36)
    ok('rolling_emits_each_newest_step_once',local.shape==(60,3) and yaw.shape==(60,))
    xyz,heading=integrate_local_steps(local,yaw,30)
    ok('rolling_integration_preserves_vertical_motion',torch.allclose(xyz@axis,torch.arange(61)*.001,atol=1e-6))
    other=Toy();dl,dy=neural_local_steps(other,features,window=24,mode='chunked')
    control,_=integrate_local_steps(dl,dy,30)
    ok('chunk_and_rolling_equal_for_context_invariant_motion',torch.allclose(control,xyz,atol=1e-6))
    neural=torch.ones(4,3)*.02;ny=torch.ones(4)*.03
    motion=torch.tensor([[.04,.01,.02]]).repeat(4,1);motion[-1]=float('nan')
    info={'residual_rms_px':torch.tensor([0.,10.,0.,float('nan')]),'weight_sum':torch.tensor([100.,100.,0.,100.])}
    fused,fy,alpha=quality_fuse(neural,ny,motion,info,camera)
    ok('quality_gate_rejects_poor_empty_nonfinite_solver',torch.equal(alpha,torch.tensor([1.,0.,0.,0.])))
    ok('fallback_is_exact_independent_neural_motion',torch.equal(fused[1:],neural[1:]) and torch.equal(fy[1:],ny[1:]))
    triangles=np.array([[[-2,0,-2],[2,0,-2],[2,0,2]],[[-2,0,-2],[2,0,2],[-2,0,2]],
                        [[-2,2,-2],[2,2,-2],[2,2,2]],[[-2,2,-2],[2,2,2],[-2,2,2]]],float)
    index=VerticalFloorIndex(triangles)
    h=index.support(0,0,0.,1.2);up=index.support(0,0,2.,1.2)
    ok('absolute_upstairs_floor_is_not_clearance_error',abs(h['camera_clearance_m']-1.2)<1e-9 and abs(up['camera_clearance_m']-1.2)<1e-9)
    mismatch=index.support(0,0,.5,1.2)
    ok('height_audit_measures_mesh_clearance',abs(mismatch['camera_clearance_m']-1.7)<1e-9)
    ok('mp3d_axis_conversion_is_fixed_right_handed',np.array_equal(mp3d_to_habitat(np.array([[1.,2.,3.]])),[[1.,3.,-2.]]))
    with tempfile.TemporaryDirectory(prefix='gqft-height-plan-',dir='/tmp') as temp:
        poses=Path(temp)/'source.npz';audit=Path(temp)/'audit.json'
        source=np.array([[0.,0.,0.],[.1,0.,0.]])
        np.savez(poses,pose=source,leg_start=np.array([0]),floor_y=3.,episode_id=1,scene='example.glb',
                 physical=json.dumps({'camera_position_agent':[0.,1.2,0.]}))
        payload={'poses_sha256':hashlib.sha256(poses.read_bytes()).hexdigest(),
                 'frames':[{'status':'measured','floor_y':2.},{'status':'measured','floor_y':2.1}]}
        audit.write_text(json.dumps(payload));fixed,physical=prepare(poses,audit)
        ok('height_plan_preserves_recorded_xz_yaw',np.array_equal(fixed['pose'],source))
        ok('height_plan_camera_is_mount_above_measured_floor',np.allclose(fixed['camera_y']-fixed['local_floor_y'],1.2))
        payload['frames'][1]['status']='missing_support';audit.write_text(json.dumps(payload))
        try:prepare(poses,audit);rejected=False
        except ValueError:rejected=True
        ok('height_plan_rejects_uncertain_support',rejected)
    model=GQFT(GQFTConfig(predict_yaw=True,motion_integration='yaw_local',motion_prior='ground_solver',
                          ground_learned_weights=True,canvas_height=810),camera).eval()
    before={k:v.clone() for k,v in model.state_dict().items()}
    configure_solver_control(model,variant='center')
    ok('runtime_center_control_preserves_all_checkpoint_parameters',all(torch.equal(v,model.state_dict()[k]) for k,v in before.items()))
    result={'checks':checks,'passed':sum(checks.values()),'total':len(checks),'scope':'Synthetic CPU contracts, not real-data improvement'}
    args.out.write_text(json.dumps(result,indent=2)+'\n')
    if not all(checks.values()):raise SystemExit(1)


if __name__=='__main__':main()
