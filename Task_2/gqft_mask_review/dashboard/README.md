# GQFT offline comparison dashboard

Open **[dashboard.html](../dashboard.html)** in Chrome or Firefox. The single HTML file embeds all data, scripts, styles and twelve original camera frames. It works by double-clicking the file; no server, internet, Python environment, GPU or training is required to view it. Copy that one HTML file to share the dashboard.

## What you can inspect

- Select episode-629 legs **00, 02, 03 and 04**. Each is its first 24 recorded flow pairs, not a complete leg.
- Choose any two of the **four new trained models plus original pretrained yaw** for synchronized camera overlays. Magenta is recorded ground truth.
- Scrub poses 0–24, play the saved trajectory, hide/show ground truth and full paths, pan/zoom both camera views, fit the paths and download the displayed PNGs. The pose slider moves a cursor through the fixed 24-pair prediction; it does not rerun a model at another history.
- Inspect ground paths, per-pose ground/pixel errors and a sortable scorecard. Chart model buttons change visible curves; hovering the error chart moves the shared cursor.
- Compare learned attention at source pairs 0, 12 and 23 on the correct raw image. Inspect soft reliability, valid-flow coverage and the ground-ray prior; unmasked models explicitly show that a mask prior is absent. The heatmap scale is shared across checkpoints for each source pair, with a power transform for attention visibility.
- Open **Validation & history** for the separate matched 104-window validation, ambiguity/close-pair counts, history selection, seven input histories and four training-time validation curves.
- Save per-leg observations in this browser, export selected-leg JSON with observations, or download a CSV containing all twenty leg/model score rows. The dashboard has no server-side storage.

The lower camera band is the existing extended query canvas. Dotted paths continue after the analytic prefix gate. Ground-error means exclude the origin in the episode diagnostics; the separately displayed fixed-validation pixel means include it. No scale or rotation was fitted to a trajectory. Validation evidence and episode windows have distinct scope; neither is a new locked-test evaluation.

## Files and provenance

```text
gqft_mask_review/
  dashboard.html               self-contained dashboard — open this
  dashboard/
    README.md                  this guide
    template.html              page structure
    app.css, app.js             presentation and interactions
    build_dashboard.py         packs preserved data and images; no inference
    build_manifest.json        source/artifact hashes and output identity
    verify_dashboard.py        isolated browser interaction verification
    browser_cdp.py             standard-library Chrome test helper
    verification.json          successful desktop/mobile checks
    preview_*.png              browser previews
    assets/legNN/frame_*.png   twelve source camera frames
  trained_episode_overlays/    preserved original PNGs and prediction arrays
  pilot_results/              preserved training metrics and fixed validation
```

Rebuild from repository root:

```bash
python3 -B Task_2/gqft_mask_review/dashboard/build_dashboard.py
```

This build reads the completed pilot `20261019T101035Z_431613`, visualization `20261019T123632Z` and fixed validation `validation_20261019T104120Z`. It does not change models or original evidence. New results should be imported and explicitly selected in the builder rather than relabeling an existing run.

Browser verification is recorded in [verification.json](verification.json); screenshots cover desktop comparison, attention, validation and the mobile layout. All tests use an isolated temporary Chrome profile and the local file URL. The older image gallery remains available in the original visualization folder.
