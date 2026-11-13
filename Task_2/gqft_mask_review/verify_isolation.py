"""CPU verification of ablation equivalence and the local-support control."""
from dataclasses import replace
import json
import torch
import numpy as np
from isolate_masking import ROOT, LAB, PoolingIntervention, neighbour_experiment
from step2.checkpoint import load_gqft_checkpoint
from step2.models.gqft import GQFT
from step2.episode_contract import pack_normalized_flow

torch.set_num_threads(2)
model, _ = load_gqft_checkpoint(ROOT/'runs/gqft_spatial_yaw_v1/best.pt', 'cpu')
model.eval()
masked = GQFT(replace(model.config, spatial_mask='validity'), model.camera).eval()
masked.load_state_dict(model.state_dict(), strict=True)
source = LAB/'ep629/leg00/20261013T170841_769161Z/probe/flow_searaft_160x90.npz'
with np.load(source, allow_pickle=False) as data:
    flow = torch.from_numpy(pack_normalized_flow(data['flow'], data['confidence'], data['valid']))
with torch.inference_mode():
    pool = PoolingIntervention(model.flow_encoder, .75)
    pool.prepare(flow)
    assert pool.input_change == 0 and pool.feature_change == 0
    pool.policy = 'original'
    assert torch.equal(pool(flow), model.flow_encoder(flow))
    pool.policy = 'both'
    assert torch.equal(pool(flow), masked.flow_encoder(flow))
    result = neighbour_experiment(pool)
    assert result['status'] == 'completed'
    assert result['frozen_norm_neighbour_feature_l2_change'] > 0
    assert result['frozen_norm_outside_footprint_feature_l2_change'] == 0
    # Fully missing observations must remain finite; preserve the production zero token.
    empty = torch.zeros_like(flow[:2])
    pool.prepare(empty)
    for policy in ('original', 'attention_only', 'max_only', 'both', 'rescue_both', 'rf_both'):
        pool.policy = policy
        assert torch.isfinite(pool(empty)).all()
        if policy in ('both', 'rescue_both', 'rf_both'):
            assert torch.count_nonzero(pool(empty)) == 0
print(json.dumps({'passed': ['original_token_bit_exact', 'joint_token_bit_exact',
                            'input_and_features_unchanged', 'neighbour_influence_with_zero_outside_control',
                            'empty_observation_finite_all_policies'], 'neighbour_experiment':result}, indent=2))
