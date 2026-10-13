# Task 5: navigation benchmark audit

Audit date: **14 October 2026**. This audit covers the 16 external benchmarks
and the repeated **Ours** row shown in the three uploaded WhatsApp photos.
Counts refer to the inspected release or explicitly identified paper, rather
than assuming that every paper and current release contain identical data.

## What route length means

**A route goes from its start to its endpoint along a particular path. Its
length is the distance along that path, including bends and detours.** The
endpoint alone does not determine the route length.

For saved 3D positions `p[0], ..., p[n]`, the trace length used here is:

```text
L_trace = sum(||p[i + 1] - p[i]||_2, for i = 0, ..., n - 1)
```

| Measurement | Meaning | Treatment in this audit |
| --- | --- | --- |
| Direct start-to-end distance | Euclidean distance between endpoint and start; ignores the intervening route and obstacles | Kept separate from route length |
| Reference trace length | Sum of distances between consecutive positions on the saved reference route | Computed for OctoNav, LHPR-VLN and Ours |
| Shortest-path / geodesic distance | Length of the shortest traversable path between start and the specified goal | Read from PAN's `info.geodesic_distance` field |
| Stored annotation distance | A dataset's existing `distance` value; its precision is limited by the annotation | Read for REVERIE and ULN; not presented as newly recomputed geometry |
| Executed trajectory length | Distance along the path actually taken by a human or model | Kept separate from the benchmark reference length |
| Action count | Number of actions, including turns, stops and potentially failed moves | Not converted to metres by multiplying all actions by the forward step size |

For example, walking 3 m forward and then 4 m to the side produces a **7 m
route**, while the direct start-to-end distance is **5 m**. Turning in place
adds an action but adds no positional distance. A detour can make a human's
executed trajectory longer than the reference route to the same endpoint.

The trace calculation uses all three coordinates, including elevation.
Sparse reference waypoints, dense movement traces and shortest-path distances
are different measurements and must be labelled when comparing datasets.
Floating-point results describe stored coordinates, not physical measurement
accuracy. Summary distances below are displayed to six decimal places.

## Uploaded folder inventory

Folder: `WhatsApp Unknown 2026-10-14 at 2.08.22 AM/`.

| Item | Count / size | Audit result |
| --- | --- | --- |
| `WhatsApp Image 2026-10-14 at 2.07.11 AM.jpeg` | 56,234 bytes | Benchmark-table photograph |
| `WhatsApp Image 2026-10-14 at 2.07.12 AM.jpeg` | 92,544 bytes | Benchmark-table photograph |
| `WhatsApp Image 2026-10-14 at 2.07.13 AM.jpeg` | 95,632 bytes | Benchmark-table photograph |
| Corresponding ZIP | 244,924 bytes | Contains the same three images; integrity check passes |
| External benchmarks named | 16 | Counted across all photographs |
| Ours | Appears three times | One project, not three datasets |
| Dataset annotations / route coordinates inside the upload | 0 | Exact dataset statistics require external annotations or papers |

## Benchmark counts

**Counted** means the available annotation records were inspected. **Reported**
means the count comes from a primary paper or dataset card. An instruction
record is not necessarily a distinct sentence. An episode is a task instance;
multiple instruction variants or repeated attempts can share one physical route.
A tour groups multiple episodes and must not be counted as one ordinary route.

| Benchmark | Instruction / query records | Episodes, paths or task definitions | Scene count and scope | Evidence |
| --- | --- | --- | --- | --- |
| R2R | 21,567 instructions | 7,189 sampled paths; three instructions per path give 21,567 instruction-based task instances | 90 | Reported; [S01](#sources) |
| RxR | 126,069 guide instructions | Paper reports 16,522 sampled paths | 88 represented in the inspected guide release | Instructions and scenes counted; paths reported; [S02](#sources) |
| REVERIE | 21,702 instructions | 8,297 original-release annotation records before expanding instruction lists | 86 represented in the original release | Counted; [S03](#sources) |
| DDN | Approximately 2,600 demand-to-object mappings collected; experiments use 200 training and 300 testing mappings | A fixed total of navigation episodes was not verified; mappings are not episode counts | 600 selected ProcTHOR scenes: 200 training, 200 validation, 200 testing | Reported; [S04](#sources) |
| IntentionNav | 2,000 instruction instances | 500 underlying intents, expressed in four styles | 176 reported scenes | Reported; [S05](#sources) |
| ULN / R2R-ULN | 14,044 reported underspecified instructions: 3,132 validation-seen + 6,714 validation-unseen + 4,198 test | Public validation has 1,622 source records representing 903 distinct viewpoint paths; 9,846 rewritten instructions | 66 represented in public validation; complete test-inclusive count unverified | Validation counted; test reported; [S06](#sources) |
| IVLN | Discrete: 17,385 episode/instruction instances; continuous: 13,239 | 375 discrete tours or 414 continuous tours; these are alternative representations | 72 discrete / 71 continuous, from split unions | Reported split counts; [S07](#sources) |
| VCN-Bench | 104,305 episode-associated instruction instances | 103,055 training + 1,250 test; 309 training and 21 test tour videos | 72: 61 training + 11 test | Reported; annotation download returned authentication required; [S08](#sources) |
| FindingDory | Public dataset card: 85,083 queries, comprising 79,213 training + 5,870 validation | Paper: 1,578 history episodes, comprising 1,478 training + 100 validation; 60 task templates | Paper: 137, comprising 107 training + 30 validation | Query counts from release card; history counts reported; [S09](#sources) |
| SIF | 480 evaluation task instances; unique instruction wording count unverified | 240 validation + 240 test tasks; generated training tasks counted separately | 10 houses: 6 seen + 4 unseen | Reported; [S10](#sources) |
| PersONAL-PAN | 12,000 stored query variants; 11,220 distinct strings | 2,000 episodes: 600 easy + 700 medium + 700 hard | 31 | Counted; [S11](#sources) |
| OctoNav-Bench | 39,523 instruction records, all distinct in the inspected archive | 39,023 training + 500 validation episodes | 438: 397 training + 41 validation | Counted from `octonav.tar`; [S12](#sources) |
| LMEE-Bench | 166 released evaluation task-instruction records | 166 evaluation tasks; broader paper dataset: 1,816 training + 166 testing trajectories | 33 represented in released evaluation files; paper describes a source pool of 145 training + 36 testing scenes | Evaluation counted; broader dataset reported; [S13](#sources) |
| NavA3 | 50 expert-defined task descriptions | 50 task definitions; repeated rollout count described inconsistently | 5 office regions, not five independent houses | Reported; [S14](#sources) |
| LH-VLN / LHPR-VLN | Compact release: 3,342 instruction records, comprising 1,052 long-task + 2,290 step-task instructions | 1,052 long-task episodes; paper instead reports 3,260 tasks | 153 represented in compact release; paper instead reports 216 scenes | Release counted; paper totals kept separate; [S15](#sources) |
| VLN-NF | 6,628 instructions | 3,314 feasible/infeasible pairs, giving 6,628 task instances | 65: 55 training + 10 unseen; seen-validation overlaps training | Reported; [S16](#sources) |
| Ours: presentation | 30 Level 1-3 instruction records; 10 primary Level-3 requests; 22 Level-3 condition/variant records | 10 unique reference routes | 4 MP3D scenes | Counted from the server presentation and reference traces; [S17](#sources) |

## Calculated and stored distance statistics

`>40 m` is evaluated using the particular metric and scope in each row. A
dataset's training routes and evaluation routes can produce different answers.
Means for annotation rows are weighted by records, not deduplicated paths.

| Dataset and inspected scope | Metric | Minimum (m) | Mean (m) | Maximum (m) | Records >40 m | Source |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| OctoNav: all 39,523 episodes | Saved reference-position trace length | 0.500001 | 11.515868 | 64.278196 | 126 | [S12](#sources) |
| OctoNav: 500 validation episodes | Same trace metric | 2.000000 | **9.620095** | 35.211116 | 0 | [S12](#sources) |
| PAN: all 2,000 episodes | Stored shortest-path/geodesic distance | 2.003442 | 5.037371 | 10.977433 | 0 | [S11](#sources) |
| LHPR-VLN: 1,052 long tasks | Saved 3D traces joined in subtask order, including positional movement between subtasks | 1.750000 | 25.750048 | 84.004609 | 140 | [S15](#sources) |
| REVERIE: 5,993 training/validation records | Stored `distance` field, already rounded to 0.01 m | 5.020000 | 9.675038 | 23.310000 | 0 in inspected records | [S03](#sources) |
| ULN: 1,622 public validation records | Stored `distance` field | 5.040000 | 10.449439 | 22.140000 | 0 in inspected records | [S06](#sources) |
| Ours: 10 presentation routes | Dense saved ground-truth movement trace | 9.504373 | 30.995304 | 55.172735 | 4 | [S17](#sources) |

REVERIE's 2,304 public test records expose only the starting viewpoint, so the
complete test-inclusive route-distance distribution was not calculated.
OctoNav's validation mean above corrects the earlier conversational arithmetic
value; the weighted calculation from all four validation subsets is
`9.62009546135879 m`.

### OctoNav split audit

| Scene source | Split | Episodes / instructions | Scenes | Minimum (m) | Mean (m) | Maximum (m) | >40 m |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Gibson | Training | 10,886 | 110 | 1.999271 | 9.812493 | 36.965049 | 0 |
| Gibson | Validation | 128 | 10 | 2.000000 | 8.813593 | 17.250436 | 0 |
| HM3D | Training | 16,077 | 161 | 0.500001 | 10.983834 | 39.356047 | 0 |
| HM3D | Validation | 250 | 20 | 2.518067 | 9.559946 | 27.321663 | 0 |
| MP3D | Training | 6,053 | 61 | 2.160323 | 17.501688 | 64.278196 | 125 |
| MP3D | Validation | 59 | 6 | 2.000000 | 13.350071 | 35.211116 | 0 |
| ProcTHOR | Training | 6,007 | 65 | 1.999999 | 10.152818 | 40.049908 | 1 |
| ProcTHOR | Validation | 63 | 5 | 2.013986 | 8.004241 | 25.548628 | 0 |

All 39,523 inspected OctoNav episodes have nonempty instructions and reference
position traces. Their first reference positions match their stored starts.

### PersONAL-PAN difficulty audit

| Difficulty | Episodes | Scenes | Query variants | Distinct query strings | Minimum (m) | Mean (m) | Maximum (m) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Easy | 600 | 31 | 3,600 | 3,486 | 2.003442 | 3.052601 | 3.997257 |
| Medium | 700 | 31 | 4,200 | 4,062 | 3.015968 | 5.055030 | 6.977834 |
| Hard | 700 | 31 | 4,200 | 4,146 | 3.042278 | 6.720943 | 10.977433 |
| Combined | 2,000 | 31 unique | 12,000 | 11,220 across all difficulties | 2.003442 | 5.037371 | 10.977433 |

The difficulties share scenes. Plain and gzipped copies of the same scene
annotations were not counted twice.

### Other route-length evidence and limits

| Benchmark | Verified statement | Remaining limitation |
| --- | --- | --- |
| R2R | Original paper reports about 10 m mean; RxR's comparison reports 9.4 m | Rounded published values, not an exact annotation recomputation in this audit |
| RxR | Paper reports 14.9 m mean and a 40 m sampling cap for original graph paths | Exact released min/max and RxR-CE conversion-specific statistics were not calculated |
| IVLN | A tour contains multiple episodes and inter-episode transfers | Exact tour-distance statistics were not verified; tours are not comparable to one ordinary route |
| VCN-Bench | Episode counts were verified against the paper | Exact reference distances unavailable in this audit because annotation download required authentication |
| DDN | 100-action episode limit | This is not a 100 m route length; complete reference-distance distribution unverified |
| SIF | Evaluation includes navigation and interaction tasks | Complete reference-distance distribution unverified |
| FindingDory | History duration and frame counts describe experience collection | History length is not the navigation distance for an individual query; exact route distribution unverified |
| IntentionNav | Reported model trajectory length measures predicted/executed navigation | It is not a ground-truth dataset route-length distribution |
| LMEE-Bench | Released task definitions include starts and target lists | Full reference trace-distance distribution was not calculated from the trajectory release |
| NavA3 | Five office regions and 50 task definitions | Exact reference route-distance distribution unverified |
| VLN-NF | Separates reaching a room from exploration and the final FOUND/NOT-FOUND decision | A complete reference-distance distribution was not verified |

**Unverified does not mean zero or prove that routes longer than 40 m are absent.**
The original RxR and continuous RxR-CE releases must not be assigned identical
counts or distances without checking conversion and filtering.

## Ours: exact presentation route audit

These are the full floating-point 3D trace sums, independently recomputed from
the saved ground-truth `locations`. They match the presentation's
`gt_walk_trace_length_m` field. Sparse waypoint polylines are shown separately
to make the metric difference explicit.

| Episode | Collector task label | Episode key | Dense reference trace (m) | Sparse waypoint polyline (m) | Dense trace >40 m |
| --- | --- | --- | ---: | ---: | --- |
| 1 | Help Mary after exercise | `QUCTc6BB5sX_6120` | 9.562629003681936 | 10.047877816265729 | No |
| 2 | Prepare kids' school clothes | `QUCTc6BB5sX_8247` | 9.504372764029327 | 10.727247506956976 | No |
| 3 | Asha's morning tea | `2azQ1b91cZZ_3919` | 12.500062118524752 | 11.996581437874930 | No |
| 4 | Help Nora with phone | `TbHJrupSAjP_7120` | 25.799466906900552 | 26.373618814658524 | No |
| 5 | Another round of board games | `TbHJrupSAjP_10286` | 31.389256912405806 | 31.854176351432756 | No |
| 6 | Food for today's outing | `QUCTc6BB5sX_3568` | 20.538413436748524 | 19.177520857211240 | No |
| 7 | Return parcel for courier | `2azQ1b91cZZ_4240` | 45.156377567604444 | 41.491573329747060 | Yes |
| 8 | Riya's school things | `EU6Fwq7SyZv_10664` | 49.969474066647580 | 39.206777348347934 | Yes |
| 9 | Help Asha read after dinner | `2azQ1b91cZZ_7372` | 50.360248922778084 | 45.543804151069025 | Yes |
| 10 | Pack Riya's toiletries | `EU6Fwq7SyZv_5784` | 55.172735240792970 | 39.066642041301920 | Yes |

| Dense-trace statistic | Value |
| --- | ---: |
| Routes | 10 |
| Minimum | 9.504372764029327 m |
| Mean | 30.995303694011398 m |
| Median | 28.594361909653180 m |
| Maximum | 55.172735240792970 m |
| Total | 309.953036940113900 m |
| Routes >40 m | 4 of 10 |

The sparse waypoint metric gives **2 of 10** routes over 40 m. These traces and
waypoints come from different saved reference representations; neither should
be silently substituted for the other or called the shortest geodesic route.

### Scenes, instructions and memories

| Collector environment label | MP3D scene ID | Presentation episodes |
| --- | --- | --- |
| Mary & Riya | `QUCTc6BB5sX` | 1, 2, 6 |
| Asha & Maya | `2azQ1b91cZZ` | 3, 7, 9 |
| Nora & Leo | `TbHJrupSAjP` | 4, 5 |
| Riya, Oliver & Sam | `EU6Fwq7SyZv` | 8, 10 |

| Presentation quantity | Count |
| --- | ---: |
| Unique routes | 10 |
| Unique scenes | 4 |
| Instruction levels | 3 |
| Level 1-3 instruction records | 30 |
| Primary Level-3 task requests | 10 |
| Primary Level-3 condition records | 20 |
| Additional alternate-condition records | 2 |
| Total Level-3 condition/variant records | 22 |
| Distinct authored memories | 16 |
| Memory images | 50 |

The 22 Level-3 condition/variant records reuse the ten reference routes. The
environment names are authored character labels, not official house names.

### Saved human collection snapshot

Location on the server:
`bench/experiments/level3_manual_collector_v2/sessions/`.

| Quantity | Count |
| --- | ---: |
| Saved sample attempts | 9 |
| Contributors | 3 |
| Distinct episode keys attempted | 3 |
| Scenes represented | 2 |
| Navigation MP4 files | 9 |
| Screen MP4 clips | 8 |
| Separate voice MP4 clips | 2 |
| Saved reasoning-text annotation events | 1 |
| Samples with zero movement actions | 1 |
| Optional route-guidance-viewed events | 3 |

Nine saved attempts are not nine fully annotated, independent reasoning
episodes. Screen clips can contain microphone narration without a separate
voice clip or saved transcript. Attempts using route guidance need an explicit
label when evaluating unaided reasoning. This snapshot counts saved records;
it does not certify audio quality or annotation correctness.

## Corrections and interpretation for the comparison slides

| Issue | Correct interpretation |
| --- | --- |
| IVLN value 789 | 375 discrete tours + 414 continuous tours; not 789 independent navigation episodes |
| Reusing MP3D's 90 scenes for every derived benchmark | Original REVERIE annotations represent 86; inspected RxR guide annotations represent 88 |
| OctoNav 45k+ | Paper description; inspected public archive contains 39,523 records, including 500 validation episodes |
| OctoNav routes >40 m | 126 in the complete inspected archive, all in training; zero in the 500 validation episodes |
| LHPR-VLN 3,260 tasks / 216 scenes | Paper totals; inspected compact release has 1,052 long-task episodes, 2,290 step-task instructions and 153 scenes |
| FindingDory total | Paper: 85,089 queries; release card: 85,083, a difference of six validation queries |
| FindingDory venue | Current author PDF labels it ICLR 2026; the slide's ECCV 2026 label is unsupported by that source |
| PersONAL ICRA 2026 label | Not verified from the inspected primary sources; cite the paper/release without asserting this venue |
| LMEE scenes | 33 represented in released evaluation definitions; distinguish this from the paper's source-scene pool |
| NavA3 scenes | Five office regions should not be described as five independently scanned homes |
| Action count presented as route length | Turns, stops and failed forward moves invalidate this conversion |
| Model trajectory length presented as reference length | These measure different paths and must remain separate |
| Ours >40 m flag | Four dense reference traces exceed 40 m; only two sparse waypoint polylines exceed 40 m |
| Missing distance statistics | Mark unverified; do not replace with zero or a No flag |

Recommended comparison-table columns: **instruction records**, **unique
routes/task definitions**, **episode instances**, **scene count and scope**,
**reference-distance metric**, **distance mean/range**, **number over 40 m**,
and **source/release**.

## Sources

| ID | Primary source / inspected release |
| --- | --- |
| S01 | [Original R2R paper](https://users.cecs.anu.edu.au/~sgould/papers/cvpr18-vgn.pdf) |
| S02 | [RxR official repository](https://github.com/google-research-datasets/RxR/tree/d22df5940a0486a42b703cd445937210ce21e9f5) and [RxR paper](https://aclanthology.org/2020.emnlp-main.356/); inspected Google-hosted guide files for train, validation-seen, validation-unseen, test-standard-public and test-challenge-public |
| S03 | [REVERIE original annotation files](https://github.com/YuankaiQi/REVERIE/tree/207e90cdde48acf2f2f3fc912528966a062fc432/tasks/REVERIE/data), Git tree `207e90cdde48acf2f2f3fc912528966a062fc432` |
| S04 | [DDN NeurIPS paper](https://papers.nips.cc/paper_files/paper/2023/file/34e278fbbd7d6d7d788c98065988e1a9-Paper-Conference.pdf) |
| S05 | [IntentionNav paper](https://arxiv.org/html/2605.23187v1) |
| S06 | [ULN validation annotations](https://github.com/weixi-feng/ULN/tree/0f251df3ffc6dd9c538d075db8674e6ad54a596b/ULN-Rec-VLN-BERT/data), Git tree `0f251df3ffc6dd9c538d075db8674e6ad54a596b`; [ULN paper](https://aclanthology.org/2022.emnlp-main.429/) |
| S07 | [IVLN CVPR paper](https://openaccess.thecvf.com/content/CVPR2023/papers/Krantz_Iterative_Vision-and-Language_Navigation_CVPR_2023_paper.pdf), Table 1 split statistics |
| S08 | [VCN-Bench paper](https://arxiv.org/html/2609.34687v1) and [author dataset](https://huggingface.co/datasets/qqqqi/VSI-NavBench) |
| S09 | [FindingDory dataset card](https://huggingface.co/datasets/yali30/findingdory/blob/016160dd7ec1d0d23aa09bba7d48470e835030a0/README.md), revision `016160dd7ec1d0d23aa09bba7d48470e835030a0`; [author paper PDF](https://arxiv.org/pdf/2506.15635) |
| S10 | [SIF ECCV paper](https://www.ecva.net/papers/eccv_2024/papers_ECCV/papers/07826.pdf), evaluation-task split table |
| S11 | [PersONAL-PAN annotation files](https://github.com/ZiliottoFilippoDev/PersONAL/tree/34be105236f0b2433d9d04f50cce3ebb72b7f001/data/split), Git tree `34be105236f0b2433d9d04f50cce3ebb72b7f001` |
| S12 | [OctoNav public release](https://huggingface.co/datasets/Oshwiciqwq/OctoNav-Bench/tree/main), inspected `octonav.tar`; [CVPR paper](https://openaccess.thecvf.com/content/CVPR2026/papers/Gao_OctoNav_Towards_Generalist_Embodied_Navigation_CVPR_2026_paper.pdf). Archive was read from `main` on the audit date; a revision hash was not captured |
| S13 | [LMEE-Bench evaluation files](https://huggingface.co/datasets/wangsen99/LMEE-Bench/tree/ac0d3fc102e99ed05db07b19f3e061a42b1529f1/lmee_bench), revision `ac0d3fc102e99ed05db07b19f3e061a42b1529f1`; [LMEE paper](https://arxiv.org/html/2601.10744v1) |
| S14 | [NavA3 ACL paper](https://aclanthology.org/2026.acl-long.37/) |
| S15 | [LHPR-VLN compact release](https://huggingface.co/datasets/Starry123/LHPR-VLN/tree/af66785e0b456639088d673bc100dcc63f2df997), revision `af66785e0b456639088d673bc100dcc63f2df997`; inspected `episode_task.zip`, `task.zip` and `step_task.zip`; [CVPR paper](https://openaccess.thecvf.com/content/CVPR2025/papers/Song_Towards_Long-Horizon_Vision-Language_Navigation_Platform_Benchmark_and_Method_CVPR_2025_paper.pdf) |
| S16 | [VLN-NF ACL paper](https://aclanthology.org/2026.acl-long.1152/), Table 1 |
| S17 | Server `172.26.186.222`: `/home/guest-isl/rishabh/bench/experiments/awarevln_levels_1_2_3_presentation/presentation.html`; dense traces in `awarevln_level2_10/datasets/val_unseen/val_unseen_guide_gt.json.gz`; sparse metadata in `bench/trajectory_catalog/episodes/`; saved samples in `bench/experiments/level3_manual_collector_v2/sessions/` |

The audit did not run navigation inference or use a GPU. Dataset inspections
were read-only; the documentation does not contain copied scene assets, videos
or contributor credentials.
