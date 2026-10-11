# GQFT experiment status

| Stage | Status | Evidence / pending work |
| --- | --- | --- |
| Released baseline | Reproduced | Fixed-history test ADE/FDE 9.630945/15.847433 px |
| Historical flips | Discontinued | Training-time validation gains only; runs archived |
| Attention | Evaluated | Validation ADE improves; test regresses; selected-history gate fails |
| Attention + Yaw | Recovered/evaluated | Test 8.783099/13.322794 px at history 24; selection-protocol caveat |
| Adapter/loader repair | CPU verified | Normalization, pitch/anchor, strict architecture/output equivalence |
| Label geometry | Failure isolated | Three validation windows conflict with fixed-height inference projector |
| Paired supervision | Planned | Attention/no yaw/no flips, fixed seed/batch/steps; only sequence-floor vs fixed-rig labels vary |
| Navigation integration | Pending | Waypoint/velocity interface and language-task/collision/latency evaluation |
| Supervisor: attention masking | Research pending | Diagnose unreliable validation regions; exact mask to be clarified; [controlled masking plan](MASKED_ATTENTION_PLAN.md) |
| Supervisor: unify VLM / trajectory / RL | Design recorded; implementation pending | Motion estimation feeds calibrated local navigation; VLM provides subgoals, RL executes bounded velocity commands; [integration plan](../docs/INTEGRATION_PLAN.md) |

Current hypothesis: supervision consistency must be isolated before attributing errors to pooling/yaw. The planned annotation experiment reports both protocols separately; legacy benchmark labels remain the default. [Technical report](README.md) · [Detailed plan](gqft_algorithm_sharing_vivekananda/experiments/spatial_ground_plane_control_v1/plan.json).
