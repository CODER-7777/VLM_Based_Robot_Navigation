# Repository organization and artifact ownership

Use each task's README as its entry point and `docs/mid_evaluation/` as the portable presentation package. Existing experiments, checkpoint paths, and raw outputs are retained in place so scripts and historical links continue to work.

## Folder responsibilities

| Path | Keep here | Availability |
| --- | --- | --- |
| Root `README.md` | Current project/review summary | Parent Git repository |
| `docs/mid_evaluation/` | Slide guide, evidence index, selected copied metrics, source hashes, seven presentation figures, validators | Parent Git repository; offline reading |
| `Task_1_Simulator_Evaluation/` | Go2 script, task report, demo video; `notes/` holds the preserved original evaluation | Main report/code/video tracked; policy/office dependencies external |
| `Task_2/` | Current task report, roadmap, earlier codebase/deliverable/tracker reviews | Parent documents plus separate model checkout |
| `Task_2/gqft_algorithm_sharing_vivekananda/` | Model source, preserved baseline, active variants, recovered runs, archived experiments | Separate Git repository; parent stores a gitlink, not its uncommitted files |
| `Task_3/notes/` | Historical learning notes, reviews, explanations, recording instructions | Some tracked and some local working-tree documents |
| `Task_3/tools/jitter_analysis/` | Recording, plotting, comparisons, and diagnostic implementations | Parent tools; some recent additions remain local working-tree work |
| `Task_3/tools/results/<study>/` | Frozen study protocol, manifests, traces, metrics, figures, source snapshots | Mix of tracked and local files; ~2.5 GB locally |
| `Task_3/tools/results/interactive/<session>/` | Separate keyboard sessions and attempts; generated output in `plots/` | Preserve raw chunks, resets, failures, and command logs together |
| `Task_3/xterra_mjlab/` | Robot/controller/training source, checkpoints, copied evaluation runs, Python environment | Independent local Git checkout; not tracked by the parent |
| `Task_3/moe_jitter_audit_20260921/`, `Videos/` | Historical audit and screen recordings | Local evidence; copied hardware report is included in the review package |
| `Task_4/` | Named repair-stage folders with README, `evidence/`, `images/`, and where needed `source/` | Local scene snapshot/reports; large final assets remain on ISL |
| `genesis-world/` | Simulator source and local assets | Declared Genesis submodule; local extras are not guaranteed by cloning it |
| `reference_materials/` | Research papers, learning/scratch notes, retained source archives | Reference material; separate from evaluated result claims |
| `workflow.md` | Original tracker/daily workflow | Historical project guidance; use explicit staging for these documentation commits |

The existing local task sizes are approximately 23 MB for Task 1, 7.2 GB for Task 2, 11 GB for Task 3, and 845 MB for Task 4. These include Python environments and large artifacts; they are not Git commit sizes or a model-memory benchmark.

[WORKSPACE_INVENTORY.json](WORKSPACE_INVENTORY.json) records file counts, extension groups, and bytes across all six research/reference roots, excluding environments, Git metadata, and caches. It is a metadata inventory, not an assertion that every raw sample or binary was individually inspected. The archived Robofest payload contains separate drone/container tooling; it is preserved as reference material and is not used to substantiate the four task results.

## Changes made for this review

- Replaced the root and Task 1/3 overviews with current evidence-based reports; added Task 2's entry README; refreshed Task 4's overview.
- Preserved Task 1's previous evaluation in `Task_1_Simulator_Evaluation/notes/INITIAL_EVALUATION.md` and Task 4's previous overview in `Task_4/notes/PREVIOUS_OVERVIEW.md`. Their preserved relative links refer to the original task-root context.
- Added the presentation/evidence package, byte-identical selected copies, manifests, and standard-library validation/refresh utilities.
- Relocated the loose gzip archive named `gcs@192.168.31.171` to `reference_materials/archive/robofest_update_20261009.tar.gz`, preserving its payload and recording the mapping/hash in [ORGANIZATION_RECORD.json](ORGANIZATION_RECORD.json).
- Added narrowly scoped ignore rules for retained local archives and presentation-figure exceptions. Existing tracked media/evidence remain tracked.

The archive is preserved locally and excluded from these documentation commits. No checkpoint, dataset, raw experiment directory, production controller, reward, simulator parameter, or nested-repository pointer was changed for the review. Existing research edits are outside the documentation commit set.

## Git boundaries and the four commits

The requested four commits are grouped by task:

1. Task 1 report and preserved initial evaluation.
2. Task 2 report, copied benchmark/validation evidence, and two existing figures.
3. Task 3 report, copied audits/comparisons, and the contact-setting figure.
4. Task 4 report/evidence/figures plus the cross-task project README, presentation guide, validation tooling, and organization documentation.

Stage these paths explicitly. The older workflow's `git add .` would also collect unrelated research modifications and large untracked outputs. Do not stage or change nested-repository commits merely to clear parent status. These commits describe and preserve review evidence; they do not publish all current training/simulator source changes.

In particular, `.gitmodules` declares Genesis but does not register the existing Task 2 gitlink. A fresh parent clone is not guaranteed to initialize the GQFT checkout automatically. Use its independently managed repository/source provenance when restoring that research environment; do not treat the parent README as an installation lock.

## Local, portable, and server-dependent evidence

The committed review reports, copied metrics/figures, and Task 1 tracked demo can be read offline. Some links intentionally lead to extended reports and source checkouts available only in the full working workspace. The package validator reports absent extended-source links separately when validating a smaller parent clone; copied presentation evidence remains verifiable without those sources.

The local `Task_4/scenes/v15/2azQ1b91cZZ.glb` is an older scene. Final kitchen/visual assets remain under ISL's `/data/robotics/toshith/rxr_author/refined/`; current reported files include `kitchen_all_upgrade/test.glb`, `test_pbr.glb`, and `scene_refined.npz`. Source RGB/depth data and the full GQFT cache are also external dependencies. A report or launcher does not make those datasets part of this repository.

Do not rely on the server demo during the evaluation without checking it beforehand. The Task 4 all-kitchen launcher may start missing services and tunnels; this documentation review did not execute it. The seven copied images supply an offline alternative.

## Rules for future work

1. Put every new experiment in a new named results directory; never overwrite a reference run or discard failed attempts.
2. Keep raw recordings beside their manifest, status, source/configuration/checkpoint hashes, and generated plots. Archive superseded interpretations with a pointer to the new report.
3. Use task READMEs for current conclusions. Keep deeper numbered notes as history and technical explanation; avoid treating their earlier “next steps” as the current status.
4. Keep virtual environments, caches, shared datasets, large archives, and checkpoints out of broad staging. Track selected evidence and exact asset provenance intentionally.
5. Record split, query/history protocol, observation/control contract, revision, metric units/denominators, and whether evidence is simulated or physical.
6. Preserve asset credit/license files. A copied scene or downloaded model is not automatically redistributable without its original terms.
