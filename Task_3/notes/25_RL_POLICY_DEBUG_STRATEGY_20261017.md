# RL jitter investigation with contact ratio fixed at 100

User decision, 2026-10-17: use RL only, retain the newest 91,000-update checkpoint and `impratio=100`, and investigate the feedback loop before changing the policy or training again. The VLM proposal in note 24 is not part of this plan.

**Current conclusion:** the new recording reproduces through the saved policy and implemented controller, but exhibits large commanded-target changes and contact-amplified motion. The gate participates; the evidence does not identify it as the sole initiating fault. The previous-action input to the actor is a particularly useful next investigation target. A sensitivity probe is not evidence to remove or delay that input.

This follow-up ran existing offline diagnostic scripts on CPU. It did not run new physics trajectories, training, GPU inference, hardware commands, or modify runtime/controller code or weights.

[New diagnostics dashboard](../tools/results/policy_debug_20261017/index.html) · [Per-attempt measurements](../tools/results/policy_debug_20261017/summary.json) · [Saved-input checks and hashes](../tools/results/policy_debug_20261017/contract_checks.json) · [Previous audit](24_GATE_FREQUENCY_AND_VLM_AUDIT_20261011.md).

## What the latest recording establishes

Session: `tools/results/interactive/20261017_205511_247716`, four closed attempts, checkpoint SHA-256 `dec9775d4b368b69964dde679985455d8b723d5af7fb2d24e8798fa4fdd66da4`. Recorded ratio 100, elliptic cone, 5 ms physics/PD step, 20 ms policy step, kp=18, kd=0.7, legacy observations, current deployment target bounds.

All **2,982 recorded policy inputs** were reconstructed and replayed on CPU. Maximum raw-action error was **7.16e-6**, gate error below **6.2e-7**. There were no target changes outside policy ticks. The coupled PD reconstruction agrees within **2.28e-6 Nm**. Additional saved-data checks confirm command placement, q/dq scaling, the selected legacy frame, previous clipped action from the preceding policy tick, action clipping, target mapping, gate normalization, and finite policy outputs. These checks establish consistency with the recorded implementation, not agreement with the original training environment or actual motor firmware.

Constant-command windows, with separate boundaries at first riser contact:

| Attempt and interval after reset | Command (vx, vy, yaw) | Mean joint 8–30 Hz RMS | Actual speed along requested axis | Interpretation |
| --- | --- | ---: | ---: | --- |
| 1, 11.120–14.055 s | (0.50, 0, 0) | 0.765° | vx=0.373 m/s | Oscillation exists before stair contact |
| 1, 14.055–18.580 s | (0.50, 0, 0) | 1.219° | vx=0.258 m/s | Contact interval amplifies motion; peak tilt 40.39° |
| 2, 2.685–15.545 s | (0, 0.55, 0) | 0.539° | vy=0.344 m/s | No stair contact; command exceeds saved reference ±0.30 m/s lateral range |
| 3, 2.615–5.805 s | (0.50, 0, 0) | 0.414° | vx=0.334 m/s | Another approach with different startup/history |
| 3, 5.805–7.925 s | (0.50, 0, 0) | 0.802° | vx=0.209 m/s | Short contact interval, no completed ascent |
| 4, 0–5.915 s | (0, 0, 0) | 0.147° | — | Standing/reset diagnostic, includes startup transient |

These are descriptive windows of manual runs, not matched treatment comparisons. Whole-run averages mix standing, acceleration, contact and stopping. The earlier ratio-10 session used different commands and durations, so do not calculate a causal 10-versus-100 percentage from these two manual sessions.

Attempt 1's contact interval contains a maximum **79.97° commanded joint-target change in one 20 ms policy interval**, after target limits. This is a target jump, not a measured joint rotation over 20 ms. At 15.660 s, RL thigh requested torque is −34.91 Nm and is clipped to −12 Nm; its position and damping terms are −10.96 and −23.96 Nm. Increasing damping without diagnosis is therefore not a justified next step.

The new actor-input probes substitute the preceding value of one input group for a single inference, retaining all other current inputs. During attempt 1's contact interval, target-output sensitivity RMS is **7.78° for previous action**, **4.42° for expert features**, **2.77° for joint velocity**, **2.43° for gyro**, **2.38° for joint position**, and **2.07° for gate weights**. These are interacting, all-frequency, one-step probes, not additive percentages of physical jitter or predictions of modified rollouts. Previous-action sensitivity is also larger than gate sensitivity in the other moving windows. See [attempt 1 probe plots](../tools/results/interactive/20261017_205511_247716/attempt_001/plots/policy_spike_review.html).

The maximum gate weight reaches about 0.70 in this new session. The earlier observation of diffuse weights at ratio 10 must not be generalized to every ratio-100 event. This network still blends soft weights; argmax changes are not hard expert switching. Inspect the weighted features and final output as well as gate weights.

## Fixed baseline and evidence standard

Keep checkpoint identity, ratio 100, friction, geometry, masses, gains, transmission, target limits, torque limits, 50 Hz policy and 200 Hz PD fixed during the first investigation. Ratio 100 is the chosen repository baseline; it is not a measured property of the hardware. MuJoCo defines `impratio` as a constraint-impedance ratio, distinct from the friction coefficient. Hardware calibration remains a later evidence question. [MuJoCo definition](https://mujoco.readthedocs.io/en/stable/XMLreference.html#option-impratio).

For every experiment retain: hypothesis, exact changed line/configuration, checkpoint/source/XML hashes, initial state, command schedule, all results including failure, matched metrics, and the next decision. A quieter robot that stalls or loses stair clearance does not pass.

## Investigation order and decision rules

| Stage | Concrete work | Evidence needed before changing the controller |
| --- | --- | --- |
| 1. Establish repeatable evaluation | Compare fresh-process starts with in-process resets at the same pose and policy phase. Use scripted commands and identical histories. | Repeated baseline outputs and state trajectories agree within documented numerical tolerance; deviations identify retained state or timing differences. |
| 2. Verify the training/deployment interface | Recover the exact 91k training environment/config; compare observation ordering/scales/frame conventions, previous-action clipping semantics, history ordering, action scale, target bounds, delay and torque/transmission semantics. | A specific mismatch with its source and a paired corrected trial. Existing replay alone cannot prove this interface is correct. |
| 3. Locate event onset | Read an aligned trace around contact onset, the largest target changes, and the first sustained oscillation. Include quiet and unsuccessful cases. | Establish which signals change first at their actual sample times; classify hypotheses without claiming causality from lead/lag alone. |
| 4. Isolate policy pathways offline | Replay exact histories; test gate, expert-feature and direct actor-input sensitivity, especially previous action, dq and gyro. Inspect mixture norm and feature differences. | A reproducible output-sensitive pathway at the problematic event; verify it also exists in in-range command tests. |
| 5. Test one mechanism in closed loop | From the same complete initial state, run one named change per trial while preserving contact and actuator parameters. Start with reset/timing/interface corrections, then a narrowly justified policy intervention. | Improved oscillation with maintained speed, heading, support and task completion across paired initial states. |
| 6. Decide whether learning must change | If implementation/interface checks pass and the controller still generates damaging oscillations under the fixed baseline, evaluate a focused continuation. | A demonstrated policy limitation and a loss/architecture change targeting it, with a held-out evaluation set. No evidence currently requires training from zero. |

Reset deserves attention before network modification: the current reset rewrites pose/velocity/history but does not reset all MuJoCo state, viewer pacing, or global policy-tick phase. Compare first; a repair must coordinate all those items. `mj_resetData` alone resets simulation time and would require recorder/pacing integration. MuJoCo documents both state reset and state-dependent derived quantities that can be one step old. [Simulation and state documentation](https://mujoco.readthedocs.io/en/stable/programming/simulation.html).

The existing `fresh` observation mode provides a useful paired diagnostic. Current recorded gyro differences between legacy/fresh readings have whole-attempt RMS about 0.154, 0.154, 0.157 and 0.078 rad/s. It is a test of timing consistency; prior fresh-versus-legacy outcomes were mixed, so do not assume it solves jitter. Keep each timing mode explicitly labelled.

## What to record at each instant

Use one structured trace with episode ID, policy-tick ID, simulation time and monotonic wall time. Record numerical data in buffered chunks; generate plots offline. Printing tensors synchronously on every tick can perturb timing and makes comparisons harder. Measure logging overhead and dropped records.

| Boundary | Sampling and fields | Diagnostic question |
| --- | --- | --- |
| Sensor/state → observation | 200 Hz state, 50 Hz exact selected frame; q, dq, IMU/orientation, timestamps, command, previous action, history indices | Wrong scale/order/sign, stale sensing, missing/repeated history, or unexpected command? |
| History → gate and experts | 50 Hz eight weights, optional logits, expert features, pre-normalization mixture norm and normalized latent | Is a gate change consequential because features disagree? Is normalization amplifying changes? |
| Latent + newest frame → actor | 50 Hz raw action; reconstruct sensitivities offline from exact saved history | Does the direct previous-action/dq/gyro path produce the large target change? |
| Actor → target limits | Raw action, clipped action, requested target, final target, per-joint removed amount and target difference | Is a requested recovery repeatedly removed by deployment bounds? |
| Target → actuator → state | 200 Hz position/damping torque terms, unclipped/clipped torque, delivered control, q/dq, foot forces/contact IDs and body motion | Does oscillation start with target reversal, tracking error, saturation or impact? |

The existing recorder already contains much of this chain. Expert features/logits can be recovered offline after checkpoint replay passes; add runtime storage only if exact replay is unavailable. Full-state checkpoints for future branched simulations must include solver state, policy history/previous action, scheduling phase and commands. The current recorded q/qvel alone are not sufficient for an exact restart.

Plot around an event at three scales: several seconds for command/gait context; a subsecond window for feedback cycles; individual 5 ms rows for force/state alignment. In these logs, state at t precedes the force applied over [t,t+5 ms]; its response belongs to the next state sample. Do not treat all fields in one row as simultaneous responses.

At 50 Hz, gate/action spectra have 25 Hz Nyquist. Use the established 8–20 Hz policy-target band and 8–30 Hz measured-joint band at 200 Hz, plus a common band for comparisons. Retain low-frequency motion and task outcomes: the selected high-frequency band includes impacts and useful corrections as well as unwanted vibration. Lead/lag and coherence help select hypotheses, but feedback and common contact inputs prevent causal attribution from correlation alone.

## Minimal next simulation matrix (proposed, not launched)

Start with five short command cases at ratio 100: zero command; forward +0.15; forward +0.30; sideways +0.15; sideways −0.15 m/s. Use fresh-process starts initially. Hold zero for 3 s, ramp over 1 s, then hold the selected command for 8 s on clear flat terrain. Record stop transients separately. Verify the complete training command range before expanding it; the known lateral reference is ±0.30 m/s.

First repeat identical initial conditions to check reproducibility; deterministic duplicates are not independent success-rate samples. Then use at least three predefined small initial offsets with matched baseline/intervention pairs. Report every case; expand the set only when results justify it. This is screening, not a reliable population success estimate.

After flat behavior is characterized, use the same fixed approach at 0.30 m/s on 10 cm stairs with no operator steering. Evaluate full-foot traversal, tilt, heading, clearance, foot slip/support, achieved speed, target steps and saturation. A trial cut short must be reported as incomplete, not successful. Compare contact-aligned phases as descriptive measurements and retain fixed-time/task metrics so a slower controller cannot win merely by reaching the obstacle later.

The first paired changes should address an identified reset/interface/timing issue. If those checks pass, a mild gate temporal filter can be a diagnostic candidate only if event probes support it. Permanent gate freezing, hard top-k routing, zeroing previous action, changing policy frequency, and adding large output filters are not justified initial fixes. Prior gate freezing nearly stopped one sideways trial; prior previous-action delay and output-filter experiments sometimes worsened behavior.

For a gate-related learning change, evaluate gate temporal regularization together with expert-feature/output changes and motion performance. For a previous-action feedback issue, first verify that the saved value and delay match training, then quantify small input perturbations and their temporal propagation; a large one-step sensitivity does not prove unstable closed-loop gain. If continuation is needed, candidate objectives include penalties on realized-target reversals and requests outside verified deployment bounds, balanced against clearance and tracking. Their weights and benefit remain experiments; no new reward is adopted here.

## Available scripts and reproduction

From `Task_3`, regenerate the new dashboard using saved data only:

```bash
CUDA_VISIBLE_DEVICES='' MPLCONFIGDIR=/tmp/svanm2_strategy_matplotlib \
  xterra_mjlab/.venv/bin/python -B tools/jitter_analysis/diagnose_updates.py \
  tools/results/interactive/20261017_205511_247716 \
  --device cpu --out tools/results/policy_debug_20261017
```

Generate the actor-input and event probes for the three moving attempts:

```bash
CUDA_VISIBLE_DEVICES='' MPLCONFIGDIR=/tmp/svanm2_strategy_matplotlib \
  xterra_mjlab/.venv/bin/python -B tools/jitter_analysis/inspect_policy_spikes.py \
  tools/results/interactive/20261017_205511_247716/attempt_001 \
  tools/results/interactive/20261017_205511_247716/attempt_002 \
  tools/results/interactive/20261017_205511_247716/attempt_003 --device cpu
```

Open `tools/results/policy_debug_20261017/index.html`; each attempt links to the gate/update analysis and the moving attempts link to policy-spike probes. The spike script requires a sufficiently long constant moving command window, so it was not applied to standing-only attempt 4. Rerunning these tools replaces their derived plots/metrics; raw recordings and checkpoint weights are retained.

`audit_gate_frequency.py` provides an exact three-pathway decomposition, but its current CLI selects attempt 4 and October 11 phase boundaries. Do not run it unmodified on a different recording. Generalizing attempt/phase selection is a useful later tool improvement. `verify_current_contract.py` and `audit_control_loop.py` run new simulations; they are not offline log readers.

The added output is evidence for the next experiment, not a completed jitter fix. No training is required for the proposed checks; any later training/GPU job must be discussed with the user before launch.
