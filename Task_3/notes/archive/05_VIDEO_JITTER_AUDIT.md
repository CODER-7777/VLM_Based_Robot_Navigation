> Historical note. For current commands and decisions, start at [Task 3](../../README.md).

# MoE 90k video audit — 26 September 2026

The main visible problem is a combination of unstable stair interaction, poor directional tracking, and failure to make useful progress. The selected deployed-limit stair clip repeatedly attempts the lower steps and tips; the filtered clip also tips; the legacy-limit clip stays upright but leaves the stair lane. None demonstrates successful stair ascent.

[Open the visual review with videos and timestamp buttons](../video_jitter_audit_20260926/index.html) · [Observations CSV](../video_jitter_audit_20260926/observations.csv) · [Review manifest](../video_jitter_audit_20260926/review_manifest.json)

## Scope and how to interpret this review

- Source: the eight MP4 files in `moe_jitter_audit_20260921/videos`. These are simulation state replays. The word **hardware** describes the deployed target-bound profile; it does not mean a real-robot camera recording.
- All eight files were decoded completely (3,506 frames total). Visual review used 151 overview frame selections across the full clips and 124 additional detail selections around contact, tipping, and terrain transitions; some selections overlap. It was a frame-sequence review, not continuous playback inspection of every frame.
- All clips are 640×480 at 25 encoded frames/s and contain no audio stream. The five flat/rough/slope clips are 1× replays; the three stair clips are 0.5× replays.
- The overlays begin near simulation time 4.50 s. Approximately: `simulation time = 4.50 + playback speed × video time`. A 10 s point in a half-speed video therefore corresponds to about 9.50 s in the simulated episode. Prefer the on-screen overlay for exact alignment.
- The visible `fell`, `left lane`, and `traversed` captions are whole-run outcome labels already present at the start of a clip. They do not mean the event has happened at that video frame.
- Video observations are distinguished below from saved telemetry. At 25 fps, normal-speed footage cannot reliably resolve the full 8–30 Hz band. Half-speed rendering still cannot establish the whole band from these videos. Small foot motions, normal gait and camera movement must not be labelled as measured high-frequency jitter from appearance alone.
- Companion metrics below are the matching **seed-0 configuration rows**, consistent with observed outcomes and displayed time/tilt. The original renderer was not available to recover an independently verified video-to-trace mapping. All metric sources are linked explicitly.
- Every stair video here uses **15 cm stairs**. There is no 10 cm ascent video in this set. The CSV has 10 cm outcomes, but these videos cannot visually verify that task.

## Observations by video

Times in the following table are **video-player times**, not simulation times.

| Clip | Visible observation | Main times to inspect | Practical inference |
|---|---|---|---|
| [V1 — Flat ground, forward](../../moe_jitter_audit_20260921/videos/flat_hardware_forward.mp4) | The body remains approximately level and the legs keep cycling throughout the sampled sequence. The camera follows the robot, so screen position alone cannot measure forward progress. | 0s; 2s; 10s; 15s | Useful retention case: a reward change should preserve forward tracking and balance. Upright does not mean zero joint oscillation. |
| [V2 — Flat ground, lateral](../../moe_jitter_audit_20260921/videos/flat_hardware_lateral.mp4) | The robot remains upright but its orientation progressively changes, especially in the latter half. The overlay requests lateral motion with zero yaw rate. | 4s; 8s; 12s; 15s | Balance and directional tracking must be scored separately. The overlay reaches 0.6 m/s lateral, above the saved training range of ±0.3 m/s; repeat diagnosis within that range. |
| [V3 — 3 cm rough tiles, forward](../../moe_jitter_audit_20260921/videos/rough_3cm_hardware_forward.mp4) | The robot approaches, steps onto the tiles, crosses the patch, and returns to the surrounding flat surface. Posture varies at transitions, but no tip is visible in the reviewed frames. | 3.8s; 5s; 10s; 13s; 15s | Preserve this capability. Penalizing every rapid movement or impact could remove useful terrain adaptations. |
| [V4 — 20 degree downslope, forward](../../moe_jitter_audit_20260921/videos/slope_down_20_hardware_forward.mp4) | The body pitches with the descent and later returns toward level after leaving the ramp. The robot remains supported in the reviewed sequence, with a visible heading change. | 4s; 6s; 10s; 14s | A body inclination near the terrain slope is not automatically unwanted jitter. Retain successful descent while tracking heading error. |
| [V5 — 20 degree upslope, forward](../../moe_jitter_audit_20260921/videos/slope_up_20_hardware_forward.mp4) | Near the ramp entrance the robot rotates and progresses diagonally/across the slope. Around 12–13 seconds of video it descends off the side and continues on surrounding flat ground. | 4s; 6s; 11.6s; 12s; 13s | This is a lane-exit failure despite survival. An upright-only success test would incorrectly reward this outcome. |
| [V6 — 15 cm stairs, deployed bounds, no filter](../../moe_jitter_audit_20260921/videos/stairs_up_15_hardware_forward_half_speed.mp4) | After reaching the first step, the robot repeatedly changes leg extension and body inclination near the lower steps. Its heading changes, progress remains limited, and the final sequence shows a large rotation into the tip threshold. | 6.3s; 7s; 12.16s; 13s; 20.96s; 21.84s | The task failure includes limited progress, repeated corrections and loss of balance. A smoother action curve alone will not establish successful ascent. |
| [V7 — 15 cm stairs, deployed bounds, 20 ms filter](../../moe_jitter_audit_20260921/videos/stairs_up_15_hardware_forward_filter20ms_half_speed.mp4) | The approach reaches the lower step. The body lowers and rotates near the step, followed by rapid loss of upright posture near the end. It does not complete the staircase. | 6.26s; 8s; 8.84s; 9.4s; 9.72s | Filtering does not rescue this example. It tips sooner after contact than the unfiltered seed-0 reference; shorter failure episodes also complicate whole-run oscillation comparisons. |
| [V8 — 15 cm stairs, legacy bounds, no filter](../../moe_jitter_audit_20260921/videos/stairs_up_15_legacy_forward_half_speed.mp4) | The robot approaches the lower steps, rotates away from its original heading, and travels across/along the lower stair region. By roughly 17–19 seconds of video it moves off onto surrounding flat ground and continues upright. | 5.9s; 8s; 12s; 17s; 20s; 30s | Wider target limits change the failure mode but do not produce valid ascent. Staying upright by leaving the staircase is a failure, not a fix. |

## What the companion measurements add

These are **existing saved simulation metrics**, not angles estimated from the video. Joint and target HF values are the audit's 8–30 Hz RMS metrics over its selected moving samples. They do not describe the entire walking swing. Each row is one seed-0 run, not a population average or a success-rate estimate. Different failure durations mean the rows are not all equal-duration comparisons.

| Clip | Recorded outcome | Joint HF RMS (°) | Target HF RMS (°) | Peak heading change (°) |
|---|---|---:|---:|---:|
| [V1 metrics](../../moe_jitter_audit_20260921/runs/flat__hardware__forward__s0__dt0.005__f0__d0.005__c0.01/metrics.json) | upright | 0.552 | 1.611 | 10.1 |
| [V2 metrics](../../moe_jitter_audit_20260921/runs/flat__hardware__lateral__s0__dt0.005__f0__d0.005__c0.01/metrics.json) | upright | 0.583 | 1.842 | 47.2 |
| [V3 metrics](../../moe_jitter_audit_20260921/runs/rough_3cm__hardware__forward__s0__dt0.005__f0__d0.005__c0.01/metrics.json) | traversed | 0.552 | 1.667 | 12.8 |
| [V4 metrics](../../moe_jitter_audit_20260921/runs/slope_down_20__hardware__forward__s0__dt0.005__f0__d0.005__c0.01/metrics.json) | traversed | 0.592 | 1.828 | 27.9 |
| [V5 metrics](../../moe_jitter_audit_20260921/runs/slope_up_20__hardware__forward__s0__dt0.005__f0__d0.005__c0.01/metrics.json) | left lane | 0.748 | 2.163 | 90.7 |
| [V6 metrics](../../moe_jitter_audit_20260921/runs/stairs_up_15__hardware__forward__s0__dt0.005__f0__d0.005__c0.01/metrics.json) | fell | 1.445 | 3.662 | 56.9 |
| [V7 metrics](../../moe_jitter_audit_20260921/runs/stairs_up_15__hardware__forward__s0__dt0.005__f0.02__d0.005__c0.01/metrics.json) | fell | 0.963 | 1.942 | 36.9 |
| [V8 metrics](../../moe_jitter_audit_20260921/runs/stairs_up_15__legacy__forward__s0__dt0.005__f0__d0.005__c0.01/metrics.json) | left lane | 0.856 | 2.542 | 87.2 |

Heading changes come from [suite_summary.csv](../../moe_jitter_audit_20260921/suite_summary.csv); the linked per-run JSON contains the other metrics.

The lateral clip remains upright despite about 47° of recorded peak heading change. The upslope and legacy-stair cases have about 91° and 87° respectively and leave the lane. These examples show why survival, forward progress and direction need separate scores.

## The three stair clips: contact, repeated attempts and outcome

| Configuration, seed 0 | First feature contact (simulation s) | Tip threshold (simulation s) | Time from contact to tip | Valid traversal |
|---|---:|---:|---:|---|
| Deployed bounds, no filter | 7.655 | 15.415 | 7.760 s | No |
| Deployed bounds, 20 ms filter | 7.630 | 9.365 | 1.735 s | No |
| Legacy bounds, no filter | 7.450 | No tip recorded in 24 s | Not applicable; leaves lane | No |

The unfiltered sequence reaches the stair around video 6.3 s, repeatedly lifts/lowers and extends/retracts near the lower steps, then tips near video 21.8 s. The 20 ms filtered clip reaches contact around video 6.26 s, lowers and rotates near the step, and ends near video 9.72 s. Its last encoded frame is slightly before the saved tip-threshold timestamp; the trace determines the recorded failure.

The legacy clip turns across the stair region and moves onto surrounding flat ground around video 17–19 s. Remaining upright is real, but it achieves that without completing the stair task.

![Balance and progress in the three saved stair runs](../video_jitter_audit_20260926/stairs_balance_and_progress.png)

This plot uses full saved traces from simulation time 4.5 s onward; it extends beyond the video crop where the trace exists. The horizontal feature-end line marks the world-x endpoint of the staircase. Base x alone is not the traversal test: all feet must pass while staying in the lane. The legacy run's increasing lateral displacement is consistent with the visible departure.

The filtered run has a lower whole-run HF number yet fails sooner in this pair. This supports rejecting it as a demonstrated task fix. It does not prove filtering always worsens ascent: failure windows differ and the sample is small. The second recorded filtered start also tipped, at simulation 16.605 s; that additional result comes from telemetry, not another video reviewed here.

## Close visual evidence

- [First stair contact, video 6.16–7.96 s](../video_jitter_audit_20260926/stair_first_contact_detail.jpg): changing foot placement and body orientation near the edge.
- [Repeated attempt, video 12.16–13.96 s](../video_jitter_audit_20260926/stair_repeated_attempt_detail.jpg): body lifting and lowering while remaining near the lower steps.
- [Unfiltered tip, every encoded frame from video 20.96–21.84 s](../video_jitter_audit_20260926/stair_tip_detail.jpg).
- [Filtered tip, every encoded frame from video 8.84–9.72 s](../video_jitter_audit_20260926/filtered_tip_detail.jpg).
- [Upslope edge transition, video 11.60–12.48 s](../video_jitter_audit_20260926/slope_lane_exit_detail.jpg).
- [Rough-ground entry, video 3.80–4.68 s](../video_jitter_audit_20260926/rough_entry_detail.jpg).

The detail images are crops of actual decoded frames. Apparent foot/riser interaction does not by itself identify toe collision, slip, contact force, or the exact supporting foot. Use the contact/force/feet arrays and geometry for those questions.

## What is supported, and what remains a hypothesis

| Claim | Status and evidence |
|---|---|
| The policy can remain balanced on some terrain | Supported by the flat, rough and downhill sequences and their recorded outcomes. |
| Stair difficulty appears during interaction with the lower steps | Supported by the video sequence and recorded first-contact times. |
| The staircase problem includes turning and lack of progress | Supported; the legacy clip and upslope clip leave the lane, and deployed-bound ascent does not complete. |
| Filtering is already a successful fix | Not supported. The filtered stair video tips. |
| Wider calf target limits solve ascent | Not supported. The legacy-bound clip leaves the lane. |
| Saturation deserves measurement | Supported by saved metrics, but it is not sufficient by itself to explain failure. For example, the upright flat-forward run records RR-calf target clipping in about 52.1% of moving samples; the failed unfiltered stair run records about 55.0%, and the filtered run about 67.5%. |
| The action-rate reward is too weak | A testable hypothesis; the videos do not determine the right coefficient. |
| A particular motor is defective or a particular foot slips | Unresolved by these rendered views. |
| Increasing inference to 100 Hz would fix this | Unresolved; none of these videos tests that change. |
| An expert switches abruptly and causes shaking | Unsupported by these videos; the inspected model uses continuously weighted experts. |

## Implications for your manual reward experiments

1. Preserve the successful behaviours: keep flat, 3 cm rough-ground and downslope evaluations as checks against regressions.
2. Require actual 10 cm staircase completion, lane retention, and command tracking. Add matched 10 cm recordings; the current 15 cm clips are diagnostic examples only.
3. Compare an unchanged-reward continuation with your `action_rate_l2 = -0.15` candidate, both from the original 90k checkpoint, using equal training budgets. This is still an experiment, not a demonstrated solution.
4. Log both the raw action-change quantity and its weighted reward contribution. A larger negative weight can make a reward curve look worse even when the physical behaviour is unchanged.
5. Examine first contact separately from approach: target changes, calf target clipping, joint torques, foot contact and speed tracking. Compare equal-duration pre-contact and post-contact windows where both runs have data; keep failed runs in the outcome table.
6. Investigate uncommanded yaw and lateral departure before adding a blanket turning penalty. Existing angular-velocity tracking already rewards following the requested yaw rate. A body-frame forward command can continue to be followed while the robot's world heading drifts; full lane/traversal scoring remains necessary.
7. Consider target second-difference or saturation penalties only as separate later tests. Avoid indiscriminately suppressing all leg extension, contact acceleration, or clearance movement needed for lifting onto steps.

The immediate conclusion is to evaluate **smoothness plus useful progress plus balance**, with matching control semantics. The videos narrow where to inspect the controller, but do not identify one exclusive reward, actuator or contact cause.

## Qualification of the supplied problem-fixability table

The table supplied during this review is useful, with these corrections:

| Item | More precise status | What to do | Is it alone a proven jitter fix? |
|---|---|---|---|
| Wrong checkpoint | Not supported for the specific recorded policy replay; this does not verify an arbitrary later simulator launch. | Record the checkpoint path/hash and verify that the deployed student export matches the trained checkpoint in each evaluation. | No new fix is implied; keep the verification. |
| Calf target-limit mismatch | The mismatch is correctable; actual hardware mechanical range and software command bounds are different quantities. | Match all deployed target bounds in the evaluation path. Inspect training action processing, then introduce any required target-bound correction deliberately and compare both reward arms under that same chosen contract. Preserve the original action-history convention. | No. The deployed-bound stair clip still fails. The legacy clip also fails by leaving the lane. |
| Contact time constant / physics timestep | The requested-versus-effective setting can be made explicit. The physically correct contact properties remain uncalibrated. | First keep the explicit 10 ms contact setting and fixed policy/PD rates while checking physics resolution. Test a 2 ms setting separately only if justified; reducing the timestep and stiffening contact simultaneously confounds two changes. | No successful general fix is demonstrated. The videos do not isolate the contact model as the sole cause. |

For positive `solref` time constants, MuJoCo's default reference-safety rule prevents a time constant below twice the physics timestep. Thus a 5 ms physics timestep imposes a 10 ms floor; a timestep of 1 ms or less can permit a 2 ms request under that rule. Permitting the request does not validate its physical realism or numerical accuracy. [MuJoCo 3.6 solver-parameter documentation](https://mujoco.readthedocs.io/en/3.6.0/modeling.html#solver-parameters).

A 1 ms physics timestep means 1,000 integration steps per simulated second. It does not require 1,000 policy updates or 1,000 external PD updates; keep the intended policy and PD schedules explicit during a resolution experiment.

The table's phrase “target oscillation also occurs in air/free motion” is not established by this video review. A swinging foot does not make the whole robot contact-free. That statement needs analysis conditioned on recorded contact states and gait phase, with the frequency measure distinguished from normal stepping.

## Evidence and provenance

This is a new review of the existing 21 September audit, prepared on 26 September. No new simulation or training result is claimed. Original report: [REPORT.md](../../moe_jitter_audit_20260921/REPORT.md). Original dashboard: [index.html](../../moe_jitter_audit_20260921/index.html). Source file hashes, frame selections and companion run IDs are recorded in [review_manifest.json](../video_jitter_audit_20260926/review_manifest.json).

The original evaluator source was not found in the searched local repository. The currently available interactive stair controller still has the legacy calf upper bound `+0.5 rad`. Therefore a new run of that controller should not automatically be treated as a reproduction of the dashboard's deployed-bound videos.
