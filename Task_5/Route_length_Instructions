# Route lengths and instruction counts

| Distance | Definition |
| --- | --- |
| Route length | Distance along the reference path from start to endpoint |
| Geodesic distance | Shortest walkable start-to-goal distance |
| Direct / Euclidean distance | Straight-line distance between the specified start and target |

Published figures and previously audited annotation values are listed separately.
**NR** = no numeric statistic located in the inspected source. Counts retain
explicit paper/release labels. Paper averages are not exact recomputed values.

## Instructions, episodes and scenes

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
| PersONAL-PAN | 12,000 stored query variants; 11,220 distinct strings | Release: 2,000 episodes (600 easy + 700 medium + 700 hard); paper Table III: 2,020 episodes (600 + 700 + 720) | 31 | Counted; [S11](#sources) |
| OctoNav-Bench | 39,523 instruction records, all distinct in the inspected archive | 39,023 training + 500 validation episodes | 438: 397 training + 41 validation | Counted from `octonav.tar`; [S12](#sources) |
| LMEE-Bench | 166 released evaluation task-instruction records | 166 evaluation tasks; broader paper dataset: 1,816 training + 166 testing trajectories | 33 represented in released evaluation files; paper describes a source pool of 145 training + 36 testing scenes | Evaluation counted; broader dataset reported; [S13](#sources) |
| NavA3 | 50 expert-defined task descriptions | 50 task definitions; repeated rollout count described inconsistently | 5 office regions, not five independent houses | Reported; [S14](#sources) |
| LH-VLN / LHPR-VLN | Compact release: 3,342 instruction records, comprising 1,052 long-task + 2,290 step-task instructions | 1,052 long-task episodes; paper instead reports 3,260 tasks | 153 represented in compact release; paper instead reports 216 scenes | Release counted; paper totals kept separate; [S15](#sources) |
| VLN-NF | 6,628 instructions | 3,314 feasible/infeasible pairs, giving 6,628 task instances | 65: 55 training + 10 unseen; seen-validation overlaps training | Reported; [S16](#sources) |

## Annotation-derived distances

Previously audited release values; these are not paper-reported statistics.

| Dataset and inspected scope | Metric | Minimum (m) | Mean (m) | Maximum (m) | Records >40 m | Source |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| OctoNav: all 39,523 episodes | Saved reference-position trace length | 0.500001 | 11.515868 | 64.278196 | 126 | [S12](#sources) |
| OctoNav: 500 validation episodes | Same trace metric | 2.000000 | **9.620095** | 35.211116 | 0 | [S12](#sources) |
| PAN: all 2,000 episodes | Stored shortest-path/geodesic distance | 2.003442 | 5.037371 | 10.977433 | 0 | [S11](#sources) |
| LHPR-VLN: 1,052 long tasks | Saved 3D traces joined in subtask order, including positional movement between subtasks | 1.750000 | 25.750048 | 84.004609 | 140 | [S15](#sources) |
| REVERIE: 5,993 training/validation records | Stored `distance` field, already rounded to 0.01 m | 5.020000 | 9.675038 | 23.310000 | 0 in inspected records | [S03](#sources) |
| ULN: 1,622 public validation records | Stored `distance` field | 5.040000 | 10.449439 | 22.140000 | 0 in inspected records | [S06](#sources) |

## Published distances

| Benchmark | Reported route / path distance (m) | Reported direct / Euclidean distance (m) | Scope / other reported length | Source |
| --- | --- | --- | --- | --- |
| R2R | Mean approximately 10 in original paper; 9.4 in RxR comparison | NR | Reference graph paths; published averages | [S01](#sources), [S02](#sources) |
| RxR / RxR-CE | RxR mean 14.9; sampling cap 40 | NR | Original RxR graph paths; separate RxR-CE statistics not verified | [S02](#sources) |
| REVERIE | NR | NR | No verified metre-based reference mean/range in inspected paper/docs | [S03](#sources) |
| DDN | NR | NR | 100-action episode limit; not a distance | [S04](#sources) |
| IntentionNav | NR | NR | Model trajectory-length results are execution metrics, not reference-distance statistics | [S05](#sources) |
| ULN / R2R-ULN | NR | NR | Uses R2R paths; model TL results are not a reference-route distribution | [S06](#sources) |
| IVLN | NR | NR | Tour-distance distributions shown; exact mean/range not verified | [S07](#sources) |
| VCN-Bench | Geodesic sampling lower bound 3; exact mean/range NR | NR | Shortest-geodesic-distance distribution shown in Figure 10 | [S08](#sources) |
| FindingDory | NR | NR | History frames/duration are not route distance | [S09](#sources) |
| SIF | NR | NR | No verified metre-based reference mean/range in inspected source | [S10](#sources) |
| PersONAL-PAN | **Mean geodesic: 5.30** | **Mean Euclidean: 5.10** | Paper Table III, 2,020 episodes; keep separate from the 2,000-episode release | [S11](#sources) |
| OctoNav-Bench | NR | NR | Trajectory-length distribution shown in Figure 12; exact numeric mean/range not verified | [S12](#sources) |
| LMEE-Bench | NR | NR | Initial-to-target distance ranges: easy 1-5, medium 5-10, hard 10-30; distance metric not specified in that table | [S13](#sources) |
| NavA3 | NR | NR | No verified metre-based reference mean/range in inspected source | [S14](#sources) |
| LH-VLN / LHPR-VLN | NR | NR | Mean 150.95 action steps in Table 1; not metres | [S15](#sources) |
| VLN-NF | NR | NR | Reported model reach/exploration lengths are execution metrics, not dataset reference-distance statistics | [S16](#sources) |

### PAN: both distances as reported in Table III

| Difficulty | Episodes in paper | Mean geodesic distance (m) | Mean Euclidean distance (m) |
| --- | ---: | ---: | ---: |
| Easy | 600 | 3.12 | 3.40 |
| Medium | 700 | 5.23 | 4.80 |
| Hard | 720 | 7.56 | 7.09 |
| Total | 2,020 | 5.30 | 5.10 |

PAN's navigable goal viewpoint and object position can differ. Its two
reported distance fields should not be assumed to use identical endpoints.

## Sources

| ID | Primary source / inspected release |
| --- | --- |
| S01 | [Original R2R paper](https://users.cecs.anu.edu.au/~sgould/papers/cvpr18-vgn.pdf) |
| S02 | [RxR official repository](https://github.com/google-research-datasets/RxR/tree/d22df5940a0486a42b703cd445937210ce21e9f5) and [RxR paper](https://aclanthology.org/2020.emnlp-main.356/); inspected Google-hosted guide files for train, validation-seen, validation-unseen, test-standard-public and test-challenge-public |
| S03 | [REVERIE original annotation files](https://github.com/YuankaiQi/REVERIE/tree/207e90cdde48acf2f2f3fc912528966a062fc432/tasks/REVERIE/data), Git tree `207e90cdde48acf2f2f3fc912528966a062fc432`; [REVERIE paper](https://openaccess.thecvf.com/content_CVPR_2020/papers/Qi_REVERIE_Remote_Embodied_Visual_Referring_Expression_in_Real_Indoor_Environments_CVPR_2020_paper.pdf) |
| S04 | [DDN NeurIPS paper](https://papers.nips.cc/paper_files/paper/2023/file/34e278fbbd7d6d7d788c98065988e1a9-Paper-Conference.pdf) |
| S05 | [IntentionNav paper](https://arxiv.org/html/2605.23187v1) |
| S06 | [ULN validation annotations](https://github.com/weixi-feng/ULN/tree/0f251df3ffc6dd9c538d075db8674e6ad54a596b/ULN-Rec-VLN-BERT/data), Git tree `0f251df3ffc6dd9c538d075db8674e6ad54a596b`; [ULN paper](https://aclanthology.org/2022.emnlp-main.429/) |
| S07 | [IVLN CVPR paper](https://openaccess.thecvf.com/content/CVPR2023/papers/Krantz_Iterative_Vision-and-Language_Navigation_CVPR_2023_paper.pdf), Table 1 split statistics |
| S08 | [VCN-Bench paper](https://arxiv.org/html/2609.34687v1) and [author dataset](https://huggingface.co/datasets/qqqqi/VSI-NavBench) |
| S09 | [FindingDory dataset card](https://huggingface.co/datasets/yali30/findingdory/blob/016160dd7ec1d0d23aa09bba7d48470e835030a0/README.md), revision `016160dd7ec1d0d23aa09bba7d48470e835030a0`; [author paper PDF](https://arxiv.org/pdf/2506.15635) |
| S10 | [SIF ECCV paper](https://www.ecva.net/papers/eccv_2024/papers_ECCV/papers/07826.pdf), evaluation-task split table |
| S11 | [PersONAL-PAN annotation files](https://github.com/ZiliottoFilippoDev/PersONAL/tree/34be105236f0b2433d9d04f50cce3ebb72b7f001/data/split), Git tree `34be105236f0b2433d9d04f50cce3ebb72b7f001`; [PersONAL paper, Table III](https://arxiv.org/html/2509.19843v1) |
| S12 | [OctoNav public release](https://huggingface.co/datasets/Oshwiciqwq/OctoNav-Bench/tree/main), inspected `octonav.tar`; [CVPR paper](https://openaccess.thecvf.com/content/CVPR2026/papers/Gao_OctoNav_Towards_Generalist_Embodied_Navigation_CVPR_2026_paper.pdf); [arXiv paper, Figure 12](https://arxiv.org/html/2506.09839v1). Archive was read from `main` on the audit date; a revision hash was not captured |
| S13 | [LMEE-Bench evaluation files](https://huggingface.co/datasets/wangsen99/LMEE-Bench/tree/ac0d3fc102e99ed05db07b19f3e061a42b1529f1/lmee_bench), revision `ac0d3fc102e99ed05db07b19f3e061a42b1529f1`; [LMEE paper](https://arxiv.org/html/2601.10744v1) |
| S14 | [NavA3 ACL paper](https://aclanthology.org/2026.acl-long.37/) |
| S15 | [LHPR-VLN compact release](https://huggingface.co/datasets/Starry123/LHPR-VLN/tree/af66785e0b456639088d673bc100dcc63f2df997), revision `af66785e0b456639088d673bc100dcc63f2df997`; inspected `episode_task.zip`, `task.zip` and `step_task.zip`; [CVPR paper](https://openaccess.thecvf.com/content/CVPR2025/papers/Song_Towards_Long-Horizon_Vision-Language_Navigation_Platform_Benchmark_and_Method_CVPR_2025_paper.pdf) |
| S16 | [VLN-NF ACL paper](https://aclanthology.org/2026.acl-long.1152/), Table 1 |
