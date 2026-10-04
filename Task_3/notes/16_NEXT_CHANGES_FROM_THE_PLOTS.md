# What I would change next, based on the plots

**Additional contact-setting check (October 4):** local training and the saved October 2 candidate use `impratio=10`, while the standard stair viewer builder uses `100`. Both use elliptic cones. Its effect on jitter is unmeasured. [The updated paper review](12_REVIEW_OF_SMOOTHNESS_AND_MOE_REPORT.md) explains why the cited paper warns that a smoother simulation at 100 can reflect unrealistic traction for its robot. Keep the current run fixed; compare contact settings separately.


## Latest review — 2026-10-04 new comparison recordings

Read [the compact comparison](../tools/results/interactive_comparison_20261004/index.html): two plots and a JSON summary, generated only from your saved keyboard-operated data. No new simulation, policy training, or server access occurred during this review.

**Implemented among the five ideas:** (1) optional `--swing-height 0.13` in `scripts/train_other.py`, setting both existing clearance preferences; (2) optional viewer `--observation-timing fresh`, refreshing derived observations on copied state. Neither flag is enabled automatically. No new heading objective, standing-support objective, or friction override was added. Training already randomizes foot friction over 0.3–1.5, containing the viewer's 0.85. The time-aware target-rate term is separately implemented and enabled only with `--target-rate-weight`; existing second-difference and saturation-pressure terms remain registered.

**What the new data show:** `compare_old_90000` has four recorded riser-contact attempts; `compare_new_90500` has six. None records all four feet reaching the top and remaining upright/in the lane for 0.5 s. Other attempts are brief resets or idle. This is an observed outcome count, not a controlled success-rate estimate: keyboard command schedules and durations differ. Both sessions use the same scene, hip upper bound +1.0472 rad, calf upper +0.5 rad, and legacy observations. Their checkpoint hashes confirm original 90000 versus the October 2 candidate 90500; these recordings do not evaluate a model trained with the new time-aware or 13 cm flags.

- Original attempt 006: joint 8–30 Hz RMS increases from 0.539° in the four seconds before first contact to 1.419° afterward. Candidate attempt 013: 0.532° → 1.855°. Both encounter stronger rapid joint motion after contact; gait/commands can also change, so this is not proof of one internal cause.
- Candidate attempt 013 partially climbs: base height is 1.016 m at 11 s. The body exits the stair lane at 11.485 s, height drops to 0.344 m by 13 s, and later world-x progress occurs on the ground outside the lane. World x alone is a misleading ascent score. It ends around +66° heading while requested yaw rate is zero.
- Candidate attempt 005 first contacts at foot-center height 10.22 cm but still does not finish. The earlier successful original run first contacts at 6.26 cm and later finishes. Height at the first collision alone does not determine success.
- The contacting leg has zero target removal and raw torques below its limits at each initial contact in these ten attempts. Later targets and torques can clip; the instant-of-contact result must not be generalized to the whole run.
- Rear-left low standing support is also seen in an original attempt. It cannot be called a problem unique to the candidate. Windows containing early movement must not be interpreted as all-feet-down standing tests.
- Long idle/fallen intervals can hide strong short motion in a whole-run RMS. Use contact windows and actual outcome together.

**Relevant primary research:**

1. [Loquercio, Kumar and Malik, Learning Visual Locomotion with Cross-Modal Supervision](https://antonilo.github.io/vision_locomotion/pdf/manuscript.pdf), Figure 3: a blind policy touches the stairs multiple times before adapting and climbing. The paper also uses progressive stair training and retains flat-terrain experience. This directly cautions against declaring a low first collision to be proof that the policy cannot lift. Adding vision is a larger architecture/data change, not the current trial.
2. [Siekmann et al., Blind Bipedal Stair Traversal](https://arxiv.org/html/2105.08328v1): random stair terrain plus memory enabled Cassie to climb; no new stair-specific reward was required. Higher clearance, steeper swing descent, and support impulses emerged. Their biped and reward design differ from ours, so this supports inspecting terrain exposure and support transfer, not copying coefficients.
3. [Chamorro et al., Reinforcement Learning for Blind Stair Climbing](https://arxiv.org/html/2402.06143v1): a goal-position task includes facing the goal and discouraging stalling, with a single-step-to-staircase curriculum. Real hardware demonstration is on Ascento; quadruped results are in simulation. This motivates reviewing progress/heading objectives and curriculum, but adding their observation/task formulation would alter our existing policy interface.
4. [Miki et al., robust perceptive locomotion](https://leggedrobotics.github.io/rl-perceptiveloco/): terrain perception enables adaptation before contact. Our deployed student is proprioceptive; changing a height reward does not give it advance stair visibility.
5. [Hwangbo et al., agile and dynamic motor skills](https://arxiv.org/html/1901.08652v1): actuator modeling uses measured command errors, velocities and torques, with validation data. This supports a later actuator investigation; generic gain reductions cannot substitute for measuring our coupled transmission.

**Next experiment:** preserve original 90000, test original and old candidate in fresh observation mode under the same commands, then run an explicitly labeled continuation candidate. The command below bundles 13 cm preference with the requested gentle time-aware penalty (-0.01), while retaining action-rate -0.15, second-difference -0.01 and saturation -0.01. Multiple changes in one run cannot reveal which individual change caused an improvement. These penalties can also oppose useful stepping corrections. The wide target profile matches the tested simulator; it is not a hardware-limit recommendation, and the original 90000 training configuration is still missing.

Run this **on the local laptop** (there is no space between SSH address and colon):

```bash
cd /home/vivekananda/UGP_1_VLM/VLM_Based_Robot_Navigation/Task_3
scp xterra_mjlab/scripts/train_other.py \
    xterra_mjlab/scripts/jitter_rewards.py \
    xterra_mjlab/scripts/target_rate_reward.py \
    guest-isl@172.26.186.222:/data/robotics/toshith/vivekananda/m2_moe/xterra_mjlab/scripts/
```

This uploads the three training files. The viewer timing option is already local and need not be uploaded for headless server training. The existing server environment/configuration and logging adapter must be the versions used for the prior continuation.

Run this **on the server**, once, after checking GPU 1 is available. The script creates the output directory with `exist_ok=False`: do not pre-create `$M2_RUN`. The log is a sibling file (`$M2_LOG`) so shell redirection does not require creating the output directory. This corrects the earlier failed launch caused by `mkdir -p "$M2_RUN"`:

```bash
cd /data/robotics/toshith/vivekananda/m2_moe/xterra_mjlab
M2_PY=/data/robotics/toshith/envs/xterra_mjlab/bin/python
"$M2_PY" scripts/train_other.py --help
M2_RUN="../runs/moe_swing013_time_rate_wide_retry_$(date +%Y%m%d_%H%M%S)_updates91000"
M2_LOG="${M2_RUN}.log"
mkdir -p ../runs
nohup env CUDA_VISIBLE_DEVICES=1 PYTHONPATH="$PWD" "$M2_PY" -u scripts/train_other.py \
  --algorithm moe \
  --source /data/robotics/toshith/m2_algorithm_sources20260913/go2_rl_gym \
  --out "$M2_RUN" \
  --num-envs 8192 --steps 24 --seed 103001 \
  --resume checkpoints/svanm2_moe/model_90000.pt \
  --updates 91000 --stabilize --max-learning-rate 1e-5 \
  --target-limit-profile viewer-wide \
  --action-rate-weight -0.15 \
  --target-rate-weight -0.01 \
  --target-rate-limits 7.093 11.275 20.365 \
  --swing-height 0.13 \
  > "$M2_LOG" 2>&1 < /dev/null &
tail -f "$M2_LOG"
```

This is 1000 additional updates (90000→91000), not training from zero. The log should contain `SWING_HEIGHT_REWARD`, `TARGET_LIMIT_PROFILE`, `TARGET_RATE_REWARD`, then `RECOVERY_READY moe 90000 91000` and increasing `completed_updates`. Configuration banners alone do not prove training started. Ctrl+C exits `tail`, leaving `nohup` running. The saved file belongs to this new run directory; the October 2 90500 file remains an older candidate. Evaluate at 91000 before deciding whether to continue to 91500. A from-zero experiment needs its own output directory and a full training budget; removing `--resume` from this low-learning-rate continuation is not an equivalent experiment.

Implementation validation already passed: reward/controller/recording checks and the 24-step GPU environment check with finite contributions. The GPU check is synthetic-action validation, not evidence of improved climbing. No server file was altered or training launched by the assistant.


**2026-10-04 fact check and implementation update:** the five ideas were rechecked against source and saved raw data. A low first-riser contact is not proof that the policy never learned to lift: the successful original run `user_run_original_4_by_sir/attempt_001` first contacts with FR foot-center height **6.2606 cm** at **10.47 s**, then completes the staircase. The 12.2 cm value is the approximate center height for clearing the horizontal top with a 2.2 cm-radius foot, not a required height at every first collision. The candidate's unclipped contacting-leg targets/torques apply to that instant, not its full trajectory.

Implemented as explicit experiment options:

- Training `scripts/train_other.py --swing-height 0.13` sets both existing clearance preferences to 0.13 m before configuration saving/environment creation. Existing weights and command gates remain. Without the flag they stay 0.10 m. Height means foot-site height above raycast terrain (four nearby samples, minimum reduction), not world height and not a guarantee of pre-impact clearance.
- Interactive viewer `--observation-timing fresh` refreshes derived readings on copied MuJoCo state before policy inference. The live physics state is not forwarded again. `legacy` remains the default to reproduce earlier recordings. New manifests identify the mode and raw records include the actual `obs_policy` frame; plots show the mode. Test both checkpoints under the same mode.

Other findings:

- Heading +115.6° and rear-left standing clearance 6.277 cm / zero loaded contact are confirmed in the old central candidate trace. They are observations for that run, not universal causes. No heading penalty or all-feet-down walking constraint was added. A future support objective must be standing-only; forcing contact during swing would obstruct locomotion.
- Training nominal friction is 0.6 but its startup event replaces tangential foot friction with samples from **0.3–1.5**. The viewer's 0.85 lies within that range. The foot has higher contact priority; changing floor friction alone is not equivalent to changing effective foot friction. No friction edit is justified by the proposed constant-0.6 comparison.
- The installed local training environment refreshes derived state before computing observations. Its rewards run earlier in the step; do not describe every training signal as refreshed. The original server package/version remains to be verified.

Validation: seven reward/configuration checks and five controller/analysis checks pass. Fresh frames match independently refreshed observations without mutating live solver state; recording captures the actual input and legacy instrumentation preserves the tested trajectory. The actual GPU environment also passed 24 synthetic-action steps with 0.13 m preferences and finite reward contributions. This is implementation validation, not a new policy training or a successful climbing result. No new Markdown file was added. The remaining text records the earlier proposal and historical trials.

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
