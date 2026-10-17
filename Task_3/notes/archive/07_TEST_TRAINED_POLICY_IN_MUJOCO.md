> Historical note. For current commands and decisions, start at [Task 3](../../README.md).

# Test the trained policy in MuJoCo

> **2026-10-02 update:** Follow [the main guide](PROJECT_HISTORY.md) for current paths, edited limits and the next training trial. The calf upper bound has already been corrected; the copy paths and status below describe an earlier setup.

Date: 2026-09-28. This guide documents a first visual comparison and the requirements for quantitative jitter evaluation. No controller or training code was changed.

## Verified setup

The existing viewer accepts a compatible training `.pt` checkpoint directly; no ONNX conversion is necessary. Track 1 contains twelve 10 cm steps. The local `.venv/bin/python` successfully imports MuJoCo and PyTorch, and CUDA is available. GPU inference is supported; this viewer's physics runs on the CPU. The candidate checkpoint itself has not been inspected or tested here.

**Known limitation:** `svanm2_moe_stair_sim/controller.py` still uses `+0.5000 rad` as the calf target upper limit. This is the legacy demo, not the corrected hardware-contract evaluator described in the audit. Keep its settings identical between checkpoints for this preliminary comparison. Success here does not verify performance under deployed target limits.

## Copy the candidate

Run on your local graphical desktop, outside the server SSH session:

```bash
cd /home/vivekananda/UGP_1_VLM/VLM_Based_Robot_Navigation/Task_3/xterra_mjlab
mkdir -p checkpoints/moe_jitter_candidates
```

If you used the previously suggested server run directory:

```bash
scp isl-server:/data/robotics/toshith/vivekananda_moe_jitter_20260926/runs/candidate_rate015_90500/latest.pt \
  checkpoints/moe_jitter_candidates/candidate_rate015_90500.pt
```

The server path is an example, not verified remotely. Substitute your actual run path and SSH alias if different. Preserve the original 90000 checkpoint. Renaming a checkpoint does not change its stored update or weights.

## Run the original

From the same local project directory:

```bash
.venv/bin/python svanm2_moe_stair_sim/run_interactive_sim.py \
  --checkpoint-file checkpoints/svanm2_moe/model_90000.pt \
  --track 1 --device cuda:0
```

Close this run before launching the candidate.

## Run the candidate

```bash
.venv/bin/python svanm2_moe_stair_sim/run_interactive_sim.py \
  --checkpoint-file checkpoints/moe_jitter_candidates/candidate_rate015_90500.pt \
  --track 1 --device cuda:0
```

Verify `[INFO] Loaded checkpoint:`, `[INFO] Checkpoint update:`, and `[INFO] Policy device:`. A continuation completed at update 90500 should report 90500. The general viewer banner always says MoE 90,000; it is not evidence of which file loaded. You do not need to set the reward coefficient in this viewer: it runs the trained policy without learning.

## Identical initial visual test

1. Launch a fresh process at the track-1 entrance for each trial.
2. Leave commands at zero for about three seconds of simulation time; observe standing shake.
3. Focus the terminal and tap `w` six times. Each press adds 0.05 m/s. Confirm the display reads `vx=+0.30, vy=+0.00, yaw=+0.00`; use the same startup timing as closely as practical.
4. Observe the short flat approach and then stair contact separately. The approach is 1.5 m, so at perfect 0.30 m/s tracking it would take about five seconds. Actual travel time can differ.
5. Allow up to 30 seconds after applying the command, or stop after a clear fall. Record full ascent, fall, stall, or lane exit. Full ascent means reaching the top with all four feet and staying upright; touching a step is not success.
6. Do not steer one policy back onto the staircase. Record its deviation as an outcome.
7. Record video and simulation times of first stair contact and completion/failure if possible. Repeat three times per checkpoint as an initial check. Manual repetitions are not statistical validation or a substitute for scripted commands and controlled starting conditions.

`Space` zeros velocity commands; it does not pause physics or disable the policy. `R` resets the entrance, but use fresh processes for the comparisons because the legacy reset is not the fully audited reset. Avoid lateral commands in this first test. The brief flat approach does not replace a sustained flat-ground evaluation.

| Checkpoint | Trial | Standing shake | Approach shake | Stair shake | Full ascent? | Fall / stall / lane exit | Contact-to-outcome time |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Original 90000 | 1 | | | | | | |
| Candidate -0.15 | 1 | | | | | | |
| Control -0.10, if trained | 1 | | | | | | |

Use a consistent subjective description such as none / mild / strong. This is not a numerical jitter measurement.

## What the comparison can establish

Original versus candidate checks whether the new policy behaves better in this setup. To assess the reward change, also compare against a continuation trained from the same 90000 checkpoint for the same number of updates using the original -0.10 weight. Load the control through the same `--checkpoint-file` argument. Training randomness and evaluation variability still limit conclusions from a single pair of runs.

Do not judge solely by weighted action-rate reward, because its coefficient changed. Inspect the raw action-rate quantity and actual joint motion. Less shaking accompanied by stopping or worse climbing is not a successful fix.

## Quantitative jitter evaluation

The existing interactive launcher has no trajectory-logging or jitter-metric CLI option. Training TensorBoard reward logs do not replace evaluation joint traces.

To reproduce the audit-style measurement, an evaluator needs simulation timestamps, twelve measured joint angles, twelve final commanded joint targets, velocity commands, base pose/velocity, contacts, and recorded outcomes. Sampling at every 200 Hz physics step supports analysis of the 8–30 Hz band. Save checkpoint identity, simulator configuration, command schedule, and initial condition too.

Compare measured-angle and target-angle RMS in that band using the audit's same filtering, units, and window definitions. Also compare actual speed tracking, heading drift, full traversal, falls, stalls, lane exits, and target saturation. Separate standing, flat travel, approach, and stair-contact windows; compare equivalent windows and report failed trials. Whole-run RMS contaminated by a fall is not a fair steady-motion jitter comparison.

Visual improvement is preliminary evidence. Numerical reduction requires logged traces. None were generated by writing this guide. Establish the corrected hardware-contract evaluation setup before claiming that the hardware jitter problem is fixed.

## Sources

- [Viewer and arguments](../../xterra_mjlab/svanm2_moe_stair_sim/run_interactive_sim.py)
- [Checkpoint loader](../../xterra_mjlab/svanm2_moe_stair_sim/checkpoint_policy.py)
- [Controller and target limits](../../xterra_mjlab/svanm2_moe_stair_sim/controller.py)
- [Keyboard controls](../../xterra_mjlab/svanm2_moe_stair_sim/teleop.py)
- [Training/server workflow](06_REWARD_LOGGING_SERVER_WORKFLOW.md)
- [Earlier video audit](05_VIDEO_JITTER_AUDIT.md)
