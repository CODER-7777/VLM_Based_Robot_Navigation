# Task 1 — Simulator evaluation and Go2 demonstration

**Mid-evaluation status, 10 October 2026:** a Genesis/Go2 demonstration and simulator-selection study are recorded. Quantitative cross-simulator benchmarking, obstacle-contact validation in the office, and end-to-end language navigation remain open.

[Project overview](../README.md) · [Presentation guide](../docs/mid_evaluation/PRESENTATION_GUIDE.md) · [Original evaluation notes](notes/INITIAL_EVALUATION.md)

## Objective and constraints

Find a practical environment for developing quadruped locomotion with realistic visual context. The initial development machine was recorded as an RTX 3050 with 4 GB VRAM. This made scene complexity, collision processing, and renderer overhead central considerations.

The comparison considered Genesis, Isaac Sim/Isaac Lab, Unreal/Unity, Habitat, and MuJoCo/MJX. Only Genesis has a runnable project demonstration in this task directory. The other entries are design assessments recorded in the initial report; they are not measured FPS, memory, or task-success benchmarks. Historical hardware-requirement and licensing statements should not be presented as current verified specifications.

## Attempts, outcomes, and interpretation

| Attempt | Motivation / method | Recorded outcome | What we learned |
| --- | --- | --- | --- |
| Compare simulator options | Assess visual assets, quadruped support, setup, and local hardware constraints | Genesis selected for the initial demonstration | Early development needed a manageable visual/physics workflow; selection is project-specific |
| Load a detailed office with collision processing | Use the scene mesh for both visuals and interaction | Initial notes report an out-of-memory failure during collision-hull processing | Detailed visual meshes can be too expensive as collision models; no numeric VRAM trace is saved here |
| Use a visual office mesh and a separate floor | Set `collision=False`, `convexify=False`; add `plane.urdf` | The supplied script implements this workaround; a demo video is retained | The floor supplies support while the office supplies appearance. Office furniture does not become a physical obstacle through this setup |
| Integrate a pretrained Go2 policy | Map policy joint order to URDF order, scale observations/actions, apply position targets | `run_go2.py` provides stand/walk modes and keyboard commands | Learned control depends on the checkpoint's observation, joint-order, action-scale, and gain contract |
| Separate live preview from high-quality rendering | Keep development responsive; consider offline rendering | Proposed in the original evaluation; the supplied script does not configure the ray-tracer | This is a design direction, rather than a demonstrated photorealistic-rendering benchmark |

The saved video is [Genesis_without_physics.mp4](videos/Genesis_without_physics.mp4). Its filename alone does not establish the physics configuration of that recording. The current script contains robot physics and a support plane, with the office mesh visual-only. No synchronized configuration/metric manifest accompanies the video.

## Implementation documented from the script

| Component | Current implementation |
| --- | --- |
| Entry point | [run_go2.py](run_go2.py), `Go2Controller` |
| Backend | Genesis GPU; Torch inference explicitly uses `cuda:0` |
| Simulation setting | `dt=0.02`, `substeps=2`; one policy call per scene step in walk mode |
| Robot / scene | Go2 URDF, plane URDF, office GLB |
| Policy joint order | FR, FL, RR, RL; hip/thigh/calf within each leg |
| Observation | 45 values: body angular velocity, projected gravity, velocity/yaw command, relative joint position, joint velocity, previous action |
| Action | 12 scaled offsets from standing angles, remapped to URDF order |
| Gains configured | Fixed gains 150/5 and RL gains 40/1; see mode-switch code |
| Controls | `0` stand, `1` walk, up/down forward/backward, left/right turn, Space stop, Escape exit |

These details describe this Go2 script. Task 3 uses a different robot, policy history, transmission, and controller; its settings must not be substituted here.

## Reproduction and dependencies

The office GLB and pretrained `rl_sar` policy are external dependencies. The script currently has a hardcoded policy path and a relative office path. Before running, check the `__main__` block and provide the matching assets:

```text
Policy: /home/vivekananda/UGP/rl_sar/rl_ws/src/rl_sar/policy/go2/robot_lab/policy.pt
Office: genesis-world/office-env/Office+2.glb
```

The policy path points outside this repository. The Genesis checkout is a separate submodule with local files; a fresh clone does not establish that the office asset or policy is available. Use the environment compatible with this script's Genesis keybinding API; the initial report does not contain a reproducible dependency lock.

With those assets and Genesis, PyTorch, NumPy, CUDA, and a graphical display available:

```bash
cd Task_1_Simulator_Evaluation
python run_go2.py
```

This documentation review did not rerun the GPU viewer. A video demonstration establishes recorded behavior, while a fresh run with source/configuration and performance logs is needed for repeatable measurements.

## Remaining work and presentation takeaway

1. Record a reproducible scene/policy/dependency manifest and measure memory, physics throughput, image latency, and tracking error.
2. Add simplified furniture/obstacle collision geometry instead of relying solely on a floor plane.
3. Verify the Go2 policy contract and measure gait stability before using the environment for navigation experiments.
4. Compare render and collision fidelity separately, then connect the visual environment to the language/planning pipeline.

**Presentation statement:** “We selected Genesis for an initial Go2 demonstration and worked around detailed-mesh collision memory costs by separating appearance from floor physics. This demonstrates setup feasibility; realistic obstacle interaction still needs validation.”
