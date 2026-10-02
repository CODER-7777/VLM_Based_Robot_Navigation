# Which research suggestions should we use for our MoE jitter problem?

Written **2026-10-03**. This is an evidence review and proposed experiment order. No training, actuator, policy, viewer or server code was changed for this review.

Read this alongside [the fresh failure report](../tools/results/20261002_matched_v1/REPORT.md), [the plot-reading guide](15_HOW_TO_READ_THE_PLOTS.md), and [the proposed clearance experiment](16_NEXT_CHANGES_FROM_THE_PLOTS.md). The older September audit and the research papers are sources of hypotheses; our recorded measurements must determine which hypotheses apply.

## 1. What our plots actually say

In the central candidate run, the front-left foot hits the vertical face of the first stair at **9.730 s**. Its center is only **5.63 cm** high. To pass directly over a 10 cm top, this 2.2 cm-radius sphere needs its center above approximately **12.2 cm**, plus clearance margin. See [the event plot](../tools/results/20261002_matched_v1/candidate90500_stairs_viewer_start0/08_first_contact.png) and [the underlying event measurements](../tools/results/20261002_matched_v1/candidate90500_stairs_viewer_start0/first_contact_analysis.json).

At that instant, the contacting leg's targets and torques are not clipped. Even putting the joints at their current commanded angles with the body frozen produces a low foot in the static geometric check. This does not predict the dynamic trajectory, but it gives no evidence that the immediate problem is simply insufficient torque to achieve an already-high foot target.

The policy makes much larger corrections after contact. In matched six-second windows, measured joint 8–30 Hz RMS averages **0.331° on flat versus 0.833° with stairs**. The [matched comparison](../tools/results/20261002_matched_v1/candidate90500_stairs_viewer_start0/09_flat_comparison.png) shows progress stopping and body tilt increasing after stair contact. This identifies an effect of the stair on the complete feedback loop. It does not isolate a faulty motor, gate or reward, and the frequency band includes impacts and useful corrections as well as potentially unwanted vibration.

Across the repeated starts, improved speed tracking and less target removal did not produce consistent jitter improvement or successful ascent. Therefore, increasing smoothness punishment again is not the best-supported next step. We need to investigate **foot lifting before collision, timing, support transfer and direction**.

## 2. Quick decision table

| Suggestion | Useful for us? | What to do with it |
| --- | --- | --- |
| Learned/residual actuator model | Potentially, especially for hardware transfer | First measure a repeatable simulator–hardware response mismatch; do not add a network just because the simulator shakes |
| Observation/action delay randomization | Yes; first check what already exists | Training already configures actuator delay; verify server implementation and test equivalent evaluation conditions |
| Gate flicker diagnosis | Yes as a diagnostic | Use existing gate traces and inspect expert/actor sensitivity before any architecture change |
| Filter contact/state observations | Conditional | Our student has no direct contact input; identify a noisy input and assess added delay before filtering |
| Change PD gains or policy rate | Useful controlled sensitivity experiments later | Keep changes separate from reward comparisons and check compatibility with the trained dynamics/history |
| Hierarchical fast foot controller | Possible longer-term redesign | Requires a new control contract and training/evaluation design; not an immediate 90k checkpoint patch |

## 3. Actuator modelling: a good idea, but not a proven first fix

Our current simulator already uses a coupled motor-space PD model, rather than teleporting joints to desired angles. [svanm2_actuator.py](../xterra_mjlab/xterra_mjlab/actuators/svanm2_actuator.py) implements the transmission and torque clamp. [constants.py](../xterra_mjlab/xterra_mjlab/assets/svanm2/constants.py) configures kp 20, kd 0.7, gear ratios 8/8/16, coupling 0.5, armature 0.01 and joint-side torque limits 12/12/24 Nm. These are implemented assumptions, not proof of complete hardware calibration.

Hwangbo's ANYmal work learned actuator torque response from histories of position error and velocity using hardware data. That is a useful precedent, but a different robot's fitted model cannot be copied into ours. [Original paper](https://arxiv.org/pdf/1901.08652).

The linked 2026 paper fits simulator changes against hardware proprioceptive/action distributions. It includes a small residual torque model added to nominal PD, rather than replacing PD. Its distribution-based approach does not require directly measured torque labels in the same way as supervised torque regression. [Simulator Adaptation paper](https://arxiv.org/pdf/2604.11090).

For our robot, first compare recorded commanded targets, actual q/dq, timestamps and reliable torque/current estimates where available. Look for consistent response lag, gain error or load-dependent tracking error. Validate on separate recordings. Training a residual only on our simulator's own traces would not identify missing real actuator dynamics. Preserve thigh–calf coupling; an independent correction for each joint needs justification for this mechanism.

Also distinguish **improving the actuator model inside training simulation** from **adding a corrective torque controller to the real robot**. These are different changes. Neither is implemented here.

## 4. Delay: our training is already configured to randomize action latency

This is an important correction to the pasted suggestion's zero-latency assumption.

In [constants.py](../xterra_mjlab/xterra_mjlab/assets/svanm2/constants.py), the training actuator has:

```python
delay_min_lag = 0
delay_max_lag = 2
delay_update_period = 0
```

[env_cfgs.py](../xterra_mjlab/xterra_mjlab/tasks/velocity/config/svanm2/env_cfgs.py) selects the delayed robot when `play=False`. The completed candidate's [saved env.yaml](../xterra_mjlab/evaluation_runs/20261002_moe_target_bundle_updates90500/env.yaml) contains these same settings, physics timestep 0.005 s and decimation 4.

In the inspected **local installed mjlab implementation**, actuator lag is in physics steps and period 0 means resample every step. The custom actuator receives delayed command targets before calculating torque. This corresponds to a configured **0, 5 or 10 ms command delay**, not 0, 20 or 40 ms. Observation delays in that saved configuration are zero. The current viewer has no equivalent explicit randomized command-delay buffer.

Implementation references:

- [Actuator delay configuration and application](../xterra_mjlab/.venv/lib/python3.11/site-packages/mjlab/actuator/actuator.py).
- [Delay-buffer implementation](../xterra_mjlab/.venv/lib/python3.11/site-packages/mjlab/utils/buffers/delay_buffer.py).
- [Entity actuator application](../xterra_mjlab/.venv/lib/python3.11/site-packages/mjlab/entity/entity.py).

The saved YAML establishes the run's configured settings. Verify the actual **server mjlab version and implementation** before claiming that its runtime behavior matches the currently installed local package exactly.

Next, compare the trained delay convention with the viewer in an isolated evaluation experiment, keeping policy, sensing, gains, contacts and commands fixed. Do not introduce a large arbitrary observation delay or remove smoothness rewards simultaneously.

The two cited delay sources describe different approaches. [HiLo](https://arxiv.org/pdf/2502.03122) is a humanoid paper that blends previous and current targets with a random factor; this is a stochastic lag, not an exact model of every communication delay. [Multi-Modal Delay Randomization](https://neurips.cc/virtual/2021/38508) concerns quadrupedal vision/proprioceptive observation timing. Our student has no vision input, so only the relevant proprioceptive timing ideas transfer directly.

**Delay randomization and action-rate penalties serve different purposes.** One teaches robustness to delayed commands/sensors; the other discourages rapid changes. We do not need to choose one and delete the other without a comparison.

## 5. The gate: investigate it, but do not call correlation the root cause

Our [checkpoint_policy.py](../xterra_mjlab/svanm2_moe_stair_sim/checkpoint_policy.py) shows:

```text
five 45-value observation frames → 225-value history
                          ↓
             eight soft gate weights
                          ↓
        weighted mixture of eight 32-value features
                          ↓
              normalization and final actor
                          ↓
                 twelve joint actions
```

The gate already receives history. It has no recurrent hidden state, but describing it as an instantaneous-only, memoryless gate is misleading. The experts produce latent features, not eight separate joint-action vectors. There is no hard one-expert switch in this forward path.

I checked the existing central candidate gate logs on 2026-10-03. At the 50 Hz policy ticks, I calculated `||w[t] - w[t-1]||₂`, assigning each difference to its endpoint time. Each window contains 300 differences:

| Same-time six-second window | Mean gate change, stairs | Mean gate change, matched flat |
| --- | ---: | ---: |
| 3.73–9.73 s, before first stair contact | 0.04339 | 0.04339 |
| 9.73–15.73 s, after first stair contact | 0.07373 | 0.04089 |

Source: `trace.npz` in [the stair case](../tools/results/20261002_matched_v1/candidate90500_stairs_viewer_start0/) and [the matched flat case](../tools/results/20261002_matched_v1/candidate90500_flat_viewer_start0/). These are dimensionless gate-change magnitudes, **not joint jitter amplitudes**. This is one paired start, not a cross-trial causal result.

The gate changes more after the stair collision. However, the collision also changes the observations and each expert's features. The gate may be reacting appropriately to the disturbance. This result motivates further diagnosis; it does not prove the gate causes the shaking.

The next useful diagnostic is to inspect expert features and final-action sensitivity with the gate held versus updated on recorded histories. Such offline counterfactuals locate immediate network sensitivity but do not establish closed-loop task performance. Then test a justified change in matched rollouts. A constant gate can itself disable needed terrain adaptation.

Options with a deliberation cost are temporally extended decisions, not a direct equivalent of this dense soft mixture. [Options paper](https://arxiv.org/abs/1709.04571). A recurrent gate is a new architecture; its parameters, hidden-state resets and training sequence handling require deliberate changes. It cannot be assumed to load the existing 90k checkpoint unchanged.

## 6. Observation filtering: first identify which input is noisy

The deployed student frame contains commands, gyro, projected gravity, joint positions, joint velocities and previous clipped raw actions. See [controller.py](../xterra_mjlab/svanm2_moe_stair_sim/controller.py). There is **no explicit binary contact signal, contact force or stair-height input** to this student. Training's reward/critic sensors should not be confused with actor inputs.

A stair impact can still alter q, dq and gyro, and therefore affect the gate indirectly. Inspect these signals and their timing before selecting any filter. Synchronizing readings is different from smoothing them.

Filtering observations also changes the information and can introduce phase lag. The statement that it leaves fast corrections untouched is not generally valid: the correction depends on the filtered input. Maintain the trained observation convention, or deliberately train against the changed convention.

## 7. Gains and rate: experiments, not automatic remedies

Our policy runs at 50 Hz and PD/physics at 200 Hz. Lowering the policy rate is not automatically better. It also changes the time covered by five history frames and how long targets are held. An existing checkpoint was not trained under that new timing.

Gain changes can be evaluated without learning, but they still change the physical response the policy was trained against. Log tracking error, actual motion, contact forces and clipping while keeping the other conditions fixed. Do not copy generic Unitree XML gain ranges into our coupled SvanM2 controller: our PD is calculated in Python/motor space.

Do not modify J_LEG because joint target bounds changed. The transmission matrix represents mechanical gear/belt ratios, not allowed joint-angle ranges.

## 8. Hierarchy: a later redesign

We already separate the 50 Hz neural position-target policy from a faster PD torque controller. That does not rule out a useful future foot-placement controller, but it makes the claim that one network currently performs every millisecond-level correction inaccurate.

A terrain-aware foot-placement or residual controller would need suitable terrain/state information, target-combination rules and retraining or deliberate adaptation. It could help ascent, but the current plots do not prove that the existing architecture is inherently incapable of the task. This is a larger project than continuing the same 90k architecture with different rewards.

## 9. Updated next-step checklist

- [ ] Verify server and local delay implementation, gains, contact parameters, target bounds and observation timing. The saved run already configures action delay; do not add it twice.
- [ ] Establish a consistent evaluation setup; retain the old results as a separate baseline rather than mixing different sensing/delay settings in one comparison.
- [ ] Inspect actual student stair episodes: foot-height sensor readings, first-contact type, commanded foot motion, support transfer, heading and individual reward contributions.
- [ ] If height/reward semantics are verified, run the conditional clearance trial described in [note 16](16_NEXT_CHANGES_FROM_THE_PLOTS.md): preferred heights 0.10 → 0.13 m, same existing weights. This is an experiment, not a proven fix. Check whether lift happens **before** collision.
- [ ] Keep action rate −0.15, target second difference −0.01 and saturation penalty −0.01 fixed for that initial behavior comparison; review actual reward contributions before changing them again.
- [ ] Use matched checkpoints, continuation budgets, commands, starts and evaluation conditions. If the task requires starting from 90000, start both comparison arms from 90000.
- [ ] Measure full ascent, falls/stalls/lane exits, speed tracking, heading, first-riser clearance, support and matched joint oscillation. Do not accept a smoother stall as improvement.
- [ ] If evidence points to a gate-sensitive response, analyze expert/actor contributions before changing the gate. If evidence points to actuator mismatch, calibrate against hardware before fitting a learned residual.

**What changed in this review:** the interpretation and proposed diagnostic order. The new findings are that training already configures command delay, the gate already reads temporal history, the student has no direct contact input, and gate movement increases after contact in one matched pair. None establishes a complete jitter fix.
