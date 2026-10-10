# Task 1 — Simulator evaluation

Objective: execute quadruped control in a visually detailed environment under the recorded RTX 3050 / 4 GB VRAM constraint.

## Attempts and results

| Attempt | Implementation / outcome | Limitation |
| --- | --- | --- |
| Simulator comparison | Genesis, Isaac Sim/Lab, Unreal/Unity, Habitat, MuJoCo/MJX assessed; Genesis used for the prototype | Design comparison, not measured cross-engine benchmarking |
| Detailed office collision mesh | Collision/convex-hull processing reportedly caused OOM | No saved numerical memory trace |
| Split visual and collision geometry | `Office+2.glb`: `collision=False`, `convexify=False`; `plane.urdf` supplies support | Furniture is visible but has no collision response |
| Pretrained Go2 controller | Joint-order remapping, 45-D observation, 12 position-target actions, stand/walk keyboard modes | Policy/scene dependencies are external; no language navigation |
| Offline high-quality rendering | Proposed separation from live preview | Ray-traced rendering benchmark not implemented in this script |

## Control implementation

[run_go2.py](run_go2.py): Genesis GPU; `dt=0.02`, two substeps; one inference per scene step in walk mode. Observation: angular velocity (3), gravity (3), command (3), relative joint position (12), joint velocity (12), previous action (12). Policy joint order: FR/FL/RR/RL, hip/thigh/calf. Configured stand gains 150/5 and walk gains 40/1. Actions are offsets from the standing pose.

The script requires CUDA, a display, Genesis/PyTorch/NumPy, the matching `rl_sar` policy, and `genesis-world/office-env/Office+2.glb`. Its policy path is currently hardcoded outside this repository.

```bash
cd Task_1_Simulator_Evaluation
python run_go2.py
```

[Recorded demo](videos/Genesis_without_physics.mp4) · [Initial evaluation](notes/INITIAL_EVALUATION.md). The video has no synchronized configuration manifest; its filename does not verify its physics setup.

## Current hypothesis and pending work

A detailed visual mesh with simplified collision geometry should reduce scene-processing cost while retaining useful observations. Pending: furniture collision proxies; source/asset/environment hashes; memory and physics/render latency measurements; tracking/stability evaluation; connection to the navigation interface.
