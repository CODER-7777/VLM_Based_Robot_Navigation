# Task 3 — persistent MoE 90k learning and jitter workflow

Updated: 2026-09-25. This is the master checklist and restart point for our work.

## Objective and recommended order

Understand how this MoE policy learns and acts, inspect all existing jitter evidence,
trace every reward and penalty, establish a reproducible baseline, then test whether
controlled fine-tuning from `model_90000.pt` reduces jitter while preserving walking
and improving 10 cm stair traversal.

Your six assigned tasks are appropriate. The important adjustment is to inspect the
dashboard and establish the baseline BEFORE deciding which rewards to change.
Reward changes are the intended experiment; they are not yet a proven cure.
The audit supports a policy–actuator–contact interaction and has not established
one exclusive cause or a reliable general fix.

Recommended sequence:

1. Learn RL, MoE, gating, teacher/student training and the control loop.
2. Trace how THIS 90k policy was trained, using source and saved configuration.
3. Finish the entire dashboard/report observation table.
4. Audit every reward/penalty and measure its contribution.
5. Establish a consistent evaluation setup and frozen 90k baseline.
6. Choose evidence-based hypotheses and one-change-at-a-time experiments.
7. Validate GPU training continuation from 90k, then run control and candidate training.
8. Compare checkpoints on fixed tests and record whether jitter and task performance improve.

Stages 2–4 can inform each other: revisit source when a plot raises a question.
Stages 4–5 also overlap because reward contributions must be measured in a valid
training/evaluation environment. Reading a reward coefficient is not a measurement.

## Mapping to your six assigned tasks

| Your task | Where we do it | Required output |
|---|---|---|
| 1. Learn MoE, experts, gating, RL and training in depth | Stages 1–2 | Concepts note and source-backed training map |
| 2. Identify rewards and punishments | Stage 4 | Complete formula/weight/contribution table |
| 3. Understand how and what to change | Stages 4–6 | Hypotheses with tradeoffs and measurements |
| 4. Examine all HTML dashboard items and report | Stage 3 | One observation row per item, plus limitations |
| 5. Reduce jitter through reward changes | Stages 6–8 | Controlled comparisons, not just smoother videos |
| 6. Train starting from 90000.pt | Stages 7–8 | Verified continuation from the original `model_90000.pt` |

## Current status — do not confuse preliminary inspection with completion

Previously completed in this conversation:

- [x] Located the checkpoint and identified update 90,000.
- [x] Added and checked direct-checkpoint inference and GPU policy inference in the stair demo.
- [x] Observed instability in the interactive 10 cm stair demo.
- [x] Read the audit report and inspected the dashboard inventory.
- [x] Previously compared the checkpoint fingerprint with the audit provenance.
- [x] Explained the hardware joint-angle/target plot at an introductory level.
- [x] Saved a plain-language audit explanation in `02_JITTER_AUDIT_EXPLANATION.md`.
- [x] Updated this master workflow to reflect your six assigned tasks.
- [x] Wrote [03_RL_MOE_AND_CONTROL.md](03_RL_MOE_AND_CONTROL.md): detailed Step 1 lesson, code evidence, examples and self-check questions.

Still incomplete:

- [ ] Review the saved Step 1 lesson together and resolve your questions; writing it does not establish understanding.
- [ ] Complete the historical training-source/configuration trace; selected local and pinned upstream paths have now been inspected.
- [ ] Formal observations for all eight videos and nine plots.
- [ ] Complete reward formulas and measured contributions.
- [ ] Recovery/reconstruction of the corrected evaluation implementation.
- [ ] Reproducible local baseline using a documented control setup.
- [ ] Training dependency/source recovery and verified continuation.
- [ ] Reward changes and fine-tuning experiments.
- [ ] Demonstrated jitter reduction with preserved task performance.

No reward-training fix has been completed. GPU inference support does not establish
that the full GPU training pipeline is ready. The original stair demo is not
automatically equivalent to the audit's corrected simulator.

The audit reports successful replay of 30,175 recorded policy outputs and 34 export
fixtures. These support inference consistency on those inputs; they do not prove
stair-climbing ability. Its two baseline 10 cm ascent trials had no valid traversal
(one did not traverse; one left the lane). These are historical audit results,
not a newly executed baseline and not a reliable population success-rate estimate.

## Stage 1 — learn the concepts before changing parameters

Learning order and questions:

- [ ] Observation/state: what does the robot sense, and what remains hidden?
- [ ] Action/policy: how does the network choose commands from observations?
- [ ] Reward/penalty: which behavior earns a higher or lower scalar training signal?
- [ ] Return/discount factor: how do future rewards affect the current decision?
- [ ] Episode/rollout/termination: what data is collected, and when does a trial end?
- [ ] Value function/critic/advantage: how is an action judged against expectations?
- [ ] Actor–critic/PPO: how do policy updates use those estimates and limit change?
- [ ] Entropy/exploration: why does training sample actions, and how does evaluation differ?
- [ ] Batch/minibatch/epoch/update/learning rate: what does one training update involve?
- [ ] Curriculum/domain randomization: how are terrain difficulty and physical variation sampled?
- [ ] MoE: what is an expert, what does the gate output, and how are experts combined?
- [ ] Dense versus sparse routing: are all experts weighted, or are only some selected?
- [ ] Teacher/student/distillation: what privileged information is available in training?
- [ ] Control: joint angle `q`, velocity `dq`, desired target, torque, PD gains and saturation.

Known high-level description to verify against the complete training implementation:
this policy uses eight continuously weighted experts in a student representation.
The student receives five frames of 45 observations (225 values); the actor outputs
12 joint actions. Do not assume one expert means stairs, another means flat ground,
or that expert identities are manually assigned. Specialization needs evidence.
The pinned upstream learner has now been inspected: it does contain latent-matching and batch-level expert load-balancing losses. The detailed learning paths and provenance limits are explained in the Step 1 lesson.

The central feedback loop is:

```text
Sensors + command + observation history
  -> MoE student representation -> actor -> raw actions
  -> action clipping/scaling + nominal pose -> bounded joint targets
  -> motor/PD response -> contact and body movement -> new sensor observations
```

A reward is a learning signal used during training. Changing its configuration
alone does not change a frozen checkpoint's learned weights during inference.
The complete loop matters: jitter may reflect commands, control response, contacts,
or their interaction. Smoothing penalties can also weaken required stair stepping.

Deliverable: [03_RL_MOE_AND_CONTROL.md](03_RL_MOE_AND_CONTROL.md) — written on 2026-09-25; your review and self-check remain pending.
Completion: explain the loop, experts/gating, and training versus inference in your own words.

## Stage 2 — reconstruct how this checkpoint was trained

Read and trace:

1. [Repository README](../xterra_mjlab/README.md)
2. [Model card](../xterra_mjlab/MODEL_CARD.md)
3. [Checkpoint README](../xterra_mjlab/checkpoints/svanm2_moe/README.md)
4. [Training entry point](../xterra_mjlab/scripts/train_other.py)
5. [Algorithm environment setup](../xterra_mjlab/scripts/m2_algorithm_env.py)
6. [Robot task configuration](../xterra_mjlab/xterra_mjlab/tasks/velocity/config/svanm2/env_cfgs.py)
7. [Backend integration](../xterra_mjlab/scripts/other_backends.py)
8. [Training recovery](../xterra_mjlab/scripts/training_recovery.py)
9. [Checkpoint inference reconstruction](../xterra_mjlab/svanm2_moe_stair_sim/checkpoint_policy.py)

The inference loader helps explain the network, but cannot establish the full
training algorithm, losses, curriculum or reward implementation by itself.

- [x] Located public upstream algorithm files at commit `30e74dc507bec7a642a8c98be26081f2c6f0822d`, the commit named by the local training script.
- [ ] Recover the compatible local training source and verify it against historical source hashes; the checkpoint-recorded source directory is still absent.
- [ ] Recover the saved MoE training configuration, including the original environment configuration.
- [ ] Do not substitute a different policy's configuration (such as HIMLoco's `env.yaml`).
- [ ] Enumerate all 45 observation values, scaling, noise and frame order.
- [ ] Trace teacher and critic inputs, including privileged observations.
- [ ] Trace expert outputs, gating normalization, combination and actor input.
- [x] Identified optimizer roles and principal losses in the pinned upstream learner; see Step 1 sections 8–10.
- [ ] Confirm these definitions and all resolved loss settings against the historical training run.
- [ ] Trace actions into joint targets, previous-action feedback and coupled torque.
- [ ] Record training terrains, command ranges, curriculum and randomization.
- [ ] Record episode lengths, resets and termination conditions.
- [ ] Separate checkpoint-saved settings from present-day defaults in the repository.

Previously inspected checkpoint metadata:

| Item | Value |
|---|---:|
| Update | 90,000 |
| Parallel environments | 8,192 |
| Rollout steps per update | 24 |
| Samples per update | 196,608 |
| Seed | 103001 |
| Optimizer states | 2 |

`90,000` denotes training updates here; it does not mean 90,000 individual samples
or 90,000 files to load. Verify the counter convention when continuing training.

Deliverable: `04_TRAINING_CODE_MAP.md` (planned), with file/function/line references
and each finding labelled source-verified, report-only, or unresolved.

## Stage 3 — examine the entire dashboard and report

Sources:

- [Dashboard](../moe_jitter_audit_20260921/index.html)
- [Technical report](../moe_jitter_audit_20260921/REPORT.md)
- [Our plain-language explanation](02_JITTER_AUDIT_EXPLANATION.md)
- [Rollout results](../moe_jitter_audit_20260921/suite_summary.csv)
- [Provenance manifest](../moe_jitter_audit_20260921/manifest.json)

Serve the dashboard using:

```bash
cd /home/vivekananda/UGP_1_VLM/VLM_Based_Robot_Navigation/Task_3/moe_jitter_audit_20260921
python3 -m http.server 8000
```

Open `http://localhost:8000/index.html`. Keep the terminal running; Ctrl+C stops it.

Eight videos (check off only after writing the observation row):

- [ ] Flat ground, forward command.
- [ ] Flat ground, lateral command.
- [ ] Rough 3 cm terrain, forward command.
- [ ] 20-degree downslope, forward command.
- [ ] 20-degree upslope, forward command.
- [ ] 15 cm ascent, deployed target bounds, 20 ms filter, half-speed video.
- [ ] 15 cm ascent, deployed target bounds, half-speed video.
- [ ] 15 cm ascent, legacy target bounds, half-speed video.

Nine plots:

- [ ] Hardware joint angles and sent targets (initial explanation done; formal row pending).
- [ ] Hardware spectra, moving windows and expert weights.
- [ ] Original incident angles from the approximately 20 Hz recording.
- [ ] Terrain comparison.
- [ ] Filtering/delay/timestep ablation comparison.
- [ ] Simulated 15 cm stair joint curves.
- [ ] Flat lateral-motion joint curves.
- [ ] 20-degree uphill joint curves.
- [ ] Rough 3 cm terrain joint curves.

Observation table template:

| Item and source | Conditions | Direct observation/number | Failure onset/outcome | Supported inference | Unknowns | Next check |
|---|---|---|---|---|---|---|
| Fill one row per video/plot | Terrain, command, bounds, timestep/filter, seed | What is actually visible/measured | Before contact, on stairs, after fall; traversal/stall/exit/tip | Qualified interpretation | What this item cannot prove | Relevant metric or source |

- [ ] Cover each report section and link its claims to data/code where available.
- [ ] Record both useful results and failed cases, limitations and missing evidence.
- [ ] Separate reports of prior tests from tests we reproduce locally.

Interpretation rules:

- Dashboard video label `hardware` means deployed target bounds in simulation.
- Upright, approaching stairs and completing stairs are different outcomes.
- Hardware joint-angle windows lack synchronized terrain labels.
- Software target saturation is not proof of a physical joint hitting a stop.
- The calf upper-bound difference is about 79.5 degrees; the original incident's
  approximately 72.6-degree body tilt is a different quantity.
- Strong correlation does not establish which part of the feedback loop caused jitter.
- Eight weighted experts do not establish abrupt hard expert switching.
- Lower oscillation while stalled or fallen does not establish improvement.
- Passing interface tests and finishing 120 rollout processes do not mean 120 successful traversals.

Deliverable: `05_DASHBOARD_OBSERVATIONS.md` (planned), containing 17 item rows and
an evidence summary: observations, supported explanations and unresolved questions.

## Stage 4 — audit rewards and punishments completely

A punishment is usually a penalty term that reduces total reward. Inspect both
the function and weight: the sign of a coefficient alone is not the whole formula.
Distinguish environment rewards from PPO, value, entropy and distillation losses.
Also inspect early termination, which changes the future reward available.

Preliminary terms from earlier code inspection and the audit; verify against the
saved MoE configuration before treating this as the full active reward set:

| Term | Previously reported weight | Intended purpose to verify |
|---|---:|---|
| Linear velocity tracking | +6.0 | Follow commanded translational speed |
| Angular velocity tracking | +3.0 | Follow commanded yaw rate |
| Upright posture | +0.5 | Encourage desired body orientation |
| Pose preference | +0.25 | Encourage preferred joint posture |
| Self-collision | -0.1 | Discourage robot links colliding |
| Shank collision | -0.1 | Discourage lower-leg terrain collisions |
| Trunk collision | -0.1 | Discourage body contact with terrain |
| Action rate | -0.1 | Discourage rapid action changes |
| Foot slip | -0.1 | Discourage sliding during contact |
| Foot clearance | -2.0 | Penalize clearance-related error; inspect exact formula |
| Soft landing | -1e-5 | Penalize harsh landing behavior; inspect exact formula |
| Joint limit | -1.0 | Penalize joint-limit behavior; inspect exact formula |

A tiny coefficient can have a large contribution if its raw term is large.
An existing joint-limit penalty might act on measured angles rather than commanded
targets. An action-rate penalty may operate before target scaling/clamping.
These distinctions decide whether a proposed new penalty duplicates an old one.

For EVERY active term:

- [ ] Find implementation and inherited definitions, including the correct `mjlab` version.
- [ ] Record formula, coefficient, sign, units, normalization and timestep scaling.
- [ ] Identify signals used: raw action, commanded target, measured position or contact.
- [ ] Record activation masks: stance/swing, moving/stationary, terrain or termination.
- [ ] Measure raw and weighted distributions during comparable motion phases.
- [ ] Inspect flat walking, stair approach, successful steps and failure onset separately.
- [ ] Exclude post-fall motion from normal walking jitter comparisons.
- [ ] Identify conflicts between tracking, balance, clearance, slip and smoothness.

Table template:

| Term | Source/formula | Weight/units/time scaling | Active when | Raw and weighted measurements | Helps | Possible tradeoff |
|---|---|---|---|---|---|---|
| TBD | Exact function and saved config | Verified values | Masks/conditions | Mean, spread and peaks by phase | Intended behavior | E.g. inhibits stepping |

Deliverable: `06_REWARD_AND_PENALTY_AUDIT.md` (planned).
Completion: all active terms traced and contributions measured; no weight selection
based only on the preliminary table.

## Stage 5 — establish the evaluation setup and baseline

Known gap from prior inspection: the report references a separate corrected
`svanm2_moe_hardware_audit` implementation that was not found in the local Task 3
copy. Recover it or reconstruct and validate its relevant behavior before calling
the original stair demo an equivalent reproduction.

- [ ] Preserve and fingerprint the original `model_90000.pt`.
- [ ] Record source revision, resolved configuration and software versions.
- [ ] Verify observation order/scaling/history and action/target mapping.
- [ ] Verify target bounds, raw-action history, command shaping, sensor refresh and resets.
- [ ] Document physics, PD and policy rates separately, plus delay and contact settings.
- [ ] Resolve actuator assumptions where possible; label remaining uncertainty.
- [ ] Keep environment/control corrections separate from reward-change experiments.
- [ ] Freeze evaluation commands, starting poses, terrain geometry and durations.
- [ ] Choose multiple deterministic starts before seeing candidate results.
- [ ] Include flat walking and full 10 cm ascent; use other terrains for regression checks.
- [ ] Define traversal, fall, stall, lane exit and motion-analysis windows explicitly.
- [ ] Log raw actions, targets, measured q/dq, torques, contacts, commands, expert
  weights, reward components and failure reasons where available.
- [ ] Reuse the same cases and metric implementation for every model.

Metrics: full traversal count/rate with number of trials; falls/stalls/lane exits;
tracking error and unintended yaw; joint and target oscillation; target saturation;
foot clearance/slip/impacts; reward contributions. Report the selected oscillation
band and sampling rate. The audit's 8–30 Hz metric is an indicator, not a definition
of every unwanted movement.

Define acceptance criteria before candidate training. A nearly stationary robot
can have low jitter, so improvement must include adequate commanded movement and
no unacceptable regression in balance, tracking or task completion.

Deliverable: `07_BASELINE_PROTOCOL_AND_RESULTS.md` (planned).

## Stage 6 — decide what to change, based on evidence

The overall view needed to manipulate rewards is:

```text
Task objective + observed failure
  -> relevant physical signal
  -> existing reward formula and measured contribution
  -> hypothesized conflict or missing incentive
  -> one controlled change
  -> training from 90k
  -> independent task and jitter measurements
```

Experiment template:

> We observe X under conditions C. We suspect Y because of evidence E. Changing Z
> should improve metric A while preserving B. Result R would weaken this hypothesis.

Possible experiments, not established fixes:

- [ ] Adjust existing action-rate weight if its measured contribution supports doing so.
- [ ] Test normalized physical-target second-difference penalty:
  `-lambda * ||(q_cmd[t] - 2*q_cmd[t-1] + q_cmd[t-2]) / action_scale||^2`.
- [ ] Test target saturation-pressure penalty:
  `-lambda * ||(q_raw_target - q_cmd) / action_scale||^2`, with
  `q_raw_target = q0 + action_scale * clip(raw_action, -6, 6)` and
  `q_cmd = clip(q_raw_target, deployed_bounds)` for the reported action mapping.
- [ ] Examine clearance, slipping or landing terms only when failure evidence points there.
- [ ] Consider a measured joint-acceleration term only after checking numerical/sensor consistency.

For each candidate, specify weight range, units, timestep dependence, history reset
behavior, activation conditions and expected tradeoffs. Target second difference
can suppress rapid reversals but also needed stair corrections. Saturation pressure
can discourage unusable requests but may reduce useful extension if poorly weighted.

Correct target limits, command coverage and actuator modeling are environment/control
changes, not reward changes. Test and document them as separate factors. Existing
penalties mean adding more smoothness penalties blindly is not justified.

Deliverable: `08_EXPERIMENT_PLAN.md` (planned), with one-factor ablations and criteria.

## Stage 7 — verify continuation from model_90000.pt using GPU

Previous inspection found training dependencies/upstream MoE source missing from
the inspected environment. Recheck the intended environment before installation.

- [ ] Locate/recover matching source and dependency versions.
- [ ] Verify PyTorch/CUDA and the intended GPU training backend actually run.
- [ ] Verify checkpoint architecture and all required optimizer states load.
- [ ] Inspect which update, scheduler, RNG and curriculum states are saved/restorable.
- [ ] Restore every available required state; document missing states and initialization.
- [ ] Distinguish full resume from weights-only fine-tuning; do not label them equivalent.
- [ ] Check resume constraints for algorithm, environment count, rollout length and seed.
- [ ] Measure GPU memory use and feasibility of the saved 8,192-environment setup.
- [ ] If hardware needs fewer environments, explicitly validate the batch/update change
  and use the same adaptation for all comparisons.
- [ ] Preserve the original checkpoint and save new runs to separate directories.
- [ ] Run a short continuation smoke test; verify finite losses, update counter and reload.

The earlier recovery-code inspection found checks requiring matching algorithm,
environment count, rollout length and seed. Confirm their current behavior before
issuing a training command. We will write the exact command after verifying these
prerequisites; a guessed command is not a completed training setup.

Deliverable: `09_RESUME_SETUP_AND_COMMANDS.md` (planned), including the actual
verified environment, resume semantics, commands, paths and smoke-test results.

## Stage 8 — train, evaluate and decide

Start each experiment independently from the preserved original 90k checkpoint:

| Run | Purpose |
|---|---|
| Original 90k, evaluation only | Frozen reference |
| A: unchanged-reward continuation | Measure effect of additional training |
| B: one reward change | Test that reward hypothesis |
| C: another individual change, if justified | Separate test from the same 90k start |

For A/B/C, keep environment/control settings and training budgets comparable.
If the environment was corrected, A and B must share that correction, so the
reward comparison is not mixed with a simulator change.

- [ ] Save resolved configuration, initial checkpoint hash, seeds and run logs.
- [ ] Compare equal sample budgets and record elapsed time and update counts.
- [ ] Evaluate periodically on fixed held-out cases using the baseline protocol.
- [ ] Check task metrics alongside reward curves; higher total reward alone is insufficient.
- [ ] Compare common locomotion phases and report early failures rather than hiding them.
- [ ] Check promising changes across multiple training seeds and evaluation starts.
- [ ] Test flat ground and other terrain for regressions.
- [ ] Verify checkpoint/export inference agreement for a selected candidate.
- [ ] Record negative findings as well as improvements; revisit hypotheses if necessary.

| Model/run | Jitter during motion | 10 cm traversal (successes/trials) | Falls/stalls/exits | Tracking | Saturation | Regressions |
|---|---|---|---|---|---|---|
| Frozen original 90k | TBD local baseline | TBD | TBD | TBD | TBD | TBD |
| A: unchanged rewards | TBD | TBD | TBD | TBD | TBD | TBD |
| B: candidate | TBD | TBD | TBD | TBD | TBD | TBD |

Deliverable: `10_TRAINING_RESULTS_AND_DECISION.md` (planned).
Completion means a measured improvement meeting the predefined criteria, or a clear
negative result and next justified experiment. Simulation improvement alone does
not establish that hardware jitter is fixed. Hardware validation is separate work.

## Persistent notes and resuming after a break

Files that currently exist:

- [01_PROJECT_CHECKLIST.md](01_PROJECT_CHECKLIST.md): this master workflow/status.
- [02_JITTER_AUDIT_EXPLANATION.md](02_JITTER_AUDIT_EXPLANATION.md): simpler report explanation.
- [03_RL_MOE_AND_CONTROL.md](03_RL_MOE_AND_CONTROL.md): detailed RL/MoE/control lesson with source references and self-check questions.

Files numbered 04–10 above are planned deliverables, not completed analyses.
Create each as its stage is performed; keep useful explanations, commands, source
references, observations and decisions in those notes rather than only in chat.
Update this checklist after each session with evidence and the next unfinished step.
Label findings as verified in source, measured locally, reported by audit, or hypothesis.

## Immediate next task

Read [03_RL_MOE_AND_CONTROL.md](03_RL_MOE_AND_CONTROL.md), starting with sections
1–6, and ask about anything unclear. Continue through the architecture, training,
control and jitter sections, then use the self-check questions. The lesson is written;
your understanding should not be marked complete automatically.

After that, begin `04_TRAINING_CODE_MAP.md` for the full historical training trace.
The lesson has already verified selected local code, checkpoint metadata and pinned
upstream behavior. Still recover the original resolved configuration/source provenance,
then finish the dashboard observations and reward audit before selecting changes.

Restart prompt you can use later:

> Read Task_3/notes/01_PROJECT_CHECKLIST.md and the completed stage notes. Tell me
> what is verified, what is pending, and continue the next unchecked learning or
> analysis task. Save the new explanation and update the checklist.

### Session record — 2026-09-25 workflow update

- Reordered the learning path to begin with RL/MoE concepts and actual training.
- Preserved all dashboard items and the preliminary reward list.
- Added deliverables, completion criteria, experiment controls and resume checks.
- Clarified that reward-only causation and a successful jitter fix remain unproven.
- This session updated documentation; no reward code or training run was changed.

### Session record — 2026-09-25 Step 1 lesson

- Created `03_RL_MOE_AND_CONTROL.md` with 24 sections, worked examples, glossary,
  source map and self-check questions.
- Verified student architecture, checkpoint metadata, teacher/critic dimensions and
  relevant pinned upstream learning paths. Found the public code online; the saved
  original training-source directory remains absent locally.
- Distinguished lesson delivery from user review, and selected source inspection from
  a completed historical training/reward audit.
- No reward code, policy weights or training run changed.
