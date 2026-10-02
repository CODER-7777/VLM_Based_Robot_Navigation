# Review of actuator advice and a controlled MuJoCo gain experiment

Date: 2026-09-28. The user wants to review pasted reward/actuator/timestep advice and try actuator tuning manually. This document records inspected facts and proposed experiments. No controller, XML, training code, checkpoint, or hardware setting was changed by the assistant, and no gain sweep was run.

## Current code and compiled-model findings

- The user has changed all four calf upper targets in the local viewer to -0.88776 rad. Other limits remain as currently configured; this does not establish complete deployed-bound parity.
- `svanm2_moe_stair_sim/controller.py`, lines 70-71, sets `self.kp = 20.0`, `self.kd = 0.7`.
- The viewer computes coupled motor-space PD torque, maps it back to joint space, clamps it, and writes torque to `data.ctrl`. MuJoCo receives `<motor>` actuator controls with gear 1. It does not use an XML position servo for this control loop.
- The compiled local `scene.xml` has a 0.005 s physics timestep. The viewer updates external PD each physics step (200 Hz) and the policy every four steps (50 Hz). The saved training configurations also specify 0.005 s and decimation 4.
- Compiled FL hip/thigh/calf joints have passive damping 0.1 and frictionloss 0.2, matching the inherited scene defaults. These are separate from the Python derivative gain.
- Compiled actuator control limits are +/-12 Nm for hips/thighs and +/-24 Nm for calves, with unit actuator gear.
- Training nominal gains are `STIFFNESS = 20.0`, `DAMPING = 0.7` in `xterra_mjlab/assets/svanm2/constants.py`. The saved runs configure startup PD multipliers between 0.8 and 1.2 and actuator delay lags from 0 to 2.
- The copied candidate has action-rate weight -0.15; its saved reward list has no separate torque-squared term. The installed framework contains a `joint_torques_l2` function that could be registered in a later reward experiment.

## Which pasted claims need correction?

1. **Action-rate penalty is not an established cure for heat or all jitter.** It discourages consecutive action changes. We have not established overheating or a thermal root cause from the supplied observations. A torque-squared term is an effort proxy, not a calibrated motor-temperature prediction. Real heating assessment would need current/temperature and motor/thermal parameters, including the coupled transmission.
2. **The action-rate term already exists.** Do not duplicate it in `step`, replace the whole reward with `forward_reward - ...`, or silently reduce its weight to the example's -0.01. The project uses a batched GPU reward manager, so a new term should return one cost per environment using Torch and be registered through `RewardTermCfg`.
3. **There is no justified universal SvanM2 gain range of kp=40-80 or kd=1-5.** The actual controller uses 20 and 0.7, with coupled transmission and model-dependent dynamics. Moving to 40 would increase the nominal proportional gain, not reduce it. Large or small gains alone do not establish heating or instability.
4. **The XML position-servo example is not a drop-in replacement.** Replacing the viewer's motor actuators with position actuators would change the meaning of `data.ctrl` while Python still writes torque values. Preserve the torque-actuator interface for this experiment.
5. **Passive joint damping is already present.** Changing it from 0.1 to the pasted 1.5 is a fifteen-fold change, not a minor adjustment. Passive damping and active PD damping have different roles; adding unmeasured passive friction/damping can change the physical model and obscure the cause.
6. **Equal policy/physics rates do not universally cause jitter.** This project already uses different rates. Decimation is not a guarantee of smoothness.

MuJoCo distinguishes actuator outputs from forces mapped into generalized joint coordinates, and distinguishes passive joint damping from servo feedback. See [actuation model](https://mujoco.readthedocs.io/en/stable/computation/index.html#actuation-model) and [XML actuator reference](https://mujoco.readthedocs.io/en/stable/XMLreference.html#actuator-position). Here the viewer uses gear-one joint motors, so their scalar force outputs correspond to modeled joint torques; they should not be called measured physical motor currents or motor temperatures.

The attached literature is useful as motivation, not as a source of universal gain values for this robot. [Tune to Learn](https://arxiv.org/abs/2604.02523) investigates interactions between controller gains and learned policies and finds learning-paradigm-dependent outcomes; its manipulation focus is not direct validation of SvanM2 stair settings. The [Hwangbo ANYmal paper](https://arxiv.org/abs/1901.08652) concerns transfer to another quadruped. This review does not independently verify every numerical claim in the attached literature list.

## First experiment: change only the viewer's proportional gain

Use the same fixed checkpoint for every trial. For example, keep the candidate 90500 checkpoint. Keep the newly edited calf targets fixed in every trial; otherwise the gain comparison also changes the target contract.

Record a baseline at kp=20, kd=0.7. Then manually change only `self.kp` in `svanm2_moe_stair_sim/controller.py`:

```python
self.kp = 18.0
self.kd = 0.7
```

This is a 10% reduction in proportional gain. It is a sensitivity experiment, not a known good gain. Do not edit the XML or change rewards for this first comparison.

Restart the viewer after each edit:

```bash
cd /home/vivekananda/UGP_1_VLM/VLM_Based_Robot_Navigation/Task_3/xterra_mjlab
.venv/bin/python svanm2_moe_stair_sim/run_interactive_sim.py \
  --checkpoint-file evaluation_runs/20260927_moe_jitter_candidate_weight015_updates90500/latest.pt \
  --track 1 --device cuda:0
```

No retraining is needed for this diagnostic. Verify the loaded checkpoint path/update. Start a fresh process for each trial, leave the command at zero for roughly three simulation seconds, then set vx=0.30, vy=0, yaw=0 (six terminal W presses from zero). Use the same timing and duration; avoid steering. Record standing, the flat approach, and the 10 cm stair attempt separately. Manual timings only approximate repeatability; quantitative conclusions need scripted commands and logged traces.

## Small follow-up sweep

Run B first. If movement/support is retained, consider C. D is a separate comparison against A, with kp returned to 20; do not cumulatively change both gains.

| Trial | kp | kd | Purpose |
| --- | --- | --- | --- |
| A | 20.0 | 0.70 | Current gain baseline |
| B | 18.0 | 0.70 | 10% lower proportional response |
| C | 16.0 | 0.70 | 20% lower proportional response |
| D | 20.0 | 0.84 | 20% higher derivative response only |

These nominal values lie within the saved +/-20% startup gain-scaling ranges. That does not establish robust performance: combinations, gain distributions, and the viewer's other dynamics can differ. More damping is not automatically better; torque saturation and delayed feedback can matter.

Keep checkpoint, target limits, reference pose/action scales, terrain, startup/command schedule, timestep, control rates, passive damping, friction, torque caps, and filters fixed. Preserve the thigh-calf coupling. A poorer result is useful evidence and should be retained rather than hidden.

Record joint/target oscillation, position-tracking error, torque RMS and saturation occupancy, actual forward speed, heading drift, full stair traversal, falls and stalls. A robot that becomes weak, crouches, stops, or fails to lift its feet is not an improvement because its video looks calmer. The viewer currently lacks the required trajectory logger, so an initial video comparison is preliminary.

## Important training trap: stiffness also changes action scale

The training constants file computes:

```python
action_scale = 0.25 * effort_limit / STIFFNESS
```

With stiffness 20, hip/thigh scales are 0.15 and calf scale is 0.30. Changing STIFFNESS to 18 would also change those scales to approximately 0.1667 and 0.3333 unless explicitly prevented. That would change both control gains and the policy's requested position amplitudes.

If a subsequent training experiment changes nominal gains, hold the action scales at [0.15, 0.15, 0.30] per leg and keep training/evaluation mappings matched. One option is a gain override on the already-created training actuator configuration after action scales are resolved; another is explicit fixed scale constants. Verify the final saved configuration and actual resolved runtime gains/scales. Account for startup gain randomization.

Changing simulation gains to make a video smoother is not a physical actuator calibration. Before treating a chosen gain/model as representative of deployment, compare against actual controller configuration and measured response. No real-robot gain changes are part of this experiment.

## Timestep and rewards are later, separate experiments

Changing dt from 0.005 to 0.002 while retaining decimation 4 would change the policy to 125 Hz and the external PD loop to 500 Hz. Even decimation 10 would preserve 50 Hz policy but still change the external PD rate. A physics-resolution experiment must separate integration and controller schedules; 1 ms physics can support a held 200 Hz PD torque updated every five substeps and 50 Hz policy every twenty substeps, but the current combined `physics_step` needs restructuring for that. Do not change dt as part of this gain sweep.

The audit also showed contact-timeconstant sensitivity to timestep. Keep contact settings fixed and inspect their effective meaning in any later resolution test.

After the gain study and control-contract checks, test normalized target second differences, saturation pressure, or torque cost as separately logged reward changes. A torque penalty does not replace torque limits; choose its coefficient from measured magnitudes and check required stepping/support effort. Keep the original 90000 checkpoint and existing 90500 runs intact for comparisons.

## Source locations

- [Viewer gains and control law](../xterra_mjlab/svanm2_moe_stair_sim/controller.py).
- [Training gains and action-scale formula](../xterra_mjlab/xterra_mjlab/assets/svanm2/constants.py).
- [Coupled training actuator](../xterra_mjlab/xterra_mjlab/actuators/svanm2_actuator.py).
- [Viewer scene generation](../xterra_mjlab/svanm2_moe_stair_sim/build_scene.py).
- [Viewer scheduling](../xterra_mjlab/svanm2_moe_stair_sim/run_interactive_sim.py).
- [Saved candidate settings](../xterra_mjlab/evaluation_runs/20260927_moe_jitter_candidate_weight015_updates90500/env.yaml).
- [Earlier reward/contract plan](10_REWARD_AND_CONTRACT_EXPERIMENT_PLAN.md).
