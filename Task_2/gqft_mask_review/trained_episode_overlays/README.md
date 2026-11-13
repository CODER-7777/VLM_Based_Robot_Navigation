# Trained trajectory overlays

**Latest complete gallery:** [All10 recorded episodes and133 legs](20261111T220751Z_gpu4/all_episodes_20261111T223221Z/index.html). Three newly trained GPU4 pilot models, full-episode paths, complete-leg overlays and ground-error charts. [Visual guide](20261111T220751Z_gpu4/all_episodes_20261111T223221Z/README.md). This is separate from the October masking pilot below.

## October gallery — historical artifacts


For interactive analysis, open the newer **[comparison dashboard](../dashboard.html)**. It includes model/leg selection, synchronized overlays, a pose cursor, error charts, attention maps and validation/history results. This folder preserves the original rendered images and evidence.

Open [the visual gallery](index.html). The latest complete run is [20261019T123632Z](20261019T101035Z_431613/20261019T123632Z/gallery.html).

```text
trained_episode_overlays/
  index.html                   current visual entry point
  README.md                    this folder map
  20261019T101035Z_431613/      training pilot identifier
    20261019T123632Z.tar.gz     preserved original download
    20261019T123632Z/           completed visualization run
      gallery.html             model selector, original comparison and metrics
      index.html               original generated report
      START_HERE_overview.png  four legs by five models
      provenance.json          strict checkpoint hashes/configs, camera, source
      metrics.json             all four window metrics
      verification.json        hashes checked; old prediction reproduced
      ARTIFACT_SHA256.json     original server artifact hashes
      leg00/, leg02/, leg03/, leg04/
        *_overlay.png          five individual checkpoint overlays
        comparison.png         ground truth + five camera panels
        comparison_zoom.png    common crop of the same paths
        ground_paths.png       metric paths and per-pose errors
        attention_comparison.png
        mask_reliability.png
        predictions.json       exact arrays, input/cache identity and metrics
        attention_maps.npz     saved attention and reliability arrays
```

All 41 PNGs use the same four first-24-pair episode-629 windows as the earlier masking diagnostic. The latest trained pilot models and original pretrained checkpoint were loaded strictly on GPU 7 in float32. No training was launched. Earlier frozen-mask figures remain separately under `../ep629/`; numeric validation remains under `../pilot_results/`. No older evidence was moved or overwritten.

Magenta = ground truth; cyan = trained reference; green = trained soft mask; purple = trained yaw-local; orange = trained mask + yaw-local; steel blue = original pretrained yaw. Cyan and steel here refer to these GQFT checkpoints, not the DPVO curves in the historical final_overlays images.
