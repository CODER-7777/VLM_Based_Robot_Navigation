> Archived reference. For current commands and decisions, start at [Task 3](../../README.md).

# SvanM2 MoE Multi-Stair Simulation

## Current RL-only viewer defaults (October 11)

The viewer now defaults to **`impratio=100`** and the **91,000-update** checkpoint
`evaluation_runs/moe_swing013_latest/latest.pt`, the same weights as the recorded
October 11 `impratio=10` session (SHA-256
`dec9775d4b368b69964dde679985455d8b723d5af7fb2d24e8798fa4fdd66da4`).
Only viewer defaults changed; no training configuration or policy weights changed.
An explicit `--contact-impratio 10` still selects the previous comparison condition.

From **Task_3**, run this command when you want GPU inference and a new recording:

```bash
xterra_mjlab/.venv/bin/python xterra_mjlab/svanm2_moe_stair_sim/run_interactive_sim.py \
  --checkpoint-file xterra_mjlab/evaluation_runs/moe_swing013_latest/latest.pt \
  --contact-impratio 100 --device cuda:0 --track 1 --record
```

The viewer performs inference, not training. Recordings use a new automatically
named directory under `tools/results/interactive`. Use `--device cpu` for CPU inference.

## October 10 contact diagnostic

For the current jitter diagnosis, evidence, and all tested outcomes, read
[Task 3's detailed report](../23_DEEP_JITTER_ANALYSIS_20261010.md).
The viewer accepts `--contact-impratio 10` for the measured simulation mitigation;
the current default is explicitly 100. Active solver options are saved when recording.
Use `--device cpu` for CPU-only inference. No training is performed by the viewer.
The setting reduced vibration in controlled tests but did not solve every stair case
or validate a real-robot fix. Discuss training/GPU use with the user before launching it.



Interactive MuJoCo simulation environment for the **xTerra SvanM2** quadruped robot driven by a **MoE-CTS student policy**. The viewer defaults to the 91,000-update checkpoint above; `--checkpoint-file` can select an older checkpoint for comparison.

---

## Environment Layout

The world includes **6 side-by-side stair tracks** spaced 3.8 meters apart along the Y-axis:

| Track | Step Height | Total Steps | Total Rise | Top Platform Size | Color Theme |
|:---:|:---:|:---:|:---:|:---:|:---:|
| **1** | **10 cm** ($0.10\text{ m}$) | 12 | $1.20\text{ m}$ | $3.0\text{ m} \times 2.4\text{ m}$ | Sky Blue |
| **2** | **12 cm** ($0.12\text{ m}$) | 12 | $1.44\text{ m}$ | $3.0\text{ m} \times 2.4\text{ m}$ | Teal |
| **3** | **14 cm** ($0.14\text{ m}$) | 12 | $1.68\text{ m}$ | $3.0\text{ m} \times 2.4\text{ m}$ | Green |
| **4** | **15 cm** ($0.15\text{ m}$) | 12 | $1.80\text{ m}$ | $3.0\text{ m} \times 2.4\text{ m}$ | Amber |
| **5** | **16 cm** ($0.16\text{ m}$) | 12 | $1.92\text{ m}$ | $3.0\text{ m} \times 2.4\text{ m}$ | Coral Red |
| **6** | **20 cm** ($0.20\text{ m}$) | 12 | $2.40\text{ m}$ | $3.0\text{ m} \times 2.4\text{ m}$ | Magenta |

* **Approach Runways**: 4.0 m flat starting area in front of each staircase.
* **Tread Depth**: 30 cm per step.
* **Top Turnaround Platform**: 3.0 m long $\times$ 2.4 m wide platform at the top of each staircase, level with step 12. Provides ample space to turn around $180^\circ$ and walk downstairs.

---

## How to Run

Activate the environment or run with the conda Python:

```bash
python run_interactive_sim.py
```

From the repository root, explicitly select the checkpoint and 10 cm stairs:

```bash
python svanm2_moe_stair_sim/run_interactive_sim.py \
  --checkpoint-file checkpoints/svanm2_moe/model_90000.pt --track 1 --device cuda:0
```

Startup prints the absolute checkpoint path and its stored update number. The
loader uses the student encoder and actor weights from the `.pt` file on the selected device;
it does not require `offline_inference.ts` or the upstream training framework.
The interactive runner defaults to `--device cuda:0` for NVIDIA GPU inference
and prints the GPU name. Observations move to the GPU and actions return to
CPU for standard MuJoCo physics. This does not use MuJoCo-Warp: physics remains
on CPU. Use `--device cpu` explicitly to run without CUDA; a requested CUDA
device never silently falls back to CPU.
Validate agreement with the shipped export using
`python svanm2_moe_stair_sim/test_checkpoint_policy.py` from the repository root.

### Command Line Options:
```bash
# Start at a specific track (e.g. Track 4: 15cm stairs)
python run_interactive_sim.py --track 4

# Start directly on the top platform of Track 2 (12cm) to test descent
python run_interactive_sim.py --track 2 --top
```

---

## Keyboard Controls (In MuJoCo Viewer)

> **Note**: Click once inside the MuJoCo viewer window to focus it before pressing keys.

### Velocity Control (Hardware-Matched Limits)
* **`W`** / **`S`** (or **`Up`** / **`Down`**): Increase / decrease forward speed ($\pm 0.50\text{ m/s}$)
* **`A`** / **`D`**: Step left / right lateral speed ($\pm 0.60\text{ m/s}$)
* **`Q`** / **`E`** (or **`Left`** / **`Right`**): Turn left / right yaw rate ($\pm 0.40\text{ rad/s}$)
* **`Space`**: Emergency STOP / zero all command velocities (robot holds standing pose)

### Instant Teleports & Resets
* **`1`** – **`6`**: Teleport immediately to the approach runway of Track 1 to 6
* **`T`**: Teleport to the **top platform** of the active track, oriented facing downstairs
* **`R`**: Reset robot to the entrance of the current track

---

## Controller & Dynamics Matching

1. **Policy**: MoE-CTS student encoder + actor loaded directly from the selected checkpoint by `checkpoint_policy.py`; viewer default is update 91,000.
2. **Observation History**: 5 frames $\times$ 45 dimensions (oldest-first into student network).
3. **Action Mapping**: $\text{target} = q_0 + [0.15, 0.15, 0.30] \times \text{clip}(\text{action}, -6, 6)$, clamped inside physical deployment joint limits with 0.05 rad buffer.
4. **Actuator Model**: Coupled motor-space PD ($k_p=20, k_d=0.7$, gear $[8, 8, 16]$, belt coupling matrix $J$).
5. **Loop Rates**: Physics at 200 Hz ($dt=0.005\text{ s}$), Policy at 50 Hz (decimation 4).
