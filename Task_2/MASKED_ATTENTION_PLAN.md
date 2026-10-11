# GQFT masked-attention experiment

Supervisor feedback: investigate attention masking to reduce the influence of noisy motion evidence. **Research and implementation are pending.** The exact intended mask has not yet been specified; confidence/validity masking below is a candidate, not an attributed supervisor requirement.

## Current implementation

| Mechanism | Present behavior | Scope |
| --- | --- | --- |
| Flow validity | The episode adapter zeros invalid flow vectors and includes confidence/validity channels | Input packing; does not explicitly exclude CNN feature locations from pooling |
| Spatial attention | A small CNN predicts one score per feature-grid location; softmax forms a weighted sum | All grid locations enter attention normalization; max pooling is retained |
| Temporal causal mask | Blocks future observations | Prevents future-input access; not a spatial noise filter |
| Temporal history mask | Excludes padded history keys | Sequence-length handling; not a learned estimate of frame reliability |

Source: [frame encoder and Transformer](gqft_algorithm_sharing_vivekananda/step2/models/gqft.py), [flow adapter](gqft_algorithm_sharing_vivekananda/step2/episode_contract.py).

## Candidate experiment and open choices

1. Inspect saved validation flow/confidence/validity maps around high-error windows. Establish whether error coincides with invalid regions, low confidence, occlusion, or inconsistent geometry. Preserve the separate label-height diagnosis.
2. Define a reliability mask on the flow grid. Initially consider supplied validity plus a validation-selected confidence threshold. Dynamic-object or semantic masks require separate evidence and a specified source; distant background is not automatically noise.
3. Map reliability to the CNN feature grid with a documented coverage rule. CNN receptive fields mix neighbouring input locations, so masking pooled locations alone cannot guarantee that contaminated input has no effect.
4. Exclude rejected locations from attention normalization. For retained locations, normalize learned weights over the retained set. Consider soft reliability weighting as a separate alternative to a hard threshold.
5. Apply the same region eligibility rule to max pooling; otherwise its branch can still select rejected features. Compare joint attention/max masking with attention-only masking explicitly.
6. Handle an empty eligible set explicitly. Return a marked invalid motion observation or a documented finite fallback; avoid normalizing an all-masked row. Define how the temporal encoder and navigation layer respond to unreliable frames.

No thresholds, new model weights, semantic segmentation dependency, or denoising performance claim are selected yet.

## Controlled comparisons

| Candidate | Spatial pooling | Purpose |
| --- | --- | --- |
| Released baseline | Mean + max | Preserve original reference |
| Current Attention | Learned weighted sum + max | Reference for isolating masking |
| Masked Attention | Masked weighted sum + correspondingly masked max | Test whether excluding unreliable regions helps |
| Soft reliability variant, if justified | Learned attention adjusted by reliability | Test whether hard exclusion removes useful evidence |

Keep the camera, labels, split, queries, history, seed, effective batch and training budget fixed within the masking comparison. Run the separate `sequence_floor`/`fixed_rig` supervision comparison independently; do not change masking and label convention together and attribute the result to masking. No yaw or flips in the primary masking comparison.

Report full validation ADE/FDE, direct 3-D error, motion-family errors, history-selection outcome, valid-region coverage, empty-mask frequency and added latency. Inspect straight/curved/turning episodes with the corrected adapter and checkpoint identity. A perturbation study can separately examine sensitivity to injected flow corruption; clean-data regressions must also be reported. Select using validation, preserving the locked test for the established protocol.

## Integration role

GQFT currently reconstructs camera motion from observed flow. It supplies a motion estimate and reliability signal to the proposed navigation layer. It does not itself establish obstacle-free future waypoint planning. [VLM, motion and RL integration plan](../docs/INTEGRATION_PLAN.md).
