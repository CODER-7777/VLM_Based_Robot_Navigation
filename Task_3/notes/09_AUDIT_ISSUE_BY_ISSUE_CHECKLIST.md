# Work through the local jitter audit one issue at a time

> **2026-10-02 update:** The current checklist is [notes/README.md](README.md). This older issue list remains a reference. The user now requests a combined target-limit/second-difference/saturation-pressure training trial, with actuator tuning later; the calf upper-bound edit is already done.

Date: 2026-09-28. This records the user's clarification: use the available local audit and address its problems individually. This checklist supplements `08_TARGET_LIMITS_AND_SECOND_DIFFERENCE_PLAN.md`. No controller or training code has been changed by the assistant for this task.

## Interpretation

The calf upper-target discrepancy is confirmed: the old local viewer uses +0.50000 rad and the audit reports -0.88776 rad in the deployed target contract. Their approximately 79.5-degree difference is a difference between allowed bounds, not a measured joint jump. Correcting the discrepancy can change the feedback loop, but the audit already showed failures with corrected limits. It is a possible contributor, not an established complete explanation.

The user clarified that the available material is local and the controller is the existing one. The inspected local controller still contains the legacy values. We can investigate the confirmed calf discrepancy using that evidence now. Full joint-limit parity requires verifying the remaining lower/upper hip, thigh, and calf bounds; a calf-only change must be labelled partial.

## First manual experiment: calf upper target bound

1. Preserve the before-change observations/video. Use one fixed checkpoint, preferably original `model_90000.pt`, for this before/after comparison.
2. In `xterra_mjlab/svanm2_moe_stair_sim/controller.py`, find `TARGET_MAX` around line 32.
3. Change only the four calf entries (the third value in each leg's row) from `0.5000` to `-0.88776`. Do not subtract 79.5 degrees from actions, offsets, or measured joint positions. Do not apply a further 0.05 rad buffer to this already-buffered reported target bound.
4. Leave all other controller settings, policy weights, physics timing, and commands unchanged for this diagnostic test.
5. Restart the viewer as a fresh process. Repeat the same 10 cm stair command, initially vx=0.30, vy=0, yaw=0. Compare standing, approach, stair contact, tracking, full traversal, falls, stalls, and lane exits.
6. Verify recorded final calf targets do not exceed -0.88776; visual inspection alone does not prove the clamp was applied. The current viewer needs telemetry for this numerical check.
7. Record whether behavior improves, worsens, or is similar. Any result is useful. This test isolates the immediate effect on the chosen existing policy, not the effect of retraining under the new constraint.

This is a partial correction in the evaluation simulator. Both completed training runs saved `actions.joint_pos.clip: null`; correcting only the viewer does not establish matching training/evaluation limits. Before further training, configure and verify matching final target bounds in `scripts/m2_algorithm_env.py`, `make_cfg`, through `cfg.actions['joint_pos'].clip`. Use a verified joint-name mapping. Do not substitute XML mechanical joint stops or the measured-angle joint-limit reward for a final-target clamp.

## Remaining checklist

| Order | Item | Current evidence/status | Next action |
| --- | --- | --- | --- |
| Done | Starting checkpoint and completed runs | Copied metadata confirms both finished at 90500 from the same 90000 checkpoint/hash, with -0.10 and -0.15 action-rate coefficients | Preserve these artifacts; no checkpoint substitution is indicated by the metadata |
| 1 | Target limits | Legacy calf upper bound remains in viewer; training final target clipping is null | Perform the single-bound diagnostic above, then establish matching full target limits before new training |
| 2 | Sensor freshness and reset | Audit reports stale-sensor risk and incomplete reset in the original runner | Check current implementation; apply and validate sensor-refresh and full-reset corrections individually |
| 3 | Command and timing consistency | Audit identifies command-distribution and timing differences | Use fixed in-range commands; verify policy, PD, and physics schedules separately; keep them fixed across comparisons |
| 4 | Measurement and success criteria | Visual jitter remains according to the user; new quantitative results are not yet available | Log measured angles, commanded targets, saturation, commands, pose/velocity, contacts, and outcomes; require full traversal |
| 5 | Target second-difference penalty | Proposed by audit; not yet implemented or validated in this work | Run the paired experiment below after establishing the evaluation reference |
| 6 | Contact and physics sensitivity | Audit finds numerical/contact sensitivity | Test one parameter at a time while preserving control schedules; do not treat a smaller timestep as proof of physical accuracy |
| 7 | Unmeasured actuator/hardware properties | Motor saturation semantics, firmware status meanings, friction/backlash and calibration remain uncertain | Gather source or measurements; these are investigation tasks, not values to guess |

## Second-difference reward experiment

Use the audit's physical target expression:

```text
cost = sum(((q_cmd[t] - 2*q_cmd[t-1] + q_cmd[t-2]) / scale)**2)
reward contribution = -lambda * cost
```

Here `q_cmd` is the final clamped joint-position setpoint at a consistent stage of the command path. This is a second finite difference. It discourages rapidly changing target increments, including reversals. It is not measured joint acceleration or jerk.

The installed framework's existing `action_acc_l2` uses actions before final target clipping. It is a related experiment, but differs from the audit's proposal when targets saturate. Decide and document which signal is penalized; do not confuse them.

For the audit proposal, maintain history per environment once per policy step, reset it for each episode, and mask the first two samples. Return one cost per environment and register it in `cfg.rewards` with `RewardTermCfg`. The existing dynamic logging can then record its raw and weighted contributions. The detailed implementation requirements are in note 08.

Train two new continuations from the same original 90000 checkpoint, with equal budgets and identical corrected limits. Keep action-rate -0.15 in both as a fixed experimental reference: one with the second-difference term disabled, one with it enabled. Its coefficient is experimental and should be chosen from measured cost magnitudes, not claimed to be a known cure.

Compare oscillation alongside speed tracking, heading, full stair traversal, falls and stalls. Lower motion caused by stopping is not a successful fix. Keep PD, timestep, contact parameters, and output filters unchanged during the reward comparison.

## Record for every change

| Issue | Evidence before change | Exact file/setting changed | Conditions held fixed | Result after change | Decision |
| --- | --- | --- | --- | --- | --- |
| Calf upper target bound | | | | | |
| Sensor refresh | | | | | |
| Reset | | | | | |
| Target second difference | | | | | |

References: [local audit report](../moe_jitter_audit_20260921/REPORT.md), [detailed next-experiment plan](08_TARGET_LIMITS_AND_SECOND_DIFFERENCE_PLAN.md), [viewer controller](../xterra_mjlab/svanm2_moe_stair_sim/controller.py), [training configuration adapter](../xterra_mjlab/scripts/m2_algorithm_env.py).
