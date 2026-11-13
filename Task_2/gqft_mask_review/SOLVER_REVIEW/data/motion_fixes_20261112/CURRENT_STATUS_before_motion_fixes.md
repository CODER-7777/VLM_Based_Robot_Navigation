# GQFT current status — 11 November 2026

**Latest visual deliverable, 12 November:** Frozen trajectories for all10 recorded episodes and133 legs are generated from the three new trained checkpoints. [Open the offline gallery](trained_episode_overlays/20261111T220751Z_gpu4/all_episodes_20261111T223221Z/index.html). Includes continuous episode paths and complete-leg overlays. Models/settings were not selected using these images. The original validation/history failures remain unchanged.

**Latest result, 12 November — pilot complete:** All three GPU4 arms finished500 finite steps and fixed validation. H24 ADE:10.9558px yaw-local reference,15.6302px solver+residual,15.5904px solver+learned weights. All fail history selection. Neither hybrid improves over the matched reference. Two numerical training defects were repaired and regression-checked; invalid attempts are excluded. No additional training is queued. [Completed report](training/20261111T220751Z_gpu4/REPORT.md). Earlier updates below are historical.

**Current pilot progress:** Two GPU4 arms completed500 finite steps. Fixed-H24 ADE:10.9558px yaw-local reference versus15.6302px solver+residual; both fail history selection. Learned weights is being retried after cache/backpropagation and zero-residual gradient repairs. [Run report](training/20261111T220751Z_gpu4/REPORT.md). Older live updates below are historical.

**Newest live update:** The user reauthorized GPU4 and the remaining pilot arms have been restarted under a new detached controller. The completed reference is retained. [Current run](training/20261111T220751Z_gpu4/README.md). The preceding stop record below is historical.

**Latest live update, 12 November:** GPU4 permission was revoked after the new pilot started. Our job is now stopped; no replacement GPU is authorized. The500-step yaw-local control completed, solver-residual was interrupted, and learned weights did not start. Logs/checkpoints remain on the server. [Run and stop record](training/20261111T220751Z_gpu4/README.md). Corrected solver validation is now saved:16.2265px ADE versus11.6359 original yaw on the same float32 protocol; the solver is not a validation improvement. Earlier status below predates these runs.

**12 November documentation update:** The [consolidated approaches/research document](GQFT_APPROACHES_AND_RESEARCH.md), [Word](GQFT_APPROACHES_AND_RESEARCH.docx), [PDF](GQFT_APPROACHES_AND_RESEARCH.pdf), citations and [implementation ledger](research_20261104/REPOSITORY_IMPLEMENTATIONS.md) are now complete. This resolves the packaging gap recorded in item5 below. No experiment, deployment or training ran during this update. GPU4 is the latest user choice. The evaluation blockers and pending audits in this inspection remain unresolved.

Scope: local folder and saved evidence inspection. This review did not run inference, training, GPU jobs or a new server check. The latest server restoration receipt is from 4 November; it does not establish that the 9 November source changes have been deployed there.

## What is complete

| Area | Saved evidence | Meaning |
| --- | --- | --- |
| Four-arm masking/yaw pilot | [Pilot report](pilot_results/20261019T101035Z_431613/validation_20261019T104120Z/REPORT.md) | All four arms completed500 steps with one matched seed; fixed validation exists |
| Masking isolation | [Isolation report](ISOLATION_RESULTS.md), [soft trial](SOFT_ATTENTION_RESULTS.md) | Hard masking removes useful learned evidence; frozen soft weighting has only a tiny uncertain gain |
| Episode visualization | [Offline dashboard](dashboard.html), [image folder](trained_episode_overlays/README.md) | Five checkpoints on episode629 legs0/2/3/4, first24 pairs each;41 PNGs;29 recorded browser checks |
| Saved-array diagnosis | [Findings](diagnosis_20261104/findings.json) | Entropy, convolution support and exact gate counts computed; no validation-state rank audit yet |
| Research review | [Markdown review](research_20261104/GQFT_RESEARCH_REVIEW.md), [repository audit](research_20261104/repository_audit.json) | Ten papers discussed;9 repository links checked;8 small pinned source snapshots saved |
| Server restoration | [Destination receipt](transfers/20261104_gqft_restore/destination_verification.json) |636 original files /1.251GiB verified on4 November; source and local backup preserved |
| New geometric solver | [9 November checks](ground_geometry_20261109/verification.json) | Zero-training planar solver and optional GQFT residual hybrid exist locally;15 recorded CPU checks pass |

## What the numbers establish

The matched pilot uses104 overlapping windows from26 sequences in one validation scene, reference history30, input history24, one anchor query,810-pixel canvas and sequence-floor labels.

| Model | H24 validation ADE px | Selected history |
| --- | ---: | ---: |
| Trained reference |12.4626|16|
| Soft mask only |12.8267|20|
| Yaw-local only |11.3485|None|
| Mask + yaw-local |11.8091|None|
| Original pretrained yaw |11.6926|16|

Masking worsens the fixed-window ADE within both integration modes. Yaw-local improves path error over the matched reference, but fails the existing history rule. AtH24 its ambiguity is4/24 cosine-near retrieved queries; the combined arm is5/25. These small, dependent counts warrant pair-level inspection, but do not invalidate the operational gate or demonstrate that the models are equivalent. Representation collapse, anisotropy and last-token signature mismatch remain untested explanations.

### New direction: floor-flow geometry

The torch solver's saved episode results are:

| Episode629 window | Original Attention+Yaw mean ground error | Ground solver mean ground error |
| --- | ---: | ---: |
| Leg00 |10.248cm|1.646cm|
| Leg02 |7.077cm|1.760cm|
| Leg03 |3.021cm|3.395cm|
| Leg04 |8.466cm|1.687cm|

The solver improves3/4 windows. This is an exploratory lead: its1.5m range cutoff was chosen on those same windows. It is not a held-out validation improvement. The scipy prototype has different saved figures; use the torch verification results above when describing the implemented solver.

The optional hybrid adds solver motion, solver diagnostics and bounded learned corrections to GQFT. Synthetic recovery, gradients, checkpoint round trips and legacy-output checks are recorded. No trained hybrid checkpoint or matched ground-solver validation result was found in the inspected local folders.

## Issues discovered in this folder review

1. **Solver evaluation is not yet matched to the pilot.** `tools/evaluate_ground_solver.py` defaults to8 queries, does not pass `virtual_extension_px=270` to the dataset, and constructs `SolverOnly` without an810-pixel canvas. Merely setting `--queries 1` does not fix the anchor: without the extension the dataset samples a regular image query. Correct and record the query/canvas contract before comparing its ADE with12.46/11.35/11.69px.
2. **Locked-test episode837 is in the episode script's defaults.** `tools/episode_diagnosis.py` includes flowvo index0 (sceneTbHJrupSAjP). Exclude it from diagnosis that informs architecture, cutoff, stitching or training choices. Report locked-test results only after those choices are frozen.
3. **Some causal statements are stronger than the evidence.** The newer notes call training-motion mismatch the main cause and rule out the Transformer/flow. Four windows support a coverage-mismatch hypothesis; they do not isolate it from representation, integration, flow or optimization effects. Likewise, overlapping Wilson intervals are not proof of model equivalence and assume more independence than these windows offer.
4. **Three known label conflicts are still a validation-only finding.** All belong to one sequence. The training split's frequency, physical floor convention and gradient effects remain unaudited.
5. **Documentation packaging is unfinished.** The research Markdown and repository snapshots exist. Its listed DOCX export, exporter, citation JSON/BibTeX, standalone implementation ledger and document verification file do not exist yet. They must not be described as completed. The linked audit JSON already contains exact repository revisions and files.
6. **The dashboard predates the new solver.** It shows the October five-checkpoint comparison; it does not yet visualize solver/hybrid results. Add those only with explicit model/run provenance and comparable windows.
7. **Current source and server snapshot differ in date.** Ground-solver code is a9 November local addition; the restored server manifest reflects the earlier snapshot. Stage and hash the matching source before server evaluation. Do not assume the earlier staged source contains this solver.

## Next steps, in order

1. **Finish the research handoff.** Keep the Markdown as the canonical explanation; complete the promised citation/implementation ledger and optional Word export. Update its status to include the new geometry direction without rewriting November4 as if those results existed then.
2. **Repair and verify the evaluator protocol locally.** Match history24/reference30, stride5, seed20260820, one fixed query(480,809),960x810 canvas and the chosen label convention. Confirm query locations, task count and metric domains against the existing evaluator. Keep the released baseline and historical results untouched.
3. **Evaluate the solver before training.** Stage matching source on ISL; choose a range cutoff on a fixed training subset only, then freeze it. Run the104 validation windows on CPU with matched original checkpoints. Report direct3-D error, pixel ADE/FDE, yaw error and low-support/failure counts. Score sequence-floor and fixed-rig labels as separately declared protocols; do not pick the primary convention after seeing results.
4. **Investigate remaining failures.** Inspect per-window support and residuals, turns-in-place/variable-speed coverage and chunked-versus-sliding integration on training/validation or non-test diagnostic episodes. Complete the terminal/pooled/centered embedding audit if the history gate remains an acceptance requirement. Preserve original gate metrics and account for the6 unobserved reference pairs atH24.
5. **Only then consider hybrid training.** If the frozen solver has a defensible validation result, prepare matched yaw-local, solver+residual and solver+learned-weights arms with the same labels, initialization, budget and multiple seeds. Ask the user to select an available GPU before starting training. Do not select settings on episode837 or the locked test split.

The immediate recommendation is **protocol correction and solver validation, not another masking or hybrid training run**. Existing CNN/Transformer checkpoints remain the working references until the new method passes that comparison.

## Folder ownership

- `Task_2/gqft_algorithm_sharing_vivekananda/`: active model, dataset, solver and evaluation source.
- `Task_2/gqft_mask_review/`: canonical lab artifacts, dashboard, research and this status note.
- `research_20261104/repositories/`: static external source snapshots; inspected, not integrated dependencies.
- `transfers/20261104_gqft_restore/local_backup/`: checksum-verified historical server backup, not the active local source.
- `Task_2/APPROACHES_TRIED.md`:9 November narrative; read alongside the qualifications and protocol issues above.

Local disk usage at inspection: masking lab about1.4GiB including the backup; active GQFT directory about7.2GiB including its environments/artifacts. No cleanup, source modification, server deployment or experiment was performed by this status review.
