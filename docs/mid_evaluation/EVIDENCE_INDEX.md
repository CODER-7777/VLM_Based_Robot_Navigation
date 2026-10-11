# Evidence index and interpretation rules

This review is based on the local repository, nested source checkouts, historical reports, and saved result artifacts. Recorded benchmark metrics were not rerun. The current source review also ran CPU regression checks for strict checkpoint/output equivalence, reward integration, recording, and short passive MuJoCo trajectories; it did not contact ISL, collect robot data, launch training, or reevaluate locked test. Snapshots are byte-identical copies with source hashes in the three manifests.

## Claim-to-artifact map

Latest polygon/PBR evidence: [v8 scene checks](evidence/task4/v8_scene_verification.json), [23-view/30-route browser review](evidence/task4/v8_browser_review.json), [33-prop screening](evidence/task4/v8_placement_audit.json), [tray geometry](evidence/task4/v8_tray_geometry.json), and [shared-camera home-tour checks](evidence/task4/v8_home_tour_verification.json). [Home-tour image](figures/task4_v8_home_tour.png) and [tea-setting comparison](figures/task4_v8_tea_comparison.jpg) are copied unchanged from retained browser evidence. Gaussian accuracy is still a separate pending evaluation.

| Claim / question | Portable evidence | Qualification |
| --- | --- | --- |
| Genesis office/Go2 demonstration | [Task 1 script](../../Task_1_Simulator_Evaluation/run_go2.py), [saved video](../../Task_1_Simulator_Evaluation/videos/Genesis_without_physics.mp4), [historical notes](../../Task_1_Simulator_Evaluation/notes/INITIAL_EVALUATION.md) | Reported feasibility; no quantitative performance/VRAM manifest; office is visual-only in current script |
| Released GQFT test reference | [baseline_test_h24.json](evidence/task2/baseline_test_h24.json) | Existing test result, reference history 24 |
| Attention test regression | [attention_test_h24.json](evidence/task2/attention_test_h24.json) | Existing fixed-history test; validation history-selection gate fails |
| Yaw fixed-history improvement | [yaw_test_h24.json](evidence/task2/yaw_test_h24.json), [summary.json](evidence/task2/summary.json) | Historical test history differs from validation-selected history; repeated anchors inflate counts without independent tasks |
| Matched validation tradeoffs | [validation_diagnostics.json](evidence/task2/validation_diagnostics.json) | CPU float32, one scene, 104 windows, common histories/query/window settings |
| Label/projector inconsistency | [geometry_oracle.json](evidence/task2/geometry_oracle.json) | Oracle experiment isolates geometry; it does not set a universal minimum model error |
| GQFT adapter/loader checks | [cpu_contract_checks.json](evidence/task2/cpu_contract_checks.json) | Historical software verification, not a new model benchmark |
| Hardware target/angle association and contract differences | [hardware_audit_report.md](evidence/task3/hardware_audit_report.md) | Copied historical report; raw robot logs and external audit implementation are not bundled; its original relative links may need the original audit folder |
| 90500 matched motion and failures | [matched_90500.csv](evidence/task3/matched_90500.csv), [stair_starts_90500.csv](evidence/task3/stair_starts_90500.csv) | Common 4–8 s early window; 12 distinct stair cases; candidate changes several settings |
| Exploratory target-rate references | [target_rate_summary.json](evidence/task3/target_rate_summary.json) | 41 attempts reviewed, 19 windows selected, six reference windows; not motor calibration |
| Rate/clearance code integration | [rate_clearance_integration.json](evidence/task3/rate_clearance_integration.json) | Synthetic-action smoke, not policy success; local saved check used CUDA historically |
| Gain effects | [gain_sensitivity.json](evidence/task3/gain_sensitivity.json) | Matched scripted simulator conditions, checkpoint-specific outcomes |
| Contact-setting vibration / traversal changes | [contact_findings.json](evidence/task3/contact_findings.json) | Nominal-start paired simulation outcomes and repeated flat sensitivities; no hardware causal proof |
| Force/torque/slip response | [contact_response.json](evidence/task3/contact_response.json) | Offline analysis of the same saved simulations; rigid-foot slip proxy |
| Fixed-state regularization comparison | [fixed_state_regularization.json](evidence/task3/fixed_state_regularization.json) | Same recorded state, no integration; shows numerical constraint change, not proportional physical-force change |
| Solver/substep follow-up | [solver_probe.json](evidence/task3/solver_probe.json) | 28 simulator cases; grid/confirmation stages; not independent trained seeds |
| Licensed toaster source | [toaster_archive_metadata.json](evidence/task4/toaster_archive_metadata.json) | Source provenance/license; approximate product match; model archive stays in original source folder |
| Bounded wall repair | [wall_geometry_result.json](evidence/task4/wall_geometry_result.json) | Local repair counts; does not certify the whole room |
| Initial Gaussian held-out failure | [initial_gaussian_evaluation.json](evidence/task4/initial_gaussian_evaluation.json) | Displayed/JPEG metric on modeled masks and synthetic toaster target; two held-out cameras |
| Dense-corner appearance/depth tradeoff | [dense_corner_evaluation.json](evidence/task4/dense_corner_evaluation.json), [dense_corner_geometry.json](evidence/task4/dense_corner_geometry.json) | Measured-depth comparison and mesh-consistency comparison have different reference truth/denominators |
| Latest all-kitchen complexity / valid depth / kernel timing | [all_kitchen_publication.json](evidence/task4/all_kitchen_publication.json) | One published production frame; current service availability unverified |
| Final placement evidence | [all_kitchen_placement.json](evidence/task4/all_kitchen_placement.json), [size_exceptions.json](evidence/task4/size_exceptions.json) | Reviewed thresholds with two explicit size exceptions; static fit checks |
| Static collision and camera bridge | [physics_validation.json](evidence/task4/physics_validation.json) | Sensorless NavMesh prototype; empty-world Bullet timing is not articulated-contact performance |
| Gallery/model/browser checks | [browser_verification.json](evidence/task4/browser_verification.json) | Saved browser state; not a new live verification |

## Conflicting or superseded statements

| Earlier statement / source | Current interpretation |
| --- | --- |
| Root README: augmentation is the next active GQFT experiment | Flip runs are historical/discontinued. Current controlled plan investigates projection-label consistency without augmentation. |
| `Task_2/CURRENT_STATE_REVIEW.md`: yaw benchmark/checkpoint missing; architecture mismatch unresolved | Later recovered results and strict variant loader supersede those gaps. The earlier review accurately records its then-local evidence state. |
| Earlier yaw FDE 14.21 px | Recovered metric JSON gives **13.322794 px**. |
| Attention improves 3-D performance by 31% | Earlier report mixed baseline validation retrieval gaps with attention test retrieval gaps. Same-test retrieval gaps worsen; retrieval is not direct prediction error. |
| Aug_v2 tracker history table matches baseline; test improvement implied by training validation | Use actual archived run metrics; training-time validation cannot establish locked-test improvement. |
| GQFT overlays show a verified baseline or obstacle avoidance | Some “baseline” overlays used an augmented checkpoint; legacy adapters had flow/pitch defects. Reconstruction overlays do not demonstrate collision avoidance. |
| Task 3 overview identifies candidate 90500 as latest | Newest 91000 (`dec9775d…`) and earlier 91000 (`f74e62bf…`) are distinct. Use recording/checkpoint hashes and saved settings. |
| Earlier stair cases show no policy can climb | Earlier 90000/90500 cases fail in their stated setups. Later 90000/newest91000 contact-setting pairs complete at 10. Keep both results and their configurations. |
| Low initial foot contact proves no learned lift | The later successful candidate first contacts low and then recovers. Low first contact is a diagnostic, not a proof of impossibility. |
| Change simulator `impratio` to fix real hardware | It is a simulator contact parameter. The results motivate validation of contact/control assumptions; they do not supply a hardware switch or validated deployment change. |
| Task 4 current scene has 349k or 1.04M Gaussians | Those are earlier Gaussian/corner stages. Latest saved all-kitchen publication has **4,378,360**. |
| Task 4 earlier search says selected toaster has not been downloaded | Later selected-model installation obtained it through a licensed archive and preserved PBR materials. |
| `scenes/v15/2azQ1b91cZZ.glb` is the final repaired scene | It is an older local snapshot; later final assets/checkpoints remain on ISL. |
| A depth-validity or placement pass proves photorealism | Coverage, depth accuracy, support geometry, and visual fidelity require separate evaluation. |
| 36k navigation queries/s proves 1,000 FPS RGB-D | Different workloads; render and end-to-end transport latency must be measured separately. |

Older reports and source artifacts are preserved. The task READMEs and this index establish the interpretation for this mid-evaluation.

## Metric definitions and comparability

| Metric | Meaning / unit | Comparison rule |
| --- | --- | --- |
| ADE / FDE | Mean trajectory-point / endpoint displacement error, here pixels | Match labels, split, windows, query anchor, history, precision, and visibility convention |
| Direct 3-D trajectory error | Predicted vs ground-truth displacement, metres | Different from nearest-neighbour embedding-retrieval curve gaps |
| Selected history | Shortest history satisfying the documented validation rule | Do not replace a failed gate by a convenient fixed history without disclosure |
| Joint-band RMS | Measured-angle frequency-band amplitude, degrees | Recent joint traces use 200 Hz / 8–30 Hz; targets at 50 Hz use 8–20 Hz; gait/impact content may contribute |
| Target removal / occupancy | Clamp-removed requests / time at target bounds | Neither establishes torque clipping or physical joint-stop contact |
| Speed RMSE / mean speed | Tracking error / actual commanded-axis velocity, m/s | Preserve command, frame, window duration, start, and contact status |
| Stair traversal | Recorded all-foot/loaded-platform/upright/lane/hold criterion | Distinct from base progress, partial stepping, or a visually promising clip |
| PSNR | Masked displayed RGB agreement, dB | Match revision, camera, clipping/JPEG, masks, real/synthetic target; training view ≠ unseen view |
| Depth validity | Fraction meeting opacity/depth criteria | Coverage is not accuracy; record full-image vs selected-surface denominator |
| Depth error | Difference to measured depth or mesh ray intersection | State the reference truth; those two checks are not interchangeable |
| Raster / query timing | One CUDA kernel or isolated navigation query, ms | Excludes other application costs; not end-to-end sustained FPS |

## Scope of verification in this review

The package validator checks report links/anchors, copied-file hashes, JSON/CSV structure, GQFT percentage arithmetic, the 12 earlier stair outcomes, the four paired later traversals, and the latest kitchen publication values. It verifies that the documentation agrees with its artifacts; it does not repeat the underlying experiments or independently establish physical truth.

Use [manifest task2](evidence/task2/manifest.json), [manifest task3](evidence/task3/manifest.json), and [manifest task4](evidence/task4/manifest.json) to trace each snapshot/figure to its original source and SHA-256.

## Current presentation evidence — October 10

| Claim | Snapshot | Protocol |
| --- | --- | --- |
| Current tight-limit contact intervention: 34 CPU cases; 63.5–70.5% flat reduction; 0/6→3/6 stairs | [Current verification](presentation/assets/task3_current_verification.json), [flat CSV](presentation/assets/task3_current_flat.csv) | Current hips ±0.735, calf upper −0.88776, kp18/kd0.7; independent of the older wider-limit four-pair study |
| Latest product mesh: 22 reviewed selections, seven routes / 88 panels | [Browser review](presentation/assets/task4_product_browser_review.json), [HTTP checks](presentation/assets/task4_product_http_checks.json) | Private PBR mesh; no Gaussian retraining; saved review, no live availability check |
| Original toaster retains 11 parts and all three maps | [Material verification](presentation/assets/task4_original_toaster_materials.json) | SHA-256 comparison; product mesh branch |
| Actual slide images and demo frame | [Asset manifest](presentation/assets/manifest.json) | Byte-identical plot/browser copies; single extracted Genesis video frame has separate source hash |

Independent diagrams are explanatory. Papers and publication metadata are verified in [REFERENCES.md](REFERENCES.md).
