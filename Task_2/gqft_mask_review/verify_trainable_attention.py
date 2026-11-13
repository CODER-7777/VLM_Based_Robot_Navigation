"""CPU checks of trainable reliability/ground priors and local-yaw semantics."""
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import sys
import tempfile

LAB=Path(__file__).resolve().parent
ROOT=LAB.parent/'gqft_algorithm_sharing_vivekananda'
sys.path.insert(0,str(ROOT))
import numpy as np
import torch
from torch import nn
from step2.models.gqft import GQFT, GQFTConfig, FlowFrameEncoder, gqft_loss
from step2.geometry import (CameraModel, canonical_ground_normal_camera, rotate_about_axis_torch,
                            local_increment_targets_torch, ground_ray_support_torch)
from step2.checkpoint import initialize_gqft, load_gqft_checkpoint


def main():
    torch.set_num_threads(2)
    torch.manual_seed(42)
    camera=CameraModel(width=960,height=540,fx=198.82250993908562,fy=198.82250993908562,
                       cx=480.,cy=270.,camera_height_m=1.2,pitch_down_deg=30.)
    cfg=GQFTConfig(d_model=32,temporal_layers=1,temporal_heads=4,max_history=4,dropout=0,
                   predict_yaw=True,canvas_height=810)
    flow=torch.randn(2,3,4,90,160)*.005
    flow[:,:,2]=.8
    flow[:,:,3]=1
    flow[:,:,3,:,:40]=0
    flow[:,:,:3,:,:40]=0
    hist=torch.tensor([[True,True,True],[True,True,False]])
    query=torch.tensor([[[480.,809.]],[[480.,809.]]])
    checks={}

    # Ground prior is calibrated but cannot label a visible wall as non-ground.
    support=ground_ray_support_torch(camera,90,160,near_m=.5,far_m=8.,device='cpu')
    assert not support[0,0,0].any() and support[0,0,-1].all()
    tiny=ground_ray_support_torch(camera,90,160,near_m=100.,far_m=101.,device='cpu')
    assert tiny.sum()<support.sum()
    checks['calibrated_horizon_depth_prior']=True

    encoder=FlowFrameEncoder(32,spatial_mask='soft_confidence_ground',mask_coverage_rule='receptive_field',camera=camera)
    plain=FlowFrameEncoder(32,camera=camera)
    plain.load_state_dict(encoder.state_dict(),strict=True)
    # Expose both pooling vectors and verify max selection remains original.
    encoder.pool=nn.Identity()
    plain.pool=nn.Identity()
    pooled,maps=encoder(flow[0],return_diagnostics=True)
    torch.testing.assert_close(pooled[:,32:],plain(flow[0])[:,32:],rtol=0,atol=0)
    torch.testing.assert_close(maps['attention_weights'].flatten(1).sum(1),torch.ones(3))
    assert maps['feature_reliability'].min()>=.25
    checks['soft_ground_retains_original_max_and_normalized_attention']=True

    # Controlled equal logits: higher confidence must receive higher attention.
    confidence=FlowFrameEncoder(32,spatial_mask='soft_confidence',camera=camera)
    with torch.no_grad():
        for p in confidence.attention.parameters():
            p.zero_()
    equal=torch.ones(1,4,90,160)
    equal[:,2,:,:80]=.1
    _,d=confidence(equal,return_diagnostics=True)
    assert d['attention_weights'][0,0,:,1].mean()<d['attention_weights'][0,0,:,8].mean()
    checks['confidence_bias_direction']=True

    # Hard validity gate is attention-only, finite even with no surviving cells.
    gated=FlowFrameEncoder(32,spatial_mask='soft_confidence_ground',mask_hard_min_coverage=.1,camera=camera)
    missing=torch.zeros(1,4,90,160)
    result,d=gated(missing,return_diagnostics=True)
    assert torch.isfinite(result).all() and not d['attention_weights'].any() and not d['motion_observed'].any()
    broken=missing.clone()
    broken[:,0,3,4]=float('nan')
    assert torch.isfinite(gated(broken)).all()
    checks['empty_hard_gate_and_nonfinite_input_finite']=True

    # Independent known path: forward, left turn, forward; initial yaw is NOT used twice.
    axis=torch.tensor(canonical_ground_normal_camera(30.),dtype=torch.float64)
    fwd=torch.tensor([0.,-.5,np.sqrt(3)/2],dtype=torch.float64)
    left=torch.tensor([-1.,0.,0.],dtype=torch.float64)
    local=fwd.expand(1,3,3).clone()
    yaw=torch.tensor([[[0.],[np.pi/2],[np.pi/2],[np.pi/2]]],dtype=torch.float64)
    rotated=rotate_about_axis_torch(local,yaw[:,:-1,0],axis)
    torch.testing.assert_close(rotated[0],torch.stack([fwd,left,left]),atol=1e-12,rtol=0)
    path=torch.cat([torch.zeros_like(rotated[:,:1]),rotated.cumsum(1)],1)
    recovered=local_increment_targets_torch(path,yaw,axis)
    torch.testing.assert_close(recovered,local,atol=1e-12,rtol=0)
    torch.testing.assert_close((rotated*axis).sum(-1),torch.zeros(1,3,dtype=torch.float64),atol=1e-12,rtol=0)
    checks['previous_yaw_sign_pitched_up_and_inverse_targets']=True

    # A loss on displacement must backpropagate into yaw through the new rotation.
    angles=torch.tensor([[0.,.3,.6]],dtype=torch.float64,requires_grad=True)
    increments=local.clone().requires_grad_()
    rotated=rotate_about_axis_torch(increments,angles,axis)
    rotated[...,0].sum().backward()
    assert angles.grad.abs().sum()>0 and increments.grad.abs().sum()>0
    checks['rotation_has_yaw_and_translation_gradients']=True

    both_cfg=replace(cfg,spatial_mask='soft_confidence_ground',mask_coverage_rule='receptive_field',motion_integration='yaw_local')
    model=GQFT(both_cfg,camera).eval()
    original=GQFT(cfg,camera).eval()
    source={'architecture':'GQFT','model':original.state_dict(),'model_config':asdict(cfg),'camera_model':asdict(camera)}
    try:
        initialize_gqft(model,source)
    except ValueError as exc:
        assert 'increment frames' in str(exc)
    else:
        raise AssertionError('Silently reinterpreted old motion weights')
    fresh={k:v.clone() for k,v in model.delta_head.state_dict().items()}
    initialize_gqft(model,source,reinitialize_motion_heads=True)
    assert all(torch.equal(v,model.delta_head.state_dict()[k]) for k,v in fresh.items())
    assert torch.equal(model.time_embed,original.time_embed)
    checks['semantic_init_requires_explicit_reset_and_preserves_backbone']=True

    output=model(flow,hist,query)
    assert torch.equal(output['delta'][1,-1],torch.zeros(3))
    gt_yaw=torch.tensor([[[0.],[.2],[.4],[.6]],[[0.],[.1],[.2],[.2]]])
    gt_delta=torch.tensor([[[0.,-.01,.02]]]).expand(2,3,3).clone()*hist[:,:,None]
    gt=torch.cat([torch.zeros_like(gt_delta[:,:1]),gt_delta.cumsum(1)],1)
    batch={'displacement':gt,'target_yaw':gt_yaw,'target_uv':output['uv_norm'].detach(),
           'target_valid':output['analytic_valid'].detach()}
    loss=gqft_loss(output,batch)['loss']
    assert torch.isfinite(loss)
    loss.backward()
    assert all(torch.isfinite(p.grad).all() for p in model.parameters() if p.grad is not None)
    assert model.flow_encoder.attention[-1].weight.grad.abs().sum()>0
    assert model.delta_head[-1].weight.grad.abs().sum()>0 and model.yaw_head[-1].weight.grad.abs().sum()>0
    checks['full_loss_local_nll_attention_yaw_and_delta_backward']=True
    no_yaw=dict(batch)
    no_yaw.pop('target_yaw')
    try:
        gqft_loss(output,no_yaw)
    except ValueError:
        pass
    else:
        raise AssertionError('Local NLL accepted missing target yaw')
    checks['local_loss_rejects_missing_frame_supervision']=True

    # Exact GT local increments + yaw must yield zero motion/yaw error.
    exact=dict(output)
    exact['displacement']=gt
    exact['delta_local']=local_increment_targets_torch(gt,gt_yaw,output['motion_up_axis'])
    exact['yaw']=gt_yaw+2*torch.pi
    exact['motion_logvar']=torch.zeros_like(exact['delta_local'])
    gt_losses=gqft_loss(exact,batch)
    assert gt_losses['motion']==0 and gt_losses['motion_nll']==0 and gt_losses['yaw']<1e-10
    checks['local_target_loss_and_wrapped_yaw_consistent']=True

    with torch.inference_mode():
        earlier=model(flow,hist,query)
        changed=flow.clone()
        changed[:,-1,:2]+=.1
        later=model(changed,hist,query)
        torch.testing.assert_close(earlier['displacement'][:,:-1],later['displacement'][:,:-1],atol=1e-7,rtol=1e-5)
    checks['new_modes_remain_causal_and_padding_safe']=True
    model.zero_grad(set_to_none=True)
    with torch.autocast('cpu',dtype=torch.bfloat16):
        amp=model(flow,hist,query)
        amp_loss=gqft_loss(amp,batch)['loss']
    amp_loss.backward()
    assert torch.isfinite(amp_loss) and all(torch.isfinite(p.grad).all() for p in model.parameters() if p.grad is not None)
    checks['new_modes_bfloat16_forward_backward_finite']=True

    with tempfile.TemporaryDirectory(dir='/tmp',prefix='gqft_new_modes_') as tmp:
        path=Path(tmp)/'model.pt'
        torch.save({'architecture':'GQFT','model':model.state_dict(),'model_config':asdict(both_cfg),
                    'camera_model':asdict(camera)},path)
        restored,_=load_gqft_checkpoint(path)
        assert restored.config==both_cfg
        with torch.inference_mode():
            torch.testing.assert_close(model(flow,hist,query)['displacement'],restored(flow,hist,query)['displacement'],atol=0,rtol=0)
    checks['strict_new_config_checkpoint_roundtrip']=True
    for args in ({'motion_integration':'yaw_local'}, {'mask_soft_floor':0},
                 {'mask_logit_strength':float('nan')},{'mask_ground_near_m':10},
                 {'mask_hard_min_coverage':-1},{'mask_coverage_rule':'unknown'}):
        try:
            GQFTConfig(**args)
        except ValueError:
            continue
        raise AssertionError(f'Invalid config accepted {args}')
    checks['invalid_new_config_rejected']=True
    # The new trainable soft-validity mode must match the earlier frozen probe.
    from probe_soft_attention import SoftAttentionIntervention
    from step2.episode_contract import pack_normalized_flow
    loaded,_=load_gqft_checkpoint(ROOT/'runs/gqft_spatial_yaw_v1/best.pt')
    source=LAB/'ep629/leg00/20261013T170841_769161Z/probe/flow_searaft_160x90.npz'
    with np.load(source,allow_pickle=False) as data:
        real=torch.from_numpy(pack_normalized_flow(data['flow'],data['confidence'],data['valid']))
    soft=GQFT(replace(loaded.config,spatial_mask='soft_validity',mask_coverage_rule='receptive_field'),loaded.camera).eval()
    soft.load_state_dict(loaded.state_dict(),strict=True)
    reference=SoftAttentionIntervention(loaded.flow_encoder,.75)
    with torch.inference_mode():
        reference.prepare(real)
        reference.policy='soft_rf_attention'
        torch.testing.assert_close(soft.flow_encoder(real),reference(real),atol=2e-6,rtol=1e-5)
    checks['trainable_soft_validity_matches_frozen_real_checkpoint_probe']=True
    output_folder=LAB/'implementation_20261016'
    output_folder.mkdir(exist_ok=True)
    files=('step2/models/gqft.py','step2/geometry.py','step2/checkpoint.py','step2/train_gqft.py','infer_gqft.py')
    payload={'passed':True,'device':'cpu','torch_version':str(torch.__version__),'checks':checks,
             'trained':False,'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in files}}
    (output_folder/'verification.json').write_text(json.dumps(payload,indent=2)+'\n')
    print(json.dumps(payload,indent=2))


if __name__=='__main__':
    main()
