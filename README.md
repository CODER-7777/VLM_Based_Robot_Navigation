# VLM-Based Robot Navigation — UGP

**Vivekananda Y24 · Mid-evaluation: 10 October 2026**

Objective: language-conditioned quadruped navigation with visual scene understanding, geometric trajectory estimation, and physically executable locomotion. The current repository contains component experiments; end-to-end language-navigation success is not yet measured.

## System components

| Component | Implementation | Current result | Pending |
| --- | --- | --- | --- |
| [Task 1: simulation](Task_1_Simulator_Evaluation/README.md) | Genesis, Unitree Go2, pretrained position-target policy | Office/robot demonstration using visual mesh + collision plane | Furniture collision, reproducible assets, memory/throughput measurements |
| [Task 2: visual trajectories](Task_2/README.md) | SEA-RAFT → spatial CNN → causal Transformer → 3-D displacement / pixel projection | Spatial + Yaw fixed-history test ADE 8.783 px versus baseline 9.631 px | Consistent projection labels, history protocol, navigation integration |
| [Task 3: locomotion](Task_3/README.md) | SvanM2 MoE student, 225-D history, 50 Hz policy, coupled 200 Hz PD | Contact-setting intervention reduces vibration and changes tested stair outcomes | Deployed-contract calibration and measured hardware improvement |
| [Task 4: scene observations](Task_4/README.md) | Calibrated MP3D kitchen repairs; Habitat/NavMesh + separate Gaussian RGB-D | 4.378M-Gaussian scene, 23 comparison groups, reviewed placement audit | Novel-view quality, measured-depth accuracy, articulated robot coupling |

These systems use different embodiments and runtimes: Go2/Genesis, SvanM2/MuJoCo, and a Habitat navigation agent. Their interfaces are not yet one integrated robot pipeline.

## Principal experimental results

| Experiment / protocol | Reference | Candidate | Interpretation |
| --- | ---: | ---: | --- |
| GQFT test ADE, history 24 | 9.630945 px | 8.783099 px | Spatial + Yaw: 8.80% lower; tested history differs from validation selection |
| GQFT test FDE, history 24 | 15.847433 px | 13.322794 px | Spatial + Yaw: 15.93% lower |
| GQFT CPU validation ADE, 104 matched windows | 11.2625 px | 10.2826 px | Attention improves validation; its test ADE worsens to 10.091 px |
| MoE 90000/90500 stair cases, October 2 | — | 0/12 traversals | Better early tracking / less target removal; jitter changes mixed |
| Newest91000 forward joint 8–30 Hz RMS, `impratio` 100 → 10 | 0.284° | 0.120° | Matched simulator contact intervention; speed maintained/increased |
| MoE stair pairs, two checkpoints × two gains, nominal start | 0/4 at 100 | 4/4 at 10 | Controlled simulation cases; hardware validity remains unresolved |
| Dense-corner Gaussian reference PSNR | 27.52 dB | 18.79 dB | Cleaner local geometry trades off photo agreement; held-out 7.28/10.48 dB |

Results are saved records, not new benchmark runs. [Metric artifacts and source hashes](docs/mid_evaluation/EVIDENCE_INDEX.md).

## Current research direction

- **Trajectory estimation:** isolate inconsistent ground-plane supervision before another architecture change. Compare `sequence_floor` and `fixed_rig` with architecture, seed, split, history, and query held fixed.
- **Locomotion:** separate control-contract/contact-model error from policy error. Keep deployed hardware parameters fixed; compare vibration, velocity/heading tracking, and traversal together.
- **Scene reconstruction:** retain fixed geometric surfaces and original PBR assets; improve calibrated coverage/materials, then evaluate the final revision on unchanged held-out cameras.
- **Integration:** specify a waypoint/velocity interface and measure language-task success, path efficiency, collisions/falls, and end-to-end latency.

## Source and artifacts

`Task_2/gqft_algorithm_sharing_vivekananda/` and `Task_3/xterra_mjlab/` are independent source repositories. Task 3 analysis tools and Task 4 repair/rendering tools are maintained in the parent repository. Large datasets, environments, model weights, and final kitchen checkpoints remain local or on ISL.

[Code and dependency index](docs/mid_evaluation/CODE_INDEX.md) · [Evidence index](docs/mid_evaluation/EVIDENCE_INDEX.md) · [Repository layout](docs/mid_evaluation/REPOSITORY_GUIDE.md)
