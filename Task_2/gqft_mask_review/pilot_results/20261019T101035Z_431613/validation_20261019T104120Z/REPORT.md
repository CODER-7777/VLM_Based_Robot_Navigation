# Completed four-arm GQFT pilot — 19 October 2026

Server run: `/data/robotics/toshith/vivekananda/gqft_algorithm_sharing_vivekananda/gqft_mask_review/pilots/20261019T101035Z_431613`.

All four arms completed 500 steps with a 500-step finite streak. Both best and last checkpoints are at step 500. Staged source hashes were verified before evaluation. Evaluation used physical GPU 7.

## Training-time validation

These are mixed-history training validation scores (260 queries). They are separate from the fixed-window results below.

| Arm | ADE (px) | FDE (px) |
| --- | ---: | ---: |
| Reference (attention + yaw auxiliary) | 9.8412 | 12.0066 |
| Soft masking only | 9.7691 | 12.1146 |
| Yaw-local integration only | 8.9469 | 10.6780 |
| Soft masking + yaw-local integration | 9.0909 | 10.8815 |

## Matched validation at history 24

All models see the same 104 reference windows from 26 validation sequences, with one extended anchor query per window. Reference horizon is 30 flow pairs; only model inputs are truncated. Pixel ADE includes the origin and all reference-valid points (2,600 at history 24), independent of the predicted stopping gate. Labels use sequence_floor, seed 20260820, virtual extension 270 px. Precision is the existing evaluator’s CUDA bfloat16 autocast.

| Arm | ADE (px) | FDE (px) | ADE change vs pilot reference | Selected history* |
| --- | ---: | ---: | ---: | ---: |
| Reference (attention + yaw auxiliary) | 12.4626 | 17.4344 | +0.00% | 16 |
| Soft masking only | 12.8267 | 18.8231 | +2.92% | 20 |
| Yaw-local integration only | 11.3485 | 13.3930 | -8.94% | none |
| Soft masking + yaw-local integration | 11.8091 | 14.1293 | -5.24% | none |
| Original pretrained attention + yaw | 11.6926 | 15.3060 | -6.18% | 16 |

*Selected among 4, 8, 12, 16, 20, 24 and 30. The gate uses cross-sequence embedding retrieval of full 31-point reference curves: retrieval gap within 2% of the best equal/longer history and ambiguity ≤0.05 among cosine-near pairs (cosine ≥0.995; different curves >0.10 m apart). These are sequences, not necessarily different houses. This is not proof of unambiguous motion in all environments.

## Interpretation and next step

The lowest fixed-history-24 pilot ADE belongs to **Yaw-local integration only**. Use the fixed-window table when judging long-horizon motion; a mixed-history average can hide a regression there.

Masking alone increases H24 ADE by 2.92%. Adding masking to yaw-local increases ADE by 4.06%. The pilot therefore supplies no accuracy evidence for adopting this masking configuration. Yaw-local alone has a useful path-error signal, but both yaw-local arms fail history selection at every tested history. At H24 their ambiguities are 0.1667 and 0.2000, versus the 0.05 limit.

This is one seed and 500 steps, with newly initialized motion and uncertainty heads in every pilot arm. The original pretrained checkpoint retained its trained heads and has a different training budget, so it is an operational reference rather than a matched training arm. A lower score is descriptive; no statistical or test-set improvement has been established.

Recommendation: retain the original checkpoint as the working reference and defer a long combined mask/yaw run. First inspect the yaw-local nearest-neighbour ambiguity cases and per-sequence trajectory errors. Reproduce the reference/yaw-only comparison with matched seeds before increasing the budget. For a follow-up, hold the same initialization, labels, windows and budget across arms; use fresh output folders and at least three matched seeds. Preserve the four saved checkpoints. Keep the locked test untouched until the model and history are fixed on validation. No additional training was launched during this review.

The soft mask floors reliability at 0.25, retains original max pooling and has no hard attention cutoff in this pilot. Reported feature coverage of 1.0 means all feature cells remain eligible; it does not mean their confidence/ground weights are all one. No empty-mask frames were observed.

## Evidence

- [Checkpoint/configuration/source provenance](provenance.json)
- [All histories and metrics](comparison.csv)
- Per-arm JSON and logs in this directory preserve complete evaluator output.
- Copied training metrics/configurations are in the parent run folder.
