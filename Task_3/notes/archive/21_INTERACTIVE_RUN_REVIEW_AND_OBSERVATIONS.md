> Historical note. For current commands and decisions, start at [Task 3](../../README.md).

# Your interactive runs: findings, observations and next steps

Updated 2026-10-03. **Follow this note now.** Notes 16–18 remain background proposals; note 19 tells you how to record. This note reviews all currently saved interactive data and explains the new short plots.

## What we completed

- [x] Read all five saved interactive sessions: **41 attempts**, about **12.4 minutes** of measurements.
- [x] Check checkpoint identity, target bounds, command inputs, reset separation, timestamps, contacts and numerical warnings.
- [x] Plot normalized target second differences beside actual rapid joint motion and applied torque.
- [x] Inspect actual saved training logs to confirm whether the penalty was used and decreased.
- [x] Record your observation: **“Much stronger after stair contact.”**
- [ ] Fill the remaining observation cells below.
- [ ] Record original 90000 and current 90500 using matching commands and controller settings.
- [ ] Verify training foot-height and delay/sensing semantics, then choose the next training experiment.

No controller, reward, checkpoint or server file was changed for this review. No new simulated trajectory was generated. The new figures were calculated from your saved keyboard-controlled runs. The raw recordings are retained under `tools/results/interactive/`; the review is separate under `tools/results/interactive_review_20261003/`.

## Open the new dashboard

From Task_3, if your existing server is not already running:

```bash
cd /home/vivekananda/UGP_1_VLM/VLM_Based_Robot_Navigation/Task_3
python3 -m http.server 8000 --bind 127.0.0.1
```

Open <http://127.0.0.1:8000/tools/results/interactive_review_20261003/index.html>.

The [full report](../../tools/results/interactive_review_20261003/REPORT.md) includes methods and interpretation limits. [Every attempt](../../tools/results/interactive_review_20261003/attempts.csv) is listed, and the [observations worksheet](../../tools/results/interactive_review_20261003/observations.csv) has one row per attempt and blank columns for your comments.

## What I understood from these runs

**Shaking becomes much stronger when the feet encounter stairs.** For `user_run_03/attempt_006`, mean measured joint 8–30 Hz RMS is approximately **0.201° before contact versus 1.193° after**. For the tighter-limit ascent, it is **0.337° versus 1.379°**. These are averages of a selected rapid-motion band, not full leg swings. The before/after intervals differ in duration and may contain command changes; they describe these attempts, rather than proving a single cause.

**The first foot hits the face of the step before it has lifted enough to clear the tread.** Across all 26 entrance-start attempts that reached the stairs, first vertical-face foot-center heights are **2.40–9.79 cm**. Directly clearing the 10 cm top with a 2.2 cm-radius foot requires approximately **12.2 cm** center height. This gives us a concrete event to improve: lift/placement before collision, then coordinated support and recovery. Some low-hit attempts recover and climb partway, so this is not proof that low contact inevitably causes failure.

**Your observation that wider limits sometimes climb farther is plausible and appears in the data.** One wider attempt reaches body x=2.547 m before falling; another reaches 1.967 m before the recording ends. The first tighter ascent reaches 0.381 m; the latest tighter session reaches at most 0.734 m. However, some wider attempts use 0.5 m/s while the tighter one uses at most 0.3 m/s. The latest session adds four tighter moving ascents, bringing the total to five. Their commands and starts still differ. We need matching trials before blaming the limits. No recorded entrance-start attempt completes all 12 steps; top-start descent is a different task.

**All sessions use the same 90500 checkpoint.** Wider and tighter runs therefore compare controller/settings/input differences, not different learned policies. They cannot show whether training from 90000 helped. The common checkpoint hash is recorded in the report and manifests.

The fifth session, `with_the_hardware_limits_02`, was included after it finished during this review. Its 0.5 m/s `attempt_005` still makes little ascent progress and shows HF RMS rising from 0.429° to 1.646° after contact. Faster commands alone do not solve climbing. Its long `attempt_002` uses steering, and `attempt_008` descends then walks on flat ground; separate those phases when interpreting the graphs.

## Why we still see jitter despite the second-difference penalty

Your idea is useful, but the quantity needs a precise name:

| Quantity when the signal is joint position | Meaning |
| --- | --- |
| First derivative | Angular velocity |
| Second derivative | Angular acceleration |
| Third derivative | Angular jerk |

The implemented penalty is **a normalized second difference of final commanded position targets**:

```text
increment_now    = q_cmd[t]   - q_cmd[t-1]
increment_before = q_cmd[t-1] - q_cmd[t-2]
second_difference = increment_now - increment_before
cost = sum((second_difference / action_scale)^2)
```

It discourages changing the requested increments abruptly. Example: `0°, 5°, 10°` has equal increments and zero second difference. `0°, 5°, 0°` suddenly reverses and has a larger cost. This is acceleration-like at a fixed update interval, not a third-derivative jerk term. The implementation does not divide by the timestep squared.

**It penalizes what we ask the motors to do, not what the joints actually do.** A smooth request can still produce a collision and a large physical response. The policy is also rewarded for moving, tracking and other behaviors; smoothness is a tradeoff, not a hard constraint. Training aims to improve expected reward across its sampled states, not to guarantee no vibration at every stair edge. Increasing the penalty too far can also make useful stepping/recovery worse.

The saved training logs show the raw target second-difference cost fell from **10.169 to 9.501**, comparing the first and last 50 updates: **6.57% less**. The action-rate cost also decreased by **5.57%**. The penalty is active; it produced a modest aggregate trend, not a demonstrated elimination of stair jitter. These training averages are not a student-only stair analysis or a controlled comparison of one reward change.

Also, the wider viewer bounds differ from the tighter training bounds. The cost of final clamped targets can change just because the permitted range changed. A clipped plateau can have little second-difference cost even while raw requests vary; this is why the separate saturation-pressure cost also exists.

**The earlier three-figure interactive dashboard did not explicitly plot the second-difference cost.** That is why you could not directly inspect it there. The new short figures now show this cost alongside physical motion. We did not silently add a new reward.

## Inspect these images in this order

| Order and image | Read it like this | Question for your observation |
| --- | --- | --- |
| 1. [Training penalties](../../tools/results/interactive_review_20261003/training_penalties.png) | Top left is raw target cost; lower right is its negative weighted contribution. Lower raw cost and a contribution nearer zero indicate less punishment. | Is the improvement modest or a complete elimination? It is modest. |
| 2. [Wider-limit ascent, attempt 006](../../tools/results/interactive_review_20261003/user_run_03_attempt_006_signal_chain.png) | Red dotted line is first riser contact, **8.325 s after reset**. Read each panel before and after it. | Does rapid measured motion become larger after contact? Your answer: yes. |
| 3. [Tighter-limit ascent, attempt 001](../../tools/results/interactive_review_20261003/with_the_hardware_limits_01_attempt_001_signal_chain.png) | First riser contact at **11.755 s**. Later rear-right thigh torque reaches its ±12 Nm bound and the actual angle departs markedly from the target. | Is there a contact/recovery problem as well as changing targets? Which comes first in the unfiltered signals? |
| 4. [First-riser heights](../../tools/results/interactive_review_20261003/first_riser_clearance.png) | Bars are measured foot-center heights at first face contact, not desired heights. Green is approximate direct clearance of the first tread. | Was lift early/high enough before the face hit? |
| 5. [Cost versus measured motion](../../tools/results/interactive_review_20261003/cost_vs_jitter.png) | Each dot is a four-second constant-command upright interval. Right means more abrupt target increments; up means more rapid actual joint motion. | Do they tend to rise together? Yes; this supports investigation, not proof of causation. |
| 6. [All ascent progress](../../tools/results/interactive_review_20261003/all_ascent_progress.png) | Top bars are body progress; bottom bars are maximum requested speed. | Am I comparing equal commands? Does progress actually reach the platform? |

The four-panel event plots mean:

1. **Requested / clamped / actual angle:** what the policy asks, what limits permit, and what the joint does. Light-blue versus orange separation means target limiting; green versus orange separation means tracking error.
2. **Second-difference costs:** blue uses final clamped targets; orange uses clipped actions. Both sum all 12 joints, without weights. Higher peaks mean more abrupt changes in requested increments. The plotted cost is recomputed from recorded actions/targets, not a new training reward measurement.
3. **Actual 8–30 Hz component:** an analysis-only bandpass of one measured joint. Larger excursions mean more rapid motion in that band, including impact and recovery. This does not modify the controller.
4. **Torque / riser force:** blue is actual torque for the selected joint; red is force summed over all feet hitting vertical stair faces. Read the separate Nm and N axes.

The selected joint is the one with the largest rapid-motion RMS in that short window. The cost and force panels combine multiple joints/feet, so a peak need not originate in the displayed joint. The analysis filter is zero-phase and can spread an impact around its timestamp; use raw unfiltered angles/contact timestamps for ordering, not the filtered panel.

## Write your observations here

Keep **observation**, **possible explanation**, and **next check** separate. Write timestamps relative to this attempt's reset.

| Run | Recorded fact | Your visual observation | Possible explanation, not a proven cause | Next check |
| --- | --- | --- | --- | --- |
| `user_run_03/attempt_006` | First riser hit 8.325 s; phase HF RMS 0.201° → 1.193° | User: much stronger after stair contact | Collision disturbs the policy–controller–contact loop | Which foot hits; targets/torque before and after; foot lifting before hit |
| `with_the_hardware_limits_01/attempt_001` | First riser hit 11.755 s; phase HF RMS 0.337° → 1.379° | User: much stronger after stair contact | Restricted targets and contact recovery may interact | Inspect target clipping separately from later torque clipping |
| `user_run_01/attempt_005` | Body reaches x=2.547 m; sustained failure at 14.295 s | Add what you saw before the fall | Later support/heading/recovery may fail despite partial progress | Open its full overview and foot/force plots; compare front and rear support |
| `user_run_03/attempt_013` | Body reaches x=1.967 m; no sustained failure threshold before recording ends | Add whether it paused, drifted or was stopped | Incomplete progress; no automatic stall claim | Inspect last commands, actual vx, body x, heading and foot contacts |
| `user_run_02/attempt_003` | Top spawn, then descent | Add descent observations | Descending requires different foot placement/support | Compare ascent and descent separately |
| `with_the_hardware_limits_01/attempt_004` | Top spawn, descent and later yaw commands | Add steering/landing observations | Command changes and terrain phase affect metrics | Separate descending interval from later flat turning |

For any remaining attempt, use the all-41-row CSV worksheet. Its facts are prefilled; add your comments in `what_I_saw_before_contact`, `what_I_saw_after_contact`, `target_vs_actual_observation`, `my_hypothesis`, and `next_check`. Your observations should not be inserted into the raw numeric recordings.

## What to do next

1. **Finish those two event-plot observations first.** We have already established that shaking is much stronger after contact. Record whether target reversals, actual tracking error and torque plateaus are present, and identify the foot that hits too low.
2. **Record a fair original-versus-current comparison.** Use original `model_90000.pt` and the Oct 2 `latest.pt`, matching valid bounds, reset pose, initial standing time and the +0.30 m/s, vy=0, yaw=0 command sequence. Repeat several attempts each and keep failures. Keep controller changes separate from policy comparisons.
3. **Keep the current three smoothness weights fixed initially:** action rate −0.15; target second difference −0.01; saturation pressure −0.01. The strongest common early event is a low foot/riser hit, so more smoothness alone is not my first proposed change.
4. **Check the existing foot-height rewards and student stair training episodes.** The saved candidate uses 0.10 m targets for `foot_clearance` and `foot_swing_height`. After verifying sensor and contact-mask definitions, a candidate trial is both preferences at 0.13 m, keeping their weights unchanged. See [note 16](16_NEXT_CHANGES_FROM_THE_PLOTS.md) for exact proposed lines. This is not yet applied and not guaranteed; earlier lifting matters as much as peak height.
5. **Inspect timing and the brief torque-limited recovery episodes.** Training has configured actuator delay; the current viewer is not an exact timing reproduction. Check the saved server implementation before declaring reward causality. See [note 17](17_REVIEW_OF_ACTUATOR_DELAY_AND_GATE_SUGGESTIONS.md). No J or actuator change is justified merely by changed angle bounds.
6. **If a later matched experiment shows target reversals remain the problem, test a stronger second-difference weight separately.** A −0.01 versus −0.02 comparison with equal budgets and the same starting checkpoint is a possible test, not a fix prediction. Check traversal, falls, speed and foot lift alongside HF RMS. Do not replace it with third-derivative jerk just because of its name.

Success means less unwanted shaking **and** useful movement with reliable full ascent. Lower cost alone or standing still is insufficient.

## Files involved

| File | Purpose |
| --- | --- |
| [review_interactive.py](../../tools/jitter_analysis/review_interactive.py) | New offline all-session review, target-cost plots, training-log trend and observations CSV |
| [plot_interactive.py](../../tools/jitter_analysis/plot_interactive.py) | Existing three-figure per-attempt dashboard; reads actual saved data |
| [jitter_rewards.py](../../xterra_mjlab/scripts/jitter_rewards.py) | Existing reward formulas; unchanged by this analysis |
| [train_other.py](../../xterra_mjlab/scripts/train_other.py) | Registers reward terms/overrides before saved configuration and environment creation |
| [env_cfgs.py](../../xterra_mjlab/xterra_mjlab/tasks/velocity/config/svanm2/env_cfgs.py) | Robot training targets, sensors and reward configuration |
| [controller.py](../../xterra_mjlab/svanm2_moe_stair_sim/controller.py) | Viewer target transformation and coupled motor control; unchanged in this review |

To repeat this offline review after future recordings, choose a fresh output name:

```bash
xterra_mjlab/.venv/bin/python -B tools/jitter_analysis/review_interactive.py \
  --out tools/results/my_next_interactive_review \
  --training-log xterra_mjlab/evaluation_runs/20261002_moe_target_bundle_updates90500
```

This reads existing data only. It creates a generic report/worksheet; your written observations stay in the previous review and this note. Close active recording sessions before reviewing. Input hashes and saved metadata distinguish measured evidence from interpretation. The detailed October 3 report is a reviewed interpretation, not ground truth or a file inherited from the original repository.
