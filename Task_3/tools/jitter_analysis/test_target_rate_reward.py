"""CPU contract checks for the active optional reward; no training or MuJoCo run."""
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "xterra_mjlab" / "scripts"))
import torch
from mjlab.managers import RewardTermCfg, RewardManager
from target_rate_reward import TargetRateExcess, configure_target_rate_trial, target_rate_excess
from jitter_rewards import config_jitter_rewards
from train_other import configure_training_rewards, make_cfg


class RateRewardChecks(unittest.TestCase):
    def test_swing_height_override_keeps_standing_gates_and_weights(self):
        from copy import deepcopy
        baseline = configure_training_rewards(make_cfg(2, 103001), 'moe')
        original = {name: deepcopy(baseline.rewards[name])
                    for name in ('foot_clearance', 'foot_swing_height')}
        candidate = configure_training_rewards(make_cfg(2, 103001), 'moe', swing_height=.13)
        for name, before in original.items():
            self.assertEqual(before.params['target_height'], .10)
            after = candidate.rewards[name]
            self.assertEqual(after.weight, before.weight)
            self.assertEqual(after.params, {**before.params, 'target_height': .13})
            self.assertEqual(after.params['command_name'], 'twist')
        for invalid in (0., -.1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                configure_training_rewards(make_cfg(2, 103001), 'moe', swing_height=invalid)

    def test_viewer_profile_is_explicit_and_preserves_thigh_bounds(self):
        baseline = make_cfg(2, 103001)
        original = dict(baseline.actions['joint_pos'].clip)
        configure_training_rewards(baseline, 'moe', -.15, -.01)
        self.assertEqual(baseline.actions['joint_pos'].clip, original)
        candidate = configure_training_rewards(make_cfg(2, 103001), 'moe', -.15, -.01,
            target_limit_profile='viewer-wide')
        bounds = candidate.actions['joint_pos'].clip
        self.assertEqual(bounds[r'.*_hip_joint'], (-1.0472, 1.0472))
        self.assertEqual(bounds[r'.*_calf_joint'], (-2.7227, .5))
        for name, value in original.items():
            if 'thigh' in name:
                self.assertEqual(bounds[name], value)
        self.assertEqual(candidate.rewards['target_saturation_l2'].weight, -.01)
        self.assertEqual(candidate.rewards['target_rate_excess_l2'].weight, -.01)

    def environment(self):
        names = [f'{leg}_{joint}' for leg in ('FL', 'FR', 'RL', 'RR') for joint in ('hip', 'thigh', 'calf')]
        term = SimpleNamespace(action_dim=12, target_names=names, scale=torch.ones(1, 12),
            offset=torch.zeros(2, 12), cfg=SimpleNamespace(clip={".*": (-1., 1.)}))
        manager = SimpleNamespace(action=torch.zeros(2, 12), prev_action=torch.zeros(2, 12),
            active_terms=['joint_pos'], get_term=lambda name: term)
        return SimpleNamespace(action_manager=manager, step_dt=.02,
            episode_length_buf=torch.tensor([1, 2]), num_envs=2, device='cpu')

    def test_elapsed_time_and_equal_speed(self):
        # A 10-degree reversal is over 100 deg/s in 20 ms, allowed in 500 ms.
        target=torch.tensor([[torch.pi / 36]])
        previous=-target
        limit=torch.tensor([[torch.pi * 100 / 180]])
        self.assertGreater(target_rate_excess(target, previous, .02, limit).item(), 0)
        self.assertEqual(target_rate_excess(target, previous, .5, limit).item(), 0)
        # Identical physical target speed has identical cost at two policy rates.
        torch.testing.assert_close(target_rate_excess(target, previous, .02, limit),
            target_rate_excess(target / 2, previous / 2, .01, limit))

    def test_manager_weights_dt_clamping_and_partial_reset(self):
        env=self.environment()
        cfg=RewardTermCfg(func=TargetRateExcess, weight=-.05,
            params={'speed_limits_rad_s': [10.] * 12, 'action_name':'joint_pos'})
        manager=RewardManager({'rate':cfg},env,scale_by_dt=True)
        env.action_manager.action[:, 0]=5.  # Clamps to +1, not a 5-rad physical request.
        value=manager.compute(dt=env.step_dt)
        torch.testing.assert_close(value,torch.tensor([0.,-.016]))
        env.episode_length_buf[:]=torch.tensor([0,3])
        env.action_manager.prev_action[1,0]=env.action_manager.action[1,0]
        torch.testing.assert_close(manager.compute(dt=env.step_dt),torch.zeros(2))

    def test_saturation_retained_once_and_registration_explicit(self):
        cfg=SimpleNamespace(rewards={});config_jitter_rewards(cfg)
        original=cfg.rewards['target_saturation_l2']
        self.assertNotIn('target_rate_excess_l2',cfg.rewards)
        configure_target_rate_trial(cfg,[10.]*12)
        self.assertIs(cfg.rewards['target_saturation_l2'],original)
        self.assertEqual(original.weight,-.01)
        self.assertIn('target_second_difference_l2',cfg.rewards)
        self.assertEqual(sum(k=='target_saturation_l2' for k in cfg.rewards),1)
        configure_target_rate_trial(cfg,[10.]*12,replace_second_difference=True)
        self.assertNotIn('target_second_difference_l2',cfg.rewards)

    def test_reject_wrong_units_configuration(self):
        env=self.environment()
        for limits in ([0.]*12,[10.]*3,[float('nan')]*12):
            with self.assertRaises(ValueError):
                TargetRateExcess(RewardTermCfg(func=TargetRateExcess,weight=-.05,
                    params={'speed_limits_rad_s':limits}),env)

    def test_actual_training_configuration_keeps_baseline_and_enables_trial(self):
        baseline=configure_training_rewards(make_cfg(2,103001),'moe',-.15)
        self.assertNotIn('target_rate_excess_l2',baseline.rewards)
        candidate=configure_training_rewards(make_cfg(2,103001),'moe',-.15,-.05)
        self.assertEqual(candidate.rewards['action_rate_l2'].weight,-.15)
        self.assertEqual(candidate.rewards['target_second_difference_l2'].weight,-.01)
        self.assertEqual(candidate.rewards['target_saturation_l2'].weight,-.01)
        self.assertEqual(candidate.rewards['target_rate_excess_l2'].weight,-.05)
        self.assertEqual(candidate.rewards['target_rate_excess_l2'].params['speed_limits_rad_s'],
            [7.093,11.275,20.365]*4)
        self.assertAlmostEqual(candidate.sim.mujoco.timestep*candidate.decimation,.02)


if __name__=='__main__': unittest.main(verbosity=2)
