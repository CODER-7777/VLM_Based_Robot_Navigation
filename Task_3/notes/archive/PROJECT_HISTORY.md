> Historical note. For current commands and decisions, start at [Task 3](../../README.md).

# Start here: current MoE training and failure-analysis status

**Current direction, 2026-10-17 — RL only, ratio 100:** [note 25: policy-debugging strategy and new recorded evidence](../25_RL_POLICY_DEBUG_STRATEGY_20261017.md). CPU replay verifies all 2,982 policy ticks in the new session. Oscillation exists before stairs, and actor previous-action sensitivity merits investigation alongside gating. The note specifies observation/actuator checks, event logging, controlled tests, and criteria for any later fine-tuning. [New diagnostics dashboard](../../tools/results/policy_debug_20261017/index.html). No new physics rollouts, training, GPU evaluation or runtime edits were made for this follow-up; the VLM proposal below is outside the user's chosen scope.

**Latest focused audit, 2026-10-11:** [note 24: gating, frequency, actuator contract, and VLM integration](../24_GATE_FREQUENCY_AND_VLM_AUDIT_20261011.md). New CPU replay matches 4,059 recorded policy inputs; a three-pathway probe shows larger target-change sensitivity through the actor's direct input than through gate weights. Twelve September filter traces and 65 hardware correlation windows were independently rechecked. Keep policy/gate at 50 Hz for the next baseline; consistent sensing/reset, deployment mapping and actuator identification remain priorities. The new manual attempt 4 passes full-foot ascent at 16.265 s, with steering and a 30.8° climb tilt peak. A VLM can supply navigation goals above the existing policy. No training, new simulation, GPU evaluation or runtime change was performed in this follow-up.

**Current synthesis, 2026-10-10:** read [note 23: deep robotics analysis, all attempts, proof, and current results](../23_DEEP_JITTER_ANALYSIS_20261010.md) first. It includes 34 new CPU-only tests under today's tighter limits, 32 historical raw-trace rechecks, reread training curves, checkpoint identities, and corrections to timestep/solver interpretations. Contact ratio 10 reduced flat vibration 63.5–70.5%, with 3/6 tested stair completions versus 0/6 at 100; failures and a sideways-tracking regression remain. The viewer has an explicit `--contact-impratio 10` option. No training or GPU evaluation was launched; discuss future training/GPU use with the user before starting. The dated “next step” recommendations below are historical and are not instructions to launch another training run.

**Hardware objective clarification, 2026-10-07:** preserve verified deployed hardware parameters. Read the new top section of [note 17](17_REVIEW_OF_ACTUATOR_DELAY_AND_GATE_SUGGESTIONS.md): `impratio` is a MuJoCo-only contact-solver setting, but changing it changes the physics experienced during training. Its diagnostic improvement does not validate a hardware fix. The previous recommendation below is an optional simulation comparison, not a deployment instruction. New offline contact-force/slip/torque measurements and a fixed-state solver check are saved in the same [focused dashboard](../../tools/results/control_loop_audit_20261006_v2/FINDINGS.html). Live runtime, weights and server files remain unchanged.

**Follow this first — verified 2026-10-07:** [note 17: contact-solver diagnosis and the next manual change](17_REVIEW_OF_ACTUATOR_DELAY_AND_GATE_SUGGESTIONS.md) and [focused plots / verified stair completions](../../tools/results/control_loop_audit_20261006_v2/FINDINGS.html). Viewer `impratio=100` differs from the current training setting `10`. Changing only that parameter reduced measured flat vibration **44–73% at kp=18/kd=0.7**, while maintaining approximately the same speed or improving it; all four tested 10 cases completed the 10 cm staircase, versus none of their matching 100 cases. These are two checkpoints × two gains at one nominal stair start, not a general success rate or hardware validation. This diagnosis used new scripted simulations, separately labelled from manual recordings. No live scene/controller, training/reward, checkpoint or server files were changed. **Test that one viewer setting before more gain/reward changes.** The sections below document earlier experiments; their earlier “next step” recommendations are historical.

**Latest comparison (October 4):** [note 16](16_NEXT_CHANGES_FROM_THE_PLOTS.md) now contains the five-idea implementation status, new interactive findings, research links, and SCP/nohup commands. [Open the two compact plots](../../tools/results/interactive_comparison_20261004/index.html). The older original and candidate both failed in these unsteered recordings; rising world x alone is not full ascent. The new 13 cm/time-aware settings are an untrained experiment, not a proven fix.


**Latest five-idea review (2026-10-04):** see the update at the top of [existing note 16](16_NEXT_CHANGES_FROM_THE_PLOTS.md). Two tested options are now available: training `--swing-height 0.13` and interactive evaluation `--observation-timing fresh`. Neither is silently enabled for old runs. The successful original model also hit the first riser low (6.26 cm), so that event alone does not prove missing lift capability. Friction is randomized during training, not fixed at 0.6. Heading and rear-support observations are real but their proposed fixes remain unproven. No new note file was created.

**Original training conditions are still unverified:** the original 90000 run's full environment/source snapshot is missing locally. The September control had no extra target clamp; the October candidate used tighter bounds and new rewards. `viewer-wide` matches the current simulator, not a verified original training configuration. Preserve 90000 and establish the original configuration before interpreting a continuation or scratch experiment; the earlier categorical advice against scratch training below is superseded by this qualification.

**Current update, 2026-10-04:** follow this paragraph before historical sections below. No new Markdown file was added. The optional time-aware reward is implemented in `xterra_mjlab/scripts/target_rate_reward.py` and registered by `train_other.py --target-rate-weight`. Six CPU checks and a 24-step actual GPU environment check pass, including the new viewer-wide configuration. These are functional checks, not proof of improved locomotion. Server training has not been started by the assistant.

**New successful recording:** `tools/results/interactive/user_run_original_4_by_sir/attempt_001` uses verified original 90000 weights and wider viewer bounds. Raw data passes the full-traversal condition, held 0.5 seconds, at **40.925 s**. All four feet load the top platform; no teleport/reset occurs during the attempt. The operator adjusts forward/lateral/yaw commands, so it is not a matched fixed-command comparison. Joint 8–30 Hz RMS is 0.850° over the full recording, 0.255° during 6.47–10.47 s and 0.870° during 10.47–14.47 s. The original can climb in this setup and still exhibits increased rapid motion after contact. Earlier failed trials remain findings for their specific protocols.

**Current trial recommendation:** resume original 90000 to **91000**, inspect climbing and jitter, and only then consider 91500. Add `--target-rate-weight -0.01 --target-rate-limits 7.093 11.275 20.365 --target-limit-profile viewer-wide --max-learning-rate 1e-5`. Keep existing action-rate −0.15, second difference −0.01 and saturation pressure −0.01. The explicit viewer-wide option matches hips ±1.0472 and calf upper +0.500 in this simulation trial; the default still retains tighter training bounds. It changes no thigh limits, PD gains, transmission matrix or action-history semantics. Successful climbing also exceeds the exploratory rate threshold, so a strong punishment may suppress useful stepping; the earlier −0.05 suggestion is superseded for this trial. Do not train from scratch on the basis of this recording.

Transfer `scripts/target_rate_reward.py`, `scripts/train_other.py` and `scripts/jitter_rewards.py` to the server. Resume validation requires `--num-envs 8192 --steps 24 --seed 103001`, even for a short checkpoint-resume smoke run. Use a new output directory, e.g. `runs/20261004_moe_time_rate_wide_updates91000`. A later local viewer must use that new run's checkpoint path after copying it back; the Oct 2 `latest.pt` stays the old candidate. Current launch commands were supplied in chat. Existing older sections below document previous experiments.

Updated: **2026-10-04**. This is the current main checklist. Notes 07–12 provide background, note 13 reviews the local video, and **[note 14](14_FRESH_FAILURE_ANALYSIS_20261002.md) links the completed fresh-data failure analysis**. **[Note 15](../15_HOW_TO_READ_THE_PLOTS.md) explains the graphs in simple English**, also shown directly above plots in the dashboard. It supersedes older ordering and stale statements about which limits have already been edited.

**New optional reward design:** [note 22: time-aware target-change penalty](22_TIME_AWARE_TARGET_PENALTY.md) explains your Δt idea, measured rate references, why weights need recalibration, existing saturation pressure, tested proposal code and exact manual integration steps. It is not active in training. [Rate dashboard](../../tools/results/time_aware_penalty_20261003/index.html).

**Latest practical step:** read [note 21: all interactive runs, short plots and your observations](21_INTERACTIVE_RUN_REVIEW_AND_OBSERVATIONS.md). Five sessions / 41 attempts are reviewed from saved keyboard-controlled measurements. All use the same 90500 checkpoint. The target second-difference training cost decreased by 6.57%, but full stair ascent remains unrecorded. Your observation—shaking is much stronger after stair contact—is recorded in the notes and worksheet. On 2026-10-04, at your request, the viewer uses the original wider hip targets ±1.0472 and calf upper +0.500 rad. Recorded sessions retain their own original bound metadata. The new review does not run simulations, edit rewards/controllers, or access the server.

**Current next step:** read [tools/README.md](../../tools/README.md), [the new report](../../tools/results/20261002_matched_v1/REPORT.md), and [note 17's review of actuator, delay and gate suggestions](17_REVIEW_OF_ACTUATOR_DELAY_AND_GATE_SUGGESTIONS.md). Twenty local evaluation executions are complete, with raw traces and plots. The candidate improves early speed tracking and reduces target removal in the tested pairs, but jitter improvement is inconsistent and none of the twelve distinct stair cases completes ascent. Initial front-foot/riser contact is too low for direct clearance; observation timing also materially changes behavior. Verify existing training command delay against evaluation, and inspect clearance/support/heading and the observation contract before another reward or actuator change. The September audit is evidence to question, **not ground truth**.

**Completed training decision:** continue from the original `model_90000.pt` with consistent position-target clipping, a normalized target second-difference penalty, and a normalized target saturation-pressure penalty. The user manually implemented the rewards and ran training. **The combined candidate completed at update 90500**, with zero numerical resets and a verified saved `latest.pt`. Its output is `runs/20261002_moe_target_bundle_updates90500`; `_retry1` was not used. Section 11 records completion. The run is copied locally and the viewer hip targets are ±0.735. The 35-second recording is reviewed in [note 13](13_CANDIDATE_VIDEO_REVIEW_20261002.md), and fresh quantitative comparisons are now in [note 14](14_FRESH_FAILURE_ANALYSIS_20261002.md). Reliable jitter reduction and stair ascent remain unachieved. **Actuator tuning comes later.**

## 1. Which file should I follow?

**Latest clarification:** [note 18](18_SHORT_TARGET_LIMIT_CHECK.md) answers whether tightening limits explains worse climbing. Saved candidate approaches never hit the hip limits, but calf upper-target clipping is common. A limits-only comparison is the next proposed diagnostic before another training change; it has not been run.

| File | Use it for |
| --- | --- |
| **This README** | Current order, exact manual edits, checks, server transfer, training and evaluation commands |
| [Dashboard](../../moe_jitter_audit_20260921/index.html) and [REPORT.md](../../moe_jitter_audit_20260921/REPORT.md) | Primary evidence and the audit's interpretation limits |
| [05_VIDEO_JITTER_AUDIT.md](05_VIDEO_JITTER_AUDIT.md) | Detailed saved-video observations and trace comparisons |
| [07_TEST_TRAINED_POLICY_IN_MUJOCO.md](07_TEST_TRAINED_POLICY_IN_MUJOCO.md) | Background on visual evaluation; use this README's current paths and status |
| [08_TARGET_LIMITS_AND_SECOND_DIFFERENCE_PLAN.md](08_TARGET_LIMITS_AND_SECOND_DIFFERENCE_PLAN.md) | Target/action definitions and implementation considerations |
| [09_AUDIT_ISSUE_BY_ISSUE_CHECKLIST.md](09_AUDIT_ISSUE_BY_ISSUE_CHECKLIST.md) | Historical issue list; this README updates its completion status and experiment order |
| [10_REWARD_AND_CONTRACT_EXPERIMENT_PLAN.md](10_REWARD_AND_CONTRACT_EXPERIMENT_PLAN.md) | Earlier separate-experiment design; the current user preference is to test the combined package |
| [11_ACTUATOR_ADVICE_REVIEW_AND_GAIN_TRIALS.md](11_ACTUATOR_ADVICE_REVIEW_AND_GAIN_TRIALS.md) | Later actuator investigation; do not start those gain edits in this run |
| [12_REVIEW_OF_SMOOTHNESS_AND_MOE_REPORT.md](12_REVIEW_OF_SMOOTHNESS_AND_MOE_REPORT.md) | Background review of the pasted literature/report |
| [13_CANDIDATE_VIDEO_REVIEW_20261002.md](13_CANDIDATE_VIDEO_REVIEW_20261002.md) | New local 10 cm recording: timestamped observations, evidence frames, interpretation limits and next diagnostics |
| [14_FRESH_FAILURE_ANALYSIS_20261002.md](14_FRESH_FAILURE_ANALYSIS_20261002.md) and [tools/README.md](../../tools/README.md) | Current fresh-data results, J_LEG explanation, first-riser event, matched plots and next investigation |
| [15_HOW_TO_READ_THE_PLOTS.md](../15_HOW_TO_READ_THE_PLOTS.md) | Simple-English meanings of command vx, measured speeds, every plot, and an observations table |
| [16_NEXT_CHANGES_FROM_THE_PLOTS.md](16_NEXT_CHANGES_FROM_THE_PLOTS.md) | Proposed next experiments: consistent sensing, conditional 0.13 m lift preference, current smoothness weights, support/heading and standing checks; no fixes applied |
| [17_REVIEW_OF_ACTUATOR_DELAY_AND_GATE_SUGGESTIONS.md](17_REVIEW_OF_ACTUATOR_DELAY_AND_GATE_SUGGESTIONS.md) | Research suggestions checked against our code: existing randomized actuator delay, history-conditioned gate, no direct contact input, one-pair gate measurements and updated experiment order |
| [18_SHORT_TARGET_LIMIT_CHECK.md](18_SHORT_TARGET_LIMIT_CHECK.md) | Short answer on tightened hip/calf bounds: measured clipping and four proposed simulation-only comparisons before retraining |
| [19_RECORD_MY_INTERACTIVE_RUN.md](19_RECORD_MY_INTERACTIVE_RUN.md) | Current commands: record your keyboard-controlled simulation, plot saved data only, read three concise figures and use the cleaned folder layout |
| [20_GITHUB_COMMIT_COMMANDS.md](20_GITHUB_COMMIT_COMMANDS.md) | Eight organized commits for only Task_3/tools and Task_3/notes, with exact staging, review and push commands |
| [21_INTERACTIVE_RUN_REVIEW_AND_OBSERVATIONS.md](21_INTERACTIVE_RUN_REVIEW_AND_OBSERVATIONS.md) | Follow now: all 41 interactive attempts, short target-cost/joint/contact plots, second difference versus jerk, your observations worksheet and next experiments |
| [22_TIME_AWARE_TARGET_PENALTY.md](22_TIME_AWARE_TARGET_PENALTY.md) | New proposal: rate deadband using policy elapsed time; measured references, weight scale, retaining saturation, tests and manual opt-in integration |

**Current target status (2026-10-04):** all four local viewer calf upper targets are `+0.500`, with hips ±1.0472, following the latest user-requested restoration. The exact September audit/training bound is `-0.88776`; historical notes and saved manifests describe their own settings. Read each run’s manifest, rather than assuming all past runs used today’s limits.

## 2. First: read the dashboard with a purpose

From your local desktop, open a terminal and run:

```bash
cd /home/vivekananda/UGP_1_VLM/VLM_Based_Robot_Navigation/Task_3
python3 -m http.server 8000 --bind 127.0.0.1
```

Open <http://127.0.0.1:8000/moe_jitter_audit_20260921/index.html>. Leave that terminal running. This serves existing files; it does not rerun the experiments.

The dashboard contains **eight simulation videos and nine diagnostic figures**. The label “hardware” on a simulation video means deployed target bounds, not real-robot video.

| Dashboard item | What to observe | Useful inference |
| --- | --- | --- |
| Flat forward video | Standing, stepping, direction and shake | Establish whether motion remains useful before judging smoothness |
| Flat lateral video and lateral joint plot | Sideways tracking and unintended turning | Maximum 0.6 m/s lateral motion exceeds the saved ±0.3 m/s training range; keep initial tests in range |
| Rough 3 cm video and joint plot | Contact changes and progress | Some uneven-ground cases work; failure is task dependent |
| 20° downhill video | Support and progress downhill | A downhill success does not establish ascent capability |
| 20° uphill video and joint plot | Lane departure, body rotation and recovery | Staying upright can still be a tracking/task failure |
| Three 15 cm ascent videos: unfiltered deployed bounds, 20 ms filter, legacy bounds | First stair contact, repeated leg corrections, tipping or lane exit | None of these selected clips demonstrates a valid full ascent; the filtered case fails earlier in the selected pair |
| Hardware joint-angle figure | Blue measured angles versus orange sent targets | Rapid target components and actual motion are related; the terrain in this hardware record is unlabelled |
| Hardware spectra/gates figure | Frequency content, windows and continuously weighted experts | Inspect sensitivity; neither correlation nor changing gate weights establishes a causal explanation |
| Original incident figure | Large tipping event in the 20 Hz recording | It cannot resolve the full 8–30 Hz band |
| Terrain comparison | Joint oscillation and failures across terrains | Read the CSV outcomes too: no fall does not mean full traversal |
| Filtering/delay/timestep comparison | Oscillation **and** tracking error | A lower oscillation number can come with worse task performance |
| 15 cm stair joint figure | Green unclamped requests, orange clamped targets, blue actual angles | Calf requests cross allowed bounds and target plateaus appear; this motivates inspecting both smoothness and saturation pressure |

Other links include the report, all-outcomes CSV and provenance manifest. The link to the separate corrected simulator points outside this copied audit; its implementation is not present in the checked local project. The dashboard remains useful, but it does not install its corrected controller into your current viewer.

### Observations that justify our next trial

| Evidence | What we can conclude | What it does not prove |
| --- | --- | --- |
| 30,175 recorded policy inputs reproduce outputs, maximum difference 2.29e-5 | Wrong weights are not supported as an explanation for that recording | That the policy can climb stairs |
| Hardware target 8–30 Hz RMS is larger than measured-angle RMS; window association is 0.962 | Investigate requested targets and the closed loop | That abrupt requests are the sole cause |
| RR calf target occupancy at a deployed limit is 64.8% of moving samples | Repeated saturation is worth measuring and discouraging experimentally | Mechanical hard-stop contact or motor damage |
| Corrected-bound ascent cases at 10/15/18 cm each had 0/2 valid traversals | Fixing bounds alone is insufficient in those trials | A statistically established success rate, or impossibility of learning ascent |
| 20 ms filtering reduced flat HF RMS by about 7%, but did not fix ascent; 40 ms increased flat HF RMS | Do not select an output filter merely because one trace looks smoother | That every possible filter is useless |
| Physics-resolution/contact experiments changed the metrics | Numerical/physical-model sensitivity remains | That a smaller timestep is automatically the correct physical model |

Sources: [audit report](../../moe_jitter_audit_20260921/REPORT.md), [all outcomes](../../moe_jitter_audit_20260921/suite_summary.csv), [saved-video analysis](05_VIDEO_JITTER_AUDIT.md). On 2026-10-02 the dashboard/report and the terrain, ablation and stair-angle figures were rechecked; the earlier video review is documented in note 05. No fresh videos of your new candidate were supplied or evaluated in this review.

## 3. Where we are now

- [x] Original 90k checkpoint identified.
- [x] Control -0.10 and candidate -0.15 continuations completed at update 90500 from the same original checkpoint, according to copied metadata.
- [x] Reward contribution logging is already in `scripts/m2_algorithm_env.py` and `scripts/train_other.py`.
- [x] User reports substantial remaining jitter; a new quantified candidate-vs-control comparison is still outstanding.
- [x] Current viewer restored on 2026-10-04: all four calf upper targets +0.500 and hip targets ±1.0472. Audit/training and older runs retain their own settings.
- [x] Current training configuration has post-scale/offset target clipping, and its regex patterns resolve to all twelve joints.
- [x] Match the local viewer hip bounds to current training: all four now ±0.735; assistant made only this controller edit at the user's explicit request.
- [x] Add the two proposed target costs and register them for MoE training.
- [x] Validate the saved implementation's syntax, imports, formulas, reset masking and reward-manager registration.
- [x] Verify the lab server interpreter, GPU access, uploaded file hashes, reward configuration and training-script imports.
- [x] Run the short robot-environment/training smoke test and inspect its saved configuration and reward logs: completed at 90005, zero numerical resets, expected settings and finite new penalty contributions.
- [x] Inspect the first full candidate attempt: stopped at 90089, no saved checkpoint; identify and document the separate `nohup` launch error.
- [x] Relaunch the full candidate successfully: live process 67031, completed update 90030 at inspection, expected reward weights and 20 s episodes confirmed.
- [x] Complete the combined candidate: final status completed, saved checkpoint update 90500, finite model tensors, both optimizer states, zero numerical resets and 500 finite reward-log entries per inspected term.
- [x] Confirm the completed candidate is copied to local `evaluation_runs/20261002_moe_target_bundle_updates90500`.
- [x] Review `Videos/2026-10-02 18-50-10.mp4`: Track 1, lower-step balance/progress problems and resets; evidence documented in note 13.
- [x] Evaluate the completed candidate with useful-motion/task criteria and quantify jitter under consistent settings: 20 local executions, paired starts and observation modes; no reliable ascent or jitter fix demonstrated. See note 14.

Important distinction: the two **old saved runs** have `clip: null`; your **current edited source** has target clipping. Editing the source today does not retroactively change what those checkpoints experienced during training.

The current thigh ranges still resemble the legacy demo ranges. The complete asymmetric deployed thigh bounds are absent from the available source/report table. We can run a **matched local target-profile experiment** now, but cannot call it complete deployed-controller parity. Do not guess missing bounds or apply an additional 0.05 rad buffer to the already-buffered calf value.

## 4. The combined trial: exactly what changes?

| Item | Setting/action | Purpose |
| --- | --- | --- |
| 1. Matched target profile | Retain current training clipping; change all four viewer hip min/max values to -0.735/+0.735 | Train and evaluate with the same known limits; retain corrected calf upper bound |
| 2. Target second difference | Add `target_second_difference_l2`, initial weight **-0.01** | Discourage rapidly changing increments/reversals of the final clamped position targets |
| 3. Target saturation pressure | Add `target_saturation_l2`, initial weight **-0.01** | Discourage requests whose excess is removed by target limiting |

Both -0.01 values are **experimental pilot coefficients**, not values proved optimal by the audit. Inspect their evaluated contributions before committing to a long continuation. Keep existing action-rate **-0.15**; do not increase it again simultaneously.

Keep nominal **kp=20, kd=0.7**, existing gain randomization/delay, reference pose, action scales `[0.15, 0.15, 0.30]` per leg, 5 ms physics and decimation 4, contact/friction settings, command ranges, and existing tracking/slip/clearance/landing rewards. Actuator/XML tuning is a later investigation. Changing `STIFFNESS` also changes the action scales through their current formula, so it would add an unintended change.

This combined experiment addresses the user's time constraint. It can show whether the package helps; it cannot tell us which individual change caused the result. If promising, use a later ablation to separate effects. Keep all older artifacts.

### Why propose the target second-difference penalty? Evidence to show your supervisor

The justification is an **experimental hypothesis supported by recorded target oscillation and a failed stair incident**, not proof that target reversals are the sole root cause. Use the following evidence chain before changing the reward.

| Specific evidence | Where to look | Observation | How it motivates this particular cost |
| --- | --- | --- | --- |
| [Hardware joint-angle figure](../../moe_jitter_audit_20260921/hardware_joint_angles.png) | 465–469 s, especially the orange hip/thigh traces | Sent targets contain short spikes/reversals superimposed on the larger walking motion. The blue actual angles have their own response and differ from the requests. | Inspect rapid changes in target increments, rather than treating every large leg swing as unwanted jitter. This figure is terrain unlabelled; do not describe it as a stair recording. |
| [Hardware spectra/window/gate figure](../../moe_jitter_audit_20260921/hardware_spectra_gates.png) and [REPORT.md hardware evidence](../../moe_jitter_audit_20260921/REPORT.md) | Target/angle frequency content and moving-window association | The report gives 8–30 Hz target RMS of 0.63–1.84° per joint, measured-angle RMS of 0.19–0.45°, and target/measured moving-window Spearman association 0.962. | The requested motion and actual oscillation are associated, making target smoothness a reasonable intervention to test. This is not causal proof; the policy also reacts to actual motion. These RMS ranges describe the analysed moving samples, not exclusively the displayed four-second figure. |
| [15 cm ascent joint figure](../../moe_jitter_audit_20260921/sim_angles_stairs_up_15_forward.png) | 7–11 s, orange hip/thigh targets; compare orange, blue and dashed green calf curves separately | Rapid target changes and reversals occur during the unsuccessful ascent. In the calf plots, unclamped requests also extend beyond the flat portions of the sent targets. | Target reversals motivate the second-difference experiment. The green-to-orange gap motivates the **separate saturation-pressure** cost; a plateau alone does not prove a large second difference. |
| [Unfiltered 15 cm ascent video](../../moe_jitter_audit_20260921/videos/stairs_up_15_hardware_forward_half_speed.mp4), [repeated-attempt detail](../video_jitter_audit_20260926/stair_repeated_attempt_detail.jpg), and [saved metrics](../../moe_jitter_audit_20260921/runs/stairs_up_15__hardware__forward__s0__dt0.005__f0__d0.005__c0.01/metrics.json) | Stair contact at **simulation 7.655 s**, tip threshold at **15.415 s**; the half-speed cropped video uses different timestamps | Repeated leg/body corrections near the lower steps culminate in a tip, with no full traversal. Saved whole-motion metrics are approximately 1.445° measured-angle and 3.662° target HF RMS, aggregated across joints. | This is the concrete failing task that the proposed change must improve. A video establishes the behavior/outcome; it does not identify the cause or reliably resolve the HF band by eye. Do not treat these whole-motion metrics as measurements of only the 7–11 s plot. |
| [Filtering/delay/timestep figure](../../moe_jitter_audit_20260921/ablation_comparison.png) and the report's filtering table | Compare HF RMS **and** tracking/outcomes | A 20 ms filter gives modest flat improvement but fails both reported 15 cm ascent starts; a 40 ms filter increases flat oscillation. | Test learned smoothness without adding an output filter in this run. This does not prove reward smoothing will work or justify banning all filters. |

The audit itself proposes normalized final-target second differences under **“Changes to make next, in order,” point 5** in [REPORT.md](../../moe_jitter_audit_20260921/REPORT.md). That is the source of the candidate formula. The audit did not train or validate this reward.

Why second differences rather than simply raising action rate again? Existing action rate penalizes consecutive action increments. The proposed cost penalizes **changes between increments of the final clamped targets**:

```text
increment_now = q_cmd[t] - q_cmd[t-1]
increment_before = q_cmd[t-1] - q_cmd[t-2]
second_difference = increment_now - increment_before
```

An illustrative three-target example, not extracted robot data:

| Targets | Two increments | Second difference |
| --- | --- | --- |
| 30°, 35°, 40° | +5°, +5° | 0° |
| 30°, 35°, 30° | +5°, -5° | -10° |

The second sequence reverses abruptly even though both increments have the same absolute size. A second-difference cost distinguishes these patterns. In code use radians, the per-joint action scales and the sum of normalized squares from section 6. This is a general smoothness preference, not a filter selecting only 8–30 Hz: normal gait reversals and necessary recovery can also incur cost, so retain tracking/stair objectives and inspect the tradeoff.

**Suggested explanation to your supervisor:**

> The audit found rapid components in commanded joint targets, a strong association between target and measured oscillation, and an unsuccessful 15 cm ascent with repeated corrections. Its proposed next experiments include a normalized second-difference penalty on final joint-position targets. I therefore propose testing this cost to discourage rapidly changing target increments, while keeping control gains and timing fixed. It remains a hypothesis: we must check whether oscillation decreases while speed tracking, foot lifting and full stair traversal are preserved.

**The initial weight -0.01 does not come from a plotted incident or a proven optimum.** It is the pilot value suggested in this workflow. The report proposes the formula without an established coefficient. Record raw/weighted costs and tune the coefficient from their magnitudes and task tradeoff. If limits and both new rewards are changed together, report a combined-package result; an improvement cannot establish the second-difference term's individual causal effect.

## 5. Manual edit A: finish matching the target profile

In [controller.py](../../xterra_mjlab/svanm2_moe_stair_sim/controller.py), `TARGET_MIN` and `TARGET_MAX` near lines 25–37: replace the **first value of each leg row** with `-0.735` and `+0.735`, respectively. Keep the other currently configured values:

```python
TARGET_MIN = np.array([
    -0.735, -1.5708, -2.7227,  # FL
    -0.735, -1.5708, -2.7227,  # FR
    -0.735, -0.5236, -2.7227,  # RL
    -0.735, -0.5236, -2.7227,  # RR
], dtype=np.float32)

TARGET_MAX = np.array([
    0.735, 3.4907, -0.88776,  # FL
    0.735, 3.4907, -0.88776,  # FR
    0.735, 4.5379, -0.88776,  # RL
    0.735, 4.5379, -0.88776,  # RR
], dtype=np.float32)
```

Your current [env_cfgs.py](../../xterra_mjlab/xterra_mjlab/tasks/velocity/config/svanm2/env_cfgs.py), inside `svanm2_rough_env_cfg` near line 125, already has the corresponding mapping:

```python
joint_pos_action.clip = {
    r".*_hip_joint": (-0.735, 0.735),
    r".*F[LR]_thigh_joint": (-1.5708, 3.4907),
    r".*R[LR]_thigh_joint": (-0.5236, 4.5379),
    r".*_calf_joint": (-2.7227, -0.88776),
}
```

Do not add another clamp to the policy's previous-action observation. It continues to store actions clipped to `[-6, 6]` **before** final position-target limiting. Joint-limit rewards on measured angles and XML physical stops are different mechanisms.

## 6. Manual edit B: add the two reward implementations

Create **`xterra_mjlab/scripts/jitter_rewards.py`** with this complete content. Paths here are relative to `Task_3`; when inside the package directory, this is `scripts/jitter_rewards.py`.

```python
"""Costs on clamped position targets for the current SvanM2 MoE interface."""
import torch

from mjlab.managers import RewardTermCfg
from mjlab.managers.manager_base import ManagerTermBase
from mjlab.utils.lab_api.string import resolve_matching_names_values


class _TargetCost(ManagerTermBase):
    def __init__(self, cfg, env):
        super().__init__(env)
        self.action_name = cfg.params.get("action_name", "joint_pos")
        # This implementation expects the inspected single action term.
        if list(env.action_manager.active_terms) != [self.action_name]:
            raise ValueError("Revisit action slicing if more action terms are added")
        self.term = env.action_manager.get_term(self.action_name)
        if self.term.cfg.clip is None:
            raise ValueError("Configure position-target clipping before these costs")
        template = env.action_manager.action
        self.scale = torch.as_tensor(
            self.term.scale, device=template.device, dtype=template.dtype
        )
        if bool((self.scale <= 0).any()):
            raise ValueError("Expected positive action scales")
        ids, _, bounds = resolve_matching_names_values(
            self.term.cfg.clip, self.term.target_names
        )
        if set(ids) != set(range(self.term.action_dim)):
            raise ValueError("Every position target must have a configured bound")
        limits = torch.tensor(bounds, device=template.device, dtype=template.dtype)
        self.lower = torch.empty_like(template)
        self.upper = torch.empty_like(template)
        self.lower[:, ids] = limits[:, 0]
        self.upper[:, ids] = limits[:, 1]

    def requested(self, action):
        # Adapter.step already clips raw outputs to [-6, 6].
        return action * self.scale + self.term.offset

    def commanded(self, action):
        return torch.clamp(
            self.requested(action), min=self.lower, max=self.upper
        )


class TargetSecondDifference(_TargetCost):
    def __call__(self, env, action_name="joint_pos"):
        if action_name != self.action_name:
            raise ValueError("Action term changed")
        manager = env.action_manager
        q_t = self.commanded(manager.action)
        q_prev = self.commanded(manager.prev_action)
        q_prev_prev = self.commanded(manager.prev_prev_action)
        delta2 = (q_t - 2 * q_prev + q_prev_prev) / self.scale
        cost = delta2.square().sum(dim=1)
        # The environment increments episode length before reward computation.
        # At least three actual policy actions are needed after each reset.
        return torch.where(env.episode_length_buf >= 3, cost, torch.zeros_like(cost))


class TargetSaturationPressure(_TargetCost):
    def __call__(self, env, action_name="joint_pos"):
        if action_name != self.action_name:
            raise ValueError("Action term changed")
        requested = self.requested(env.action_manager.action)
        commanded = torch.clamp(requested, min=self.lower, max=self.upper)
        return ((requested - commanded) / self.scale).square().sum(dim=1)


def config_jitter_rewards(cfg, second_weight=-0.01, saturation_weight=-0.01):
    if second_weight > 0 or saturation_weight > 0:
        raise ValueError("Use nonpositive weights for these costs")
    cfg.rewards["target_second_difference_l2"] = RewardTermCfg(
        func=TargetSecondDifference, weight=second_weight,
        params={"action_name": "joint_pos"},
    )
    cfg.rewards["target_saturation_l2"] = RewardTermCfg(
        func=TargetSaturationPressure, weight=saturation_weight,
        params={"action_name": "joint_pos"},
    )
    return cfg
```

Why this version: it uses the inspected action manager's existing per-environment, once-per-policy-step action histories. For the current fixed reference pose, scale and limits, reconstructing the three clamped targets is equivalent to storing those targets separately. The manager zeros history on each environment reset, and the first two new actions are masked. There is no shared history between robots and no extra update at physics frequency.

These costs use the commanded position target **after** scaling/offset/clipping, before the framework's encoder-bias correction and actuator delay. Current encoder bias is a startup randomization; this is a well-defined setpoint stage, not measured joint motion. If the target mapping changes during an episode or you use a different action type, this reconstruction must be revised.

The second difference is **not** measured joint acceleration or jerk. There is no division by timestep squared. The built-in `action_acc_l2` acts before position-target limiting and differs during saturation; do not add it as a duplicate of this term.

Saturation pressure penalizes position requests removed by the clamp, not torque saturation. A target parked at a limit can have a zero second difference while its unclamped request keeps pushing beyond the limit; the second cost covers that case.

## 7. Manual edit C: register the costs in the actual training path

In [train_other.py](../../xterra_mjlab/scripts/train_other.py):

1. Add this import next to the existing `from m2_algorithm_env import Adapter, make_cfg`:

```python
from jitter_rewards import config_jitter_rewards
```

2. Immediately after `cfg = make_cfg(a.num_envs, a.seed)` near line 45, add:

```python
if a.algorithm == "moe":
    cfg = config_jitter_rewards(cfg)
```

3. Keep the existing `--action-rate-weight` override immediately afterwards, and keep logging unchanged. These additions must run before `dump_yaml(...)` and before `Adapter(...)`.

There is no additional MoE `score` block to edit. RewardManager sums registered weighted terms automatically. The inspected logging derives names dynamically and will log:

```text
RewardRaw/target_second_difference_l2
RewardRate/target_second_difference_l2
RewardRaw/target_saturation_l2
RewardRate/target_saturation_l2
```

`RewardRaw` is the nonnegative cost; `RewardRate` includes its negative coefficient. The existing framework normally multiplies reward rates by the 0.02 s policy timestep when returning per-step rewards. Do not multiply these functions by dt again.

You do not need another logging edit in `m2_algorithm_env.py`. Its existing capture before manual reset is already present.

### Review of the user's saved manual edits — 2026-10-02

**Latest recheck: placement and saved reward implementation pass.** The earlier incomplete-file errors have been resolved. The user chose the function name `config_jitter_rewards`; it matches the definition, import and call. This guide's code examples and configuration-check command now use that name too.

The setup block in `scripts/train_other.py`, lines 46–50, runs before `dump_yaml` (line 79) and `Adapter` (line 85). Keep that order. `cfg` holds settings; `dump_yaml` saves those settings; `Adapter` constructs the environment and reward manager from them. The existing action-rate override and dynamic logging are correctly placed.

Checks on the actual saved files: all three reviewed scripts parse; `train_other.py --help` imports successfully; weights resolve to action rate -0.15, target second difference -0.01 and target saturation -0.01. Nine mathematical/API checks passed using two mock environments and the installed real RewardManager: constant targets, in-range requests, ramp, reversal, calf overshoot, equal saturated targets, independent first/second reset masks and reward registration/dt scaling. Reward-rate buffers were finite. This did not instantiate a full robot environment or start training.

Training clipping is present. Viewer hip bounds still need the section 5 edit: currently ±1.0472 versus training ±0.735. No Python file was changed by the assistant during this review. Proceed to the configuration and environment smoke checks below, after transferring the current files to the server.

## 8. Validate before a long run

From your local package directory, using its existing environment:

```bash
cd /home/vivekananda/UGP_1_VLM/VLM_Based_Robot_Navigation/Task_3/xterra_mjlab
PYTHONPATH="$PWD:$PWD/scripts" .venv/bin/python -B - <<'PY'
from m2_algorithm_env import make_cfg
from jitter_rewards import config_jitter_rewards
from mjlab.utils.lab_api.string import resolve_matching_names_values
cfg = config_jitter_rewards(make_cfg(2, 103001))
names = [f"{leg}_{stage}_joint" for leg in ("FL", "FR", "RL", "RR")
         for stage in ("hip", "thigh", "calf")]
ids, resolved, limits = resolve_matching_names_values(cfg.actions["joint_pos"].clip, names)
assert set(ids) == set(range(12))
print(list(zip(resolved, limits)))
print("scale:", cfg.actions["joint_pos"].scale)
actuator = cfg.scene.entities["robot"].articulation.actuators[0]
print("nominal gains:", actuator.stiffness, actuator.damping)
print("physics dt / decimation:", cfg.sim.mujoco.timestep, cfg.decimation)
for name in ("action_rate_l2", "target_second_difference_l2", "target_saturation_l2"):
    print(name, cfg.rewards[name].weight)
PY
```

Expected: twelve bounds, scales 0.15/0.15/0.30, gains 20/0.7, timestep 0.005/decimation 4, weights -0.15/-0.01/-0.01. Also validate:

- Constant targets → zero second-difference cost after startup.
- An unsaturated target ramp → approximately zero second-difference cost.
- A reversal → positive second-difference cost.
- An in-range request → zero saturation-pressure cost; an out-of-range request → positive cost.
- First two actions after reset → zero second-difference cost, independently for each environment.

**Verification completed on 2026-10-02:** the exact proposed snippet above was executed in memory with two mock environments and the installed real RewardManager. Nine checks passed: constant targets, in-range requests, a linear ramp, a reversal, calf overshoot, repeated targets at a clamp, independent first/second startup masks, and reward registration with dt scaling. The two new reward-rate buffers were finite. This is a mathematical/API check, not a robot rollout, training run or jitter-fix validation.

The server must have compatible action history and clip semantics too. Import/mathematical checks do not replace the short environment run below.

## 9. What to copy to the lab server

After making and checking the manual edits, copy these files from your local desktop. This uses the server directory you showed, not the obsolete example paths in note 07. The user supplied the working server address `guest-isl@172.26.186.222`.

**SCP syntax:** the destination must be one argument, `guest-isl@172.26.186.222:/data/...`, with **no space before the colon**. The failed `guest-isl@172.26.186.222 :/data/...` commands split the address and path; their errors do not establish that the intended remote project directory is missing. Run these commands in the local desktop terminal, not inside the server SSH terminal.

```bash
cd /home/vivekananda/UGP_1_VLM/VLM_Based_Robot_Navigation/Task_3
scp xterra_mjlab/scripts/jitter_rewards.py \
    xterra_mjlab/scripts/train_other.py \
    guest-isl@172.26.186.222:/data/robotics/toshith/vivekananda/m2_moe/xterra_mjlab/scripts/
scp xterra_mjlab/xterra_mjlab/tasks/velocity/config/svanm2/env_cfgs.py \
    guest-isl@172.26.186.222:/data/robotics/toshith/vivekananda/m2_moe/xterra_mjlab/xterra_mjlab/tasks/velocity/config/svanm2/
scp notes/README.md \
    guest-isl@172.26.186.222:/data/robotics/toshith/vivekananda/m2_moe/notes/
```

These copy the required changed training files and the guide. `m2_algorithm_env.py` needs copying only if your server does not already contain the logging changes you used in the completed runs. Keep the original checkpoint and existing run folders.

The server screenshot confirms the outer `xterra_mjlab` project and its inner `xterra_mjlab` Python package. This nesting is normal. Run training from `/data/robotics/toshith/vivekananda/m2_moe/xterra_mjlab`, where `scripts/` and `pyproject.toml` are located.

The viewer controller is used for evaluation; training uses its own actuator implementation. Keep the edited local controller for local evaluation. If you also want its reference copy on the server, the screenshot does not show that destination folder, so create it before copying:

```bash
ssh guest-isl@172.26.186.222 'mkdir -p /data/robotics/toshith/vivekananda/m2_moe/xterra_mjlab/svanm2_moe_stair_sim'
scp xterra_mjlab/svanm2_moe_stair_sim/controller.py \
    guest-isl@172.26.186.222:/data/robotics/toshith/vivekananda/m2_moe/xterra_mjlab/svanm2_moe_stair_sim/
```

A controller reference copy alone is not the complete runnable viewer; server-side viewing would also need the remaining viewer modules and assets. The evaluation commands below use the complete local viewer.

## 10. Server environment check and a short software run

**Environment now found and checked directly on the lab server, 2026-10-02.** The previous `training_log.txt` contains package paths under `/data/robotics/toshith/envs/xterra_mjlab`; its interpreter works with the currently uploaded project. Use it directly rather than guessing an activation command or using the unrelated GQFT Python 3.9 environment.

| Item | Verified value |
| --- | --- |
| Training Python | `/data/robotics/toshith/envs/xterra_mjlab/bin/python` |
| Python / Torch | 3.11.16 / 2.14.0+cu130 |
| MuJoCo / MuJoCo-Warp | 3.10.0 / 3.10.0.3 |
| mjlab / Warp | 1.5.2 / 1.17.0 |
| CUDA / GPU | Available; NVIDIA A40 |
| Required action history/target APIs | `action`, `prev_action`, `prev_prev_action`, and target `scale`, `offset`, `target_names`, `action_dim` all present |
| Uploaded source | `train_other.py`, `jitter_rewards.py`, `m2_algorithm_env.py` and `env_cfgs.py` hashes match the local reviewed files |
| Target clipping and scales | Non-null current mapping, with 0.15/0.15/0.30 scales |
| Reward weights | Action rate -0.15, target second difference -0.01, target saturation -0.01 |
| Gains / configured timing | 20/0.7; 0.005 s physics, decimation 4 |
| External learner source | `/data/robotics/toshith/m2_algorithm_sources20260913/go2_rl_gym` exists; `ActorCriticMoECTS` and `MoECTS` import successfully |
| Original checkpoint hash | Server SHA-256 `440bbb28d554f75db38bfd163351c04ea4a32d9d06764c37b7e6071d41daa5cb`, matching the old runs' recorded starting checkpoint |

The read-only verification checked syntax, imports, configuration and CUDA access; it did not start training or instantiate a full robot environment. GPUs 1–4 were nearly empty at inspection; the commands below select physical GPU 1. Check current usage before running. Within a process using `CUDA_VISIBLE_DEVICES=1`, the selected A40 is addressed as `cuda:0` by the trainer.

### What was trained before, and what does 90500 mean?

Both old run folders are confirmed on the server with `status: completed`, `completed_updates: 90500`. Their saved metadata records the same original 90000 checkpoint/hash. There is no `90500.py` training script: **90500 is the final update count**.

| Role | Server path relative to `/data/robotics/toshith/vivekananda/m2_moe` |
| --- | --- |
| Training program | `xterra_mjlab/scripts/train_other.py` |
| Original 90000 checkpoint | `xterra_mjlab/checkpoints/svanm2_moe/model_90000.pt` |
| Old -0.10 control at 90500 | `runs/20260927_moe_jitter_control_weight010_updates90500/latest.pt` |
| Old -0.15 candidate at 90500 | `runs/20260927_moe_jitter_candidate_weight015_updates90500/latest.pt` |
| Completed combined candidate, update 90500 | `runs/20261002_moe_target_bundle_updates90500/latest.pt` |

The old two runs added 500 training updates to the original policy. The new experiment also started from the original 90000 checkpoint, with the new target/reward settings; it was not a continuation of the old candidate's 90500 file. The user ran the smoke command successfully and completed the full candidate with the corrected background command. Section 11 records completion and earlier restart history. The assistant has not launched training or edited server files.

Run these commands **in the server terminal**:

```bash
cd /data/robotics/toshith/vivekananda/m2_moe/xterra_mjlab
M2_PY=/data/robotics/toshith/envs/xterra_mjlab/bin/python
"$M2_PY" --version
PYTHONPATH="$PWD" "$M2_PY" scripts/train_other.py --help
nvidia-smi
```

`M2_PY` simply stores the verified interpreter's path for the following commands. If opening a new shell, set it again. The server configuration check has already succeeded; section 8 can be rerun using `"$M2_PY"` if desired. Record package versions: local MuJoCo is 3.11.0, the server is 3.10.0, and the historical audit used 3.6.0. Keep evaluation versions fixed within comparisons.

Then run five updates from the original checkpoint as a software check. The output directory must not already exist:

```bash
CUDA_VISIBLE_DEVICES=1 PYTHONPATH="$PWD" "$M2_PY" scripts/train_other.py \
  --algorithm moe \
  --source /data/robotics/toshith/m2_algorithm_sources20260913/go2_rl_gym \
  --out ../runs/20261002_moe_target_bundle_smoke \
  --num-envs 8192 --steps 24 --seed 103001 \
  --resume checkpoints/svanm2_moe/model_90000.pt \
  --updates 90005 --stabilize --action-rate-weight -0.15 --smoke
```

This intentionally uses the original checkpoint's environment count, rollout length and seed, which the resume code checks. `--smoke` shortens episodes to 0.20 s; it checks imports, reward construction, finite execution and saving. **Do not use its checkpoint as the locomotion candidate or the starting point of the real continuation.**

Check smoke `env.yaml`: non-null target clip, both new negative reward weights, unchanged scale/gains/timing. Confirm the new TensorBoard tags exist. RewardManager sanitizes nonfinite reward values internally, so an apparently successful process alone is not proof that every signal was healthy; inspect raw costs and numerical-reset records.

After the command exits, read its completion status:

```bash
"$M2_PY" - <<'PY'
import json
from pathlib import Path
p = Path('../runs/20261002_moe_target_bundle_smoke/progress.json')
r = json.loads(p.read_text())
print('status:', r.get('status'))
print('completed updates:', r.get('completed_updates'))
print('numerical resets:', r.get('numerical_resets'))
PY
```

Expected completion is `status: completed`, `completed_updates: 90005`; inspect any numerical resets rather than ignoring them. If it errors, retain the traceback and resolve it before section 11. Output folders must be new; choose a new name when repeating a run rather than deleting older results.

### Completed smoke test: verified result, 2026-10-02

The pasted terminal output ended with `RECOVERY_READY moe 90000 90005` and returned to the shell. Console update summaries are printed only at multiples of ten (or absolute updates <=5), so none were expected for 90001–90005. Completion was established by reading the server artifacts, not by assuming this startup message alone meant success.

- `progress.json`: **completed**, update **90005**, **zero numerical resets**.
- `resume.json`: restored original `model_90000.pt` and optimizers; original hash matches the previously confirmed checkpoint.
- `env.yaml`: current target clipping, 0.15/0.15/0.30 action scales, 0.005 s physics, decimation 4 and 0.20 s smoke episodes.
- `latest.pt`: saved, 22,704,817 bytes. Do not use this short-episode smoke checkpoint for locomotion evaluation or as the start of the real candidate.
- TensorBoard: all five updates have finite raw/weighted logs for the existing action rate and both new terms.

| Weighted reward rate across smoke updates | Observed range |
| --- | --- |
| Action rate | approximately -0.7821 to -0.7179 |
| Target second difference | approximately -0.0728 to -0.0646 |
| Target saturation pressure | approximately -0.0426 to -0.0361 |
| Linear-velocity tracking | approximately +2.1351 to +2.4568 |
| Angular-velocity tracking | approximately +1.7802 to +1.8655 |

These are population/rollout means, including teacher/student environments. The new terms are nonzero and small relative to the two tracking contributions in this smoke run. This establishes evaluated reward inclusion/scaling; the 0.20 s episodes do not establish good long-episode behavior or reduced jitter.

The plain `python --version` failure means the default shell had no `python` executable on its PATH. The explicit `M2_PY` interpreter worked; no package installation is required to address that particular error. Warp's `cuda:0` means the first visible device after `CUDA_VISIBLE_DEVICES=1`, hence physical A40 GPU 1.

The warnings shown were not fatal: TorchScript deprecation is a future-compatibility notice; XML attach conflicts indicate child robot options are not adopted wholesale. The actual Base Environment table confirms 0.005 s physics and 0.02 s environment/policy steps, so the earlier attachment's parent 0.002 s message should not be mistaken for the final active timestep. The mass-randomization warning names a real modelling assumption (mass changes without inertia changes); retain it for later physical-model investigation rather than changing the reward experiment's dynamics simultaneously.

**This smoke check and the full continuation have now both completed.** Keep their artifacts. Proceed to section 12's evaluation steps; do not rerun the smoke or full launch commands using their existing output directories.

## 11. Combined candidate from 90k: completed run and logs

### Completed run: verified on the server

The earlier screenshot established that updates had begun. The subsequent pasted log reaches 90500, and a direct read-only server check on 2026-10-02 confirms completion:

| Item | Observed value |
| --- | --- |
| Status / process | `completed`; training process has exited |
| Completed update / target | 90500 / 90500, from original update 90000 |
| Current output directory | `runs/20261002_moe_target_bundle_updates90500` |
| Current log | `xterra_mjlab/training_log.txt` |
| Numerical resets | 0 |
| Last losses / action-distribution standard deviations | Finite; standard deviations positive |
| Existing action rate / new target costs | -0.15 / -0.01 second difference / -0.01 saturation |
| Episode length | 20 s; this is the full run, not a smoke run |
| Saved checkpoint | `latest.pt`, update 90500, 22,704,817 bytes, saved 2026-10-02 18:19:12 IST |
| Model / optimizers | Model tensors finite; two optimizer states saved |
| Training duration / peak reported allocation | Approximately 39 min 31 s / 4.024 GiB |

The last console JSON line still says `status: running`: the loop prints that line before saving its final checkpoint and then writes `status: completed` to `progress.json`. The saved status and checkpoint update were checked directly. The trainer hardcodes `checkpoint_validated: false` in its progress record; that field alone does not mean loading or saving failed, and it is not a task-validation result. Training completion does not establish reduced jitter or successful stair ascent. **Do not run the launch command again.**

The suggested `_retry1` path was not used. Monitoring, copying and evaluation instructions below now point to the actual running directory and log.

### What the reward logs show

TensorBoard contains **500 finite entries**, updates 90001–90500, for each inspected raw cost and tracking term. Compare the first 100 updates with the last 100:

| Logged signal | First-100 mean | Last-100 mean | Within-run observation |
| --- | ---: | ---: | --- |
| Raw action-rate cost | 6.1477 | 5.8492 | About 4.9% lower |
| Raw normalized target second-difference cost | 10.1365 | 9.5282 | About 6.0% lower |
| Raw normalized target saturation-pressure cost | 1.5835 | 0.7349 | About 53.6% lower |
| Weighted linear-velocity tracking reward rate | 5.1267 | 5.2414 | Slightly higher |
| Weighted angular-velocity tracking reward rate | 2.0591 | 2.0809 | Slightly higher |

This shows that the new costs were evaluated throughout training and that their averages declined while the two tracking reward averages did not collapse. These are rollout/population means from teacher and student environments, with changing states, commands and terrain curriculum. They are not a controlled comparison with the old policy or a percentage reduction in physical joint jitter. In particular, saturation pressure measures excess request magnitude, not the fraction of samples at a limit. Second differences are not a frequency-isolated 8–30 Hz metric.

The pasted final `termination_fraction` is approximately 0.0399 and `mean_episode_seconds` approximately 19.57. They describe that update's episode outcomes; they do not establish a 96% stair success rate. Full traversal, falls, stalls, heading and joint oscillation still need evaluation.

### Earlier restart history

On 2026-10-02, direct read-only checks found:

- The first full run, `20261002_moe_target_bundle_updates90500`, had `status: stopped_error`, last completed update **90089**, target 90500 and **zero numerical resets**. Its last losses and action-distribution standard deviations were finite. The recorded error message was empty; no traceback was saved, so the cause of this stop is not established.
- No `latest.pt` was present. The trainer saves at updates divisible by 100 or at the final requested update. The first scheduled save would have been **90100**; those 89 completed updates cannot be resumed from the available artifacts.
- During a later check, that full-run directory was absent. The assistant did not remove it. Keep future incomplete runs and logs so failures remain inspectable.
- The separate `xterra_mjlab/training_log.txt` contained `nohup: failed to run command 'CUDA_VISIBLE_DEVICES=1': No such file or directory`. This background launch did not start Python: `nohup` interpreted the environment assignment as an executable. **Use `nohup env CUDA_VISIBLE_DEVICES=1 ...`.** This shell-launch error does not establish a reward-code failure or explain the earlier stop at 90089.
- At that earlier inspection, no `scripts/train_other.py` process was running, GPU 1 was nearly empty, and the proposed `_retry1` directory/log did not exist. The subsequent successful launch supersedes that earlier stopped status.

**This is the combined candidate.** It keeps action rate **-0.15** and adds target second difference **-0.01**, saturation pressure **-0.01**, and the current target clipping. The previous control (-0.10) and previous candidate (-0.15 only) already completed. This command starts one new combined candidate; it does not start another control run. A future matched control must keep the same target profile and disable the two new costs explicitly; changing its folder name would not disable them.

For reference, the successful command used the original 90k checkpoint and the following paths. **It has completed; do not execute this launch block again.** For a future restart, retain existing artifacts and choose a new output directory and log. The log is outside the output directory because the trainer requires that directory not to exist when it starts:

```bash
cd /data/robotics/toshith/vivekananda/m2_moe/xterra_mjlab
M2_PY=/data/robotics/toshith/envs/xterra_mjlab/bin/python
nvidia-smi

nohup env CUDA_VISIBLE_DEVICES=1 PYTHONPATH="$PWD" "$M2_PY" scripts/train_other.py \
  --algorithm moe \
  --source /data/robotics/toshith/m2_algorithm_sources20260913/go2_rl_gym \
  --out ../runs/20261002_moe_target_bundle_updates90500 \
  --num-envs 8192 --steps 24 --seed 103001 \
  --resume checkpoints/svanm2_moe/model_90000.pt \
  --updates 90500 --stabilize --action-rate-weight -0.15 \
  > training_log.txt 2>&1 &
```

`nohup env` allows this background process to continue after an SSH disconnect. Python's optional `-u` flag makes all output unbuffered; the current trainer already flushes its periodic status lines. Do not rerun the launch block while its process is active. If repeating a failed attempt, retain the old artifacts and choose a fresh output path and log name.

Monitor it from the same project directory:

```bash
tail -f training_log.txt
```

With this background launch, Ctrl+C while watching `tail -f` stops the log viewer; it does not stop the separate training process. A background PID alone does not prove training started successfully. Check for `RECOVERY_READY` and advancing `completed_updates`, and inspect the traceback if it exits.

Read saved progress in another terminal (the file appears after initialization):

```bash
cat /data/robotics/toshith/vivekananda/m2_moe/runs/20261002_moe_target_bundle_updates90500/progress.json
```

`--updates 90500` means stop at absolute update 90500: **500 additional updates** from 90000. It does not mean train 90,500 more. The example selects one A40 (physical GPU 1); use another available GPU ID if needed. Keep `--smoke` absent, and keep gains/contact/timing unchanged.

Before committing to more than this pilot budget, inspect the existing tracking reward and the two new weighted contributions. If smoothness costs dominate while useful movement/tracking collapses, end that pilot normally and review coefficients. Lower oscillation achieved by refusing to move is not success. There is no guarantee that 500 updates are sufficient.

Completion requires `status: completed`, `completed_updates: 90500` and a saved `../runs/20261002_moe_target_bundle_updates90500/latest.pt`. Its presence alone is insufficient, because an intermediate `latest.pt` is also saved every 100 updates. A numbered `model_90500.pt` is not expected from the current 5000-update numbered-save schedule. Retain `env.yaml`, `resume.json`, `progress.json`, TensorBoard data, the external log and the automatically copied source alongside the checkpoint.

## 12. Evaluate, then decide whether to investigate actuators

Compare the original 90000, old control 90500, old -0.15 candidate 90500 and the new combined candidate in **the same current viewer settings**. This compares the training package overall, not isolated reward causality. Their older training dynamics differ from the new target profile; a later matched-target continuation without the two new costs would separate the effect of the reward package.

**The local viewer hip edit is complete.** At the user's explicit request, the assistant changed only the four hip entries in `TARGET_MIN`/`TARGET_MAX` from ±1.0472 to ±0.735; thigh/calf limits and other controller settings were retained and syntax checked. Restart the viewer after an edit so it loads the new source. Evaluate every compared checkpoint with the same controller settings; this remains a preliminary viewer comparison until sensor freshness and trace logging are addressed below.

The user's [new recording](../../Videos/2026-10-02%2018-50-10.mp4) was reviewed visually; [note 13](13_CANDIDATE_VIDEO_REVIEW_20261002.md) contains the timeline and evidence images. At recording time 10 s the HUD shows approximately 58° tilt; at 12 s base height is 0.18 m. A later attempt at +0.30 m/s repeatedly works near the lower steps. No full ascent is shown. The recording lacks a visible checkpoint startup line and numerical joint traces, so it cannot establish checkpoint identity or a quantified jitter improvement by itself.

Copy the new output back to a new local directory:

```bash
cd /home/vivekananda/UGP_1_VLM/VLM_Based_Robot_Navigation/Task_3/xterra_mjlab
scp -r guest-isl@172.26.186.222:/data/robotics/toshith/vivekananda/m2_moe/runs/20261002_moe_target_bundle_updates90500 \
  evaluation_runs/
```

Run on your graphical local desktop:

```bash
.venv/bin/python svanm2_moe_stair_sim/run_interactive_sim.py \
  --checkpoint-file evaluation_runs/20261002_moe_target_bundle_updates90500/latest.pt \
  --track 1 --device cuda:0
```

For old comparisons, substitute the corresponding `evaluation_runs/20260927_moe_jitter_control_weight010_updates90500/latest.pt`, `evaluation_runs/20260927_moe_jitter_candidate_weight015_updates90500/latest.pt`, or `checkpoints/svanm2_moe/model_90000.pt` path. There is no viewer reward-weight flag: it evaluates the saved policy without learning.

Verify the printed loaded path, update and device. The viewer's generic banner still says 90,000 regardless of the checkpoint. Track 1 is 10 cm stairs; the saved audit's selected stair videos were 15 cm, so they are background rather than the exact new test.

Use a fresh process for each attempt, initially zero command for about three simulation seconds, then terminal `w` six times for `vx=0.30, vy=0, yaw=0`. Allow up to 30 seconds after command, or stop at a clear fall. The 1.5 m flat approach takes about five seconds even with perfect 0.3 m/s tracking. Require all feet to reach the top while upright; no steering rescue, lane exit or stall counts as ascent success. Repeat under comparable conditions and retain failures.

The current viewer still lacks the audit's complete sensor/reset/command-shaping implementation and quantitative trace logger. Fresh processes address reset carry-over for preliminary comparisons; they do not correct sensor freshness. Visual comparisons are preliminary. Before reporting a numerical jitter reduction, use consistent sensor refresh and a trace-logging evaluator, recording q, unclamped/clamped targets, timestamps, commands, contacts, base motion and outcome. Sample measured joint motion at about 200 Hz to examine the audit's 8–30 Hz band; 50 Hz targets cannot resolve above 25 Hz without defining a held/upsampled setpoint representation.

| Checkpoint | Measured/target oscillation or preliminary video judgment | Tracking/heading | Saturation | Full 10 cm ascent | Falls/stalls/lane exits |
| --- | --- | --- | --- | --- | --- |
| Original 90000 | | | | | |
| Control -0.10, 90500 | | | | | |
| Old candidate -0.15, 90500 | | | | | |
| Combined target/reward candidate, 90500 | | | | | |

Only after this comparison, revisit [actuator investigation in note 11](11_ACTUATOR_ADVICE_REVIEW_AND_GAIN_TRIALS.md): coupled PD response, gain/delay sensitivity, torque-limit semantics and contact assumptions. Rewards cannot guarantee removal of instability from an incorrect physical model. For contact interpretation, MuJoCo documents timestep-dependent positive contact time-constant limits and geom priority in [its modelling guide](https://mujoco.readthedocs.io/en/stable/modeling.html#solver-parameters).

## 13. What to keep and send back for evaluation review

1. The completed run's `latest.pt`, `env.yaml`, `resume.json`, `progress.json`, TensorBoard files and saved source; retain `training_log.txt` too.
2. The manually matched viewer target arrays and the exact checkpoint path printed at startup.
3. Comparable videos or trace logs for the original and new policies, with commands, terrain, simulation version, full traversal and failure outcomes recorded.

Training completion is confirmed; evaluation remains outstanding. The long-term goal remains **less unwanted oscillation while retaining tracking and reliable 10 cm stair ascent**, not merely a calmer video or a larger training reward.
