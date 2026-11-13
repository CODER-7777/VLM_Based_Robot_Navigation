# Episode 629, leg 0 — interpreted masking probe

Reviewed 14 October 2026. Source is the user's downloaded GPU 7 run `20261013T170841_769161Z`. This is the first 24 consecutive flow pairs (25 pose samples) of leg 0, with the existing Attention + Yaw checkpoint. No mask training, fitted scale, or fitted rotation was used. The origin is excluded from both average error measures. This is an episode diagnostic, not a released validation/test benchmark.

## Measured result

| Metric, lower is better | Unmasked checkpoint | Same weights with validity masking |
| --- | ---: | ---: |
| Mean ground-position error over 24 post-origin poses | 10.248 cm | 10.965 cm |
| Ground endpoint error | 27.973 cm | 34.293 cm |
| Mean projected pixel error over the same 24 reference-valid poses | 68.711 px | 52.409 px |
| Projected endpoint error | 139.239 px | 107.770 px |
| Accepted analytic-prefix points, including origin | 25 | 2 |

Pixel errors improve, but ground-position errors worsen in this window. Masking therefore does not establish a better motion estimate here. Original and masked paths are predictions from the same trained yaw checkpoint, not a released mean/max-baseline comparison.

The recorded endpoint is `(forward,left)=(0.2160,0.7122) m`. The unmasked estimate is `(0.3988,0.5005) m`; the masked estimate is `(0.1353,0.3790) m`. Masking reduces the forward overestimate but also loses more leftward movement. Perspective pixel errors weight these differences differently, so lower pixel error need not imply lower metric motion error.

## Why the original images were difficult to interpret

- The validity and retained-input images are identical because validity-only masking was selected. Confidence values are displayed but are not thresholded in this run.
- The old pixel plot used the model's cumulative analytic validity mask. Masked pose index 2 projects to `v=812.137 px`, outside the 810-pixel canvas; subsequent points remain analytically gated out even when they return inside. Only the first two orange points were drawn. The raw reconstructed trajectory still exists. The diagnostic plot now distinguishes the accepted prefix from the raw continuation without changing the projector or predictions.
- Attention maps had no raw-image overlay or colour scale, and first/middle/last sampling missed frame 9's strongest rejected-attention event. The new explanatory overlay includes first, lowest-coverage, highest-rejected-attention, and last frames. This frame selection is for explanation, not algorithm selection.

## What masking actually removed

Mean rejected input coverage: 15.751%; mean rejected feature-cell coverage: 19.514%. Original attention placed 17.456% of its mass, on average, on cells later rejected. At flow frame 9 this rises to 83.653%; masked attention gives those cells exactly zero weight. Both pooling branches are masked, so attention-weight changes alone do not account for the entire prediction change.

The red overlays primarily cover flow-invalid image borders in this window. Cyan outlines indicate rejected cells on a coarse 6-by-10 feature grid; these are approximate spatial locations, not pixelwise causal saliency. This is not a wall/clock/sofa segmentation mask and does not demonstrate that an object caused the trajectory error.

## Reference construction and checks

The server recording source was inspected read-only:

- `flowvo_compare/scripts/build_poses.py`: `pose[:,0:2]` is world x/z; yaw is `atan2(heading_z,heading_x)`, reconstructed from per-tick `diag.true_local` for drive legs.
- `flowvo_compare/scripts/render_frames.py`: raw PNGs are re-rendered at these x/z/yaw samples, with constant floor height and the stored mounting settings.

Ground displacement is rotated into the window-start `(forward,left)` axes with the verified heading convention. A fixed-height, +30-degree downward-pitch camera maps this reference to the same query `[480,809]` and projection contract as the saved predictions. Pixel errors are evaluated on reference-valid points, independently of a prediction's prefix truncation. Direct ground-position errors use all 24 post-origin pose samples.

Checks passed for axis conversion at multiple initial headings, pure forward/left motion, stationary turning, and exact agreement of the NumPy projection/gating calculation with the existing Torch projector. The reference is faithful to the recorded/re-rendered planar episode, not an independent measurement of physical robot motion or terrain height.

## Clear local artifacts

Artifacts are under `analysis/masked_attention_v1/review_ep629_leg00_20261013T170841_769161Z/review/`:

- `ground_truth_comparison.png`: green recorded reference, blue original, orange masked; ground and pixel error curves.
- `projection_explained.png`: accepted prefixes and dashed raw continuations on the original image and extended canvas.
- `mask_explained.png`: raw images, red rejected-input overlays, and before/after attention with one colour scale.
- `review.json`: measured errors, coverage and projection-gate diagnosis.

The user's original download is unchanged. Raw pose/image copies for review are under the sibling `inputs/` directory.

To reproduce from the GQFT project root:

```bash
CUDA_VISIBLE_DEVICES='' .venv/bin/python tools/review_episode_mask.py \
  --probe-dir /home/vivekananda/Downloads/gqft_ep629_leg00/20261013T170841_769161Z \
  --poses-file analysis/masked_attention_v1/review_ep629_leg00_20261013T170841_769161Z/inputs/b10_A_drivefix_idx3_20260829_114756.npz \
  --frames-dir analysis/masked_attention_v1/review_ep629_leg00_20261013T170841_769161Z/inputs \
  --out-dir analysis/masked_attention_v1/review_ep629_leg00_20261013T170841_769161Z/review
```

## Next experiment

1. Score the other already-generated 629 windows against the same recorded pose convention. Use their existing caches/predictions; no additional SEA-RAFT run is needed.
2. Compare the frozen unmasked/masked model on the fixed validation scene/windows/history/query protocol. Report ground/3-D and pixel errors together, retained coverage, prefix failures and motion-family regressions. Keep the separate ground-label convention experiment explicit.
3. If the validation evidence supports proceeding, train an unmasked/masked Attention pair with identical initialization, labels, seed, history and budget. Keep yaw and flips off in that primary architecture comparison. A frozen model not trained for masked pooling can react poorly to hard removal; a new training comparison is needed to evaluate the learned masking treatment.

Do not choose confidence thresholds from this episode or interpret a single improved pixel score as a general navigation improvement.
