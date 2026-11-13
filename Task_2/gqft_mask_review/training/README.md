# GQFT GPU-4 training pilot

[Current run report](20261111T220751Z_gpu4/REPORT.md) · [Current run metadata](CURRENT_RUN.json)

The matched short pilot uses500 steps per arm, one seed, batch4, cached frozen SEA-RAFT, no flips and sequence-floor labels. Arms: yaw-local reference, solver+residual, solver+learned pixel weights. Only GPU4 is authorized. Shared datasets/environments and released baselines are preserved.

All three arms completed500 finite steps. Fixed-H24 ADE is10.9558px reference,15.6302px solver+residual and15.5904px solver+learned weights; all fail the original history gate. The learned-weight arm encountered two implementation defects (inference cache and zero-residual derivative), now covered by eight CPU/GPU regression checks. Invalid attempts are preserved and excluded from valid training progress. Consult the run report for the latest count and final comparison.

`run_training_pilot.py` starts a fresh matched pilot. `resume_training_pilot.py` preserves completed arms and supports separately staged repair snapshots. `verify_inference_cache.py` exercises validation-to-training and padded backward. These scripts do not install dependencies or regenerate flow.
