# Task 2 technical deliverable

Implemented: released-baseline reproduction; explicit mean/max, attention/max and yaw variants; strict checkpoint/config loading; normalized-flow and pitch/query adapter repair; optional `fixed_rig` labels; matched validation/motion-family analysis; geometry-oracle and CPU contract checks.

Best recovered fixed-history-24 test record: ADE **8.783099 px**, FDE **13.322794 px**, versus baseline **9.630945/15.847433**. Historical yaw validation selected 12 and test used 24; standardized validation selects 16. This is not a completed selected-history benchmark.

Unsuccessful/discontinued tracks: Attention test regression/history gate; historical flip runs with training-time validation gains but no established aug_v2 test result. Confirmed confounds: double flow normalization, mounting-pitch sign, anchor mismatch, misnamed baseline overlays, and inconsistent ground-height labels.

Current direction: paired attention-only/no-flip supervision study with unchanged architecture/seed/effective batch/steps/split/camera/query; report both legacy and fixed-rig annotation protocols. Pending: paired training, isolated yaw ablation, navigation/control integration and end-to-end task measurements.

[Results and implementation map](README.md) · [Source analysis](gqft_algorithm_sharing_vivekananda/docs/FAILURE_ANALYSIS.md).
