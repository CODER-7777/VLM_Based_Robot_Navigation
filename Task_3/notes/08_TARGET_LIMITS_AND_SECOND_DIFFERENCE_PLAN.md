# Next jitter experiment: consistent target limits and second differences

> **2026-10-02 update:** Follow [the main guide](README.md) for the current combined trial and pasteable reward code. Training now has target clipping, and the viewer calf upper bounds are already corrected. Complete deployed thigh-bound parity remains unverified.

Date: 2026-09-28. This is a manual implementation plan. No training, controller, robot, or reward implementation was changed while preparing it.

## What we have actually verified

The user reports substantial jitter remains in the candidate's MuJoCo test. No new quantitative evaluation traces were provided, so the amount of improvement or worsening is not measured here.

The copied folders in `xterra_mjlab/evaluation_runs/` contain these verified metadata:

| Run | Status | Final update | Resume update | Action-rate coefficient | Final position-target clip configuration |
| --- | --- | --- | --- | --- | --- |
| `20260927_moe_jitter_control_weight010_updates90500` | completed | 90500 | 90000 | -0.10 | `null` |
| `20260927_moe_jitter_candidate_weight015_updates90500` | completed | 90500 | 90000 | -0.15 | `null` |

Both `resume.json` files identify the same source checkpoint SHA256: `440bbb28d554f75db38bfd163351c04ea4a32d9d06764c37b7e6071d41daa5cb`.

The saved `env.yaml` files specify `actions.joint_pos.clip: null`. The inspected action implementation scales and offsets actions, then applies final target clipping only if that setting is configured. The inspected SvanM2 actuator computes coupled PD torque and limits torque; it does not add the deployed position-target bounds. Raw action clipping to [-6, 6] in the adapter is a separate operation. These are findings about the inspected local source and copied configurations, not a claim of complete runtime parity with every server dependency.

## 1. Correct the target-limit mismatch first

The audit documents calf upper command limits of +0.50000 rad in the old demo versus -0.88776 rad in deployment. Their difference is 1.38776 rad, approximately 79.5 degrees. This is a difference between allowed upper targets, not a measured 79.5-degree jump. Do not subtract 79.5 degrees from actions or joint angles.

The current interactive `controller.py` still contains +0.5000 in all four calf entries of `TARGET_MAX` and clamps `scaled_target` against `TARGET_MIN`/`TARGET_MAX` in `policy_step`. Training's final target clipping was disabled in both copied runs. Correct the training mapping and evaluation mapping together.

Intended mapping:

```text
a = clip(policy_output, -6, +6)
q_requested = q0 + scale * a
q_commanded = clip(q_requested, deployed_target_min, deployed_target_max)
```

Use all twelve joint-name-mapped bounds, not just the four calf upper entries. The audit also identifies hip/thigh differences. Preserve previous-action observations as the clipped raw action, as required by the existing policy interface. Do not replace the previous-action observation with q_commanded.

The original audit applied a 0.05 rad buffer to the deployed adapter's bounds. Its reported -0.88776 is already the resulting target upper bound; do not apply that buffer twice.

The full corrected audit implementation and frozen deployed adapter were not found in the checked local project locations. The audit manifest names:

- `svanm2_moe_hardware_audit/controller.py`
- `svanm2_moe_hardware_audit/reference/moe_observation.py`
- `svanm2_moe_hardware_audit/reference/contract.json`
- `svanm2_moe_hardware_audit/test_contract.py`

Obtain or locate those files before declaring all limits matched. The report alone does not supply every joint bound. The user was asked for the server location. The audit's corrected-bounds ascent trials still failed, so this correction alone is not a demonstrated jitter fix.

Training configuration location: `scripts/m2_algorithm_env.py`, inside `make_cfg`, before environment construction. The relevant setting is `cfg.actions['joint_pos'].clip`, which the installed action implementation applies after scale and offset. Verify the server package uses the same semantics and resolves the dictionary to the intended joint names. Preserve simulator physical joint ROM until it has independent justification; changing command bounds is different from editing XML joint stops.

Evaluation location: `svanm2_moe_stair_sim/controller.py`, `TARGET_MIN`, `TARGET_MAX`, and `policy_step`. Prefer sharing one verified joint-name mapping between training and evaluation. Matching these limits does not, by itself, reproduce the audit's other corrections to sensor refresh, reset, timing, or command shaping.

## 2. Add a second-difference penalty as a separate experiment

Existing action rate penalizes squared first differences of actions received by the action manager. In this adapter those actions have already been clipped to [-6, 6].

```text
L_rate = sum((a[t] - a[t-1])**2)
```

A second difference measures a change in successive increments:

```text
delta2_q = q_commanded[t] - 2*q_commanded[t-1] + q_commanded[t-2]
L_target_second_difference = sum((delta2_q / scale)**2)
reward contribution = -lambda * L_target_second_difference
```

Here lambda is positive and the scale per leg is [0.15, 0.15, 0.30], matched by joint name/order. This is the audit's normalized target-space proposal. Use policy-step targets at fixed timing. It is a second finite difference, not measured joint acceleration and not jerk. Dividing by timestep squared would change its units and magnitude and require a differently scaled coefficient.

Example: target angles 0, 5, 10 degrees have constant increments and second difference zero. Targets 0, 5, 0 degrees have a reversal and second difference -10 degrees. Penalizing the latter may discourage rapid reversals, but excessive weight can suppress necessary stair corrections.

The installed framework already has `mjlab.envs.mdp.rewards.action_acc_l2`, using `action`, `prev_action`, and `prev_prev_action`. That term penalizes raw-action second differences, not final clamped targets. Before target saturation and with constant scale/offset, it equals the normalized target expression. With saturation the two objectives differ. Do not label the raw-action implementation as the audit's post-clamp target penalty.

Recommended implementation location for the audit proposal: a new project-owned reward module, for example `xterra_mjlab/tasks/velocity/config/svanm2/jitter_rewards.py` (not created yet). Register the callable with `RewardTermCfg` in the training configuration. It must return one cost per environment, not an average over environments. Keep existing action-rate weight the same in both new runs; -0.15 is a reasonable fixed reference for testing the next change, not a proven best coefficient.

Required implementation details:

- Use the same target stage/coordinate convention as the clamp, before actuator transport delay; keep it explicit.
- Maintain per-environment target history once per policy step, not once per physics substep or once per logger call.
- Clear history for reset environments and mask the first two samples of each new episode; avoid cross-episode penalties.
- Account for encoder offsets and target ordering if reconstructing targets rather than storing them.
- Log the raw cost and its weighted contribution through the existing dynamic reward-term logging. No separate PPO score block is needed.
- Select lambda from measured raw magnitudes; a coefficient has no demonstrated optimal value here. Start with a modest contribution and check tracking, clearance, and traversal before increasing it.

Check constant targets and linear ramps yield zero, reversals yield a positive cost, and resetting one environment does not contaminate another. Verify targets satisfy the intended bounds in actual rollouts. These checks validate implementation; successful stair traversal requires a separate evaluation.

## 3. Controlled training and evaluation sequence

1. Preserve the completed 90500 checkpoints and their logs.
2. Retrieve the deployed bounds source; make the target limits identical in training and evaluation and verify action/history semantics.
3. Evaluate existing checkpoints in that corrected setup and save target/measured-angle traces. This establishes the new evaluation reference; do not compare different checkpoint variants in different simulator configurations.
4. From the original `model_90000.pt`, train a new control with corrected target limits and action-rate -0.15, without the new second-difference reward.
5. From that same `model_90000.pt`, train a paired candidate with identical settings plus the target second-difference reward. Match training budget, seed, command/terrain settings, and optimizer/resume handling.
6. Compare both under identical flat-ground and 10 cm stair conditions. Measure 8-30 Hz joint/target oscillation, speed tracking, heading drift, full traversal, falls, stalls, and target saturation. Use comparable movement windows and retain failures.
7. Only then consider additional changes, such as saturation-pressure penalties. Keep PD gains, contact parameters, policy frequency, and output filtering fixed during this comparison.

This experiment tests whether the proposed penalty helps after correcting the target contract. It does not assume rewards are the only cause of jitter. A robot that moves less can have smaller oscillation and still perform worse.

## Evidence and references

- [Audit report](../moe_jitter_audit_20260921/REPORT.md): target mismatch table and proposed reward experiments.
- [Audit parity script](../moe_jitter_audit_20260921/parity_and_replay.py): checks bounds with the 0.05 rad buffer.
- [Audit manifest](../moe_jitter_audit_20260921/manifest.json): source filenames and hashes.
- [Training adapter](../xterra_mjlab/scripts/m2_algorithm_env.py): configuration and raw action clipping.
- [Current viewer controller](../xterra_mjlab/svanm2_moe_stair_sim/controller.py): legacy target bounds.
- [Control saved configuration](../xterra_mjlab/evaluation_runs/20260927_moe_jitter_control_weight010_updates90500/env.yaml).
- [Candidate saved configuration](../xterra_mjlab/evaluation_runs/20260927_moe_jitter_candidate_weight015_updates90500/env.yaml).
