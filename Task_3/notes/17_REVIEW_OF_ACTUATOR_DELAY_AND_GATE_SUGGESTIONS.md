# Which research suggestions should we use for our MoE jitter problem?

## Latest follow-up: +Y 0.30 m/s, equal four-second comparison

Reviewed actual recordings `comparison_y030_20261005_021830` on 2026-10-05. The existing eight-second comparison is incomplete: original provides 7.12 seconds and candidate 4.52 seconds after settling. Preserve that report, but compare [equal four-second windows](../tools/results/interactive/comparison_y030_20261005_021830/comparison_equal4s/index.html), with [exact metrics](../tools/results/interactive/comparison_y030_20261005_021830/comparison_equal4s/comparison.json). Both selected windows are complete, have matching recorded control/scene settings, and have no prior or current stair contact. Manual ramps and gait phase can still differ; this is one pair, not a general success estimate.

| Metric at requested vy +0.30 m/s | Original90000 | Candidate91000 |
| --- | ---: | ---: |
| Mean actual body vy | 0.1969 m/s | 0.2103 m/s |
| Sideways tracking RMSE | 0.1079 m/s | 0.1067 m/s |
| Joint 8–30 Hz RMS | 0.2768 degrees | 0.3801 degrees |
| p99 largest-joint target jump per 20 ms | 18.43 degrees | 26.46 degrees |
| Normalized target second-difference cost | 0.7959 | 1.3800 |
| Heading change with zero yaw-rate request | -6.21 degrees | +12.30 degrees |
| Target-clamped fraction | 0 | 0 |
| Any-joint torque-clipped fraction | 0.125% | 0 |

**Meaning:** at +Y 0.30 the candidate moves slightly faster, but joint-band vibration is approximately 37% higher, p99 target jumps 44% higher, and target second-difference cost 73% higher. Its maximum target jump is essentially unchanged (33.70 versus 33.68 degrees). The candidate's near-standing smoothness at +Y 0.15 does not demonstrate a smooth moving gait. Neither target clamping nor frequent torque limiting explains these specific flat windows. Useful stepping can also produce target changes; a penalty is a soft preference, not a guarantee that target changes decrease in every evaluation.

**Recommended next work, before changing training:**

1. Repeat +Y 0.15 and +Y 0.30, then test negative Y in fresh processes. Keep checkpoint, limits, sensing, gains and contact settings fixed; hold each request at least 12 simulation seconds. Compare tracking and heading alongside vibration, keeping stalls and failures.
2. User observations: at 0.15 does the candidate stop stepping despite the request? At 0.30 is shaking strongest at touchdown, during loaded stance, or while a foot is in the air? Does it rotate despite zero yaw request? Which leg is visibly affected? Measurements come from raw logs; the user need not estimate velocities by eye.
3. Inspect the candidate run's saved `env.yaml` and TensorBoard `RewardRate/track_linear_velocity`, `RewardRate/action_rate_l2`, `RewardRate/target_second_difference_l2`, `RewardRate/target_rate_excess_l2`, and `RewardRate/target_saturation_l2`. Also check angular tracking, clearance and pose contributions. Current logging averages teacher and student environments together; those averages alone cannot identify the student reward balance. A future diagnostic logging change should separate these groups using the actual algorithm's environment split.
4. First training experiment to consider: simplify overlapping smoothness objectives, testing removal of the added time-rate penalty while keeping second-difference and saturation weights, tracking, limits, clearance and all other settings fixed. Resume independently from preserved 90000, rather than chaining from the current candidate. This tests redundancy; it is not a claimed fix. Check the saved original continuation configuration and the existing candidate control before launching.
5. If repeated low-command stalls and student reward contributions support weak movement incentives, tune horizontal velocity tracking separately from vertical-velocity costs. The current combined tracking kernel penalizes both, so blindly narrowing its standard deviation can interfere with stair ascent. Do not choose a new weight without checking the reward budget.

No controller, reward, policy, training or server code was edited for this follow-up. Only offline plots/metrics and this existing note were written. No gate-frequency or actuator-gain change is justified by this pair alone; the policy remains a valid subject of investigation.

## Latest result: original90000 versus newest91000, +Y 0.15 m/s

Reviewed the actual user-recorded pair `comparison_y015_20261005_015702` on 2026-10-05. [Open the comparison](../tools/results/interactive/comparison_y015_20261005_015702/comparison/index.html) or [exact metrics](../tools/results/interactive/comparison_y015_20261005_015702/comparison/comparison.json).

**Conclusion: the candidate is smoother, but tracks sideways movement worse and nearly stops. This is not a successful overall fix.**

The original is the preserved 90000 SHA `440bbb28...`; the candidate is newest91000 SHA `dec9775d...`. Current checkpoint files match both recording hashes. Both recordings are closed; replay and P/D checks pass. Initial recorded state, control/scene settings and observation timing match. Both selected windows last eight seconds at `[vx=0,vy=0.15,yaw=0]`; both have no prior/current stair contact and no target clamping. The actual keyboard input also remains unchanged in these windows. This checks recorded evaluation conditions, not identical original training conditions or identical manual command ramps.

| Metric, equal eight-second windows | Original90000 | Candidate91000 | Observation |
| --- | ---: | ---: | --- |
| Mean actual body vy | 0.0491 m/s | 0.0206 m/s | Candidate 58.1% slower; both substantially below requested 0.15 |
| Sideways tracking RMSE | 0.1107 m/s | 0.1335 m/s | Candidate error 20.7% higher |
| Joint 8–30 Hz RMS | 0.1470° | 0.0512° | Candidate rapid motion 65.2% lower |
| Largest target jump per 20 ms | 22.88° | 10.81° | Candidate 52.8% lower |
| p99 largest-joint target jump | 11.70° | 5.93° | Candidate 49.3% lower |
| Normalized target second-difference cost | 0.1643 | 0.0222 | Candidate 86.5% lower |
| Heading change, yaw-rate request zero | +0.74° | +8.64° | Candidate accumulates more turn in this interval |
| Maximum tilt | 1.53° | 1.84° | Both remain upright; neither falls |
| World Y displacement | 0.390 m | 0.163 m | Ideal straight displacement at 0.15 for eight seconds is 1.2 m |
| Fraction with abs(body vy) <0.01 m/s | 28.1% | 66.8% | Candidate spends much more time nearly stationary |

**Read the graph:** panel 2 is the key. Orange candidate vy decays almost to zero even though the black requested line stays at 0.15. Panel 4 then shows almost no candidate target changes. Panel 5 shows its accumulated heading drift. Lower target/joint variation cannot be interpreted independently of its reduced movement.

In the **last five seconds** of the selected candidate window, mean vy is only **0.00224 m/s** and the largest target jump is **0.0702°**. Its joint-band RMS is nearly zero. The original continues intermittent movement, averaging 0.0408 m/s there. In the first three seconds the candidate also has lower joint RMS (0.0952 versus 0.1786°), but those are not matched actual-speed/gait trajectories; neither fact identifies one reward as the cause.

**Interpretation:** the combined training changes may have encouraged a low-motion solution at small commands, or altered when gait starts. This pair supports a smoothness/tracking tradeoff. It does not identify which individual penalty, clearance change, learned representation or changed training conditions caused it. Low gate activity in the candidate can accompany near-standing; it does not prove a gate-chattering problem was solved. Target saturation is absent here, and torque clipping is negligible (original 0.0625% of samples, candidate zero), so bounds or torque clamping are not supported explanations for this specific low-speed stall.

**Specific reward question to investigate:** current local `env_cfgs.py` sets tracking weight 6 and `std=sqrt(0.25)=0.5`. Installed `mjlab/tasks/velocity/mdp/rewards.py:track_linear_velocity` uses `exp(-(xy_error + vz²)/std²)`. In the illustrative case vx=vz=0, requested vy=0.15 and actual vy=0, standing receives `exp(-0.15²/0.25)=0.914` of the maximum tracking term; perfect tracking receives 1. That is a relatively small tracking reward gap at a low command, which can compete with smoothness/effort/pose terms. This is a hypothesis grounded in the current formula, not measured server reward contributions or a proof of the candidate's training objective balance. Check the run's saved env.yaml and teacher/student-specific contributions before editing. Narrowing this std also changes vertical-velocity penalties and can affect stair stepping; do not tune it blindly.

**Next:** retain this pair, do the same +Y 0.30 pair (A six taps, `--command 0 0.30 0`), then −Y 0.15 and −Y 0.30, in fresh processes with 12-second steady requests. Repeat before claiming consistency. If the candidate tracks higher requests but stalls at 0.15, investigate low-speed movement onset/reward balance. If it also tracks 0.30 poorly, investigate broader training/evaluation and student performance. Do not strengthen smoothing, retrain from scratch or change gate frequency based only on this pair. No runtime/training/server code was changed during this review; only this existing note and an explanatory block on the generated dashboard were updated.

## 2026-10-05: actual sideways data and deeper policy spike review

**The policy is not ruled out.** Verification that the right weights load and that replay reproduces them says nothing about whether those weights produce good control. The current recordings show substantial physical-target jumps and poor disturbed-state tracking. Changing gate frequency alone is not yet justified: the gate, expert features, direct actor inputs and contacts all participate.

Read the [new sideways policy-spike page](../tools/results/interactive/sideways_91000_20261005_011859/attempt_001/plots/policy_spike_review.html) and [the older stair-run policy-spike page](../tools/results/interactive/91000/test_2/attempt_001/plots/policy_spike_review.html). The reusable source is [inspect_policy_spikes.py](../tools/jitter_analysis/inspect_policy_spikes.py). It reads original chunks and verifies checkpoint SHA, actual five-frame inference, mapped targets and existing decomposition checks. No physics rollout, training, controller edit, target-limit edit or server operation was performed. New plots/JSON/HTML stay inside each attempt's existing `plots/` folder.

### What the velocity plot actually means

- Black vx/vy/yaw curves are user requests, fed into the policy. Blue velocity curves are measured simulator motion. The network does **not** output these velocities: it outputs 12 numerical position actions, transformed into joint targets, then coupled PD torques. Ground/contact forces also change motion. [MuJoCo equations of motion](https://mujoco.readthedocs.io/en/stable/computation/index.html#general-framework).
- A 73-second overview compresses gait cycles, brief impacts, stopping and falling into dense spikes. Spiky appearance does not establish the frequency. Joint vibration and body-speed variation need separate spectra.
- In the new steady 0.45 m/s lateral window, lateral-speed RMS is about 0.0545 m/s at 0.5–below 8 Hz and 0.00804 m/s at 8–30 Hz. The largest horizontal-speed spectral peak is around 1–2 Hz. That does not excuse tracking error; it means suppressing all visible velocity variation would also penalize gait motion.

### Measurements from the actual runs

| Recording/window | Observation | Interpretation and limits |
| --- | --- | --- |
| Old `91000/test_2`, 6.58–10.335 s, vx=0.30 | Joint 8–30 Hz RMS 0.438°; largest joint target jump 35.82°/20 ms | Flat approach already has vibration and rapid targets. A target jump is a requested change, not measured joint rotation in 20 ms. |
| Old `91000/test_2`, 11.14–14.98 s, vx=0.50 | Joint RMS 1.851°; largest target jump 109.45°/20 ms; torque clipping on any joint in 16.4% of physics samples | Severe disturbed motion, strong target reversals and limited control authority. Speed command also differs from approach, so this is not a matched terrain-only comparison. |
| New `sideways_91000_20261005_011859`, 52.84–56.92 s, vy=0.45 | No stair/non-foot contact; joint RMS 0.721°; target jump 70.57°/20 ms at 53.94 s, RL calf | Stairs are not necessary for rapid target changes. This request exceeds saved ±0.30 m/s training range. The target jumps −52.77→−123.34° and is not target-clamped there. |
| Same new session, 66.82–86.52 s, vy=0.60 | No stair contact; joint RMS 0.521°; max target jump 46.39°/20 ms; mean body vy=0.477 m/s | Sideways tracking error and vibration persist on flat ground. This is outside the saved lateral training range. |
| Same new session, vy=0.10 for 2.2 s | Mean body vy≈0.009 m/s; negligible joint HF motion | Smooth standing does not mean successful tracking. Long steady ±0.15/±0.30 trials are still needed; the recorded 0.30 requests last only about 0.2 s. |

`09_spike_chain.png` is a two-second zoom. Its red marker is the selected speed-change interval, **not** the first stair contact. Rows show requested/actual speed, foot/non-foot forces, one joint's target/actual angle, requested/applied torque, gates and policy-input sensitivity. Forces at t act during [t,t+5 ms]; the next recorded velocity is at the end of that step.

At 79.735 s in the new flat-sideways recording, vy changes approximately 0.461→0.541 m/s during one 5 ms step. There is no policy tick at the start of that step, while front-foot contact loads total about 387 N. This establishes that an instantaneous velocity jump can occur while the target is held. It does **not** establish that preceding policy targets played no role in the landing.

At 64.50 s in the old stair recording, a non-foot collision reaches about 986 N. That interval is part of a severely disturbed/failing maneuver, not a representative flat-walking sample. Raw actions are already very large before it (max absolute ≈312 at 64.48 s), and reach ≈341 at 64.52 s; commands are clipped to ±6 before scaling. Those raw outputs are poor disturbed-state behavior deserving investigation, but they do not mean 341 radians or a 341 m/s velocity request.

### What the deeper MoE/actor probe found

The actor receives **32 normalized mixed-expert values plus 45 latest-frame values**. Therefore, q/dq/gyro and the previous clipped action can influence the actor directly, without first changing gate weights. The latest frame contains no measured linear velocity or explicit contact-force input.

The new tool holds one branch at its previous value for **one offline inference**, keeps other branches current, and maps the alternate output through raw clipping, action scaling and final target bounds. This reports sensitivity in physical-target degrees. It is not an additive attribution, a high-frequency amplitude or a prediction of a modified controller's future trajectory. An input change can be useful gait feedback rather than noise.

| Window | Previous-action branch probe | Gate-hold probe | Expert-feature-hold probe | dq branch probe |
| --- | ---: | ---: | ---: | ---: |
| Old flat approach, vx=0.30 | 2.67° RMS | 2.25° | 1.81° | 0.82° |
| Old post-contact, vx=0.50 | **11.09°** | 3.15° | 5.70° | 4.96° |
| New sideways, vy=0.45 | **4.65°** | 1.65° | 2.53° | 1.60° |
| New sideways, vy=0.60 | **3.78°** | 1.73° | 2.74° | 0.97° |

The previous-action input is the strongest of these one-step branches in these windows. A specific hypothesis is that the learned action-feedback/gait update overreacts after contact disturbances. The gate is also influential and remains under investigation. Neither result proves which branch initiated the motion. `10_policy_probes.png` places these sensitivity values beside velocity spectra. The pre-normalization mixed latent does not approach zero in these windows, so no evidence here supports division by a near-zero latent as the source.

Optional original-90000 weights were also evaluated on the **same recorded candidate inputs**, including candidate previous actions. At 63.7–64.8 s they also produce very large raw values (max≈370 versus candidate≈341); flat-sideways maxima are similar. This is not the original policy's own rollout and cannot compare stair success. It weakens a claim that only the new fine-tuning introduced this response to those states.

### What to do next, before more training or changing gate frequency

1. Record fresh-process original90000 and newest91000 trials at vx=0.30 and at vy=+0.15, −0.15, +0.30, −0.30, yaw-rate=0. Keep each request steady for 10 simulation seconds. Keep sensing, limits, contact model and gains identical. Keep actual failed attempts. Classify flat intervals from contact logs.
2. Compare target jump/rate/second differences, q vibration, force peaks and tracking together. Current second-difference and rate penalties are **soft costs**, not hard limits; observed large jumps are possible even when those penalties are enabled.
3. In training review student-specific tracking/smoothness and clipping alongside teacher/student learning losses. Existing aggregate reward logs average the teacher/student environments and can hide poor student behavior. The local adapter clips raw network actions before passing them to the environment, so current environment penalties cannot distinguish raw +6 from +300 when both become +6. A raw-output excess objective would require explicit learner-side support or a deliberate change to that interface; simply increasing target saturation weight does not address that invisible difference.
4. Perform separate short closed-loop diagnostic interventions on the previous-action/actor response, gate temporal response and actuator/sensing timing. An offline branch probe is not such an intervention. Suppressing legitimate previous-action or gate changes can ruin stepping, so do not edit the deployment architecture just because a probe has a large value. Select the intervention based on whether it reduces rapid motion **and** retains tracking/support.
5. For real hardware, use verified physical/deployed target limits and a training/evaluation model of that same contract. Current controller values are the simulation-wide hips ±1.0472 and calf +0.500 upper. The supplied audit reports deployed hips ±0.735 and calf upper −0.88776. The audit is evidence to cross-check against the actual adapter/mechanism, not authorization to deploy +0.500 because a simulation climbs better. No bounds were changed in this analysis.

## Read first: corrections to the proposed three-cause explanation

Updated 2026-10-05. Flat-ground and sideways shaking belong in this investigation; stairs can amplify an existing problem without being necessary for it. Timing, held targets and changing gate weights are plausible mechanisms to test, not three established root causes.

1. **Observation timing:** the viewer reads already-integrated joint `qpos/qvel` together with derived orientation/gyro fields that can describe the preceding physics state. It is a mixed-time observation, not a uniformly 5 ms old joint-angle/velocity reading. The PD calculation itself reads current `qpos/qvel` every physics step in `controller.py:physics_step`. Therefore, the claim that its angle error necessarily uses an old joint angle is incorrect. Refreshed observations change the policy input, not that PD read. The October 2 candidate results increased from 0.331→0.451° on flat and 0.833→0.946° on stairs; this establishes sensitivity to sensing, not proof that the legacy timing is the exclusive jitter cause or that refreshing is a successful cure. Command-delivery delay is a separate issue: training configures delayed targets, while the viewer applies targets without that randomized delay buffer. The local training environment calls `sim.forward()` before actor observation computation. [MuJoCo compute-then-integrate documentation](https://mujoco.readthedocs.io/en/stable/programming/simulation.html#simulation-loop).

2. **50 Hz policy / 200 Hz PD:** this is ordinary sampled control, not automatically a frequency mismatch. The PD torque is recomputed even while targets are held. An instantaneous target change does change the proportional torque term, so target-update effects deserve a controlled test. However, 8–30 Hz joint RMS cannot by itself prove a 50 Hz update-induced vibration. A sampled controller can interact with a plant at other frequencies, so weak 50 Hz motion does not eliminate this hypothesis either. Keep the gate and policy at their trained 50 Hz while gathering evidence; lowering either changes temporal behavior and may add delay. At 50 Hz, gate-weight spectra can resolve only frequencies below 25 Hz. The update frequency and the gate signal's dominant oscillation frequency are different quantities.

3. **Filtering claim:** `notes/12_REVIEW_OF_SMOOTHNESS_AND_MOE_REPORT.md` contains a table headed **Supplied claim / Correction supported by current evidence**. “Filtering was categorically disproved” is in the supplied-claim column and is explicitly corrected in the next column. The old audit reports particular fixed-policy filters: 20 ms slightly reduced flat RMS but worsened tracking and the tested ascents; 40 ms increased flat RMS. Their failure proves neither that all filters fail nor that the original target-update rate caused the baseline jitter.

4. **Gate decomposition:** 0.2576 / 0.4640 / 1.0084 are RMS contributions to **raw neural-output differences per update**, before clipping and position scaling, in one newest-candidate post-contact window. They are not measured mechanical vibration, high-pass-filtered noise amplitudes or percentages. They indicate substantial sensitivity through the actor's direct latest-frame input. They do not establish sensor noise or that the largest contribution is the physical root cause. The 45 values are an input branch to the actor, not the final fully connected layer. Normal gait feedback changes them too. The MoE continuously blends eight latent features; argmax changes are not actual hard routing. Hold-filtering a gate can also interfere with appropriate terrain or gait adaptation.

**Sideways protocol:** analyse actual supplied traces with `vx=0`, `vy=±0.15` then `±0.30 m/s`, and yaw-rate request 0, distinguishing the startup ramp from steady movement and keeping all failed attempts. Stay within the saved ±0.3 m/s training range for the initial comparison; label ±0.6 m/s separately as outside that range. Check actual body-frame vy, lateral tracking error, heading, q/dq, targets, individual torques, floor contacts, gate weights and spectra. Absence of stair contact is not absence of foot-ground contact. Compare legacy/fresh sensing with matching commands/checkpoint/limits/contact settings before separately testing target interpolation or a gate temporal modification. A 0.3 m/s requested sideways speed can drift into a stair: use foot-contact geometry, not the requested direction, to classify flat intervals.

At the earlier check, no new Y-direction session was present: newest remained `test_swing013_91000`. Its recordings have zero vy requests. The Y commands in `91000/test_2` begin around 48.4 s, after first stair contact at 10.335 s, and therefore are not a clean flat-sideways example. Recording support was then added. **The new actual sideways session has now been analysed in the section above.** The positive/negative recording test confirms policy-tick sampling and that instrumentation leaves baseline physics unchanged. See [the recording instructions](19_RECORD_MY_INTERACTIVE_RUN.md). No controller, gate, gain, training or frequency change was made.

## 2026-10-05: newest recordings, 50 Hz holds, gates and actuator response

Read the [new offline dashboard](../tools/results/interactive/update_gate_review_20261005/index.html) and [reusable tool instructions](../tools/README.md). Original raw recordings were read; no new simulation, training or runtime control change was made. All four recorded histories replayed against their matching checkpoint within documented floating-point tolerances. P/D torque reconstruction and additive raw-action decomposition passed independently. The 20 Hz synthetic signal RMS and constant-command/contact boundary checks passed.

**Checkpoint distinction:** the user's linked `91000/test_2/attempt_001` uses SHA `f74e62bf...`, the older run with time-rate weight −0.05, profile `existing` and learning-rate cap 0.0003 in its saved checkpoint arguments. Its viewer has wide limits. The newest `test_swing013_91000` uses SHA `dec9775d...`, the completed retry with −0.01, `viewer-wide`, 0.13 m and cap 1e−5. Saved arguments identify the intended settings; no missing original 90000 environment is inferred from them.

**Commands:** Up/W increments vx by 0.05 m/s; Space immediately zeros all commands. The policy receives this request, rather than choosing its own velocity request. Actual body velocity is a separate measured simulated signal. Those keyboard jumps explain the command steps, but actual velocity also fluctuates under constant commands.

**Holding targets is not a demonstrated main cause:** both recordings update targets at 50 Hz and integrate physics/PD at 200 Hz. No target changes outside policy ticks were found. In the newest candidate's flat walking window (36.40–56.40 s, vx 0.35), measured 8–30 Hz RMS is 0.3404°, versus 0.0340° in 45–55 Hz. The spectrum is mainly gait/lower-frequency content, without a dominant narrow 50 Hz component. A small 50 Hz feature is visible in the near-stationary spectrum but at very small amplitude. Neither finding rules out sampled-control interactions at other frequencies. Four held physics steps include the tick where the target changes; a new action is issued every 20 ms, not after four extra held steps. Interpolation would change the trained action realization and can add delay; it needs a separately labeled controlled evaluation.

**Gates are active, but they blend eight latent experts:** no hard argmax route exists. In newest attempt_002, mean gate change increases 0.0522→0.0977 after contact. Symmetric offline raw-action decomposition for the post-contact interval yields RMS contributions gate 0.2576, expert features 0.4640, latest actor frame 1.0084. These are raw numerical-action units before clipping, not independent physical causes or percentages. Contributions can cancel. The direct latest-frame path is substantial, so suppressing only gate motion could miss important input-driven changes. Gate smoothing can suppress useful adaptation; do not call gate variation proven indecision.

**Newest stair event:** attempt_002 requests the same vx 0.4 before/after first FR riser contact at elapsed 8.205 s. Foot-center height is 4.49 cm, with no target or torque clipping on that leg at the instant. Across constant-command windows (5.195–8.205 and 8.205–13.110 s), measured joint 8–30 Hz RMS rises 0.3176→1.6417°. Any-joint torque clipping rises 0→11.31% of physics samples. Max tilt reaches 47.02° before manual reset; no feet loaded the platform in this recording. This is an observed interrupted attempt, not a controlled estimate of eventual success probability. Contact and gait state differ even though the command is fixed.

**Actuator investigation is justified; a hardware actuator defect is not established:** at 10.45 s, simulated FR thigh velocity is 58.21 rad/s, raw torque −75.64 Nm, applied torque −12 Nm. The position-error term is −27.74 Nm and damping term −47.91 Nm. This is later than first contact. The large velocity term could reflect contact dynamics/numerics/feedback, and cannot be fixed simply by assuming insufficient damping. The older linked run similarly requests −133.27 Nm at 63.955 s and applies −12 Nm; it ends in a settled, tilted posture with non-foot terrain contact, not staircase completion.

**Next order:** first keep checkpoint, commands, timing and contact settings controlled; examine q/dq, P/D terms, foot contacts and support transfer around onset. The training and viewer use coupled PD kp 20/kd 0.7, but their delay/contact implementations differ (see below). Then run small, separate gain/delay/contact sensitivity evaluations and retain failures. Preserve the transmission matrix and target limits for each comparison. Do not add gate filtering and target interpolation together and call any improvement causal proof. Fitting a learned real-actuator model requires real command/state/torque data with held-out validation; our simulator's own torque trace cannot identify missing physical motor dynamics. [Hwangbo et al., actuator identification](https://arxiv.org/html/1901.08652v1).

Newest attempt_001 is a flat-ground drive/turn recording that never contacts stairs; it cannot count as a failed ascent. Attempt_003 is a zero-command standing recording. They usefully show nearly quiet standing alongside moving-gait oscillation. These are four newly reviewed attempts across two checkpoints, not all historical sessions.

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
