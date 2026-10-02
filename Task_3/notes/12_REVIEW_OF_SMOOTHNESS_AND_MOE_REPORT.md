# Review of the supplied smoothness, MoE routing, and actuator report

Date: 2026-09-28. Reviewed the complete 522-line attachment titled "Introduction and Architectural Context" against the local implementation, saved jitter audit, and primary sources for CAPS, LipsNet, LipsNet++, and gSDE.

This is a technical review and revised experiment recommendation. No controller, reward, architecture, training, XML, or hardware changes were made. No new rollout or training result is claimed.

## Assessment

The document contains useful research directions but is not reliable as an implementation specification. It mixes correct ideas with incorrect definitions, unsupported causal claims, and guarantees not established for this robot. Preserve the existing issue-by-issue plan and evaluate each proposed intervention separately.

## Most important corrections

| Supplied claim | Correction supported by current evidence |
| --- | --- |
| `action_rate_l2` computes the second difference | The installed function computes the squared first difference. `action_acc_l2` computes the squared second difference of actions. The audit proposes a distinct post-clamp physical-target second difference. |
| 0.19-0.45 degree RMS describes severe jitter during stair ascent | These are band-limited hardware measurements from motion samples with no synchronized terrain labels. They do not identify stair ascent, total joint excursion, or a universal acceptable simulation threshold. |
| The 8-30 Hz band proves policy alternation near 25 Hz and opposing torque saturation | Joint traces are sampled near 200 Hz. A 50 Hz policy sequence has a 25 Hz Nyquist frequency, but held commands and physical dynamics are different signals. The band alone does not identify command alternation or torque saturation. |
| Correlation 0.962 isolates a precise mechanical cause | It is an association between target and measured oscillation. Both participate in feedback; direction and exclusive cause remain unresolved. |
| Filtering was categorically disproved | The audit tested particular 20/40 ms target filters on a fixed policy. It did not rule out all calibrated actuator-bandwidth models or filters included during training. Nor did it prove the exact reason for every failure. |
| The solution must lie entirely inside the network | Contract, sensor, reset, timing, contact, and actuator discrepancies can also matter. Reward learning is one experimental path. |
| Second differences are inherently better and are an acceleration or jerk penalty | They penalize changes of increments. For position targets, a timestep-scaled second difference approximates acceleration; jerk requires a third derivative. No universal stair-performance superiority follows. |
| 500 updates were designed to preserve mature stair skills | This was a chosen fine-tuning budget. There is no demonstrated guarantee against forgetting, and the audit's baseline stair ascents were unsuccessful. |
| A poor -0.15 trial proves reward tuning reached its limit | One coefficient/budget/seed/configuration cannot establish that. Examine actual cost magnitudes, task results and implementation first. |
| Experts directly output stance/swing joint trajectories | In this model, experts produce 32-dimensional features. A weighted and normalized latent plus the current 45-dimensional observation feeds a separate actor that outputs 12 actions. Expert roles such as stance or swing were not established. |
| Router variation is proven to cause the jitter | It remains a hypothesis. Log it alongside expert outputs, latent norms, actions, contacts and measured motion before modifying the router. |
| Filtering only the gates avoids response delay | Changing gate weights changes the final policy response. A gate filter adds state and changes temporal blending; it is not guaranteed to preserve reflex timing. |
| The audit's saturation pressure means voltage/torque saturation | The audit proposes a POSITION-TARGET clipping cost. A motor torque-speed or voltage-limit model is a different intervention requiring motor data. |
| Add history to turn the MDP into a POMDP | Hidden states/delays can cause partial observability. History helps infer hidden state. The deployed student already uses five frames; adding input dimensions changes the checkpoint interface. |
| CAPS/Lipschitz/gSDE will eradicate jitter or ensure staircase success | These are research methods with empirical results in particular settings. None of those outcomes has been demonstrated for this SvanM2 checkpoint. |

## 1. Correct reward definitions and what the completed run tested

The installed `mjlab/envs/mdp/rewards.py` implements:

```text
action_rate_l2 = sum((a[t] - a[t-1])**2)
action_acc_l2  = sum((a[t] - 2*a[t-1] + a[t-2])**2)
```

In this training adapter, actions are clipped to [-6, 6] before reaching the action manager. These terms operate before per-joint scale, standing offset, and final target clipping.

Changing -0.10 to -0.15 increased the magnitude of the configured FIRST-difference coefficient by 50%. It did not add a second-difference term, and it does not imply the realized penalty contribution increased by 50%, because the policy and state distribution can change.

The audit's proposed new term is:

```text
a = clip(policy_output, -6, +6)
q_raw_target = q0 + scale * a
q_cmd = clip(q_raw_target, target_min, target_max)

L_target_second = sum(((q_cmd[t] - 2*q_cmd[t-1] + q_cmd[t-2]) / scale)**2)
L_target_saturation = sum(((q_raw_target - q_cmd) / scale)**2)
```

Use a negative reward coefficient for each nonnegative cost. The scale vector is matched by joint and has hip/thigh 0.15 and calf 0.30 per leg. Keep timestep fixed; adding a timestep-squared denominator changes magnitudes and requires retuning. Neither term guarantees tracking, lifting, or stability.

The logger currently records per-update averaged raw/weighted reward contributions, not the full action-rate sample variance. A smaller weighted cost with a different coefficient is not, by itself, proof of smoother motion. Compare raw costs and matched evaluation trajectories. Exploration standard deviations or entropy are supporting diagnostics, not definitions of successful locomotion.

## 2. Frequency, hardware numbers, and causal evidence

The saved hardware 8-30 Hz RMS numbers describe selected frequency content, not the full leg swing. The recording lacked terrain labels, so the document's repeated assertion that these samples prove a stair-specific mechanism is unsupported. The band also includes some legitimate gait harmonics and contact impacts.

Distinguish the 50 Hz policy samples, piecewise-held setpoints, 200 Hz simulated external PD updates, and approximately 200 Hz hardware measurement records. Mechanical signals can contain frequencies above the policy's 25 Hz Nyquist limit. A 50 Hz gate log cannot uniquely resolve a 30 Hz gate oscillation; interpolation does not create that information.

To test an alternating-command/torque-saturation hypothesis, inspect time-aligned raw actions, final targets, pre/post-limit torques, joint motion and contacts. Correlations can guide experiments, but do not prove which element initiated the feedback.

Use matched simulation runs for the simulation reference. Do not set a universal simulation pass threshold of 0.19-0.45 degrees based on differently collected and terrain-unlabelled hardware samples.

## 3. Actual MoE architecture

The local checkpoint loader implements this inference path:

```text
5 frames x 45 values = 225-value history
      -> eight 32-value expert feature outputs
      -> softmax gate blends the eight feature vectors
      -> normalize the blended 32-value latent
      -> concatenate the latest 45-value frame (77 total)
      -> actor MLP
      -> 12 joint action numbers
      -> action/target mapping and coupled PD
```

The weighted expert sum is a convex feature combination, not the final joint-target vector. Normalization and the actor are downstream. A gate-only penalty does not constrain the complete observation-to-action mapping.

Useful diagnostics include the eight gate probabilities, expert feature vectors, the norm of the blended latent before normalization, deterministic actions, clamped targets, and contact transitions. Investigating small latent norms is an inference from the normalization operation, not a finding that this is causing the jitter.

Do not assign semantic expert roles without evidence. Do not assume load balancing demands uniform gates at every step or alter its weight based on that assumption. PPO is an on-policy algorithm. Inspect the actual upstream learner and losses before any router regularization. A gate penalty needs a validated implementation and its own controlled evaluation.

## 4. What the cited smoothness methods support

**CAPS:** the authors add temporal and nearby-state action regularization to policy optimization and report improvements on their tasks. It is a plausible later experiment. A direct policy regularizer has different gradients from placing a similarly shaped cost in rollout rewards. The reported quadrotor benefits are not SvanM2 guarantees. [Primary CAPS project and method](https://ai.bu.edu/caps/).

For this history-based MoE, any later CAPS experiment should target the deployed encoder-plus-actor path, handle episode boundaries, preserve observation dimensions, and use noise perturbations appropriate to each scaled sensor channel. Arbitrary independent noise on every history element or command can create unrealistic inputs. Weight choices and sensitivity to contact changes still need evaluation. Avoid promises of zero response tradeoff or guaranteed removal of every high-frequency component.

**LipsNet:** the original paper introduces multidimensional gradient normalization and an architecture that controls input-output sensitivity; it is not merely a generic penalty pasted into any actor. [Primary LipsNet paper page](https://proceedings.mlr.press/v202/song23b.html).

A Lipschitz bound constrains output change relative to INPUT change. It is not a temporal frequency cutoff. As a simple counterexample, the map pi(x)=x is 1-Lipschitz and passes a rapidly oscillating input unchanged. Soft Jacobian regularization also should not be described as a certified global bound without the necessary conditions.

**LipsNet++:** it is a real method with a Fourier observation-filter layer and a Lipschitz controller layer. It changes the policy architecture. [Primary LipsNet++ paper page](https://proceedings.mlr.press/v267/song25a.html). Replacing the current encoder/actor would require an explicit weight-transfer or distillation plan and revised export/loader checks; it is not an ordinary same-architecture resume of this 90000 checkpoint.

**gSDE:** the paper studies structured exploration using state-dependent features and periodic noise resampling, with results on simulated and real systems. [Primary gSDE paper](https://proceedings.mlr.press/v164/raffin22a.html). That does not establish that independent training noise caused this deterministic viewer's jitter or guarantee zero-shot stair success. The viewer uses direct deterministic network outputs, not per-step Gaussian action sampling. Training exploration can affect what is learned, but that is a separate hypothesis.

## 5. Target saturation versus motor torque-speed limits

The audit's target saturation pressure measures a position request removed by a software target clamp. A torque-saturation cost measures unavailable torque. A thermal constraint concerns accumulated temperature/energy losses. These are separate signals and interventions.

A speed-dependent motor model may eventually improve realism, but it requires measured or documented motor constants, bus voltage, current/torque limits, transmission mapping, firmware semantics, and appropriate treatment of motoring/braking. A simplified steady-state voltage relation is not evidence that voltage saturation caused the saved oscillation. The audit did not establish that causal claim or diagnose overheating.

For SvanM2, transform joint velocities into motor velocities using the coupled Jacobian and map motor torques back consistently. Do not apply an arbitrary per-joint torque-speed envelope and label it the hardware model. Preserve existing torque caps until a controlled alternative model is justified. The motor model need not have the same feasible envelope in every operating mode.

## 6. History, delays, and filter claims

The policy already consumes five observation frames containing previous actions. The training asset already has a delay configuration. Inspect effective timing before adding another delay. Hidden actuator state can make observations partially informative; adding history helps estimate it and does not itself create partial observability.

The original audit tested particular filters on a fixed policy and found task failures. It did not demonstrate that every possible filtered policy would fail. Conversely, training with an assumed filter does not guarantee that the real robot will stop falling; the model and learned behavior both need validation. A filter fitted to actual bandwidth is a model-identification experiment, distinct from an arbitrary smoothing change.

Changing the history length or adding input channels breaks the existing 225-input contract unless a deliberate migration is made. Keep the observation layout fixed during the planned ordinary continuation from 90000.

## Current status and next actions

Current inspection: local MuJoCo is 3.11.0, while the historical audit manifest records 3.6.0. The local viewer's calf upper entries are now -0.88776; its gains currently remain kp=20, kd=0.7. The proposed kp=18 diagnostic has not been run by the assistant. Other source/physical-model parity questions remain; matching one upper bound is not full parity.

1. Complete the already proposed fixed-checkpoint gain comparison from note 11, keeping target limits, command, scales, timestep and other settings fixed. Do not combine it with new rewards or router changes.
2. Verify the remaining training/evaluation target contract, sensor refresh, reset and timing issues. Keep diagnostic commands within the trained range. Record a usable evaluation reference.
3. Collect matched traces and outcomes on flat ground and 10 cm stairs. Add gate logging as a diagnostic if useful, without changing the gate yet.
4. Train paired continuations from the same original 90000 checkpoint with the same corrected setup: baseline versus normalized target second-difference cost. Preserve the previous-action observation convention.
5. Test target saturation pressure separately. Choose weights from logged raw magnitudes and assess full traversal, tracking, falls, stalls and clearance as well as oscillation.
6. If evidence still warrants it, test CAPS on the existing full deployed policy path. Treat LipsNet/gSDE changes or a calibrated motor torque-speed model as separate later projects with their own hypotheses and compatibility checks.

One failed candidate is not proof that scalar rewards are exhausted, and a smoother-looking video is not proof that the task is solved. Keep completed 90500 control/candidate checkpoints and compare experiments under explicitly recorded settings.

## Local evidence

- [Saved audit](../moe_jitter_audit_20260921/REPORT.md): hardware terrain caveat, frequency metrics, replay, target limits and proposed reward ablations.
- [Checkpoint architecture](../xterra_mjlab/svanm2_moe_stair_sim/checkpoint_policy.py): history, experts, latent normalization and actor.
- [Viewer controller](../xterra_mjlab/svanm2_moe_stair_sim/controller.py): current bounds, deterministic inference, gains and torque mapping.
- [Training runner](../xterra_mjlab/scripts/train_other.py): history length, configured learner and reward logging.
- [Training adapter](../xterra_mjlab/scripts/m2_algorithm_env.py): clipped action input and history handling.
- [Training actuator configuration](../xterra_mjlab/xterra_mjlab/assets/svanm2/constants.py): gains, delay and scale dependency.
- [Actuator/gain experiment](11_ACTUATOR_ADVICE_REVIEW_AND_GAIN_TRIALS.md).
- [Reward experiments](10_REWARD_AND_CONTRACT_EXPERIMENT_PLAN.md).
