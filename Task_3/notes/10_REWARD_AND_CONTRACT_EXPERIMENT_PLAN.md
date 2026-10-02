# Review of the proposed contract and reward changes

> **2026-10-02 update:** Follow [the main guide](README.md). The user now prefers testing the combined package to save training time. The separate experiments below remain useful for later attribution. Actuator tuning is deferred; current source clipping is no longer null and the viewer calf upper-bound edit is already done.

Date: 2026-09-28. This is a proposed manual implementation and experiment plan, not a record of implemented fixes or successful training. It follows the user's request to work through the local audit one issue at a time. No controller or training code was edited while writing this note.

## Decision

The proposed changes are reasonable experiments. First establish a verified, consistent control contract in training and evaluation; then test target second differences and saturation pressure separately. A smoothness reward encourages smoother motion but does not guarantee reduced physical jitter or successful stair climbing.

The copied control and candidate metadata were already inspected: both completed at 90500 from the same 90000 checkpoint/hash, with action-rate coefficients -0.10 and -0.15. Both saved `actions.joint_pos.clip: null`. The local interactive controller still has the legacy +0.50000 calf upper target. Those facts justify addressing the target mapping before interpreting another reward experiment.

## 1. Control contract and all target bounds

Use the same joint names/order, reference pose, action scale, final target bounds, observation scaling/history, and policy/control timing in training and evaluation. Preserve the existing previous-action observation convention.

```text
a = clip(policy_output, -6, +6)
q_raw_target = q0 + scale * a
q_cmd = clip(q_raw_target, deployed_target_min, deployed_target_max)
previous-action observation uses a
```

The name `q_raw_target` here means the position request after raw-action clipping, scaling, and reference-pose addition, before final position-target clamping. It is not the measured joint position or the raw neural-network output.

The audit supplies calf upper -0.88776 rad and hip targets +/-0.735 rad, and reports asymmetric thigh bounds. The complete twelve-joint mapping must come from the deployed adapter or the corrected audit source; the short report table does not specify every lower/upper thigh and calf bound. Do not guess missing values or apply the audit's 0.05 rad safety buffer twice. A calf-only correction remains a partial correction.

The approximately 79.5-degree discrepancy describes the difference between two allowed calf upper targets, not a measured 79.5-degree movement. Correcting it addresses a real mismatch; the audit's corrected-bounds stair failures show it is not a demonstrated complete cure.

Training: configure final target clipping through `cfg.actions['joint_pos'].clip` in `scripts/m2_algorithm_env.py` / `make_cfg`, before environment creation, with verified joint-name resolution and post-scale/offset semantics. Evaluation: use the same mapping in `svanm2_moe_stair_sim/controller.py`. Verify actual processed targets with representative in-range and out-of-range actions. Do not substitute XML mechanical limits or the measured-angle limit reward for a target clamp.

Keep lateral evaluation within the saved +/-0.3 m/s range during diagnosis; an initial forward-only test uses vy=0. Expanding training to +/-0.6 m/s is a later command-distribution experiment with its own evaluation, not a simultaneous jitter intervention.

Audit existing delay settings before adding latency: the inspected training asset already configures actuator delay. Distinguish policy inference, delivery, actuator update, and physics intervals, and avoid double-counting delays. Model supported command shaping and measured latency consistently. This is different from adding an output filter to hide oscillation.

## 2. Rewards: distinct roles

| Term | Signal and purpose |
| --- | --- |
| Existing action-rate cost | `sum((a[t]-a[t-1])**2)` discourages large successive changes in the adapter-clipped actions |
| Proposed normalized target second-difference cost | `sum(((q_cmd[t]-2*q_cmd[t-1]+q_cmd[t-2])/scale)**2)` discourages rapidly changing target increments and reversals |
| Proposed saturation-pressure cost | `sum(((q_raw_target-q_cmd)/scale)**2)` discourages requests removed by target clamping |

For the new costs, use a negative reward weight with a nonnegative squared cost. Normalize using the correctly ordered per-joint action scales (hip/thigh 0.15, calf 0.30 rad per action unit). Choose coefficients from measured raw-cost magnitudes and weighted contributions; none is established as an optimal jitter fix by the audit.

The second difference is not the same term as action rate. It is also not measured joint acceleration or jerk. The installed `action_acc_l2` operates on actions before target clamping, so it differs from the proposed final-target expression during saturation. Keep the policy timestep fixed; introducing division by timestep squared changes the magnitude and requires retuning.

These costs can complement each other: a clamped target can stay nearly constant while the policy repeatedly requests an unreachable position. Target second differences alone do not penalize that overshoot; saturation pressure does. Test them separately before testing their combination.

Maintain second-difference target history per environment, once per policy step. Clear it on reset and mask the first two steps of the episode. Do not alter the MoE's previous-action observation to store physical targets. Register each cost with the reward manager and retain raw/weighted contribution logging. Validate constant targets, ramps, reversals, clipping, and independent environment resets before a long run.

Do not add a large joint-acceleration or contact-impact penalty now. Foot lift, recovery, and landing require physical acceleration. Consider that later only after sensor and numerical consistency checks.

## 3. Training experiments

After the corrected evaluation/training reference is established, run the following from the same original `model_90000.pt`, for equal budgets with matching settings. Retain action-rate -0.15 in each as a fixed reference, not a claim that -0.15 is optimal.

| Run | Corrected target contract | Action-rate | Target second difference | Saturation pressure |
| --- | --- | --- | --- | --- |
| A: corrected baseline | same in every run | -0.15 | off | off |
| B: second difference | same | -0.15 | on | off |
| C: saturation pressure | same | -0.15 | off | on |

Run B versus A first. Test C separately as the next experiment. Only test both new terms together after their separate effects are understood. Preserve the old 90500 artifacts, but do not use a differently configured old rollout as the sole control for the corrected environment.

Keep PD gains, physics/contact settings, output filtering, command range, and training duration fixed within each reward comparison. A reward encourages a behavior through learning; it neither enforces smoothness nor removes real system latency.

## 4. Evaluation and record keeping

Before training, record an evaluation reference under the corrected configuration. Check sensor refresh and complete resets individually as described in the audit. For each checkpoint, use the same command schedule, starts/seeds, simulator configuration, duration, and terrain. Use flat ground and 10 cm stairs initially.

Collect measured and commanded joint angles, raw and clamped targets, timestamps, commands, base motion, contacts, target saturation and episode outcomes. Compare the audit's 8-30 Hz oscillation indicator using consistent filters and motion windows alongside speed tracking, heading drift, foot slip/clearance, full stair traversal, falls, stalls, and reward contributions. The frequency band includes some normal gait/impact content, so it is not sufficient on its own.

A robot that stops or avoids the stairs can have lower oscillation without solving the task. Keep failed trials and report them. Fixable software discrepancies and uncertain physical parameters should be tracked separately; the report does not establish exact actuator dynamics or one exclusive jitter cause.

References: [audit report](../moe_jitter_audit_20260921/REPORT.md), [issue-by-issue checklist](09_AUDIT_ISSUE_BY_ISSUE_CHECKLIST.md), [implementation considerations](08_TARGET_LIMITS_AND_SECOND_DIFFERENCE_PLAN.md).
