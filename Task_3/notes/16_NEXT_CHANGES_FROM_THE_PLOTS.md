# What I would change next, based on the plots

Written 2026-10-03. **These are proposed experiments, not applied fixes.** The fresh data are summarized in [the report](../tools/results/20261002_matched_v1/REPORT.md); [note 15](15_HOW_TO_READ_THE_PLOTS.md) explains the graphs.

Additional prerequisite from [note 17](17_REVIEW_OF_ACTUATOR_DELAY_AND_GATE_SUGGESTIONS.md): training already configures 0–2 physics-step actuator delay, while the current viewer does not reproduce that explicit delay buffer. Verify the server's actual implementation and establish consistent evaluation timing before attributing a reward trial's results to rewards alone. Gate diagnostics and the research-suggestion review are also recorded there.

My interpretation is that we need to improve the response to the first step and coordinated ascent. More smoothness punishment alone is not supported as the next solution. The candidate improved early speed tracking and reduced target limiting in the tested pairs, but jitter changes were mixed and no tested stair case completed ascent.

## 1. First make the observation timing consistent

The current viewer combines current joint positions/velocities with derived body readings left from the previous physics solve. Our isolated refreshed-observation condition changed the trajectories substantially. Neither condition solved ascent.

The inspected local training environment performs a forward update before returning observations. Before choosing the evaluation convention, check the exact version used on the server too. The training package and current local package need not be identical.

**Proposed implementation direction:** provide joint and body readings from the intended same simulation state before inference, while preserving joint order, scales, previous-action semantics and five-frame history ordering. The copied-state method in [record.py](../tools/jitter_analysis/record.py) is already an isolated prototype. Reusing it avoids assuming that adding `mj_forward()` to the live solver is a harmless change.

Files: [controller.py](../xterra_mjlab/svanm2_moe_stair_sim/controller.py), [m2_algorithm_env.py](../xterra_mjlab/scripts/m2_algorithm_env.py), and the training environment implementation. Agreement with the intended interface is the goal; refreshed observations are not a demonstrated jitter fix.

## 2. My first reward experiment: slightly higher preferred swing clearance

Evidence: in every distinct stair case, a front foot first contacted a vertical riser with foot-center height about 3.7–6.3 cm. In the central candidate run, the current target-pose check was also too low at that instant. The contacting leg's targets and torques were not clipped then. This motivates checking learned foot lifting and its timing before increasing motor effort.

Two existing reward terms already prefer height **0.10 m**:

| Term | Current local definition | Current configured weight |
| --- | --- | ---: |
| `foot_clearance` | Absolute height error multiplied by horizontal foot speed, with active-command gating | −2.0 |
| `foot_swing_height` | Squared relative error in peak airborne height, evaluated on first contact, with active-command gating | −0.25 |

The sensor measures foot-site height minus ray-hit terrain height. It reduces rays around the foot using the configured reduction; the saved setup has a 4 cm ring. It is **not identical** to our plot's sphere-bottom clearance under the center. Local XML foot sites are also slightly offset from the contact-sphere center.

**Conditional candidate:** after verifying that training sensor readings correspond to sensible airborne height, test both height preferences at **0.13 m**, keeping their weights unchanged. This is a modest candidate value, not a value proven to work and not a direct substitution of the plot's 0.122 m geometric threshold. Changing both height preferences is one coordinated behavior experiment; we cannot attribute its effects separately to the two terms.

The manual trial settings would be:

```python
cfg.rewards["foot_clearance"].params["target_height"] = 0.13
cfg.rewards["foot_swing_height"].params["target_height"] = 0.13
```

Place a trial override after `make_cfg(...)` and before configuration saving and environment creation in [train_other.py](../xterra_mjlab/scripts/train_other.py). Alternatively, robot defaults live in [env_cfgs.py](../xterra_mjlab/xterra_mjlab/tasks/velocity/config/svanm2/env_cfgs.py). Choose one source of the override so the saved configuration is unambiguous. Do not edit installed package defaults for this trial.

Before running a full continuation, a short training-environment check should log measured foot-site height, contact mask, foot velocity and these two reward contributions in selected ascending-stair/student episodes. A higher preferred peak does not guarantee the foot reaches that height **before** the riser. Inspect the first-contact plot again after training. If it lifts higher only after collision, the next experiment must address lift timing/placement rather than increasing height indefinitely.

## 3. Keep the current smoothness settings fixed for that trial

```text
action_rate_l2:              −0.15
target_second_difference_l2: −0.01
target_saturation_l2:        −0.01
```

The plots do not prove that these weights prevent lifting, nor do they establish that increasing them will reduce measured jitter. Keep them fixed initially so the next comparison tests the changed lift preference. If the new policy requests useful lift but the smoothness cost strongly opposes those corrections in the logged stair episodes, separately test a smaller second-difference weight. Do not lower it automatically from the current plots alone.

## 4. Investigate direction and rear-leg support

The central candidate/viewer run reaches approximately +116° heading and exits the lane. Its front feet contact lower step tops, but the rear-left foot does not make loaded step contact in that run. Forward body speed can look reasonable while the robot walks away from the staircase.

**What to check:** angular-velocity tracking around collision, foot support forces, rear-foot swing height and slip, and whether student stair episodes teach coordinated support transfer.

The existing `track_angular_velocity` weight is 3.0. It rewards following the requested turning **rate**; it does not directly penalize accumulated heading error. Increasing 3.0 alone need not make the robot turn back toward the lane. The student input also does not directly contain a desired world-heading error. Do not add a world-heading penalty without checking whether the policy has enough information to act on it, and do not penalize legitimate commanded turns.

A heading-feedback command layer can be investigated separately for a navigation task because the policy already accepts yaw-rate commands. That changes the evaluation protocol and is not evidence that the unassisted gait policy learned reliable stair ascent. Our current no-steering-rescue results remain the baseline.

## 5. Check standing behavior separately

During the central candidate's 1–3 s zero-command interval, its rear-left foot was about 6.3 cm above the floor with no loaded contact; the original supported itself on all four feet. This is a posture change, not proof that it caused the stair failure.

If the intended stop behavior is four-foot standing, inspect the existing standing-pose reward and startup transition first. A four-foot-contact or low-foot-height objective, if later added, must be limited to the standing condition. Applying it while walking would discourage necessary foot lifting.

## 6. Actuator/contact changes come after these checks

The first contacting leg was not torque-clipped, so increasing its torque limit would not change that immediate sample. Keep J_LEG, gains, torque limits and deployed target bounds fixed for the initial reward trial. They can affect later motion, but we have not measured a physical calibration error that justifies changing them now.

There are also training/viewer plant differences to verify: local training foot-contact configuration specifies friction 0.6, while the recorded viewer scene uses 0.85. Do not assume either is the real value, or choose one merely because it makes climbing easier. Establish the intended model and separately measure sensitivity before treating a reward comparison as physically transferable.

## 7. How to judge the next candidate

Use the same checkpoint origin and budget for a control and candidate, the same observation convention, and the same evaluation protocol. If continuing the current 90500 checkpoint, use it for both arms; if restarting from 90000, restart both there. Do not compare unequal continuation budgets as if only the reward changed.

Record:

- Foot height and requested target pose **before** first riser contact.
- Which feet hit the riser versus support the tread.
- Heading, sideways drift, body tilt and progress after contact.
- Measured joint HF RMS in matched time/frequency windows.
- Speed tracking, falls, lane exits, stalls and full traversal.
- Existing and changed reward contributions in student stair episodes.

An improved candidate must improve useful stair behavior without unacceptable loss of tracking or balance. Lower reward costs or a smoother video alone are insufficient.

**Proposed order:** verify observation/sensor semantics → test the higher lift preference with current smoothness weights → evaluate first-contact/support/heading again → choose any later standing, direction or actuator experiment from that evidence.
