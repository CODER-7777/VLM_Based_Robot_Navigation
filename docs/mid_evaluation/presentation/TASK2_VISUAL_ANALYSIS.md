# Task 2 — graph interpretation and episode selection

The slide statements below use saved measurements; no training or inference was rerun to prepare these slides. The episode PNGs were inspected visually and copied unchanged. [Slide text](SLIDE_TEXT.md) contains the short version.

## Validation comparison: what the two panels show

[Open graph](../figures/task2_validation_comparison.png) · [Underlying diagnostics](../evidence/task2/validation_diagnostics.json).

Protocol: 104 validation windows, one query/window, history 24, CPU float32. Each curve uses the same windows. The left panel plots error at each elapsed timestep, not cumulative ADE. Mean path ADE and endpoint FDE are separate summaries.

| Observation | Interpretation | Engineering decision |
| --- | --- | --- |
| Attention's error curve stays below baseline over the evaluated trajectory; overall ADE 11.2625→10.2826 px | Regional aggregation helps this validation set | Retain Attention as a candidate, with the full evaluation gate |
| Yaw has larger early/intermediate errors but the lowest validation FDE, 15.3053 px | Improved endpoints can coexist with worse average path error; yaw ADE is 11.6358 px | Report ADE and FDE together; isolate yaw in a later ablation |
| Family 1 Attention ADE 6.9609→8.2854 px | Constant-arc behavior regresses despite overall gains | Inspect turning cases; do not claim universal turning improvement |
| Family 7 remains around 20–22 px for all variants | A shared difficult group deserves diagnosis before further architecture scaling | Use the exact-motion oracle to distinguish geometry from learned-motion error |
| Attention has no selected history under the existing gate | Lower ADE alone is insufficient for the intended history-selection task | Keep selection thresholds fixed; require a valid selection before selected-history testing |

The right panel uses motion-family IDs. Family 1 is identified as constant arc in the saved failure analysis. Do not assign invented semantic names to the other IDs. Family aggregates alone do not prove that every difficult window has the same cause.

## Saved test comparison: what can be concluded

[Source metrics](../evidence/task2/summary.json).

| Variant | ADE px | FDE px | Endpoint within 10 px |
| --- | ---: | ---: | ---: |
| Baseline | 9.630945 | 15.847433 | 39.17% |
| Attention | 10.090982 | 16.591120 | 37.50% |
| Attention + Yaw | 8.783099 | 13.322794 | 45.00% |

Attention regresses by 4.78% ADE and 4.69% FDE on these saved test records. Attention + Yaw improves by 8.80% ADE and 15.93% FDE. This supports a fixed-history result, not a universal causal attribution to yaw: checkpoints/training differ and a matched yaw-only controlled ablation is pending.

Test used history 24. Historical yaw validation selected 12; the standardized validation sweep selects 16. Eight yaw queries repeat one anchor. Validation and test are distinct protocols, so do not combine their counts or treat cross-split differences as treatment effects. These are recovered results, not a new test evaluation.

## Geometry graph: which analysis justified the label experiment?

[Open graph](../figures/task2_geometry_failure.png) · [Oracle evidence](../evidence/task2/geometry_oracle.json).

- **Left panel:** even the model variants disagree with the ground-truth shape in the worst validation window. An overlay alone cannot identify the cause.
- **Right panel:** replace model motion with exact ground-truth 3-D displacement. Substantial error remains at starts 15, 10 and 5 of `val_v023`, demonstrating a label/projector mismatch.
- Labels measure camera height relative to the sequence's initial floor; the model projector assumes a fixed 1.2 m mounting height. Three windows differ by more than 1 cm.
- The bars report **history-24 oracle ADE**; the **65.525 px** headline is a maximum point discrepancy. These are different statistics.
- Matching projection height reduces maximum discrepancy to **0.000126 px**. This verifies the geometric diagnosis, not a learned-model improvement.
- The resulting optional `fixed_rig` mode is implemented and off by default. Compare it against `sequence_floor` in paired Attention training; retain both annotation protocols explicitly.

## Episode PNGs: what is actually visible?

| Image | Visible behavior | Appropriate caption |
| --- | --- | --- |
| [ep837, leg 7](assets/task2_ep837_leg07_historical.png) | Orange path follows a near-straight direction but ends short of the magenta traversed path; green is shorter and displaced | Historical near-straight episode: direction and path-length differences |
| [ep1285, leg 23](assets/task2_ep1285_leg23_historical.png) | Traversed path curves left; orange and green show different curvature and endpoint positions | Historical curved episode: heading and endpoint disagreement |
| [ep837, leg 11](assets/task2_ep837_leg11_historical.png) | Traversed path bends strongly; orange drops into the extended canvas and differs visibly from the traversed route | Historical turning episode: qualitative failure case |

Use these three cases on slide 5, which focuses on behavior still needing improvement. Magenta is the image's traversed-path reference; orange is labeled Spatial + Yaw. The other line identities and endpoint numbers are baked into legacy images, with different conventions from pixel ADE/FDE.

**Provenance limitation:** the saved audit found double flow normalization, pitch/anchor mismatches and an augmented checkpoint mislabeled baseline in historical episode tools. Therefore, the green line must not be described as a verified released-baseline comparison. These images cannot substantiate collision avoidance, success rate, or the quantitative benefits of the repaired adapter. The `LOCAL_ROUTE_REACHED` banner belongs to the historical episode, not a newly evaluated GQFT navigation policy.

Next: regenerate overlays through the corrected adapter with checkpoint hash, camera convention, anchor, segment joining and ground truth recorded. Until then, show the qualification beside the images and support model claims with the matched validation/test records.

## Evidence-to-fix chain

| Finding | Implemented change | What is still unmeasured |
| --- | --- | --- |
| Normalized cache flow divided again by grid dimensions | `pack_normalized_flow`: preserve scale and mask invalid vectors | Corrected episode benchmark |
| Opposite mounting-pitch convention and inconsistent anchor | Explicit pitch conversion, camera validation and trained anchor | Corrected episode benchmark |
| Misleading checkpoint provenance | Archive legacy tools; strict architecture-aware loader | Regenerated trustworthy overlays |
| Oracle detects incompatible label/projector height | Optional `fixed_rig` pixel targets, unchanged 3-D labels | Paired training and validation under both label conventions |

Source: [failure analysis](../../../Task_2/gqft_algorithm_sharing_vivekananda/docs/FAILURE_ANALYSIS.md). CPU checks validate contracts and output compatibility; they do not substitute for training or deployment evaluation.
