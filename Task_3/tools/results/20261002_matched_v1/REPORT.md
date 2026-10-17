# Fresh local MoE stair-failure analysis — 2026-10-02

**The candidate has not solved stair ascent. The fresh traces identify repeated low-foot contact with the first riser, followed by corrective motions, poor progress and heading loss. They do not identify one universal cause of jitter.** Increasing smoothness penalties, changing transmission ratios, or increasing motor effort is not justified as the next automatic step.

This report was generated from new local simulations and inspected plots. The September audit supplied hypotheses; its conclusions were not assumed to be ground truth. Neither this report nor a simulator can establish the real robot's physical parameters without measurements.

Read the [central-start dashboard](index.html), [three-start comparison](../20261002_stair_repeats_v1/index.html), and [measurement/tool guide](../../README.md). The supplied screen recording is separately reviewed in [note 13](../../../notes/archive/13_CANDIDATE_VIDEO_REVIEW_20261002.md); these simulations are **not a replay** of its manual commands or resets.

## 1. What was actually run

- Eight initial runs: original 90000 and candidate 90500, each on flat ground and 10 cm stairs, each with existing viewer observations or refreshed observations.
- Twelve additional stair runs: both policies × both observation modes × three matched starting poses. Four repeat the central stair cases; eight add small offsets. Thus there are **20 evaluation executions, 16 distinct conditions**, plus a separate 5 s smoke run and validation tests.
- Starting poses: center; y −0.03 m/yaw −0.02 rad; y +0.03 m/yaw +0.02 rad. These are deliberate sensitivity cases, not random seeds or statistical success-rate estimates.
- Command: MoE active at zero command for 3 s, ramp over 1 s to forward 0.30 m/s, zero lateral/yaw command. Maximum 30 simulation seconds. Fresh simulation state each time; no steering rescue.
- Same current target bounds, kp=20, kd=0.7, coupled transmission, 12/12/24 Nm joint limits and 5 ms physics timestep for both policies. Policy inference every 20 ms.
- RTX 3050 Laptop GPU inference; standard MuJoCo 3.11.0 CPU physics; Torch 2.14.0+cu130; NumPy 2.4.6. No server access or training was needed for this investigation.

| Checkpoint | SHA-256 |
| --- | --- |
| Original `model_90000.pt`, saved update 90000 | `440bbb28d554f75db38bfd163351c04ea4a32d9d06764c37b7e6071d41daa5cb` |
| Combined candidate `latest.pt`, saved update 90500 | `06f8f2788367b89df9cf37a1c7091749ceedf7686cc5903b46a8e9381367382a` |

Every case includes its exact path, hashes, configuration, numeric trace, named contact records and code snapshots. The scene hash is `62934ac0a698ae6ea9716a882c975c83642dec7aab53b934a8c08df47597f3bf`.

## 2. The most useful incident: the candidate's first contact

Start with [the event plot](candidate90500_stairs_viewer_start0/08_first_contact.png), [the full motion plot](candidate90500_stairs_viewer_start0/01_motion.png), and [the event data](candidate90500_stairs_viewer_start0/first_contact_analysis.json).

| Observation | Fresh measured evidence | Interpretation |
| --- | --- | --- |
| First loaded stair contact | At **9.730 s**, `FL_foot` meets the vertical face of `step_1_1`; normal force approximately 29.3 N | It meets the riser before landing on the tread |
| Foot height at contact | Foot center z=**0.0563 m**; radius=0.022 m | The foot bottom is about 0.0343 m high. Clearing a 0.10 m flat top requires roughly 0.122 m center height, plus any desired margin |
| Current target pose also low | Holding the recorded body pose fixed and setting joints to their clamped targets gives FL center z=**0.0571 m** | At this instant the requested joint pose does not supply enough height to clear the riser. This is a static geometry check, not a prediction of dynamic motion |
| No first-leg target clipping at this instant | FL hip/thigh/calf requested-minus-clamped targets are all zero | The immediate low-foot event is not explained by FL target clipping at that sample |
| No first-leg torque clipping at this instant | FL raw torques approximately **1.29, 0.04, 0.27 Nm**, below 12, 12, 24 Nm | Raising torque limits would not change these three applied torques at this sample |
| Corrective motions follow | Larger target changes, foot force bursts and body tilt appear after contact; front feet reach some lower treads | The policy reacts, but useful coordinated ascent is not maintained |
| Heading and progress deteriorate | Base x peaks at **0.058 m**, then retreats; heading reaches about **+116°**; lane-exit stop at **17.28 s** | Some body-forward walking continues while movement along the staircase fails |
| Rear support differs | FL/FR have recorded top/diagonal contacts through step 2, RR through step 1; RL has no loaded step contact in this run | Inspect coordination and support transfer, not just whether one front foot can step up |

The base starts at x=−1.5 m; the first riser is x=0 and the top platform starts at x=3.6 m. Base x alone is not the traversal criterion. The conservative full-traversal check requires all feet to reach the platform region while upright and within the lane.

Across **all twelve distinct stair cases**, the first loaded stair contact is a front-foot/riser event with foot-center height approximately **3.7–6.3 cm**. At those first-contact samples the contacting leg has neither target removal nor torque clipping. This is a repeatable observation in this model, not merely one selected frame. It does not rule out clipping elsewhere in the trajectory or indirect effects of limits on the learned gait.

## 3. A controlled comparison shows the terrain matters

The flat tests disable only the compiled stair/platform/curb collisions. The same checkpoint, commands, spawn and controller remain. In the central candidate/viewer pair, measured joint trajectories first differ by more than 1e-6 rad at **9.735 s**, one physics step after the first loaded stair contact. They match before that event.

Compare [the paired motion/cost plot](candidate90500_stairs_viewer_start0/09_flat_comparison.png). In the **same six-second interval starting at the stair-contact time**, mean per-joint measured 8–30 Hz RMS is:

| Policy and observation mode | Flat collisions only | Stairs enabled |
| --- | ---: | ---: |
| Original, viewer timing | 0.369° | 0.899° |
| Candidate, viewer timing | 0.331° | 0.833° |
| Original, refreshed observations | 0.360° | 1.176° |
| Candidate, refreshed observations | 0.451° | 0.946° |

For the central candidate/viewer case, the stair value is approximately **2.52 times** its matched flat value. The controlled terrain intervention produces a different closed-loop trajectory and more rapid joint motion. This does **not** distinguish contact stiffness, reactive policy behavior, required impact response and actuator dynamics as the sole cause. The 8–30 Hz band includes rapid corrective movements and impact transients, not only unwanted steady vibration.

## 4. Did the reward candidate reduce jitter?

**Not consistently enough to call it a jitter fix.** The fixed 4–8 s interval is before stair contact in every tested case and gives equal-duration comparisons. See the [paired-start plot](../20261002_stair_repeats_v1/paired_starts.png).

| Observation mode | Start | Original joint HF RMS | Candidate joint HF RMS |
| --- | --- | ---: | ---: |
| Viewer | Center | 0.270° | 0.222° |
| Viewer | Negative offset | 0.248° | **0.390°** |
| Viewer | Positive offset | 0.398° | 0.267° |
| Refreshed | Center | 0.298° | **0.386°** |
| Refreshed | Negative offset | 0.326° | 0.274° |
| Refreshed | Positive offset | 0.265° | **0.319°** |

The central viewer case improves by about 18%, but the three-start viewer mean improves by only about **4.1%**. The refreshed-observation mean is about **10.2% higher** for the candidate. Three starts are too few for a general performance claim, and the direction changes across cases.

Other candidate effects are more consistent in this early-motion window:

- Target removal falls in every paired case: mean joint-sample fractions **13.71% → 9.90%** for viewer observations, and **14.13% → 10.10%** for refreshed observations. These average across all twelve joints; calf-only rates can be much higher.
- Forward body-speed RMSE improves in every pair: three-start means **0.127 → 0.098 m/s** and **0.143 → 0.097 m/s**, respectively.
- Stair traversal still fails in every tested case. Better speed tracking and less saturation pressure do not guarantee foot placement, support or heading control.

Window choice matters: for example, using the entire unequal-duration approach gives candidate/viewer HF RMS 0.365° versus original/viewer 0.267°. That is a different comparison from fixed 4–8 s and must not be hidden. Raw phase metrics are saved so conclusions can be checked rather than selecting the most flattering window.

The candidate changes rewards and target clipping together and is only one trained checkpoint. We cannot assign these effects to a particular reward from this comparison.

There is also a **startup posture difference before any stair contact**. During 1–3 s of zero command in the central viewer cases, original mean foot normal forces are approximately `[35.3, 12.5, 11.4, 39.6] N` for FL/FR/RL/RR. The candidate gives `[42.1, 9.8, 0.0, 47.0] N`, with its RL foot about **6.3 cm above the floor**. It is standing on three contacts in this interval while the original has four. See the beginning of [the candidate contact plot](candidate90500_stairs_viewer_start0/04_contacts.png). This motivates inspecting zero-command posture, reward gating and startup/history sensitivity; it does not by itself explain later stair failure. The protocol uses the MoE immediately at zero command, not a separate hardware stand/blend sequence.

## 5. Observation timing is a real sensitivity, not a proven fix

The existing controller reads integrated `qpos/qvel` alongside derived gyro/orientation values left by the previous dynamics solve. MuJoCo documents its compute-then-integrate step order. The alternative condition refreshes measurements on a copied state before constructing each policy observation; live physics stepping is unchanged. [MuJoCo simulation documentation](https://mujoco.readthedocs.io/en/stable/programming/simulation.html)

For **each policy**, the three viewer-timing stair outcomes were two lane exits and one tip. The refreshed-observation outcomes were two incomplete timeouts and one lane exit. No condition completed the stairs. Sensor timing changes the trajectory materially, but refreshed observations did not uniformly lower joint HF RMS or solve ascent.

This supports verifying observation timing in the evaluation and training pipelines. It does not justify inserting an untested controller change or claim that refreshed observations match real hardware latency.

## 6. What this says about J_LEG, gains and limits

Changing hip/calf target limits does not require changing `J_LEG`. The [guide explains the mapping and distinguishes it from the foot Jacobian](../../README.md#do-the-changed-angle-limits-require-a-changed-j_leg). Current training and viewer code use the same gear/belt mapping. Its physical accuracy remains a calibration question.

Target saturation remains present elsewhere. For example, in the central candidate/viewer approach, calf target-removal fractions are approximately FL 24.1%, FR 25.0%, RL 17.8%, RR 52.0%. Yet none of the contacting leg's targets is clamped at the first riser impact. Both observations can be true: frequent limiting deserves study, while that particular initial collision cannot be blamed on instantaneous limiting of that leg.

Torque clipping also occurs later but is sparse on average. In the candidate/viewer first six seconds after contact it affects about **0.40% of joint-samples**; the largest individual rate is RL thigh at about 1.6%. The [torque plot](candidate90500_stairs_viewer_start0/03_torques.png) and trace preserve short bursts that averages can hide. This is insufficient evidence that a universal lack of available torque is the main problem. Gains, transmission assumptions and contacts could still affect response even without torque clipping.

In the supplied screenshot, MuJoCo's **Control** values are torque-motor inputs for this model, not the policy's joint-position targets. Use the logged `requested`, `target` and `q` arrays to check angle limits.

## 7. What to investigate next, and exactly where

| Priority | Investigation | Evidence motivating it | Files/data to inspect |
| --- | --- | --- | --- |
| 1 | Agree on and verify observation timing, joint order, action history and evaluation protocol before another reward comparison | Freshness intervention materially changes outcomes | [controller.py](../../../xterra_mjlab/svanm2_moe_stair_sim/controller.py), [m2_algorithm_env.py](../../../xterra_mjlab/scripts/m2_algorithm_env.py), [record.py](../../jitter_analysis/record.py) |
| 2 | Measure clearance and horizontal foot motion before the first riser, then inspect the existing clearance reward's actual contribution | Every tested first-contact foot is too low to clear the riser directly | `08_first_contact.png`, `contacts.jsonl`; saved [candidate env.yaml](../../../xterra_mjlab/evaluation_runs/20261002_moe_target_bundle_updates90500/env.yaml); local `mjlab/tasks/velocity/mdp/rewards.py::feet_clearance` |
| 2a | Check zero-command posture and reward gating before movement | Candidate RL foot is unloaded and elevated in the central zero-command interval | Beginning of `04_contacts.png`, `q/target/command` in `trace.npz`; standing pose and command-gating terms |
| 3 | Inspect support transfer and zero-yaw tracking after contact, separately from forward body speed | Front-foot progress can coexist with rear-foot failure and >90° heading loss | `04_contacts.png`, `05_feet.png`, `01_motion.png`; [env_cfgs.py](../../../xterra_mjlab/xterra_mjlab/tasks/velocity/config/svanm2/env_cfgs.py) tracking, pose, contact and clearance terms |
| 4 | Verify how often the **student** experiences appropriate ascending stairs and whether its training losses track those episodes | Deployment uses student history; mixed training statistics and smoothness costs do not establish student stair competence | [train_other.py](../../../xterra_mjlab/scripts/train_other.py), [m2_algorithm_env.py](../../../xterra_mjlab/scripts/m2_algorithm_env.py), saved terrain settings and per-reward logs |
| 5 | If commanded lift is adequate but actual lift repeatedly fails, run isolated gain/contact/delay sensitivity tests | Corrective lift pulses can show target/actual lag after collision | `02_angles.png`, `03_torques.png`, `08_first_contact.png`; [svanm2_actuator.py](../../../xterra_mjlab/xterra_mjlab/actuators/svanm2_actuator.py) |

The saved candidate configuration already sets clearance `target_height: 0.1`. The inspected **local** `feet_clearance` implementation penalizes `sum(abs(measured_height − target_height) × horizontal_foot_speed)`, gated by active commands. Consequently, 0.1 is a reward preference, not a hard guarantee of a 10 cm swing. This term is not simply squared angle error; it also becomes small when horizontal foot speed is small. Before increasing its weight, verify height-sensor semantics, stationary-foot behavior and the exact server package version used for training. Do not blindly replace 0.1 with 0.122: the reward sensor's reference differs from the sphere-center geometric test above.

The deployed student input contains command and proprioceptive history, not an explicit stair-height map. A blind policy can learn contact-triggered stair adaptation; low initial swing does not prove ascent is impossible. Our data show that this adaptation is not reliably successful here.

**Next reward decision:** examine clearance/placement, support and heading contributions alongside smoothness. Do not increase all penalties together: that could discourage the corrective lift needed after contact. Keep current candidate and original checkpoints frozen as reference models. Actuator tuning remains a later, separately measured experiment.

## 8. Validation and remaining limits

- Four test methods passed: exact passive trajectory equality for 240 CPU physics steps; known-frequency RMS/units with minimum-window and Nyquist guards; traversal criteria; and transmission/gain mapping.
- Every recorded physics step checks applied actuator torque against reconstructed clipped coupled-PD torque. All 20 evaluation runs completed without reported MuJoCo warnings or nonfinite-state errors. Physical task failures are retained as outcomes.
- Checkpoint update and hash are recorded. Central stair reruns reproduced the same reported metrics; offsets produced different outcomes, showing why one video is inadequate.
- Joint motion sampled at 200 Hz supports the chosen 8–30 Hz band. Policy-tick targets sampled at 50 Hz use **8–20 Hz**, not an invalid >25 Hz target spectrum. Different-band amplitudes must not be presented as an equal-band comparison.
- Clearance and static target poses have explicit geometric limitations. No motor temperature, real torque sensor, or synchronized hardware stair record was collected. A simulated force peak is not a measured hardware impact.
- Contact dynamics, real delay, friction and actuator calibration remain unvalidated. A robot-like failure in this simulation alone cannot establish a hardware root cause.
- Only new local tools, their results and documentation were added for this analysis. Existing controller/training/actuator settings were not changed during these experiments. The earlier explicitly requested hip-bound edit predates this comparison. No server files were altered.

**Supported conclusion:** the candidate improves early-motion speed tracking and reduces target removal in these cases, but neither reliable jitter reduction nor 10 cm stair ascent is demonstrated. The most defensible next work is to address verified observation-contract details and inspect foot clearance/support/heading around first contact using these recorded signals.
