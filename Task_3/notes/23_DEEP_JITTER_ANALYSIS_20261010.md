# SvanM2 jitter: control-system diagnosis, experiment history, and current results

Reviewed 2026-10-10, with the new recording added on 2026-10-11. For the subsequent focused gate/frequency audit, independent September raw rechecks, verified full-foot completion of the new recording, and VLM integration proposal, read [note 24](24_GATE_FREQUENCY_AND_VLM_AUDIT_20261011.md). Earlier dated notes remain the experiment history.

**We have demonstrated a substantial simulator mitigation, but have not eliminated jitter or validated a real-robot fix.** The strongest controlled evidence implicates the interaction between simulated foot contact, the coupled actuator, and the learned feedback policy. Target oscillation is strongly associated with measured hardware oscillation, but the available hardware evidence does not isolate which part of that loop initiates it.

In **34 new CPU-only simulations**, under the controller's **current tighter target limits**, changing only MuJoCo `impratio` from 100 to 10 reduced flat joint 8–30 Hz RMS by **63.5–70.5%**. It enabled **3 of 6 tested policy/start stair cases** to finish, versus **0 of 6** matching baselines. Those six cases are two checkpoints × three deliberate starting offsets, not independent training seeds or a population success-rate estimate. Original90000 sideways tracking became worse in one flat comparison. The mitigation therefore needs a task-level qualification.

**No training or GPU evaluation was launched for this review.** New inference and physics ran on the CPU. Tell the user and establish GPU availability before any future training or GPU evaluation; the commands below use CPU only.

[New plots and all outcomes](../tools/results/deep_audit_20261010/index.html) · [Numeric verification](../tools/results/deep_audit_20261010/verification.json) · [Evidence inventory](../tools/results/deep_audit_20261010/catalog/inventory_summary.json) · [Main README](../README.md).

## 1. What was examined, and what the evidence can establish

The inventory pass covered **5,477 project/evidence files, approximately 3.91 GB**, excluding the installed `.venv`, caches, VCS internals, and configuration directories. The whole folder is larger because the installed environment is large. The inventory includes 43 Markdown files, 137 `.log` files, 1,374 NPZ files, 624 PNGs, 35 JPEGs, and nine MP4s at the time of scanning. These counts include historical source snapshots and intermediate outputs, not that many independent experiments.

The review traced the active controller, checkpoint inference, training actuator, target/reward mapping, recorders, contact analysis, and evaluation criteria. It inspected the hardware-spectrum/contact plots and the saved first-contact video contact sheet, read historical reports and key numeric summaries, reopened the three available training event logs, hashed and inspected six MoE checkpoints, and recomputed **32 historical contact-study traces**, including all eight nominal stair comparisons. The new stair outcomes were also verified directly from numeric foot positions, platform loads, tilt, and clearance, independently of their saved outcome labels.

The inventory is not a claim to have watched every frame of every video or semantically reviewed every duplicate source snapshot. The September hardware findings below are supported by the retained audit summaries, plots, and replay results. The original full hardware telemetry and synchronized terrain labels are not reproduced by the new CPU simulations. A screen recording cannot supply contact force or motor torque measurements.

| Folder / track | Role in this diagnosis |
| --- | --- |
| `moe_jitter_audit_20260921/` | Hardware-log analysis, replay parity, 120 final historical rollouts, filtering/delay/terrain investigations. `invalidated_prototype/` and `pre_sensor_refresh_runs/` are excluded from its final conclusions. |
| `notes/` | Decisions and their historical rationale; several older “next step” instructions are now superseded. |
| `tools/results/20261002_*` | Original-versus-90500 matched flat/stair/sensing tests and first-contact measurements. |
| `tools/results/interactive/` | User-operated simulator sessions, reset-delimited attempts, recorded commands; these are not hardware recordings. |
| `tools/results/control_loop_audit_20261006_v2/` | Controlled contact, sensing, gate, delay, and substep interventions; historical wider target limits. |
| `tools/results/tier1_solver_probe_20261007/` | Solver-count and timestep sensitivity; interpret the limitations in section 8. |
| `tools/results/deep_audit_20261010/` | This review's inventory, checkpoint identities, training-log reread, 34 CPU rollouts, plots, and raw verification. |
| `xterra_mjlab/` | Runtime source, assets, checkpoints and multiple learning tracks. Flat PPO, HIMLoco, WTW, and ISL work are not interchangeable evidence for the MoE student. |

Machine-readable sources: [file inventory and hashes](../tools/results/deep_audit_20261010/catalog/inventory.json), [checkpoint metadata](../tools/results/deep_audit_20261010/catalog/checkpoints.json), [training event summaries](../tools/results/deep_audit_20261010/catalog/training_logs.json), [historical raw recheck](../tools/results/deep_audit_20261010/catalog/historical_raw_recheck.json).

## 2. Conventional robotics interpretation of the control loop

### 2.1 Signals, rates, and the plant

The relevant loop is:

```text
operator velocity command + measured joint/body state + previous action
  → five-frame observation history
  → MoE latent encoder and actor, 50 Hz
  → raw action clamp → standing offset and scale → joint-target limits
  → coupled PD at 200 Hz → torque limits
  → robot dynamics, ground contact, and integration
  → next measured joint/body state
```

The policy history is five 45-dimensional frames, 225 values. The viewer supplies oldest-first history; the actor also receives the newest 45-value frame directly. Each frame contains command, scaled gyro, projected gravity, joint displacement from the reference pose, scaled joint velocity, and previous action. The student receives no explicit staircase height map or direct contact-force input. Contact influences it through motion and history.

The eight experts produce 32-dimensional latent features, combined by softmax weights and normalized before the actor. They are **not eight motor controllers selected by hard switching**. The actor maps the latent plus newest frame to 12 actions. This distinction matters when evaluating “MoE chattering.” See [checkpoint_policy.py](../xterra_mjlab/svanm2_moe_stair_sim/checkpoint_policy.py).

For each joint, with radians throughout:

```text
a = clamp(actor_output, -6, +6)
q_requested = q0 + scale * a
q_commanded = clamp(q_requested, target_min, target_max)
scale per leg = [0.15, 0.15, 0.30]
```

The previous-action observation is `a`, before the position-target clamp. Feeding back the final target instead changes the checkpoint's observation semantics. Targets are held for 20 ms; PD recomputes torque every 5 ms. A 50 Hz hold is normal sampled control, but delay and contact stiffness can still reduce closed-loop robustness.

One cannot calculate a trustworthy gain margin, damping ratio, or mechanical resonance from `kp` and `kd` alone. The configuration-dependent inertia, contact constraints, effective delay, and local policy Jacobian are also needed. As a scale illustration only, a pure extra 5 ms delay contributes 36° phase lag at 20 Hz. This is not a measured stability margin for SvanM2.

### 2.2 The actuator is coupled, not twelve independent PD loops

For a leg ordered hip/thigh/calf:

```text
J = [[8,0,0], [0,8,0], [0,8,16]]
G = diag(8,8,16)
tau_motor = diag(kp / G_diag²) J (q_commanded - q)
            - diag(kd / G_diag²) J dq
tau_joint = Jᵀ tau_motor
tau_applied = clamp(tau_joint, ±[12,12,24] Nm)
```

Thus `K = Jᵀ diag(kp/gear²) J` and `D = Jᵀ diag(kd/gear²) J`. At today's `kp=18`, `kd=0.7`:

```text
K = [[18,0,0], [0,22.5,9], [0,9,18]]       Nm/rad
D = [[0.7,0,0], [0,0.875,0.35], [0,0.35,0.7]]  Nm·s/rad
```

A calf error or velocity contributes to thigh torque, and vice versa. At `kp=20`, thigh stiffness is 25, not 20. The actuator's old introductory comment incorrectly implied equal effective diagonal gains; this review corrects that explanation without changing the control law. The current viewer's top-level docstring still mentions historical kp=20; the executed initializer and new manifests establish kp=18.

The September estimated-torque comparison favors retaining this coupling: thigh reconstruction RMSE was about 0.69–0.83 Nm versus 1.66–2.88 Nm for diagonal PD. That supports the transmission model relative to the diagonal alternative; estimated torque is not a load-cell calibration of the plant. Tightening target bounds does not require changing `J`.

### 2.3 Three different nonlinear limits

| Quantity | Meaning | What it cannot prove |
| --- | --- | --- |
| Position-target removal / occupancy | Requested angle exceeds a software bound, or target sits on it | Physical joint-stop contact |
| Torque clipping | Coupled PD requests more than the modeled effort limit | Exact real motor current/torque saturation law |
| Geometric joint-stop or foot contact | A physical/simulated constraint is active | That a target penalty caused it |

Clipping is continuous and nonexpansive for a fixed box; it does not intrinsically amplify an instantaneous target increment. It can change reachable poses and subsequent closed-loop behavior. Torque saturation removes effective control authority during large disturbances, so increasing damping can increase saturation rather than cure a recovery oscillation.

## 3. Current contract versus the settings in older evidence

The current `controller.py` already had user edits when this review began. They were preserved.

| Setting | Current viewer | October 6–7 successful contact tests | Interpretation |
| --- | --- | --- | --- |
| Hip target limits | ±0.735 rad | ±1.0472 rad | Different action realization |
| Calf upper target | −0.88776 rad | +0.5000 rad | Difference 1.38776 rad, approximately 79.5° |
| Calf lower target | −2.7227 rad | −2.7227 rad | Same |
| Front thigh target | [−1.5708, 3.4907] rad | Same | Current limits do not establish all deployed firmware conventions |
| Rear thigh target | [−0.5236, 4.5379] rad | Same | September audit also described deployment asymmetries; verify complete deployed contract |
| Viewer kp / kd | 18 / 0.7 | Compared at 18/0.7 and 20/0.7 | Compare within matched gains |
| Scene `impratio` | 100 | 100 versus 10 | Explicit new CLI override available; XML default remains 100 |
| Current local training `impratio` | 10 | Saved October 2 YAML also says 10 | Original90000's complete training environment is not reconstructed by current source |
| Policy / PD / physics | 50 / 200 / 200 Hz | Same for primary A/B pairs | Internal substeps are separate tests |
| Observation timing | Legacy by default; optional fresh | Both tested, separately | Changing sensing also changes policy inputs |

The newest91000 checkpoint's saved arguments specify `viewer-wide` training targets, while today's viewer uses tighter targets. That is a known train/evaluation contract discrepancy. It does not alone prove why any particular rollout fails. Restoring wider targets to make a simulation succeed would not validate those angles for the real robot.

**A checkpoint update number is not an identity.** There are three distinct local 90500 policies and two distinct 91000 policies:

| Name in this report | SHA-256 prefix | Recorded distinguishing settings |
| --- | --- | --- |
| Original90000 | `440bbb28d554` | Reference checkpoint; full original environment/source provenance incomplete locally |
| September 27 control90500 | `dc6e763ee449` | Action-rate weight −0.10 |
| September 27 candidate90500 | `a 248e08e2b12` | Action-rate weight −0.15 |
| October 2 bundle90500 | `06f8f2788367` | Action rate −0.15 plus target second difference and saturation; changed bounds |
| Older91000 | `f74e62bf1f1e` | Rate weight −0.05, target profile `existing`, saved LR cap 0.0003 |
| Newest91000 | `dec9775d4b36` | Rate weight −0.01, `viewer-wide`, swing preference 0.13 m, saved LR cap 0.00001 |

All six inspected model state dictionaries are finite. Saved arguments establish what the launch requested, not a complete reconstruction of every imported server function. Full hashes and metadata are in the [checkpoint catalog](../tools/results/deep_audit_20261010/catalog/checkpoints.json).

## 4. What the graphs and hardware logs actually say

### 4.1 Hardware: targets and measured motion are related; timing spikes are weaker evidence

The retained September audit reports 122,607 roughly 200 Hz control samples and 30,175 policy I/O records in the later recording. Measured-angle 8–30 Hz RMS during motion was about 0.19–0.45° per joint; held-target band RMS was about 0.63–1.84°. The worst four-second joint window was 465–469 s, around 0.87° across joints. See [hardware diagnostics graph](../moe_jitter_audit_20260921/hardware_jitter_diagnostics.png) and [deep summary](../moe_jitter_audit_20260921/deep_hardware_summary.json).

In the graph, target bars exceed measured-angle bars, and calves have relatively large motion. This is consistent with a mechanical/control response to rapidly varying references. It does not prove the policy initiated the event: ground disturbances can change observations, which change targets, closing the same loop.

Across moving windows, Spearman correlation with measured-angle band motion was **0.962 for target motion**, versus 0.154 for maximum control interval, 0.020 for sensor age, and 0.097 for action age. The low-pass derivative-of-angle and reported velocity curves almost overlap; their fitted scales were 0.993–1.008. Wrong velocity units or a persistent sign inversion are therefore poorly supported explanations for that recording.

The original 4,141-sample incident was only approximately 20 Hz. Its 72.6° peak tilt documents a large failure, but its Nyquist frequency is approximately 10 Hz: it cannot measure an 8–30 Hz band. Do not combine it with the later 200 Hz record as if their spectral resolution were identical.

The four calf targets occupied limits during approximately 17.7%, 20.0%, 19.4%, and **64.8%** of moving samples. Rear-right asymmetry deserves a contract/joint-specific check. Nonzero firmware `fault` fields 98/99/100/102 occurred in 500 telemetry rows, 422 during motion; their interpretation is unresolved. The associated higher vibration is confounded by operating conditions. It is neither evidence to dismiss the flags nor proof of 500 independent motor failures.

All 30,175 recorded policy outputs were reproduced from their exact inputs in the retained replay audit: max absolute difference 2.29e−5, RMS 7.73e−7. This argues against wrong weights or reversed history **for that audited path**. It does not prove every later deployment/export is correct. [Replay evidence](../moe_jitter_audit_20260921/parity_summary.json).

### 4.2 Stair video and contact traces: impacts and support transfer matter

The [October 2 video contact sheet](video_review_20261002_candidate90500/first_contact_5fps.jpg) shows repeated front-foot interaction with the riser, forward/rear support at different heights, and growing body rotation. Its timestamps belong to that video; do not map them directly onto a separate scripted run.

In the separately instrumented October 2 bundle90500 center-start test, first loaded FL riser contact occurs at **9.730 s**, with foot center **5.63 cm** above the floor. A 2.2 cm foot radius needs roughly 12.2 cm center height to clear a 10 cm top directly. At the incident sample, target-pose forward kinematics gives only 5.71 cm, and neither FL target nor torque is clipped. Increasing the torque ceiling cannot change the already-unsaturated torque at that instant. [Event analysis](../tools/results/20261002_matched_v1/candidate90500_stairs_viewer_start0/first_contact_analysis.json).

However, a later successful wide-bound/contact10 run first meets the stair at only **4.39 cm** foot-center height and then recovers. A low first collision is an adverse event, not proof that the policy lacks all lifting capability. Recovery, rear support, heading, and contact response determine whether that event becomes failure.

The newest91000 manual attempt described in note 17 keeps vx=0.4 through first contact. Joint band RMS rises from **0.3176° to 1.6417°** in the selected before/after windows; any-joint torque clipping rises from 0 to **11.31%** of samples. Later FR thigh velocity reaches 58.21 rad/s; raw torque −75.64 Nm comprises −27.74 Nm position and −47.91 Nm damping terms before clipping to −12 Nm. The damping term is already large. This supports analyzing contact/feedback excitation and saturation, rather than simply increasing `kd`. [Detailed retained measurements](archive/17_REVIEW_OF_ACTUATOR_DELAY_AND_GATE_SUGGESTIONS.md).

### 4.3 The “50 Hz staircase” and MoE gate are not established root causes

In the reviewed newest flat interval, 8–30 Hz joint RMS was 0.3404°, versus 0.0340° in 45–55 Hz. A dominant narrow 50 Hz resonance was not demonstrated. Plotting piecewise-held targets naturally draws stair steps; visual steps alone do not establish harmful jitter.

Gate changes increase around contact, but the actor's direct newest-frame pathway also contributes strongly to output changes. In the saved fixed-gate diagnostic, newest91000 Y joint-band RMS falls from 0.3703° to 0.1575° **while speed falls from 0.2202 to 0.0386 m/s**. A quieter nearly stalled gait is not a successful fix. Delaying only the actor's previous-action input often worsens the response. These are controlled architecture sensitivities, not deployment recommendations. [Control-loop summary](../tools/results/control_loop_audit_20261006_v2/summary.json).

## 5. Our attempts so far: why each change was tried and what happened

| Attempt | Evidence / reason for trying it | Observed result | Current decision |
| --- | --- | --- | --- |
| September deployment-contract and replay audit | Simulator limits, history conventions, command shaping, sensing, reset, and contact assumptions differed from deployment | Replay passed; corrected offline tests still showed ascent failures and oscillatory targets | Keep parity checks and distinguish contract errors from policy quality |
| 20 ms target filter | Rapid held-target changes correlated with measured vibration | Flat RMS 0.546→0.507° (about −7%); tracking worsened; selected 15 cm stair cases tipped | Not a validated deployment fix |
| 40 ms target filter | More aggressive smoothing | Flat RMS 0.546→0.802° (about +47%) | Added lag can worsen the closed loop; do not increase smoothing blindly |
| Smaller timestep / delay / motor-space clipping probes | Uncertain physical actuator and numerical contact response | Sensitive trajectories; no reliable ascent established in the September suite | Useful identification experiments, not identified hardware parameters |
| September 27 action-rate −0.10 versus −0.15 continuations | Existing action-rate cost penalizes successive action changes; inspect a stronger coefficient | Both completed update90500, zero reported numerical resets; raw cost declines more in −0.15 run | Training objective change verified; physical jitter improvement not established by training logs alone |
| October 2 combined target bundle | Action penalties did not directly describe final bounded targets; frequent saturation motivated explicit costs | Target second difference fell 6.57%; saturation cost fell strongly; mixed measured jitter and 0/12 distinct scripted stair traversals | Combined changes prevent attribution to one reward or bound change |
| Wider viewer targets restored for comparisons | Tightening may restrict extension and differ from what the checkpoint learned | Original90000 user-steered run completed at 40.925 s; shaking remained | Capability exists in that setup; manual steering and wider limits prevent a matched hardware claim |
| Time-aware target-rate cost | The same angle change over shorter time is more aggressive | Elapsed-time, clamping/reset, and manager integration tests pass | Implemented objective, not proof of better control |
| Older91000 −0.05 rate trial | Stronger rate-excess discouragement | Different checkpoint and target profile from newest91000 | Keep identity separate; do not mix results by update number |
| Newest91000: −0.01 rate, 0.13 m swing, viewer-wide, LR cap 1e−5 | Avoid suppressing necessary stair recovery; encourage greater foot height | Near-stall at +Y0.15 in a matched recording; worse jitter at +Y0.30 in another; no universal superiority | Multiple changes remain confounded; do not continue training automatically |
| Legacy versus fresh observations | After `mj_step`, derived sensor arrays can lag integrated q/dq | Material trajectory changes, mixed direction-dependent improvements | Establish the intended timing contract; freshness alone is not a cure |
| Gain sweep: kp=18/20, kd=0.56/0.7/0.84 | Test position/damping sensitivity while retaining coupling | Checkpoint-dependent flat responses; all eight saved stair follow-ups failed full ascent | No universal “increase damping” or “reduce kp” answer |
| Freeze gate / actor-history intervention | Test the gate-chattering hypothesis | Gate freeze sometimes stalls; actor-path delay can increase oscillation substantially | Preserve trained semantics; do not patch gate frequency from correlation |
| Contact `impratio` 100→10, October 6–7 | Current training uses 10, viewer 100; strong contact-linked oscillation | 44–73% flat-band reduction at kp=18; four wide-bound nominal stair pairs succeed at 10 and fail at 100 | Strong simulator contributor; historical bounds and hardware limits remain distinct |
| Tier1 solver/physics sweep | Test whether iteration cap or coarse integration explains contact sensitivity | Large resolution sensitivity; sampled solver maxima below cap20 | Does not prove convergence; effective contact stiffness changed with timestep |
| October 10 current-contract recheck | Old successful tests no longer matched today's tighter limits | 63.5–70.5% flat-band reduction; 3/6 stair completions at 10, 0/6 at 100; original Y speed regression | Explicit simulator mitigation available; robust control and hardware validation remain unfinished |

The historical filter/terrain source is [September report](../moe_jitter_audit_20260921/REPORT.md). The combined-candidate source is [October 2 report](../tools/results/20261002_matched_v1/REPORT.md). Gain follow-ups are in [stairs summary](../tools/results/gain_sensitivity_20261005_v1/followup/stairs_summary.json). This table records tested changes separately from proposals such as gait clocks, top-k routing, learned actuators, and contact-conditioned objectives, which are not proven fixes in this repository.

### Training curves reread from the actual local event files

First 50→last 50 means within each saved continuation, not matched evaluation episodes:

| Run / metric | First 50 | Last 50 | What this establishes |
| --- | ---: | ---: | --- |
| September 27 −0.10 raw action-rate cost | 6.1623 | 6.0887 | About 1.19% decrease |
| September 27 −0.15 raw action-rate cost | 6.0688 | 5.3570 | About 11.72% decrease |
| September 27 tracking reward rate, −0.10 | 5.4472 | 5.4485 | Aggregate tracking stays similar |
| September 27 tracking reward rate, −0.15 | 5.4469 | 5.4474 | Aggregate tracking stays similar |
| October 2 raw target second difference | 10.1688 | 9.5007 | 6.57% decrease |
| October 2 raw saturation cost | 1.8794 | 0.7583 | About 59.65% decrease |
| October 2 tracking reward rate | 5.0598 | 5.2341 | Aggregate tracking contribution increases |

These curves mix training populations/conditions; they do not isolate the deployed student on ascending stairs. Reward-rate logs are before multiplication by `step_dt`; raw costs and weighted contributions are different quantities. A smaller loss or larger aggregate reward is not a measurement of joint vibration. Only three local TensorBoard event files were available in these six checkpoint folders; the newest trial's missing local event/source snapshot limits reward attribution.

The time-aware penalty is `sum(relu(abs(Δq_commanded)/(Δt * rate_reference) - 1)^2)`. Its exploratory hip/thigh/calf references are 7.093/11.275/20.365 rad/s, derived from selected recorded approaches, not motor speed specifications. Second difference is acceleration-like, not third-derivative jerk. Both objectives can penalize useful lift or recovery as well as unwanted motion. The low-speed tracking reward is also relatively tolerant: with the inspected std=0.5 formula, standing at a requested 0.15 m/s retains about 91.4% of the maximum linear-tracking term in the simplified zero-other-error example. That motivates objective analysis, not an automatic coefficient change.

## 6. New results under today's limits

### Protocol

Two exact checkpoints (original 90000 and newest91000), CPU inference, fresh process-created simulation state per case, kp=18/kd=0.7, current tight bounds, unchanged transmission and torque limits. Policy 50 Hz, PD 200 Hz, three seconds at zero command, one-second ramp to 0.30 m/s, no steering. Flat cases last 12 s and use the same full 5–11 s analysis window. Stair cases use 10 cm risers and a maximum 40 s.

Four flat cases per checkpoint/direction: baseline 100, ratio 10, explicit positive contact timeconstant floor 10 ms at original 5 ms timestep, and that same explicit contact model with five 1 ms internal steps per held PD torque. The explicit-contact baseline produces **bit-identical q and targets** to the original baseline in all four flat comparisons. This checks that its contact-constant normalization did not itself change those baseline trajectories.

For stairs, compare baseline, ratio 10, and fixed-contact/sub5 at three starts: center; y−0.03 m/yaw−0.02 rad; y+0.03 m/yaw+0.02 rad. Source/checkpoint hashes were retained; protected controller, scene, and weights stayed unchanged through both suites. [Flat protocol](../tools/results/deep_audit_20261010/flat/protocol.json), [stair protocol](../tools/results/deep_audit_20261010/stairs/protocol.json).

### Flat motion: contact intervention

| Policy / command axis | Joint RMS degrees: 100→10 | Reduction | Actual speed m/s: 100→10 | Tracking RMSE m/s: 100→10 |
| --- | --- | ---: | --- | --- |
| Original90000 X | 0.32768→0.09900 | 69.79% | 0.17420→0.18716 | 0.13531→0.11468 |
| Original90000 Y | 0.38009→0.13862 | 63.53% | 0.17463→0.14811 | 0.13457→0.15414 |
| Newest91000 X | 0.26903→0.08841 | 67.14% | 0.16059→0.18483 | 0.14833→0.11809 |
| Newest91000 Y | 0.49752→0.14696 | 70.46% | 0.14812→0.20347 | 0.16019→0.09995 |

Every request is 0.30 m/s. Even the improved speeds undershoot substantially. Original Y loses 0.02652 m/s and its error rises 0.01957 m/s; lower vibration is not an unqualified win. At ratio 10, none of these four selected flat windows clips torque, but target removal remains about 14–15% of joint/sample entries. The vibration reduction therefore did **not** require removing all target clipping. [Exact flat CSV](../tools/results/deep_audit_20261010/flat/results.csv).

![Current flat comparisons](../tools/results/deep_audit_20261010/current_flat_comparison.png)

### Stair completion: all starts, including failures

| Policy / start | Baseline 100, 5 ms | Ratio 10, 5 ms | Ratio 100, 1 ms with fixed contact |
| --- | --- | --- | --- |
| Original90000 −offset | Tip 14.060 s | Lane exit 26.705 s | Incomplete 40 s |
| Original90000 center | Tip 26.390 s | **Traversed 29.730 s** | Incomplete 40 s |
| Original90000 +offset | Incomplete 40 s | **Traversed 30.865 s** | Lane exit 39.550 s |
| Newest91000 −offset | Lane exit 22.435 s | **Traversed 30.585 s** | Lane exit 21.720 s |
| Newest91000 center | Lane exit 31.400 s | Lane exit 24.020 s | Lane exit 21.625 s |
| Newest91000 +offset | Lane exit 18.545 s | Lane exit 24.135 s | Lane exit 18.195 s |

Times are last recorded state times, at 5 ms sampling; the executed interval extends one sample beyond that label. Traversal requires **all four feet** beyond x=3.622 m, all inside the lane, each having loaded the platform >1 N, tilt<30°, clearance>0.18 m, with the simultaneous condition held≥0.5 s. Base world-x alone does not establish success. The previous report's four wider-bound successes were independently recovered from their saved traces, but they are a separate contract and not today's success rate.

![All current stair outcomes](../tools/results/deep_audit_20261010/current_stair_progress.png)

The tighter current setup still fails half the ratio 10 cases. Original90000 performs better than newest91000 on these three tested stair starts, so “more training updates” is not evidence that the candidate is the preferred controller. The 1 ms fixed-contact variant improves some original-policy progress but completes **0/6** stairs and reduces forward speed in both flat policies. It is not adopted as the solution.

## 7. Ranked causes and contributors

| Finding | Evidence strength | Engineering conclusion |
| --- | --- | --- |
| **Contact/plant interaction amplifies the simulated closed loop** | Strong intervention evidence: same weights/limits/gains/rates, only ratio changed; lower joint, contact-force and torque-band motion; both historical and current tests | Largest demonstrated simulator contributor. Calibrate contact dynamics before interpreting every target spike as policy indecision. |
| **Policy targets participate in the oscillation** | Strong hardware association and reproducible policy output; large post-contact target changes | Policy feedback quality remains part of the problem. Correct weights can still generate poor control. Causal direction within the loop is not isolated. |
| **Training/evaluation/deployment contracts differ** | Direct source/manifest evidence: bounds, contact, sensing, delay, commands | These differences change the plant and observations seen by a fixed policy; harmonize verified contracts before attributing improvements to rewards. |
| **Impact, support transfer, and heading loss drive stair failure** | Event traces, video, lane exits, low-riser contacts, incomplete rear support | This is a task-control problem as well as a vibration problem. Smooth trajectories that do not climb are insufficient. |
| **Coupled PD plus torque limiting can worsen disturbed recovery** | Exact reconstruction; large damping contributions and later clipping bursts | Preserve coupling; identify real actuator dynamics and saturation before choosing gains. Not evidence of a universally underdamped motor. |
| **Objective tradeoffs can suppress necessary motion** | Low-speed candidate stalls; stronger smoothness costs do not consistently improve tracking | Evaluate progress, tracking and support alongside jitter; avoid stacking penalties without an isolated test. |
| Gate motion alone, simple 50 Hz holding, scheduler spikes, wrong dq units | Insufficient or contrary evidence in the reviewed records | Do not promote these to the principal root cause or introduce filters/architecture changes on that basis. |
| Real backlash/compliance, servo latency, firmware status, inertia/payload errors | Plausible but not identified from these simulator experiments | Still open hardware hypotheses requiring measured system identification. |

The defensible answer is a **policy–actuator–contact feedback interaction with demonstrated simulator contact sensitivity**, not a single proven broken component. A physical foot has compliance/friction dynamics; MuJoCo's `impratio` is a numerical contact parameter, with no corresponding motor register to “fix” on the robot.

## 8. Corrections that matter when reading previous evidence

1. **The later tier1 substep grid is not a pure numerical convergence test.** It leaves positive foot `solref=.002` while reducing timestep from 5 ms to 1 ms. With default `refsafe`, the effective minimum timeconstant changes from 10 ms to 2 ms. The contact model becomes harder at the same time as integration becomes finer. The earlier `audit_control_loop.py` fine 800 Hz comparison explicitly fixed the timeconstant; do not conflate the two studies. This review's fixed-contact pairs remove that particular confound. MuJoCo documents the lower bound in its [solver-parameter reference](https://mujoco.readthedocs.io/en/latest/modeling.html#solver-parameters).
2. **No iteration-cap hit is not proof of numerical convergence.** The historical maxima are below 20 in the sampled solves, but the tier1 means flatten a padded per-island array, diluting the meaningful active-island count. Finer runs save only the final substep's solver data; earlier substep peaks can be missed. Residual/cost-gradient convergence was not recorded. Do not conclude “the solver is correct” from low mean iterations.
3. **Slip summaries use different populations.** The tier1 metric includes zero entries for unloaded feet in otherwise loaded samples; the contact-response analysis conditions on loaded contacts. Their absolute RMS values cannot be interchanged. The slip proxy uses rigid-foot contact-point velocity, not measured rubber deformation. Last-substep force samples are not interval-average force measurements.
4. **50 Hz policy samples cannot support a 30 Hz target spectrum.** New policy-target plots use 8–20 Hz. A 200 Hz stream of held targets can be analyzed above 25 Hz as an applied held waveform, but those components are not independently sampled policy decisions. Physical joint samples at 200 Hz support 8–30 Hz.
5. **Band RMS contains useful gait harmonics and impacts.** It is a consistent indicator, not a universal jitter classifier. Compare identical commands and full windows, report actual speed/heading, and do not drop failed rollouts. Contact-aligned six-second windows are explanatory but not identical gait states.
6. **Warnings need provenance.** Root `MUJOCO_LOG.TXT` contains three XML attach-option conflicts, not proof that the final training environment used the parent's initial timestep. The inner `xterra_mjlab/MUJOCO_LOG.TXT` also records an October 3 unstable-QACC warning at 161.405 s. Its run is not identified by that file alone. All 34 new cases have empty recorded MuJoCo warning dictionaries; historical “zero warnings” claims apply only to their named study.
7. **Reset correctness remains a gap in the interactive runtime.** `controller.reset()` sets pose/velocity/history but does not call `mj_resetData` to clear all warm-start/applied-force state. The new study creates fresh models/data for every case, so previous attempts cannot contaminate it. A deterministic reset repair should be tested separately against clean-start trajectories before treating repeated teleports as identical starts. It is not established as the source of sustained jitter in fresh runs.

Official MuJoCo defines `impratio` as frictional-to-normal constraint impedance, distinct from friction coefficient, in the [option reference](https://mujoco.readthedocs.io/en/stable/XMLreference.html#option-impratio). At a fixed saved state, the existing audit verified unchanged normal regularization and a 10× tangential regularization increase for 100→10. The force and gait response is nonlinear; do not infer a 10× force or vibration change. [Fixed-state calculation](../tools/results/control_loop_audit_20261006_v2/impratio_fixed_state.json).

## 9. What was implemented now, and how to use the measured mitigation

The viewer now accepts **`--contact-impratio 10`**. It changes only the compiled model's contact ratio for that process, prints the active value, and preserves the scene default when omitted. Current user-edited target bounds, gains, transmission, policy history, weights, and training settings were retained. There is no automatic training or automatic hardware deployment.

Scripted and interactive manifests now save the **active compiled solver settings**, including `impratio`, instead of relying solely on a scene-file hash. This matters because a runtime override can otherwise be invisible in a recording's provenance. The new option rejects nonpositive/nonfinite values. Fourteen CPU regression tests pass, including passive trajectory equality, reward timing/reset behavior, observation consistency, recording boundaries, traversal checks, and the new override test.

To inspect the original checkpoint with the tested simulator mitigation, from Task_3:

```bash
CUDA_VISIBLE_DEVICES='' xterra_mjlab/.venv/bin/python \
  xterra_mjlab/svanm2_moe_stair_sim/run_interactive_sim.py \
  --checkpoint-file xterra_mjlab/checkpoints/svanm2_moe/model_90000.pt \
  --device cpu --track 1 --contact-impratio 10 --record
```

This opens an interactive simulation when run in a graphical session. It does not train. Omitting `--contact-impratio` returns to the scene default 100. For the candidate, explicitly substitute `xterra_mjlab/evaluation_runs/moe_swing013_latest/latest.pt`; do not select by update number alone. Manual keyboard starts need not reproduce the scripted timing.

To reproduce the CPU experiments, choose **new output directories**; the recorder refuses to overwrite evidence:

```bash
CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  xterra_mjlab/.venv/bin/python -B tools/jitter_analysis/verify_current_contract.py \
  --out tools/results/my_flat_recheck

CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  xterra_mjlab/.venv/bin/python -B tools/jitter_analysis/verify_current_contract.py \
  --out tools/results/my_stair_recheck --terrain stairs \
  --cases baseline impratio10 fixed_contact_sub5 --starts -1 0 1
```

The executed recorder snapshot for the stair suite is preserved in [source provenance](../tools/results/deep_audit_20261010/stairs/source_provenance.json). A metadata-only recorder edit occurred after that process imported its module; seven later per-case disk snapshots include the new metadata field, while the process continued executing the preserved original recorder. The control computation and protected controller/scene/checkpoint hashes did not change. Future executions also hash-protect the recorder and experiment script.

The runner explicitly selects CPU inference. It uses the current controller contract; if that file changes later, the run will represent the new contract and must be compared through its manifest. The `fixed_contact_sub5` case still changes the age of legacy derived observations with its internal timestep, so it is not a perfectly isolated integration-only intervention. It is not a recommended viewer replacement.

## 10. What is needed to remove the remaining jitter reliably

**First, establish one measured deployment contract.** Record deployed limits per joint, scales, offsets, signs, history ordering, policy/action timestamps, command shaping, gains, actual firmware servo rate, target delivery delay, and torque/current limiting. The current target constants match important September values, but that is not a full live firmware verification. Recover the exact original/newest training YAML, source snapshots, and dependency versions before a further continuation.

**Second, identify the actuator and contact response with real measurements.** On an appropriately supported robot and within its established operating envelope, use small per-joint excitation and matched standing/walking segments to estimate target-to-q/dq response, latency, coupling, saturation onset, and hysteresis. Log requested/final targets, q/dq, estimated torque/current, IMU, status codes, timestamps, and synchronized terrain/video. Distinguish firmware torque estimates from independently measured torque. Fit on some trajectories and validate on held-out trajectories; a fit to simulator-generated torques cannot identify unmodeled real actuators. Match stance slip, foot loading, impacts, and body response, rather than choosing the simulator contact ratio solely for attractive plots. No robot excitation was performed in this review.

**Third, evaluate residual policy behavior under that fixed contract.** Include standing, ±X/±Y within the intended command distribution, low-speed onset/release, turning, rough ground, and ascent/descent. Retain failures. For stairs measure foot placement and support transitions, yaw/lane error, stall duration, full-foot completion, q/target bands, and torque limiting. Compare original and candidate at the same actual task; do not accept a lower band metric achieved by stopping. Today's six start cases are an initial sensitivity check, not that validation suite.

**Only then choose one training change if needed.** A matched control and one candidate should share the checkpoint, training budget, source, target/contact/delay contract, and evaluation protocol. Log student-specific stair/low-speed reward contributions. Select a hypothesis supported by the residual error: excessive target reversals, poor foot placement/support, or delay robustness. Do not simultaneously strengthen several penalties, change bounds, change foot height, and alter gains again; that prevents attribution. **Discuss the proposal and GPU availability with the user before launching training.**

An acceptable final result must reduce unwanted vibration **while preserving useful tracking and improving repeated full traversal**, then demonstrate the same benefit on measured hardware. We have not reached that standard. The current deliverable is a reproducible simulator mitigation, a clearer causal diagnosis, all failed cases retained, and an explicit identification/evaluation path for the remaining physical problem.

## 11. New user-operated recording: update 91000 at `impratio=10`

Reviewed 2026-10-11 from saved data only. The session is [newest91000_impratio10_20261011_022418](../tools/results/interactive/newest91000_impratio10_20261011_022418/manifest.json); its per-attempt plots and numbers are linked from [attempt 4](../tools/results/interactive/newest91000_impratio10_20261011_022418/attempt_004/plots/index.html). It used the exact newest91000 SHA in the manifest, `impratio=10`, elliptic cone, 5 ms timestep, 20 iterations, legacy observations, kp=18/kd=0.7, and the current tight target bounds. The session closed without recorder errors. No training, new simulation, or GPU work was run for this follow-up.

This is useful as an operator-run demonstration, not as a controlled A/B result. The session contains four reset-delimited attempts: attempt 1 was mostly lateral/turning and never contacted the stairs; attempt 2 reset shortly after first riser contact; attempt 3 lasted only 2.825 s and did not contact a stair; attempt 4 lasted 81.17 s and contains the meaningful stair sequence. Attempt 4 ramps forward to **0.50 m/s**, then adds small yaw commands during the ascent, later turns around and descends, and includes further starts/stops. It was not the planned fixed 0.30 m/s, forward-only trial. Do not compare its whole-session RMS directly with controlled flat runs or infer an `impratio` benefit from it.

The fourth attempt does show meaningful progress: first recorded stair/riser contact is 4.825 s after reset; the robot crosses the 3.6 m stair span, reaches x≈4.07 m and z≈1.55 m, and the log records platform contacts. **The subsequent focused audit independently verifies full-foot completion at 16.265 s after reset**, using loaded-platform, foot-position, lane, tilt, clearance, and 0.5 s hold conditions; see [note 24](24_GATE_FREQUENCY_AND_VLM_AUDIT_20261011.md#6-current-stair-result-stronger-verification-than-the-first-summary). The recorded ascent has a **30.8° peak body tilt** and actual body-forward speed averages about **0.42 m/s** while the request is 0.50 m/s. After it turns around, a later descent segment reaches 19.6° tilt. This establishes an operator-assisted ascent in this setup; it does not establish repeatability or a hardware fix. The interactive recorder itself does not apply the audit's full-foot criterion; the new result comes from the saved-data recheck.

The contact-aligned joint data is more informative than the session aggregate. Using the same Welch 8–30 Hz RMS measure on contiguous physical joint samples, mean measured-joint RMS is about **0.14°** during the pre-contact approach, rises to **0.58°** over the first 3.2 s after first stair contact, remains about **0.49°** over the following ascent interval, and falls to about **0.03°** on the quiet top-platform interval. The whole attempt reports 0.269°. In the first contact interval, the comparable **8–20 Hz** RMS is about **1.90° in the 50 Hz commanded targets** and **0.57° in the 200 Hz measured joints**. Target motion is therefore much larger than the resulting joint motion in that shared band. These bands include gait, impacts, and useful correction; they are evidence of contact-associated oscillatory activity, not a standalone classification of harmful jitter.

Two practical issues stand out for the next experiment:

1. **The impact/recovery transient is the main observed hotspot.** At first stair contact the tilt rises above 26°; during the next eight seconds it peaks at 30.8°. Meanwhile the policy request is already at 0.50 m/s and yaw is being adjusted. Repeat at a fixed 0.30 m/s, zero lateral/yaw command, and identical starting pose before changing gains or rewards. This will tell us whether the large response remains when the operator-induced steering and higher speed are removed.
2. **Target limiting is frequent, while torque clipping is rare.** Across attempt 4 the calf target is clipped in roughly 61% of FL samples and 63% of RR samples; during the initial climb it is roughly 17–18% on FL and 36–38% on RR. Logged torque clipping is negligible overall, with only brief clipping at the first impact. The calf upper target is only 0.284 rad above the front reference pose and 0.246 rad above the rear reference pose. This is a possible reachability/asymmetry contributor to recovery and foot placement, not proof that the physical joint hits its stop. The focused audit also finds high target-clipping fractions during quiet standing, so clipping occurrence alone is not sufficient to explain jitter. Keep the bound unchanged until it is checked against the robot's safe range and the checkpoint's training contract; inspect raw action, requested target, clamped target, and per-joint saturation together.

For a useful follow-up, keep this 91000 checkpoint and `impratio=10`, start from reset, increase vx to exactly 0.30 m/s, then leave vx/vy/yaw untouched through approach, ascent, and a full settling interval. Save this as its own recording. For an eventual 10-versus-100 comparison, repeat the same checkpoint and command schedule with only `impratio` changed, and report contact-aligned RMS, tilt, actual speed, heading, saturation, and full-foot traversal for every repeat. This preserves the user's chosen `impratio=10` result as a recorded condition while preventing an easier-looking simulator trace from being mistaken for hardware validation.
