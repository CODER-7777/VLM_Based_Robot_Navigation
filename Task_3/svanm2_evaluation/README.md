# SvanM2 MoE evaluation battery

Headless CPU evaluation of the MoE stair policy, laid out like interiit_xterra's `eval_hs_dhav1w.sh` pipeline. The simulator itself is not copied here: the evaluator imports `controller.py`, `build_scene.py` and `scene.xml` from `xterra_mjlab/svanm2_moe_stair_sim/`, the submodule pinned by this repository.

Files:

- `eval_svanm2_moe.sh` runs the whole battery from any folder, using the Task_3 venv and the default checkpoint (`model_90000.pt`).
- `eval_policy_svanm2.py` builds the scenes, runs each command, and writes the outputs.
- `eval_metrics.py` holds the metric functions, with no MuJoCo import.
- `test_eval_svanm2.py` holds the unit tests.

## What it runs

1. **Flat command battery.** Forward, lateral and yaw sweeps on a floor-only copy of `scene.xml`. Each run is 10 s, and the first 3 s are discarded. Default commands are the viewer's teleop caps.
2. **Stairs.** One run per track (1–6), from the approach pad, at 0.3 m/s for 30 s. Use `--stair-starts center minus plus` to repeat each track from the two offset starts used in note 23.

Each run uses the viewer's `MoeStairController`, so the observation, policy and PD/torque law match the interactive simulator. Base velocity is taken at the base origin, as in interiit_xterra's `root_link_lin_vel_b`.

## Commands

Run these from `Task_3`:

```bash
svanm2_evaluation/eval_svanm2_moe.sh                                 # full battery, about 25 s on CPU
svanm2_evaluation/eval_svanm2_moe.sh --no-stairs                     # flat only
svanm2_evaluation/eval_svanm2_moe.sh --no-flat --tracks 6            # one stair track
svanm2_evaluation/eval_svanm2_moe.sh --contact-impratio 10 --label impratio10
```

Run the tests with:

```bash
xterra_mjlab/.venv/bin/python -m unittest discover -s svanm2_evaluation -v
```

## Outputs

Each run writes to `tools/results/svanm2_eval/<checkpoint>_<label>/`:

- `runs.csv` has one row per run, with tracking, cost, torque and jitter metrics.
- `summary.csv` aggregates the rows by axis or track.
- `flat_battery.png` and `stairs.png` are the figures.
- `manifest.json` records the checkpoint SHA-256, the impratio, the timing mode and the arguments.
- `tensorboard/` holds scalars for each run.

View them with `tools/launch_tensorboard.sh tools/results/svanm2_eval/<run folder>`.

## Definitions

- **Measured joint shaking:** Welch RMS of joint angle over 8–30 Hz, at 200 Hz. Same as `tools/jitter_analysis/analyze.py`.
- **Requested target shaking:** Welch RMS of requested joint angle over 8–20 Hz, at the 50 Hz policy rate.
- **Stair traversal:** a first-pass screen. All four feet must stay past the last tread for 0.5 s, with the base inside the lane, tilt below 30° and no fall. It does not check per-foot platform load or clearance, which interiit_xterra's criteria include.
