# Repository layout and source boundaries

| Path | Responsibility |
| --- | --- |
| `README.md`, task-root READMEs | Technical attempts/results, current hypotheses, unresolved work |
| `docs/mid_evaluation/` | Evidence copies, figures, source index/manifests, current checks; presentation guidelines separate |
| `Task_1_Simulator_Evaluation/` | Go2/Genesis control script, demo, preserved initial evaluation |
| `Task_2/gqft_algorithm_sharing_vivekananda/` | Independent GQFT source Git repository; parent records its revision |
| `Task_3/xterra_mjlab/` | Independent SvanM2 source Git repository; parent records its revision |
| `Task_3/tools/jitter_analysis/` | Recording, replay, rewards/target diagnostics, contact/solver interventions |
| `Task_3/tools/results/` | Frozen raw sessions/studies; source/config/checkpoint provenance; large outputs remain local |
| `Task_3/notes/`, `tools/archive/` | Detailed historical analyses and preserved earlier guides |
| `Task_4/*/evidence/`, runtime/web folders | Repair, fitting, assembly, reconstruction, services, validation, preview source |
| `Task_4/*/source/`, `scenes/v15/`, images | Original model assets and local snapshots; selective metadata tracked |
| `genesis-world/` | Genesis submodule and local asset dependencies |
| `reference_materials/` | Papers, learning notes, retained Robofest source archive |

`.gitmodules` registers Genesis, GQFT, and SvanM2 repositories. Nested source commits are independent of parent documentation/tool commits. Local commits are not remote publication; a parent gitlink identifies a source revision whose remote availability depends on the nested repository being pushed.

## Commit partition for this revision

Seven commits across three repositories: (1) GQFT variants/adapters/analysis source; (2) SvanM2 reward/controller source; (3) concise project/Task 1 technical reports; (4) Task 2 reports/trackers and source registration; (5) Task 3 analysis tools/report and source registration; (6) Task 4 fitting/assembly/dashboard source and report; (7) Gaussian physics/rendering source, launchers, source/validation indexes, and separate presentation documentation.

Only explicit source/documentation/metadata paths are staged. Environments, raw traces, videos, model/checkpoint binaries, scenes, and broad candidate-search payloads are outside this revision's commit set. Older tracked evidence remains tracked.

## Preservation and availability

The Robofest gzip payload was relocated without extraction/modification; mapping/hash: [ORGANIZATION_RECORD.json](ORGANIZATION_RECORD.json). It is separate drone/container reference material, not evidence for these four tasks. [WORKSPACE_INVENTORY.json](WORKSPACE_INVENTORY.json) records the earlier six-root metadata inventory, excluding environments/Git/caches.

Original Task 1 notes and earlier Task 4 overview remain archived. The prior Task 3 tool guide is preserved at `tools/archive/TOOL_GUIDE_20261010.md`; its relative links retain their original tool-root context. GQFT's historical visualization script is archived rather than discarded; released baseline files remain unchanged.

Large GQFT caches and weights, newer SvanM2 candidates/recordings, and final all-kitchen GLB/Gaussian checkpoints remain local/ISL runtime inputs. Task 4 `scenes/v15/` is an older snapshot. Server code retains its data/build paths and environment dependencies; syntax checks do not establish live service availability. Portable metrics/figures do not require SSH.
