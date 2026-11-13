# GQFT masking lab — one local working folder

**Dedicated solver review folder:** [SOLVER_REVIEW/START_HERE.html](SOLVER_REVIEW/START_HERE.html). This portable snapshot collects the11–12 November solver work, all1830 trajectory PNGs, the separate height experiment, raw analysis, training reports, research/source snapshots and the main validation plots. [Folder guide](SOLVER_REVIEW/README.md). Original run folders remain preserved.

**Latest trajectory overlays — complete:** [Open all10 episodes and133 full legs](trained_episode_overlays/20261111T220751Z_gpu4/all_episodes_20261111T223221Z/index.html). Three new trained models are compared with recorded poses. Includes10 continuous episode paths, full-leg camera overlays, ground-error charts, individual model PNGs and an interactive offline viewer. [Visual guide](trained_episode_overlays/20261111T220751Z_gpu4/all_episodes_20261111T223221Z/README.md). Earlier October figures below are preserved.

This is the canonical local folder for the current masking experiment. Keep new downloads, derived figures, tables and experiment notes here, inside `Task_2`. GQFT implementation remains in the existing sibling `gqft_algorithm_sharing_vivekananda/` codebase. Server work stays inside its authorized project directory; bring resulting artifacts into this local lab folder.

**Consolidated document, 12 November:** [All approaches, evidence, paper checks and next experiments](GQFT_APPROACHES_AND_RESEARCH.md) · [Word](GQFT_APPROACHES_AND_RESEARCH.docx) · [PDF](GQFT_APPROACHES_AND_RESEARCH.pdf). Includes14 approaches, the10 supplied papers plus4 geometry references, implementation status and corrected conclusions. [Pinned implementation ledger](research_20261104/REPOSITORY_IMPLEMENTATIONS.md) · [Citations](research_20261104/papers.bib). The research packaging is now complete. That document was prepared before the new GPU4 pilot. [The completed pilot](training/20261111T220751Z_gpu4/REPORT.md) now records500 finite steps per arm: neither hybrid beat the matched reference and all failed the history gate. The document itself launched no GPU job. [Detailed inspected status](CURRENT_STATUS.md). October records below remain historical evidence.

**October interactive comparison dashboard:** [Open dashboard.html](dashboard.html). Select a leg and any two models, play/scrub saved trajectories, pan/zoom the overlays, inspect ground/pixel errors and attention, compare the separate validation/history results, and export notes or metrics. This is one self-contained offline HTML file; no server, training or GPU is needed to view it. [Dashboard controls and source layout](dashboard/README.md). Browser checks passed at desktop and mobile widths with no JavaScript errors.

**October trained-model images:** [Open the episode-629 visual gallery](trained_episode_overlays/20261019T101035Z_431613/20261019T123632Z/gallery.html), with a model selector for each leg, original-checkpoint comparison, ground-truth overlays, ground paths, attention and reliability maps. **41 PNGs** cover legs 0, 2, 3 and 4, first 24 recorded pairs each. These are short windows, not complete-leg trajectories. [Organized folder guide](trained_episode_overlays/README.md). All five checkpoint hashes and downloaded-artifact hashes were checked; the original checkpoint reproduces the earlier four-window results. No training was launched while generating these images. Historical cyan/steel DPVO overlays remain separate; the new gallery identifies its own model colors explicitly.

**19 October completed training:** All four GPU-7 pilot arms completed 500 finite steps. [Matched validation and next-step report](pilot_results/20261019T101035Z_431613/validation_20261019T104120Z/REPORT.md): H24 ADE is 12.4626 px reference, 12.8267 masking only, 11.3485 yaw-local only and 11.8091 combined. Original pretrained yaw is 11.6926 px under this same protocol. Both yaw-local arms fail the history gate; selected histories are 16 for the reference and 20 for mask-only. Masking has not improved fixed-window accuracy. Keep the original reference and diagnose yaw-local ambiguity before a long run. Logs, configurations, checkpoint hashes and all seven evaluated histories are preserved under `pilot_results/`; no locked-test evaluation or additional training was run during review.

**16 October implementation:** [Trainable confidence/validity + ground-prior attention and yaw-local integration](implementation_20261016/README.md) are now optional modes in active local source. Fifteen new CPU checks and legacy checks pass. A staged-source bundle and four-way pilot commands are prepared; no deployment/training was executed. The old keyframe mode remains valid and default; the new local mode has matching local targets and explicit motion-head reset safeguards.

**Latest 15 October update:** [Soft-attention trial](SOFT_ATTENTION_RESULTS.md) completed on GPU 2 with original max pooling retained: validation ground mean 4.4917→4.4830 cm for the predeclared CNN-support candidate (0.19% reduction). Coarse-control reduction is 0.69%; both sequence-resampling intervals include zero. No training started. [Six-policy isolation results](ISOLATION_RESULTS.md) establish the preceding hard-mask failure mechanism. [Full repository implementation/progress/future-plan README](../REPOSITORY_PROGRESS_README.md). The sections below preserve the initial scored review.

Imported and reviewed 14 October 2026. All 16 files from `Downloads/gqft_mask_review`, the six raw leg-0 probe artifacts from `Downloads/gqft_ep629_leg00`, the available pose/raw-image copies and prior provenance records were collected here. The import manifest verifies SHA-256 for all 31 preserved files. Original downloads and earlier analysis artifacts are preserved.

## Result: current hard masking regresses overall

These are the first 24 flow pairs of episode 629 legs 0, 2, 3 and 4, evaluated against recorded poses. All comparisons use the same existing Attention + Yaw checkpoint and validity masking with minimum feature coverage 0.75. No new training occurred. The initial origin is excluded from average errors; all four pixel references have 24 valid post-origin samples. No scale or rotation was fitted to improve a prediction.

| Leg | Mean ground error: original → masked | Endpoint ground error: original → masked | Mean pixel error: original → masked | Reading |
| --- | --- | --- | --- | --- |
| 0 | 10.25 → 10.96 cm | 27.97 → 34.29 cm | 68.71 → 52.41 px | Pixel improvement hides worse ground motion; masked prefix terminates at pose 2 |
| 2 | 7.08 → 7.10 cm | 23.30 → 17.74 cm | 31.21 → 27.20 px | Endpoint improves; mean ground error is nearly unchanged/slightly worse |
| 3 | 3.02 → 18.14 cm | 4.32 → 45.55 cm | 8.43 → 44.84 px | Severe forward-motion underestimation |
| 4 | 8.47 → 14.08 cm | 19.11 → 24.75 cm | 24.38 → 49.08 px | Both metric and pixel errors worsen |

Across the four equal-length windows (96 post-origin poses):

- Mean ground error: **7.203 → 12.570 cm**, **74.50% higher**.
- Mean ground endpoint error: **18.676 → 30.584 cm**, **63.76% higher**.
- Mean pixel error: **33.182 → 43.380 px**, **30.74% higher**.
- Mean pixel endpoint error: **69.054 → 71.780 px**, **3.95% higher**.

This rejects an improvement claim for the current frozen-weight hard-mask intervention in these four windows. It does not establish that all masking designs or models trained with masking will fail. These are one episode's diagnostic windows, not full legs, independent scenes, or a validation/test benchmark.

## What the images show

Open [summary.png](summary.png) first. Blue is the original checkpoint and orange is the same checkpoint with hard masking. Lower error bars are better. The last panel compares estimated forward motion with the recorded reference in green.

Leg 3 is the clearest failure. Ground-truth forward displacement is 1.115 m; original prediction is 1.080 m; masked prediction is only 0.660 m. Its direction remains roughly aligned, but it loses motion magnitude. Read its [ground path and errors](ep629/leg03/20261013T165054_373912Z/ground_truth_comparison.png) alongside its [mask overlay](ep629/leg03/20261013T165054_373912Z/mask_explained.png).

The masks mainly reject flow-invalid borders in the inspected frames. They discard about 15–21% of feature cells on average. A few frames place almost all original learned attention on cells subsequently rejected: the maxima are 83.65%, 6.59%, 98.13% and 98.12% for legs 0, 2, 3 and 4. High attention on a rejected cell is not proof that its CNN feature contains only noise: convolution mixes neighbouring pixels, GroupNorm mixes spatial statistics, and the model was trained using the original pooling behaviour. Both attention and max pooling change in this experiment.

**Initial hypothesis, now tested:** the coarse coverage rule or masking the max branch may remove useful learned motion features. The subsequent controlled isolation demonstrates local valid-neighbour influence, a larger individual max-branch regression, and recovery when only rejected/RF-valid cells are reinstated. It does not attribute every recovered feature to neighbouring flow alone. The restored-cell policy remains slightly worse than original on aggregate validation; see [the complete controlled result](ISOLATION_RESULTS.md).

The orange path disappearing in the first diagnostic was a display issue: the model's analytic validity prefix permanently ends after the first canvas exit. The new projection plots distinguish raw dashed continuations from accepted prefixes. Pixel error scoring uses reference-valid points independently of a prediction's stopping gate, so early stopping cannot hide its errors.

## Folder guide

```text
gqft_mask_review/
  README.md, summary.png, summary.csv, summary.json
  import_manifest.json             # copied-file hashes and original locations
  summarize_reviews.py              # recreates the aggregate table/figure locally
  ep629/legNN/timestamp/             # the four downloaded review sets
    review.json
    ground_truth_comparison.png
    mask_explained.png
    projection_explained.png
    probe/                          # raw saved probe artifacts, currently leg 0
  inputs/ep629/                     # recorded pose NPZ and available raw PNG copies
  evidence/                        # earlier run/provenance notes, preserved as snapshots
```

The other three raw probes remain at the server locations recorded in `evidence/GPU7_EP629_RESULTS.json`; their complete review files and figures are local here. Large checkpoints and shared datasets stay in their existing locations. Active lab work should use this folder, rather than Downloads or temporary directories.

Recreate the summary from the repository root:

```bash
Task_2/gqft_algorithm_sharing_vivekananda/.venv/bin/python \
  Task_2/gqft_mask_review/summarize_reviews.py
```

## Next controlled work

1. Keep the current hard mask as a measured diagnostic result; do not adopt it as an improvement.
2. Completed: matched frozen validation, attention-only/max-only/joint factors, selective cell restoration and convolution-support replacement, with direct neighbour controls. Reports include motion errors/families and depth/prefix failures. Preserve the separate geometry/label diagnosis and locked test.
3. Completed: predeclared soft coverage weighting with original max on the same validation/episode windows. The primary has a tiny aggregate gain but no dependable sequence-level improvement established. No floor or episode-derived threshold sweep was used.
4. Completed 19 October: optional differentiable soft modes and a matched four-arm mask/yaw-local training pilot. See the latest report above. Next isolate the yaw-local signature ambiguity and repeat the reference/yaw comparison across seeds; keep the separate ground-label experiment independent.

Initial scoring/consolidation requires no new model inference or training. The new isolation performs frozen-weight inference without training. Its runner, CPU verification and authoritative reports are in this same lab's `isolate_masking.py`, `verify_isolation.py` and `isolations/20261015_gpu2_pooling_v2/`. The numerical reference convention was verified against `build_poses.py` and `render_frames.py`; it measures the recorded/re-rendered planar episode, not physical robot navigation success.
