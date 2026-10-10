# Mid-evaluation presentation guide

Suggested duration: **12 minutes**, followed by questions. Use the task reports for technical backup and the copied figures/metrics for the slides. The story is: **establish a simulation environment → investigate visual motion estimation → diagnose executable locomotion → improve scene observations → define the integration work still required**.

## Slide sequence

| Slide / time | Content to show | Main point to say | Evidence / visual |
| --- | --- | --- | --- |
| 1 / 0:30 | Project title, UGP objective, component diagram | “The long-term objective is a quadruped that follows language using visual understanding and physically executable control.” | [Project architecture](../../README.md#project-objective-and-how-the-tasks-connect) |
| 2 / 1:00 | Four-task progress table; current integration status | “This evaluation reports component studies and their evidence. The end-to-end system remains unfinished.” | [Review package](README.md) |
| 3 / 1:00 | Task 1 options, office collision issue, Go2 demonstration | “On constrained hardware, separating visual geometry from floor collision made the initial demonstration practical. Furniture collision and quantitative benchmarking remain open.” | [Task 1](../../Task_1_Simulator_Evaluation/README.md); saved [video](../../Task_1_Simulator_Evaluation/videos/Genesis_without_physics.mp4) if suitable |
| 4 / 1:15 | GQFT flow/CNN/Transformer pipeline; baseline and three candidate tracks | “We reproduced a numerical baseline before examining augmentation, regional attention, and yaw supervision.” | [Task 2](../../Task_2/README.md#attempts-and-outcomes) |
| 5 / 1:15 | Locked-test ADE/FDE table; separate matched validation results | “Yaw's recovered fixed-history result improves ADE 9.631→8.783 px. Attention improves validation but worsens test. History selection is a caveat.” | [Validation figure](figures/task2_validation_comparison.png); [summary JSON](evidence/task2/summary.json) |
| 6 / 1:00 | Flow/pitch bugs and ground-height oracle | “Some large errors were caused by preprocessing or conflicting labels. Exact 3-D motion can still disagree with pixel targets.” | [Geometry figure](figures/task2_geometry_failure.png); [oracle evidence](evidence/task2/geometry_oracle.json) |
| 7 / 1:15 | Task 3 control loop; targets versus measured angles; original/90500 results | “The reward candidate reduced target removal and improved early speed tracking, but jitter was mixed and the earlier stair cases all failed.” | [Task 3](../../Task_3/README.md#october-2-original-90000-versus-candidate-90500); [matched CSV](evidence/task3/matched_90500.csv) |
| 8 / 1:30 | Matched `impratio` figure and four stair pairs | “Changing only a simulated contact setting reduced vibration and changed traversal outcomes. This is simulation evidence, not a hardware fix.” | [Contact figure](figures/task3_impratio_comparison.png); [findings JSON](evidence/task3/contact_findings.json) |
| 9 / 1:15 | Task 4 photo / previous / repaired panels; split renderer diagram | “We repaired a derived kitchen and kept collision/navigation separate from Gaussian RGB-D rendering. Placement and camera/depth checks are recorded.” | [Toaster](figures/task4_toaster_comparison.jpg), [caddy](figures/task4_caddy_comparison.jpg), [latest kitchen](figures/task4_latest_kitchen.jpg) |
| 10 / 1:00 | Limitations and next three experiments | “Next: consistent trajectory supervision, validated robot/control/contact contracts, and matched held-out scene/navigation evaluation.” | [Evidence limits](EVIDENCE_INDEX.md), task next-work sections |

The allocations total 12 minutes. If time is limited, combine slides 5–6 and 7–8, preserving the result/protocol caveats.

## Numbers to put on the slides

- **GQFT fixed-history test:** baseline ADE/FDE 9.630945 / 15.847433 px; Attention 10.090982 / 16.591120; Spatial + Yaw 8.783099 / 13.322794. ADE reduction 8.80%, FDE reduction 15.93%. Label the yaw protocol caveat.
- **Earlier locomotion trial:** 0/12 distinct stair cases complete for the 90000/90500 comparison. Improvements in target removal and tracking are reported in the common 4–8 s window, not as full stair success.
- **Later contact study:** candidate forward RMS 0.284→0.120°, sideways 0.382→0.169°, with speed maintained/increased at the tested settings. Four nominal-start policy/gain pairs complete at 10 and fail at 100; these are paired cases, not independent seeds.
- **Latest kitchen:** 4,378,360 Gaussians, 23 labelled comparison groups, 32 props plus rangetop in the reviewed 33-object audit, and 99.0068% valid depth at one saved 800×640 frame.
- **Scene limitation:** dense-corner held-out PSNR 7.28/10.48 dB; these scores belong to that earlier revision. A new held-out evaluation of the final all-kitchen revision remains open. The one-frame 12.0576 ms CUDA raster timing excludes encoding/transfer and is not complete application FPS.

## Speaking notes for the difficult conclusions

**Why discuss failed attempts?** They narrowed the next experiment. Attention's test regression, mixed reward outcomes, and weak novel-view rendering prevent unsupported success claims and expose where more controlled measurements are needed.

**What changed in GQFT?** The baseline already includes image-coordinate information before mean/max pooling. Attention tests selective regional aggregation; yaw adds shared supervision and an episode heading output. Do not claim that the baseline contains no spatial information or that pixel ADE measures obstacle avoidance.

**Why did the stair conclusion change?** The October 2 tests used candidate 90500 and their stated contact/sensing conditions. The October 6–7 study used original90000/newest91000 and explicitly varied `impratio`. Earlier failures remain valid for their configurations. Later completion does not erase them or demonstrate that rewards alone solved climbing.

**Why is the geometry repair not perfect realism?** Dense surfaces improve silhouette/depth consistency, while appearance may fit the reference photograph less well. Placement audit, mesh-consistency depth, measured depth, valid-depth coverage, PSNR, and viewer appearance answer different questions.

## Likely questions and evidence-based answers

| Question | Answer |
| --- | --- |
| Is the full VLM navigation pipeline running? | The repository documents component studies. Language-conditioned end-to-end navigation success, SPL, collision rate, and robot task completion are not established here. |
| Did the improved GQFT beat baseline? | Yes in the recovered fixed-history-24 pixel test record: 8.783 vs 9.631 ADE. Its test history differed from validation selection; matched CPU validation gives mixed results. |
| Did flips help? | Historical training-time validation improved in two runs, but no final aug_v2 test improvement is established. Flips are discontinued in the current experiment setup. |
| Is the hardware jitter cause known? | The saved logs support target/response associations and expose contract issues. Controlled simulator contact sensitivity is strong, but the hardware cause and calibrated plant/contact model remain unresolved. |
| Why not just increase damping? | Gain effects differ across checkpoints/conditions; a universal gain-only fix was not established. Tracking and vibration must be assessed together. |
| Do smoothness rewards guarantee smooth walking? | No. They penalize selected action/target changes; they can also suppress needed contact corrections. Actual angles, contacts, tracking, and task success must be measured. |
| Is the kitchen physically correct? | The documented static placement checks pass after two reviewed size exceptions. NavMesh collision and camera bridge checks work; articulated robot contacts and dynamic scene synchronization are not implemented. |
| Are the visuals photorealistic? | Some objects and local surfaces are improved, with licensed PBR inspection available. Held-out Gaussian quality remains weak and the final scene needs matched evaluation. |
| Why not claim 1,000 FPS? | The fast measurement is an isolated NavMesh query workload. Render-kernel and end-to-end RGB-D throughput are separate measurements. |

## Demo preparation

1. Use the seven copied figures as the offline presentation fallback. Their sources are in the per-task manifests; these are existing outputs, not newly generated research results.
2. Check the recorded video before selecting a short segment. Do not infer its physics configuration from the filename.
3. For local Task 3 result dashboards, serve `Task_3` with the command in its README. This does not run the simulator.
4. For the ISL kitchen, use the all-kitchen launcher documented in Task 4. It needs SSH/network access and may start missing services. Test access before the evaluation; server availability was not checked in this documentation review.
5. Keep metric tables, checkpoint names/hashes, and protocol caveats visible in backup slides. Do not launch training or a locked-test rerun as a presentation demo.
