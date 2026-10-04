"""Functional GPU reward check with synthetic actions; not a policy evaluation."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "xterra_mjlab/scripts"))
import torch
from m2_algorithm_env import Adapter
from train_other import configure_training_rewards, make_cfg


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--weight", type=float, default=-.05)
    parser.add_argument("--target-limit-profile", choices=("existing", "viewer-wide"), default="existing")
    parser.add_argument("--swing-height", type=float, default=None)
    args = parser.parse_args()
    if args.out and args.out.exists():
        raise FileExistsError(args.out)
    torch.manual_seed(103001)
    cfg = configure_training_rewards(make_cfg(8, 103001), "moe", -.15, args.weight,
        target_limit_profile=args.target_limit_profile, swing_height=args.swing_height)
    adapter = Adapter(cfg, args.device, history=5, frame_size=45, numerical_guard=True)
    try:
        env = adapter.env
        names = env.action_manager.get_term("joint_pos").target_names
        expected = [f"{leg}_{joint}_joint" for leg in ("FL", "FR", "RL", "RR")
                    for joint in ("hip", "thigh", "calf")]
        assert list(names) == expected, (names, expected)
        assert abs(env.step_dt - .02) < 1e-9
        reward_names = list(env.reward_manager.active_terms)
        index = reward_names.index("target_rate_excess_l2")
        rates = []
        clearance_rates = {name: [] for name in ('foot_clearance', 'foot_swing_height')}
        for step in range(24):
            actions = torch.zeros((8, 12), device=args.device)
            # Alternating targets ensure the deadband is exercised.
            actions[:, 0] = 5. if step % 2 else 0.
            reward, done, info, successor = adapter.step(actions)
            assert torch.isfinite(reward).all() and torch.isfinite(successor).all()
            rate = float(info["reward_term_rates"][index])
            assert rate <= 0 and torch.isfinite(torch.tensor(rate))
            rates.append(rate)
            for name, values in clearance_rates.items():
                value = float(info['reward_term_rates'][reward_names.index(name)])
                assert torch.isfinite(torch.tensor(value))
                values.append(value)
        assert min(rates) < 0, "The injected large target changes never triggered the term"
        assert adapter.numerical_resets == 0
        result = dict(test="synthetic-action environment integration, not policy performance",
                      device=args.device, num_envs=8, steps=24, step_dt=env.step_dt,
                      target_limit_profile=args.target_limit_profile,
                      target_bounds=cfg.actions["joint_pos"].clip,
                      swing_height_preferences={name: cfg.rewards[name].params['target_height']
                          for name in clearance_rates},
                      clearance_weighted_rates=clearance_rates,
                      action_order=list(names), reward_weights={name: cfg.rewards[name].weight
                          for name in ("action_rate_l2", "target_second_difference_l2",
                                       "target_saturation_l2", "target_rate_excess_l2")},
                      target_rate_weighted_rates=rates,
                      numerical_resets=adapter.numerical_resets, passed=True)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))
    finally:
        adapter.env.close()


if __name__ == "__main__":
    main()
