# GQFT current status — 12 November 2026

The frozen **central-floor solver control** improves validation trajectory error. It remains an experimental runtime intervention because the history acceptance gate still fails and cross-scene generalization is untested. No new training is running.

| Latest check | Result |
| --- | --- |
| Learned-weight hybrid, same104 H24 validation windows, float32 | ADE15.4479 → 4.6543px; ground error6.321 → 1.713cm |
| Solver-only,26 full validation sequences, float32 | Ground error13.547 → 6.407cm;20/26 sequences improve |
| Original seven-history gate, central learned weights | No sufficient history; H24 ambiguity0.71579 |
| Far-ray yaw / near-floor translation | Worse than central joint solver; not promoted |
| Rolling24-pair context | Implemented; no clear validation gain |
| Residual/support-based neural fallback | Implemented; no overall validation gain |
| Height reconstruction | Separate1.2m counterfactual RGB rendered for629,753,1285,1395,1481; uncertain episodes deferred |
| CPU contracts |18/18 pass |

The dashboard now separates **Experiment A: original RGB** (default) and **Experiment B: camera-height reconstruction**, with separate cohort tables and explicit physical-calibration notes. [Open the separate height experiment](motion_fixes_20261112/comparison.html#height).

**[Open the paired intervention comparison](motion_fixes_20261112/comparison.html).** New overlays are complete:10 original episodes with central-floor control (725PNG), plus5 separately rendered height-corrected episodes (380PNG). Both galleries pass desktop/mobile checks. Results are mixed on long recorded paths; height correction does not universally improve frozen models.

Read the [motion-fix implementation and results](motion_fixes_20261112/README.md) for exact protocols, provenance, height caveats and reproduction commands. Parameter selection uses validation/train evidence, not episode629 alone or locked-test837.

The original renderer loses per-frame world-Y and uses a constant first-leg agent height. That is a confirmed reconstruction limitation. Actual mesh clearance must still be checked: absolute floor elevation does not equal camera clearance. A blanket correction for837/1031/1781 is not justified. Their uncertain support remains explicitly unresolved.

The completed500-step GPU4 pilot and its original failed validation/history results are preserved in [the training report](training/20261111T220751Z_gpu4/REPORT.md). Central floor changes the inference weight rule after strict checkpoint loading; the existing checkpoint parameters are unchanged. There was no new optimization step.

The original verified all-episode gallery is [here](trained_episode_overlays/20261111T220751Z_gpu4/all_episodes_20261111T223221Z/index.html). It contains10 recordings,133 legs,143 trajectory views and725 PNGs. New central-floor and corrected-height views are separate experiments linked from the motion-fix report; the original gallery pointer remains unchanged.

Research and earlier approaches are in [the consolidated document](GQFT_APPROACHES_AND_RESEARCH.md), with [Word](GQFT_APPROACHES_AND_RESEARCH.docx) and [PDF](GQFT_APPROACHES_AND_RESEARCH.pdf) exports from the prior research handoff. New motion-fix results currently live in Markdown and raw JSON; the older binary exports have not been regenerated for them.

Next: inspect paired visuals across the cohort, resolve uncertain height support using original3-D logs or verified geometry, and diagnose the terminal-state history signature. Consider matched multi-seed training only after these checks. No further split/fallback/history setting is promoted on the present evidence.

The preceding status page is preserved as [historical status](motion_fixes_20261112/CURRENT_STATUS_before_motion_fixes.md); its live progress paragraphs are superseded.
