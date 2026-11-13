"""Verify soft attention's normalization, limiting cases and untouched max branch."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import torch
from probe_soft_attention import SoftAttentionIntervention, FLOOR, LAB, ROOT
import isolate_masking as base


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path)
    args=ap.parse_args()
    torch.set_num_threads(2)
    model,_=base.load_gqft_checkpoint(ROOT/'runs/gqft_spatial_yaw_v1/best.pt','cpu')
    model.eval()
    source=LAB/'ep629/leg00/20261013T170841_769161Z/probe/flow_searaft_160x90.npz'
    with np.load(source,allow_pickle=False) as data:
        flow=torch.from_numpy(base.pack_normalized_flow(data['flow'],data['confidence'],data['valid']))
    pool=SoftAttentionIntervention(model.flow_encoder,.75)
    checks=[]
    with torch.inference_mode():
        pool.prepare(flow)
        pool.policy='original'
        assert torch.equal(pool(flow),model.flow_encoder(flow))
        checks.append('original_token_bit_exact')
        reference=base.PoolingIntervention(model.flow_encoder,.75)
        reference.prepare(flow)
        reference.policy='attention_only'
        pool.policy='attention_only'
        assert torch.equal(pool(flow),reference(flow))
        checks.append('hard_attention_control_bit_exact')
        for policy in ('soft_coarse_attention','soft_rf_attention'):
            pool.policy=policy
            token,diag=pool(flow,return_diagnostics=True)
            assert torch.isfinite(token).all()
            assert torch.equal(diag['max_pooled'],pool.feat.amax((-2,-1)))
            weights=diag['attention_weights']
            assert torch.allclose(weights.flatten(1).sum(1),torch.ones(len(flow)),atol=1e-6,rtol=0)
            coverage=pool.rf_coverage if policy=='soft_rf_attention' else pool.coarse_coverage
            reliability=FLOOR+(1-FLOOR)*coverage
            expected=(pool.logits.float().flatten(1)+reliability.flatten(1).log()).softmax(-1).reshape_as(weights)
            assert torch.allclose(weights,expected,atol=1e-6,rtol=1e-5)
            assert (weights[pool.original_attention>0]>0).all()
        checks.extend(['max_pool_bit_exact_all_policies','soft_weights_normalized_and_finite',
                       'equivalent_log_prior_formula','no_positive_original_weight_hard_rejected'])
        for all_valid in (True,False):
            special=torch.zeros_like(flow[:2])
            if all_valid:
                special[:,3]=1
                special[:,2]=.6
            pool.prepare(special)
            for policy in ('soft_coarse_attention','soft_rf_attention'):
                pool.policy=policy
                assert torch.equal(pool(special),model.flow_encoder(special))
        checks.extend(['all_valid_recovers_original_bit_exact','all_invalid_constant_coverage_recovers_original_bit_exact'])
        # Equal learned attention plus unequal reliability must give the known 1:4 odds.
        pool.prepare(flow[:1])
        pool.original_attention=torch.ones_like(pool.original_attention)/pool.original_attention[0].numel()
        pool.coarse_coverage=torch.ones_like(pool.coarse_coverage)
        pool.coarse_coverage[0,0,0,0]=0
        pool.policy='soft_coarse_attention'
        weights=pool.attention_weights()
        assert torch.isclose(weights[0,0,0,0]/weights[0,0,0,1],torch.tensor(.25),atol=1e-7,rtol=0)
        checks.append('equal_attention_reliability_odds_1_to_4')
    payload={'passed':True,'checks':checks,'device':'cpu','torch_version':str(torch.__version__),
             'runner_sha256':hashlib.sha256((LAB/'probe_soft_attention.py').read_bytes()).hexdigest(),
             'plan_sha256':hashlib.sha256((LAB/'soft_attention_plan.json').read_bytes()).hexdigest()}
    if args.out:
        if not args.out.resolve().is_relative_to(LAB.resolve()):
            raise ValueError('Keep verification output in the lab')
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(payload,indent=2)+'\n')
    print(json.dumps(payload,indent=2))


if __name__=='__main__':
    main()
