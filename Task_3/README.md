# Task 3 — SvanM2 RL locomotion and jitter debugging

Start here for the current setup, run commands, plots and analysis. Older plans are collected in [notes/archive](notes/archive/INDEX.md).

## Current setup

- **RL only:** MoE-CTS checkpoint update **91,000**, stored at `xterra_mjlab/evaluation_runs/moe_swing013_latest/latest.pt`.
- **Simulation baseline:** `impratio=100`, policy 50 Hz, physics/PD 200 Hz, kp=18, kd=0.7; legacy observation timing.
- **Status:** jitter remains unresolved. Recorded policy replay and PD arithmetic pass consistency checks; previous-action semantics, reset behavior, sensing timing and gating remain investigation targets.
- **Workflow:** implementation, simulation and training are run by the user. No training from zero is currently justified.

The checkpoint SHA-256 is `dec9775d4b368b69964dde679985455d8b723d5af7fb2d24e8798fa4fdd66da4`. The filename `latest.pt` currently contains update 91,000; check the startup message and recording manifest when running it.

## Run and record

From **Task_3**:

```bash
cd /home/vivekananda/UGP_1_VLM/VLM_Based_Robot_Navigation/Task_3

xterra_mjlab/.venv/bin/python xterra_mjlab/svanm2_moe_stair_sim/run_interactive_sim.py \
  --checkpoint-file xterra_mjlab/evaluation_runs/moe_swing013_latest/latest.pt \
  --contact-impratio 100 --device cuda:0 --track 1 --record
```

This runs GPU policy inference with CPU MuJoCo physics, without training. Use `--device cpu` for CPU inference. Track keys **1–6** select 10/12/14/15/16/20 cm stairs. Terminal **W/S** controls forward speed, **A/D** sideways speed, **Q/E** turning, **Space** stops commands, and **R** resets.

Recordings are saved to new folders under `tools/results/interactive/`; the terminal prints the exact path.

## Generate and open plots

For the latest inspected recording, **2026-10-17 / checkpoint 91,000 / impratio 100**:

```bash
CUDA_VISIBLE_DEVICES='' xterra_mjlab/.venv/bin/python \
  tools/jitter_analysis/plot_interactive.py \
  tools/results/interactive/20261017_205511_247716

xdg-open tools/results/interactive/20261017_205511_247716/index.html
```

For a new recording, replace the session path in both commands. Plotting reads saved data and needs no GPU.

[Latest recording plots](tools/results/interactive/20261017_205511_247716/index.html) · [Policy and gating diagnostics](tools/results/policy_debug_20261017/index.html).

## Important documents

| Read this | Purpose |
| --- | --- |
| [Debugging strategy](notes/25_RL_POLICY_DEBUG_STRATEGY_20261017.md) | Current evidence, investigation order, logging requirements and decision rules |
| [Detailed jitter analysis](notes/23_DEEP_JITTER_ANALYSIS_20261010.md) | Attempts so far, reasons for changes, measured outcomes and limitations |
| [Gating and frequency audit](notes/24_GATE_FREQUENCY_AND_VLM_AUDIT_20261011.md) | September rechecks and network-pathway analysis; its VLM proposal is outside the current scope |
| [How to read plots](notes/15_HOW_TO_READ_THE_PLOTS.md) | Commands versus motion, target limits, contact and frequency interpretation |

## Folder guide

| Folder | Contents |
| --- | --- |
| `xterra_mjlab/` | Robot model, RL implementation, simulator and checkpoints; [package setup](xterra_mjlab/README.md) |
| `tools/jitter_analysis/` | Recording and analysis scripts; [tool reference](tools/README.md) |
| `tools/results/` | Raw recordings, manifests, plots and experiment evidence |
| `moe_jitter_audit_20260921/` | Original September audit and retained evidence |
| `notes/` | Four active reports/guides, supporting assets and historical archive |
| `Videos/` | Recorded videos |

Keep checkpoint identities, commands, initial conditions and controller settings explicit in comparisons. Lower vibration counts as an improvement only alongside adequate tracking, support and task completion. No hardware jitter fix has been established.
