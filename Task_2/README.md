# Task 2 — GQFT trajectory estimation

Objective: reproduce the released GQFT baseline and improve visual trajectory estimation. Input is observed optical flow; outputs are camera displacement and ground-plane pixel trajectories, with optional yaw. Obstacle avoidance and language-navigation success are separate, unmeasured tasks.

## Model and data contract

`RGB → SEA-RAFT → normalized flow/confidence/validity → spatial CNN → causal Transformer → displacement increments → accumulated 3-D path → ground projection`.

Camera: 960×540, 135° HFOV, 1.2 m height, +30° downward-pitch convention, 5 Hz; flow grid 160×90; extended anchor region 270 px. Baseline pooling is mean+max; Attention replaces mean with learned weighted pooling and retains max. Yaw supervision adds a shared head and heading for episode joining.

## Attempts and outcomes

| Attempt | Change | Recorded outcome |
| --- | --- | --- |
| Baseline reproduction | Released source/checkpoint and camera contract | Test ADE/FDE 9.630945/15.847433 px |
| Historical horizontal flips | Mirror flow/query/3-D/pixel labels | Training-time best validation ADE 9.094 → 8.775/8.737 px; aug_v2 test improvement unestablished; branch discontinued |
| Spatial Attention | Learned regional aggregation | Better matched validation ADE; test regression; no valid selected history |
| Spatial + Yaw | Attention + supervised relative yaw | Recovered fixed-history test improvement; mixed matched validation results |
| Adapter audit | Normalize once, convert mounting-pitch sign, use trained anchor, strict checkpoint variants | Legacy flow/pitch/anchor defects and mislabeled augmented “baseline” overlays identified |
| Geometry oracle | Project exact ground-truth motion | Three of 104 validation windows conflict with fixed-height projection; maximum discrepancy 65.525 px |
| Controlled supervision plan | Attention without yaw/flips; vary only label ground plane | `sequence_floor` versus `fixed_rig` experiment specified; paired training pending |

## Quantitative comparison

Existing locked-test records, fixed reference/evaluation history 24:

| Model | ADE px ↓ | FDE px ↓ | Endpoint ≤10 px ↑ |
| --- | ---: | ---: | ---: |
| Baseline | 9.630945 | 15.847433 | 39.17% |
| Attention | 10.090982 | 16.591120 | 37.50% |
| Attention + Yaw | **8.783099** | **13.322794** | **45.00%** |

Yaw: 8.80% ADE / 15.93% FDE reduction. Historical validation selected history 12; test used 24; standardized validation selects 16. Eight yaw queries repeat the same anchor. This establishes a fixed-history result, not a completed selected-history benchmark or multi-seed generalization result.

Matched CPU float32 validation: scene `D7G3Y4RVNrH`, 104 windows, one query/window, reported history 24, reference 30, stride 5, no augmentation:

| Model | ADE px | FDE px | Direct mean 3-D error m | Selected history | Parameters |
| --- | ---: | ---: | ---: | --- | ---: |
| Baseline | 11.2625 | 16.6262 | 0.05197 | 24 | 3,986,823 |
| Attention | 10.2826 | 16.1270 | 0.04793 | None | 4,019,848 |
| Attention + Yaw | 11.6358 | 15.3053 | 0.05324 | 16 | 4,052,873 |

Selection: histories 4/8/12/16/20/24/30, ambiguity ≤0.05, retrieval tolerance 0.02. Embedding retrieval gaps are not direct 3-D prediction errors. Training-time validation, this CPU sweep, and test results use different protocols.

## Failure analysis and current hypothesis

Cached flow was divided by 160/90 a second time in legacy episode tools. Habitat mounting pitch −30° was passed into a +30° downward-pitch geometry convention. Some “baseline” overlays used an augmented checkpoint. Corrected adapters and strict architecture inference remove these confounds.

Original labels use height above the sequence's first floor; inference uses fixed 1.2 m height. Exact 3-D motion gives worst-window history-24 oracle ADE 55.559 px; matching label height reduces maximum discrepancy to 0.000126 px. The optional `fixed_rig` mode is off by default and changes the annotation protocol, so its scores cannot replace the legacy benchmark.

Current hypothesis: consistent projection supervision should reduce conflicting pixel/3-D objectives; regional flow aggregation remains useful but does not uniformly improve turning. Pending: paired label experiment, matched validation/history gate, source/checkpoint provenance, isolated yaw ablation, waypoint/controller integration.

## Source and verification

Source: [model](gqft_algorithm_sharing_vivekananda/step2/models/gqft.py), [strict loader](gqft_algorithm_sharing_vivekananda/step2/checkpoint.py), [episode contract](gqft_algorithm_sharing_vivekananda/step2/episode_contract.py), dataset/train/evaluation modules in `step2/`; CPU audits in `tools/`. [Detailed failure analysis](gqft_algorithm_sharing_vivekananda/docs/FAILURE_ANALYSIS.md) · [Metric snapshots](../docs/mid_evaluation/evidence/task2/summary.json).

```bash
cd Task_2/gqft_algorithm_sharing_vivekananda
CUDA_VISIBLE_DEVICES='' .venv/bin/python tools/verify_cpu_contracts.py
```

CPU checks cover strict variant loading, output equivalence to historical architectures, normalized-flow preservation, pitch/axis conversion, and contradictory configuration rejection. Dataset-dependent checks require the external cache. Training/inference weights are not included in the documentation evidence snapshots.
