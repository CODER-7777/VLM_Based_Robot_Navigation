> Historical note. For current commands and decisions, start at [Task 3](../../README.md).

**CHANGES SEPT26_2026**

1.  ![alt text](<../assets/training_plan_20260926_131520.png>)
    ![alt text](<../assets/training_plan_20260926_132043.png>)

So in the above screenshots we can see wher it is failing is shaking o much whole stepping up the stairs so teh ifirstidea i have is to inerese that 50Hz to 100hZ do u suggest to do that ?
2.  While climbing the stairs it is turning so much to cimb and it so we can improve the so we need to give strict penalyt to climb the stairs.
3.  smooth the action outputs 
4.  To decrease jitter in reinforcement learning (RL) policies, you must smooth the action outputs and penalize abrupt control changes during training. Jitter usually happens when a policy switches rapidly between extreme actions to maximize immediate rewards without considering physical constraints. Here are the most effective strategies to eliminate policy jitter, grouped by implementation layer: 1. Reward Shaping (The Most Common Fix)You can directly incentivize the agent to choose smooth transitions by adding penalties to the reward function. Action Difference Penalty: Penalize the absolute or squared difference between the current action and the previous action:\(R_{penalty} = -w \cdot \Vert{}a_t - a_{t-1}\Vert{}^2\)Action Magnitude Penalty: Penalize excessively large actions if the agent only needs minor adjustments:\(R_{penalty} = -w \cdot \Vert{}a_t\Vert{}^2\)Torque/Derivative Penalties: In robotics, penalize high acceleration, jerk, or rapid torque changes.

Reduce Entropy Regularization: A high entropy coefficient forces exploration by adding noise. Lowering it late in training helps the policy settle into a stable, deterministic routine.
Tighten PPO Clipping: If using PPO, reduce the clipping parameter (e.g., from 0.2 to 0.1) to prevent massive policy updates that cause erratic shifts.

Add an action smoothness reward, which penalises the second derivative of the actions (you can approximate this by the current, previous and second previous actions.)

You can add a PD or PID controller after your agent has chosen an action (For example a simple PD controller with a proportional gain of 1 and derivative gain of 0.05)

You can add a low-pass filter after your outputs. (I wouldn’t recommend this, because in my experience it really limits the performance of the agent, however it can decrease jittering the most.)

In order to evade this, you need to evaluate if a path in the future ( path planning ) will have a greater reward than if you continue to do nothing. And if it ever chooses to do nothing, you need to sleep.

Oh and some forgiveness on motor control is helpful too ( like if the amount of change in the left/right /forward is less than .2% maybe don't do anything.

so theese are some of the susggestions from my side once evaluare them se the we need to fix whiel trianing from the 90000.pt model and also 




# MoE 90k simulation / hardware jitter audit — 2026-09-21

**The documented stair simulator was not equivalent to the tested robot.** A separate, reproducible simulator now matches the deployed observation/action contract, target bounds and command shaping. It reproduces oscillatory targets, calf saturation and straight-command stair failures. These findings support a policy–actuator–contact interaction, but do **not** establish one exclusive cause of the hardware jitter.

No robot connection, motor command, firmware change, safety change, policy deployment or retraining was performed. The ongoing hardware session was not interrupted. Concurrent edits to the original simulator were preserved; the corrected implementation is [svanm2_moe_hardware_audit](../../../svanm2_moe_hardware_audit/README.md).

Open [videos and plots](../index.html). The most useful comparisons are the [hardware angle curves](../hardware_joint_angles.png), [simulated 15 cm stair curves](../sim_angles_stairs_up_15_forward.png), [terrain comparison](../terrain_comparison.png), [ablation comparison](../ablation_comparison.png), and [15 cm stair video at half speed](../videos/stairs_up_15_hardware_forward_half_speed.mp4).

## What was wrong or unverified

| Item | Documented/original simulator | Hardware and corrected audit |
|---|---|---|
| Policy | Original MoE 90k | Same weights confirmed by replay; no checkpoint substitution |
| History | Five frames, oldest first into TorchScript | Correct: deployed ONNX adapter accepts newest first and reverses internally |
| Calf target upper bound | **+0.50000 rad** | **−0.88776 rad**; difference 1.38776 rad / 79.5° |
| Other target limits | Hip ±1.0472, larger thigh range | Hip ±0.735; asymmetric front/rear and left/right thigh bounds from deployed adapter |
| Observation/action | Mostly correct mathematical layout | Verified against the frozen deployed adapter; raw clipped action remains history feedback after target clamping |
| Commands | Latched keyboard increments; simultaneous axes independently capped | Actual operator shaper: deadzone, neutral/X enabling, shared input budget, slew and release; caps 0.5 m/s forward/back, 0.6 m/s lateral, 0.4 rad/s yaw |
| Timing | Immediate 50 Hz inference; physics and PD both 200 Hz | Separate physics resolution, 200 Hz external PD and 50 Hz policy; nominal 5 ms delivery delay, 0/15 ms sensitivity tests |
| Sensors | Position advanced by `mj_step`, sensor arrays could still describe the preceding integration state | Explicit sensor refresh before each observation |
| Reset | Position/velocity/history reset without clearing all MuJoCo state | `mj_resetData` clears time, control and warm-start state |
| Invalid action | Quietly replaced with zero raw action | Raises an offline failure; not treated as a valid policy output |
| Stair validation | One second at 0.15 m/s starting 1.5 m before stairs | Actual foot-contact and full-foot traversal checks; lane exits and stalls are failures |
| Contact stiffness | `solref=.002` claimed to create 2 ms contact dynamics at 5 ms physics | Effective lower bound is 10 ms in that configuration; explicit 10 ms baseline and separate stiffness experiment |
| Friction | Floor/stair coefficients suggested separate foot friction | Priority-1 feet override lower-priority terrain parameters; low-friction test changes the effective foot value |
| Physical plant | Widened physical ROM, unspecified correspondence to robot | ROM, friction, inertia, payload, backlash and servo details remain unmeasured assumptions |

MuJoCo enforces a positive contact timeconstant of at least twice the timestep by default; contact priority determines which geom's friction and solver parameters apply. Those rules explain the contact discrepancies above. [MuJoCo 3.6 modelling documentation](https://mujoco.readthedocs.io/en/3.6.0/modeling.html#solver-parameters).

The model mass is 10.0575 kg. A calibrated payload mass was not available. Real bridge updates are configured at 500 Hz; the actual motor firmware's internal PD rate remains unverified. The audit uses 200 Hz external PD with held torque between integration substeps; it does not pretend this is a measured motor model.

The rollout initializer is intentionally documented: native Stand hold, then a three-second linear blend into MoE. It does not reproduce folded calibration, the complete deployed startup/recovery state machine, quintic handoff, A/B cycling, harness forces or DDS. The final three seconds of the blend are excluded from moving-window metrics. This is a locomotion audit, not a full commissioning emulator.

## Hardware evidence

Two saved runs were examined:

- **Original reported jitter/tip run:** 4,141 samples at approximately 20 Hz. MoE-phase peak tilt is 72.6°. The record cannot resolve 8–30 Hz jitter because its Nyquist frequency is about 10 Hz. [Original incident angles](../original_incident_joint_angles.png), [incident timings](../original_incident_summary.json).
- **Later full-control run, reported smoother:** 122,607 samples, approximately 200 Hz, and 30,175 exact policy input/output records. This is the main high-frequency analysis source. Terrain labels and synchronized hardware video were not recorded; its worst windows must not be labelled “flat ground” or “stairs” from joint data alone.

During commanded motion in the later run, 8–30 Hz measured-angle RMS was approximately **0.19–0.45° per joint**, with calves highest. Sent-target RMS in the same band was **0.63–1.84°**. The largest four-second angle window was **465–469 s**, approximately **0.87° RMS across all joints**. This band is a useful oscillation indicator, not a definition of all unwanted movement: normal gait harmonics and impacts also contribute.

Across separate four-second moving windows, measured-angle oscillation correlates strongly with target oscillation (**Spearman 0.962**), but weakly with maximum control interval (**0.154**), sensor age (**0.020**) or action age (**0.097**). This makes a persistent target/closed-loop response more plausible than isolated scheduling stalls as the dominant explanation in this recording; correlation alone is not causal proof.

Reported dq matches differentiated, low-pass-filtered q: fitted scale **0.993–1.008**, correlation **0.9976–0.9996** across joints. No evidence supports a velocity-unit or sign error. Timing was 198.88 Hz mean, 5.91 ms p99 interval, 12.67 ms maximum; sensor age p99 1.66 ms, action age p99 16.73 ms.

Calf targets sit on deployed limits for **17.7%, 20.0%, 19.4%, 64.8%** of moving samples, respectively FL/FR/RL/RR. Rear-right saturation is especially asymmetric. These fractions are commanded-target occupancy, not proof of physical joint-stop contact.

The saved motor power messages also contain nonzero `fault` values **98, 99, 100 and 102** in **500 rows**, including **422 motion rows**. They are repeated telemetry samples, not 500 independent faults. HF angle RMS was about **0.69° on those motion rows versus 0.32° on other motion rows**, without matching for terrain or command. Firmware-specific meanings remain unresolved; neither mechanical failure nor harmless status can be inferred from the integers. Actuator involvement cannot be ruled out.

One additional mismatch is the **command distribution**: the saved 90k training configuration samples lateral velocity only in **±0.3 m/s**, whereas the expanded hardware profile allows **±0.6 m/s**. Its curriculum expands forward speed, not lateral speed. In two paired flat-ground tests, reducing only the simulated lateral command from 0.6 to 0.3 m/s reduced HF angle RMS from about **0.61° to 0.43°**; yaw drift remained. This supports treating maximum sideways operation as extrapolation, not a capability demonstrated by training. No hardware limit was changed.

## Mathematical interpretation

For each leg, the implemented belt model is

```
J = [[8,0,0], [0,8,0], [0,8,16]]
tau_motor = diag(kp / gear²) J (q_target − q)
            − diag(kd / gear²) J dq
tau_joint = Jᵀ tau_motor
```

At kp=20 and kd=0.7:

```
K_effective = [[20,0,0], [0,25,10], [0,10,20]]
D_effective = (0.7/20) K_effective
```

Thus thigh and calf are coupled; effective stiffness is **not** simply `20 I`. This coupling agrees better with hardware estimated torque than a diagonal model: thigh torque-estimate RMSE is roughly **0.69–0.83 Nm**, versus **1.66–2.88 Nm** for diagonal PD. This validates retaining the coupling, not removing it as a jitter “fix.” Torque is estimated telemetry, not an independent load-cell measurement.

The target is `clip(q0 + scale * clip(action, −6,6), deployed_bounds)`. Hardware applies piecewise-held targets at nominal 50 Hz. Saturation changes extension, produces target plateaus and changes the subsequent observations; the policy's previous-action input still contains the pre-target-clamp raw action. Clipping itself is continuous and cannot amplify instantaneous input differences; the concern is the resulting **closed-loop** interaction and training/deployment mismatch, not a claim that clipping intrinsically creates jumps.

The MoE encoder uses **eight continuously weighted experts**, not hard argmax switching. Recorded gate changes track action changes, but that does not identify gating as the cause. Removing dq from recorded observations changes raw output by 0.196 RMS in an open-loop replay; it is a sensitivity check, not a proposed fix or a valid closed-loop replacement.

All **30,175 hardware policy outputs** were reproduced from their exact recorded histories: max absolute raw-action difference **2.29e−5**, RMS **7.73e−7**, within the existing relative/absolute tolerance. All 34 export fixtures passed as well. Wrong weights and reversed history are not supported explanations.

A further plant uncertainty is torque saturation. Hardware estimated thigh torque occasionally exceeds the simulator's 12 Nm joint clamp, reaching about **23.2 Nm**. A belt-coupled motor-space clamp permits a larger combined thigh torque. Its alternative model was tested, but no variant made stair ascent reliable. Telemetry peaks and fits do not establish the exact firmware saturation law, so this remains a named sensitivity option rather than silently changing the default.

## Terrain and fix experiments

**120 offline rollouts** were completed. Main comparisons use two deterministic starts per terrain, 24-second episodes, 0.5 m/s forward ceiling, and explicit release at 20 s. The 24-second horizon is only a simulation experiment; no hardware session timer was changed. All simulation outcomes are retained, including failures. A >60° tilt is the offline failure criterion. Lane departures do not count as traversals.

At the original 5 ms physics resolution, with deployed target bounds:

| Terrain / command | Outcomes across two starts |
|---|---|
| Flat forward, lateral, turning, combined | Upright in both starts of each case; substantial yaw drift during lateral motion remains |
| 3 cm rough tiles | 2/2 traversed |
| 10° downslope, 20° downslope | 2/2 traversed each |
| 10° upslope | One traversal, one tip |
| 20° upslope | One lane exit, one tip |
| 10 cm stairs down | 2/2 traversed |
| 15 cm stairs down | One traversal, one tip |
| 18 cm stairs down | 2/2 traversed; not proof that larger steps are easier |
| 10/15/18 cm stairs up | **0/2 valid traversals at each height**; stalls, turns, lane exits and tips |
| 10° cross-slope, low-friction flat | Upright, but pronounced drift/turning; not reliable tracking |

Only two starts were tested per main case; these are examples, not success-rate estimates. Stair height is not ranked from this small, sensitive sample. Relaxed legacy targets also fail stair cases, so target-limit mismatch is not the sole explanation. Straight-command stair runs reproduce large uncommanded heading changes, without any terrain perception input.

The films show the front feet meeting a riser while the rear feet remain lower, repeated leg-extension corrections, body rotation and—in the selected 15 cm case—a tip. This resembles the reported behaviour but is not a reconstruction of the exact hardware stair geometry/contact history.

| Offline change | Flat HF RMS, mean over two starts | Interpretation |
|---|---:|---|
| Baseline | 0.546° | Reference |
| Target filter, 20 ms | 0.507° | About 7% lower; forward tracking error increases; both 15 cm stair cases tip |
| Target filter, 40 ms | 0.802° | About 47% higher; added feedback lag can worsen joint oscillation |
| Physics 1 ms, same contact constant and 200 Hz PD | About 0.42° | Strong numerical sensitivity; not a hardware fix |
| Physics 0.5 ms | About 0.46° | Further change remains; exact convergence is not established |

At a 5 ms timestep, requesting `solref=.002` reproduced the explicit `.010` baseline, as expected from MuJoCo's lower bound. At 1 ms, `.002` becomes a different, much harder contact model and changes gait/jitter substantially. Do not tune contact stiffness just to obtain an attractive video.

Full outcomes, timing, clipping, tracking errors and contact data are in [suite_summary.csv](../suite_summary.csv) and [suite_summary.json](../suite_summary.json). Per-run XML and `trace.npz` files are under `runs/`. Main videos use the 5 ms baseline so they correspond to that comparison, not a selectively chosen smoother physics variant.

## Changes to make next, in order

1. **Use the corrected contract in evaluation and training.** Cover the intended ±0.6 m/s lateral command distribution explicitly, or evaluate within the trained ±0.3 m/s range while diagnosing; current maximum lateral commands exceed the saved training range. Keep the deployed bounds; do not copy the simulator's +0.5 rad calf allowance to hardware. Include command shaping, measured delays and target saturation in training rollouts. Preserve raw-action history semantics unless deliberately retraining a changed observation contract.
2. **Resolve the actuator model before attributing everything to rewards.** Decode the installed firmware's status fields, establish torque-limit semantics, identify loaded delay/damping/friction and add timestamped terrain/contact video to future logs. Current saved data cannot identify all of these quantities.
3. **Do not deploy either smoothing experiment yet.** The modest flat-ground improvement did not generalize to stairs, and 40 ms smoothing increased oscillation. A lower HF metric with stalled/diverted motion is not a fix.
4. **If fine-tuning is needed, resume 90k rather than restart training.** The saved training configuration already has action-rate penalty **−0.1**, foot-slip penalty **−0.1**, foot-clearance penalty **−2**, soft-landing penalty **−1e−5**, and joint-limit penalty **−1**. Adding duplicate penalties without checking their evaluated magnitude is not justified.
5. **Candidate reward ablations:** penalize normalized physical target second differences, `|| (q_cmd[t]−2q_cmd[t−1]+q_cmd[t−2]) / scale ||²`, and saturation pressure, `|| (q_raw_target−q_cmd) / scale ||²`. Consider a bounded joint-acceleration term only after sensor/numerical consistency. Compare one change at a time against velocity tracking, full stair traversal, foot slip/clearance, falls and existing reward contributions. Do not aggressively punish all contact acceleration, which could suppress required stair-lifting effort. No reward code or training run was changed in this audit.

## Reproduction and limits

Five contract tests pass: deployed-adapter observation/action parity, raw-action history preservation, full physics reset, actual operator shaping/release, and stair geometry. Saved hardware replay separately passes all 34 fixtures and 30,175 recorded frames. All 120 final rollouts completed without a process error; failed physical behaviours are reported rather than filtered out.

The old one-second stair “test” is not used as locomotion evidence. Initial batches interrupted by concurrent source edits are archived separately and excluded. `pre_sensor_refresh_runs/` is exploratory and excluded from final tables. The final report uses only `runs/` and its frozen asset/policy copies. See [implementation instructions](../../../svanm2_moe_hardware_audit/README.md) and [manifest](../manifest.json).




/home/vivekananda/UGP_1_VLM/VLM_Based_Robot_Navigation/Task_3/moe_jitter_audit_20260921
int his we hav the suite summatry once als read this and atellme wwhat are fesible and meaning gul changes we cahn do an also tel me wher to whe to ake changes i will do them manually