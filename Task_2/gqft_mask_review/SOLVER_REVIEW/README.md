# Solver review — start here

This is the dedicated review snapshot for the11–12 November solver work, with the9 November solver prototype retained for context. Open **START_HERE.html** or **index.html**. All copied files have independent contents and verified source hashes; original run folders remain preserved.

## Look at these first

1. `START_HERE.html`: strongest validation result, key PNGs, regressions and unresolved history gate.
2. `data/motion_fixes_20261112/comparison.html`: interactive comparison. Experiment A uses original RGB; Experiment B (`#height`) is the separately reconstructed camera-height experiment, with its own cohort and results.
3. `highlights/01_validation_ade.png`: central learned weights15.45→4.65px on104 same-house validation windows, float32. This is an intervention result, not a new checkpoint or established cross-scene improvement.
4. `highlights/02_full_sequence_controls.png`: solver ground error13.55→6.41cm over26 full validation sequences; a separate48-pair protocol.
5. `highlights/03_history_gate.png`: original history selection still fails. Read this alongside every positive result.
6. `data/training/20261111T220751Z_gpu4/REPORT.md`: completed500-step training pilot. The original matched training winner was yaw-local reference10.9558px (CUDA bfloat16); both hybrids were worse before inference controls.

## Everything included

- All1830 trajectory PNGs from the original solver gallery(725), central-floor gallery(725), and separate height gallery(380), plus gallery previews, six featured PNG copies, three new summary figures in PNG/PDF, and the19 images supplied for review.
- Full recorded predictions, metrics, keyframe images, saved original/counterfactual pose inputs, per-window validation results, gate results, height audits, verification receipts and source snapshots.
- Training reports, configs, launch/progress/evaluation logs and exact checkpoint hashes/server locations.
- Early geometric solver experiments, the earlier root-cause analysis, and the papers/implementation review.
- `analysis/all_recorded_trajectory_metrics.csv` for every model/view/condition; validation and history CSVs are separate.
- `SOURCE_COPY_MANIFEST.json`: source→copy hashes. `ALL_FILES.csv`, `PNGS.csv` and `PACKAGE_SHA256.json`: complete local inventory.

## Interpretation rules

The central-floor runtime control changes solver pixel selection; existing checkpoint weights remain frozen. Original-data and reconstructed-height scores stay separate. The height reconstructions preserve the1.2m model/sensor mount but change estimated agent elevation; they are not recovery of the original3-D logs. Only629,753,1285,1395,1481 have complete reconstructed recordings. The three named upstairs episodes remain unresolved.

All10 recorded episodes are retained for visual diagnosis, including locked-test837; none is a parameter-selection set. Featured examples include both gains and regressions, and are not an unbiased benchmark sample. Do not average different protocols or claim the history gate passed.

`data/root_cause_20261112/ROOT_CAUSE.md` is historical: its blanket upstairs grouping, inferred heights and “two thirds removed” causal claim are superseded by the qualified mesh/replay audit in `data/motion_fixes_20261112/README.md`. Absolute floor elevation alone is not clearance. Research DOCX/PDF are older exports; the Markdown has the later solver update.

Large model weight files, the complete raw RGB recordings and optical-flow caches remain at their original server locations. Exact checkpoint paths/hashes are in `analysis/CHECKPOINT_REFERENCES.json`; corrected RGB and cache locations are in the motion-fix report. They were not needed to open the plots, data or dashboards and were not redownloaded. Source run paths embedded in JSON remain provenance, not portable executable paths.


## Requested original-solver drawing GIFs

Open `gifs_original_solver/index.html` for478/leg03,753/leg11,837/leg00 and837/leg08. Only solver+correction and solver+learned-weights predictions are shown, with the pink reference. Paths draw progressively over the fixed original keyframe; no new inference or height correction is used. GIF frame decoding, timing and exact first/final render matches are recorded in `gifs_original_solver/manifest.json`. The renderer snapshot records the script originally run from the lab root.


## Paper review, next attempts and masked-attention images —13 November

- `research_next_attempts_20261113/index.html`: ordered next-attempt plan and method-focused review of all14 papers; Markdown,Word and PDF exports are alongside it. Access/reading-coverage receipts distinguish retrieved papers from the method sections inspected. These are recommendations, not newly executed experiments.
- `masked_attention/index.html`: all62 existing neural-mask PNGs, with historical hard masking,frozen soft weighting and trained soft-mask runs kept distinct from the November solver and height studies. Source images are unchanged and copied with hashes.


## Git checkout restoration

Full solver PNG sets and their large embedded gallery HTML are kept local and can be regenerated from versioned prediction JSON and keyframes with `python -B Task_2/gqft_mask_review/restore_solver_review.py`. Curated figures, masked-attention images and requested GIFs are committed. See `../VERSION_CONTROL.md` for the exact source/artifact policy.
