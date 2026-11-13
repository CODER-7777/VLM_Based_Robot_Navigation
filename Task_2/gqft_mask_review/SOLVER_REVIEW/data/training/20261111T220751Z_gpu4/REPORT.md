# GPU-4 pilot completed — 12 November 2026

Three matched 500-step arms, batch4, one seed, no flips, sequence-floor labels. Completed arms use their preserved original source. The learned-weight arm requires two numerical repairs; the source snapshots and failed-attempt logs are preserved separately.

| Arm | Valid training progress | Fixed H24 ADE px | FDE px | Ambiguity | Selected history |
| --- | --- | ---: | ---: | ---: | --- |
| Yaw-local reference | 500 finite steps | 10.9558 | 13.3363 | 0.2083 | None |
| Solver + residual | 500 finite steps | 15.6302 | 16.4192 | 0.7308 | None |
| Solver + learned pixel weights | 500 finite steps | 15.5904 | 16.3026 | 0.7158 | None |

Fixed evaluation:104 windows,26 validation sequences, reference30, input24, anchor(480,809), canvas960x810, CUDA bfloat16; origin included. Lower ADE/FDE is better. Both completed models fail the original history gate. Neither hybrid improved over the reference. Learned weights reduced hybrid ADE only0.0399px relative to solver+residual; a reliable gain is not established by this single-seed pilot. These results are not the mixed-history training-time validation numbers.

The floor cutoff1.0m was selected on96 training windows. Frozen float32 solver validation ADE was16.2265px versus11.6359 original yaw; no validation cutoff sweep was used.

## Learned-weight failures and repairs

1. Initial validation cached inference tensors. Subsequent backpropagation failed. Cache construction now explicitly disables inference_mode; validation motion is unchanged on the regression fixture.
2. Padded/empty frames have zero residual. Differentiating sqrt(0) in the solver RMS diagnostic produced NaN gradients. The learned-weight arm skipped its optimizer steps, so these attempted steps are not valid training. The zero diagnostic is preserved with a finite derivative; positive mean-square residuals below1e-12 are floored only for the square root.

The first invalid attempt crashed before training. The second attempted run had no finite optimizer updates. Its logs/checkpoints remain archived; it is restarted from the matched initialization rather than treating it as trained progress. Eight regression checks cover inference-to-training, preserved validation motion, solver gradients, empty-frame diagnostics and full-model padded backward. All eight checks passed on both CPU and GPU4. The corrected learned-weight run completed500 consecutive finite steps and its full seven-history validation. All three arms now have500 finite training steps and saved best/last checkpoints. No additional run is queued. Server evidence is saved in `inference_and_padding_gpu_check.json` and `latest_progress.json`.

The server run directory, code snapshots and user GPU authorization are in `run.json`. GPU4 remains the user-authorized device. No locked-test data or new training houses were used.

## Result and next decision

All1500 valid optimizer steps finished on GPU4. The best model among these matched arms is the yaw-local reference at10.9558px H24 ADE; its ambiguity0.2083 still exceeds0.05. Solver hybrids are substantially worse (15.6302/15.5904px) and have higher ambiguity. Do not promote a hybrid or extend it into a long run based on this pilot. Next diagnose the saved representations and observed-prefix/future-tail retrieval, audit label geometry, and inspect matching overlays before selecting another intervention. No locked-test evaluation was run.

## Full recorded-episode visualizations

[Open all10 episodes and133 full legs](../../trained_episode_overlays/20261111T220751Z_gpu4/all_episodes_20261111T223221Z/index.html). The three selected checkpoints are frozen. Continuous episode and independent full-leg views are separate diagnostics; no architecture settings are chosen from these images.
