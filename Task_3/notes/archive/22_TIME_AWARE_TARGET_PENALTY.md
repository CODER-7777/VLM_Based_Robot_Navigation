> Historical note. For current commands and decisions, start at [Task 3](../../README.md).

# Time-aware target changes: your idea, measured evidence and manual code steps

**2026-10-04:** implementation is now complete locally; follow the current update at the top of [README.md](PROJECT_HISTORY.md). The manual integration instructions below are historical. The successful original-policy recording motivates a smaller −0.01 trial weight and explicit simulator-matching bounds, not a proven jitter fix.

Updated 2026-10-03. This is an **isolated proposal**, not an applied training change or a demonstrated jitter fix. The assistant added diagnostic/proposal files under `tools`; active reward/controller/training files and the server were not edited. This follows your earlier preference to make training edits manually.

## 1. Your idea is reasonable, with one important correction

The same change can be acceptable when slow and excessive when fast. If the numbers are **degrees**, going from +5° to −5° means a 10° change:

| Elapsed time | Average magnitude of the target change per second |
| --- | ---: |
| 20 ms | 500°/s |
| 500 ms | 20°/s |

Those are position-target increments divided by time, not measured motor velocity. If +5/−5 means the policy's raw outputs instead, first scale, add the standing pose and apply target bounds. Raw actions are dimensionless; they are not degrees or torques. Crossing zero alone does not prove a bad command or a direction reversal of motion.

The saved training configuration uses **5 ms physics × decimation 4 = 20 ms policy/environment steps**, also confirmed by recorded policy timestamps. A condition such as `if dt < 40 ms` would be true for every ordinary action update. A time threshold alone cannot tell a small change from a large one.

Use an allowed change that grows with elapsed time:

```text
allowed_change[j] = target_rate_reference[j] * delta_t
excess[j] = max(abs(q_cmd[t,j] - q_cmd[t-1,j]) / allowed_change[j] - 1, 0)
C_rapid = sum(excess[j]^2)
reward contribution rate = negative_weight * C_rapid
```

Below the threshold, this term gives **zero penalty**. Above it, the penalty grows smoothly. Squared excess gives zero slope at the threshold, avoiding a hard binary reward jump. In our fixed-rate environment use `env.step_dt`, not the physics timestep or wall-clock inference duration. At a real asynchronous interface, measured timestamps would be needed for analysis; do not randomly substitute wall-clock delays into this simulation reward.

A +5°→−5°→+5° sequence within 40 ms contains two 20 ms changes and is evaluated on both. The existing second difference also detects its rapid reversal. A one-way fast swing may also exceed this new threshold, which is why necessary stepping must be checked.

## 2. What this adds to the existing costs

| Term | What it discourages | What it does not establish |
| --- | --- | --- |
| `action_rate_l2` | All successive raw/clipped action changes, according to the existing implementation | Which changes are needed for stepping |
| `target_second_difference_l2` | Changes in successive final-target increments; acceleration-like, not third-derivative jerk | Actual joint acceleration or complete absence of jitter |
| **Proposed `target_rate_excess_l2`** | Final-target changes faster than the selected per-joint reference | A classifier of harmful oscillation, motor overload or mechanical safety |
| `target_saturation_l2` | Requests removed by target clamping | A physical joint hitting a hard stop or torque saturation |

A constant fast sequence can have zero second difference but nonzero rate-excess cost. Small rapid oscillations can remain below a generous rate threshold. Therefore this new term is a selective **large/fast-change** penalty, not a replacement for every smoothness objective.

**Keep the current second-difference term for the first trial.** The proposal's default adds the new term while retaining action rate, second difference and saturation. An explicit replacement option exists for a later separately designed comparison. We should not remove the old term merely because the new one uses time.

## 3. Saturation pressure already exists and is active

In [jitter_rewards.py](../../xterra_mjlab/scripts/jitter_rewards.py), `TargetSaturationPressure` computes:

```text
q_requested = action * scale + standing_offset
q_commanded = clamp(q_requested, lower, upper)
C_saturation = sum(((q_requested - q_commanded) / scale)^2)
```

`config_jitter_rewards(cfg)` registers it as **`target_saturation_l2`, weight −0.01**. The copied training logs confirm nonzero contributions. The proposal requires that term to exist and retains it unchanged; do not register the same punishment again under another name.

Pressure is positive when part of the request is removed. A request exactly at a bound can have zero pressure. This is different from counting how often a target sits at a limit. Also, pressure on position targets is different from a penalty for torque limiting.

## 4. Thresholds measured from your recordings

[The new rate dashboard](http://127.0.0.1:8000/tools/results/time_aware_penalty_20261003/index.html) and [the distribution image](../../tools/results/time_aware_penalty_20261003/target_rate_distributions.png) use recorded targets only. No new simulation was run.

The source review covers **41 attempts**. This calibration uses **19 qualifying entrance-start windows**: fixed command, upright, four seconds each, entirely before or after first stair contact. Top-spawn descent and its later flat travel are excluded. The tighter-bound approach reference contains **six windows / 1200 policy intervals**. Each family pools four legs. Its commands include different forward speeds, so this is an exploratory reference, not a single-speed benchmark or a healthy hardware calibration.

| Joint family | Tighter approach P99 target rate | Exploratory reference: 1.25 × P99 | Allowed target increment in 20 ms |
| --- | ---: | ---: | ---: |
| Hip | 5.674 rad/s | **7.093 rad/s** | 8.13° |
| Thigh | 9.020 rad/s | **11.275 rad/s** | 12.92° |
| Calf | 16.292 rad/s | **20.365 rad/s** | 23.34° |

P99 means approximately 99% of the sampled family rates are at or below that value. The 25% margin is a transparent exploratory choice; it is not learned or physically calibrated. Larger calf references reflect the recorded target motions, not permission to command a real motor at that speed. The reference windows use forward commands around 0.2, 0.3 and 0.5 m/s with zero lateral/yaw commands. They do not validate the full training command distribution, which eventually reaches higher speeds. Check healthy target rates across intended speeds, directions and terrain before treating these fixed references as general-purpose reward settings; otherwise normal fast stepping may be punished. The code accepts a threshold per joint, so later per-leg or command-conditioned calibration is possible after collecting suitable data.

Using those references, the fraction of **joint/interval entries** above threshold is:

| Recorded condition | Above-reference entries | Mean proposed raw cost |
| --- | ---: | ---: |
| Wider approach | 0.146% | 0.000348 |
| Wider after-contact ascent | 6.618% | 0.280804 |
| Tighter approach | 0.396% | 0.003175 |
| Tighter after-contact ascent | 2.800% | 0.155194 |

This suggests the threshold preferentially selects the larger changes seen after stair interaction. It does **not** show they are all harmful, that they initiated the shaking, or that training against them will solve climbing. The approach may already contain unwanted oscillation; necessary stair corrections differ from flat gait.

Read the three image panels as hip/thigh/calf. Blue is the approach distribution; orange is after-contact. A curve farther right means larger target changes per unit time. The red dashed line is the reward reference. The fraction of the curve above that x-value is the set this proposal penalizes. CDF height is a sample fraction, not elapsed time or reward.

## 5. Weight calibration matters

In the selected tighter after-contact windows:

```text
Existing second-difference raw cost mean: 4.5368
Existing weighted contribution at -0.01: -0.04537
New rate-excess raw cost mean:           0.1552
New contribution if weight is -0.01:    -0.00155
```

Copying −0.01 would give approximately **29 times less average punishment** than the current second-difference term in these windows. Matching the means would require approximately −0.292, but **matching means does not match learning gradients or prove that weight is suitable**.

For an exploratory additive trial, the proposal defaults to **−0.05**. That would contribute about −0.00776 in these selected tighter after-contact windows, around 17% of their existing second-difference contribution. This is a modest additional cost, not a proven optimal coefficient. Actual training batches have different teacher/student states, terrain, commands and exploration. Inspect their real logged contributions before choosing a full budget or a stronger coefficient.

The manager normally multiplies a contribution rate by the 20 ms environment step. Existing `RewardRate/*` logs show the weighted rate; `RewardRaw/*` shows the raw cost. Do not mistake either for measured joint jitter.

## 6. Tested proposal files

- [audit_target_rates.py](../../tools/jitter_analysis/audit_target_rates.py): reads actual saved target timestamps, draws the distribution image and reports threshold-exceeding fractions.
- [target_rate_reward.py](../../tools/jitter_analysis/target_rate_reward.py): proposed manager reward and explicit configuration helper. It is **not imported by current training**.
- [test_target_rate_reward.py](../../tools/jitter_analysis/test_target_rate_reward.py): four CPU checks passed: elapsed-time dependence and equal-rate behavior; target clamping/reset masks/real reward-manager weighting; retaining saturation once; rejecting invalid threshold configurations.

The proposed term computes final clamped targets through the existing `_TargetCost` mapping, preserves raw-action history semantics, returns one cost per environment, and suppresses the first action after an episode reset. It uses the action manager's history, so it does not keep a rolling buffer that could leak across resets. It applies no output filter and adds no actuator delay.

These checks do not replace a smoke test in your exact server environment and do not demonstrate successful ascent. The proposal imports your existing `jitter_rewards.py`; check that its `_TargetCost` constructor matches the installed `ManagerTermBase` API. The currently inspected local file correctly calls `super().__init__(env)`.

## 7. Exact manual integration steps

**A. Copy the proposal into the local training scripts when you decide to run the trial:**

```bash
cd /home/vivekananda/UGP_1_VLM/VLM_Based_Robot_Navigation/Task_3
cp tools/jitter_analysis/target_rate_reward.py xterra_mjlab/scripts/target_rate_reward.py
```

This command is for you to execute; the assistant has not performed it.

**B. In `scripts/train_other.py`, beside the existing jitter-reward import, add:**

```python
from target_rate_reward import configure_target_rate_trial
```

**C. Beside the existing `--action-rate-weight` parser argument, before `parse_args()`, add:**

```python
p.add_argument("--target-rate-weight", type=float, default=None)
```

**D. Immediately after the existing MoE `config_jitter_rewards(cfg)` block, add the conditional override. Keep the action-rate override below it:**

```python
cfg = make_cfg(a.num_envs, a.seed)
if a.algorithm == "moe":
    cfg = config_jitter_rewards(cfg)

# New optional trial. Existing training remains unchanged without this flag.
if a.algorithm == "moe" and a.target_rate_weight is not None:
    cfg = configure_target_rate_trial(
        cfg,
        speed_limits_rad_s=[7.093, 11.275, 20.365] * 4,
        weight=a.target_rate_weight,
        replace_second_difference=False,
    )

# Existing override: keep this.
if a.algorithm == "moe" and a.action_rate_weight is not None:
    cfg.rewards["action_rate_l2"].weight = a.action_rate_weight
```

Do not duplicate `make_cfg` or the existing blocks. The whole block remains **before `dump_yaml(...)` and `Adapter(...)`**. The thresholds assume hip/thigh/calf order repeated for FL/FR/RL/RR; verify the action term's `target_names`. If the order changes, reorder the threshold vector.

With no `--target-rate-weight`, the baseline uses its original terms. With `--target-rate-weight -0.05`, the candidate adds this one term. Saturation remains −0.01 in both. Do not alter the previous-action observation or transmission matrix.

**E. Validate the local proposal and parser:**

```bash
xterra_mjlab/.venv/bin/python -B tools/jitter_analysis/test_target_rate_reward.py
xterra_mjlab/.venv/bin/python xterra_mjlab/scripts/train_other.py --help
```

The second command must show `--target-rate-weight` after your edits. If not, do not use the candidate command yet.

**F. Files needed on the server for this trial:**

- `scripts/target_rate_reward.py` — new optional term.
- `scripts/train_other.py` — import, optional argument and registration.
- `scripts/jitter_rewards.py` — existing target transformation, second difference and saturation; verify its current version matches what you intend to use.

Your existing `m2_algorithm_env.py` already provides per-term logging; the server must have that checked logging version. No new controller/XML/actuator file is needed just to add this reward. Preserve old runs and source snapshots.

**G. Run a short smoke check before a full continuation**, using your server interpreter and a fresh output directory:

```bash
cd /data/robotics/toshith/vivekananda/m2_moe/xterra_mjlab
M2_PY=/data/robotics/toshith/envs/xterra_mjlab/bin/python

env CUDA_VISIBLE_DEVICES=1 PYTHONPATH="$PWD" "$M2_PY" scripts/train_other.py \
  --algorithm moe \
  --source /data/robotics/toshith/m2_algorithm_sources20260913/go2_rl_gym \
  --out ../runs/time_rate_smoke_90005 \
  --num-envs 8192 --steps 24 --seed 103001 \
  --resume checkpoints/svanm2_moe/model_90000.pt \
  --updates 90005 --smoke --stabilize \
  --action-rate-weight -0.15 --target-rate-weight -0.05
```

This is an example for manual execution **after integration**. If the directory already exists, use a new name. Confirm the saved `env.yaml` has all four expected terms/weights and 12 thresholds, and logs contain finite `RewardRaw/target_rate_excess_l2` and `RewardRate/target_rate_excess_l2`. A near-zero new cost in a short standing smoke episode is possible and does not prove a wiring failure; its purpose is setup validation, not stair evaluation. Never evaluate the smoke checkpoint as a locomotion candidate.

For full baseline/candidate continuations from 90000, use equal fresh budgets such as `--updates 90500`, normal 20 s episodes (`--smoke` absent), and identical other settings. Only the candidate receives `--target-rate-weight -0.05`. Use separate fresh run directories and retain `latest.pt`, configuration, progress, source and training logs. Do not launch a full run solely because this document has an example command; first review the smoke output and reward magnitudes.

## 8. What to add to the analysis/checklist

- [x] Check real policy Δt: 20 ms, not 5 ms.
- [x] Measure target rates from actual policy samples; do not differentiate repeated 200 Hz held targets.
- [x] Separate ascent approach, ascent interaction and top-start descent.
- [x] Derive explicit exploratory per-family thresholds and plot their coverage.
- [x] Preserve one existing saturation-pressure term.
- [x] Test time dependence, reset behavior, target clipping and reward-manager integration on CPU.
- [ ] Manually add the optional term/import/CLI flag, if choosing this trial.
- [ ] Inspect the exact server's installed API and action ordering; run the short smoke check.
- [ ] Log raw/weighted new cost separately for teacher and student, and especially student ascending-stair episodes. Current aggregate logging does not provide that separation.
- [ ] Compare baseline/candidate from the same checkpoint with equal budgets and evaluation settings.
- [ ] Record first-foot placement, full traversal, speed tracking, heading, falls and stalls alongside joint 8–30 Hz RMS.
- [ ] Inspect whether the punished spikes were needed for lift/recovery. Less punishment achieved by standing still is failure.
- [ ] If foot/riser collision remains the earliest problem, return to [note 16's conditional lift-timing/height experiment](16_NEXT_CHANGES_FROM_THE_PLOTS.md), separately from this reward trial.

This term is a test of your timing idea. It cannot guarantee a jitter cure: low-amplitude vibration can fall under the threshold, contacts can disturb otherwise smooth targets, and a delayed/incorrect control model can still oscillate. Our measured low first-foot hits remain important; reward regularization alone does not establish correct foot placement.
