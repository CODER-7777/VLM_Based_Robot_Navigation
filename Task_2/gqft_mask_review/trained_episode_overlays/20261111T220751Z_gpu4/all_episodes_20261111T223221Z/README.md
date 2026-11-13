# All recorded episode trajectory overlays

Open [index.html](index.html) to compare the three new pilot checkpoints. The interactive camera/ground viewer is offline; the PNG links open the saved figures.

Pink: recorded ground truth. Cyan: yaw-local reference. Orange: solver + correction. Violet: solver + learned weights.

Each episode has a continuous full-episode view and independent full-leg views. Every frame is included. The background is the first frame of the selected view; playback reveals path points. The region below the RGB image is the original virtual query canvas.

## Coverage

| Episode | Frames | Legs |
| --- | ---: | ---: |
| 629 | 418 | 7 |
| 478 | 445 | 9 |
| 753 | 521 | 16 |
| 837 | 1170 | 21 |
| 1031 | 314 | 7 |
| 1285 | 1431 | 30 |
| 1395 | 128 | 5 |
| 1481 | 382 | 12 |
| 1689 | 636 | 17 |
| 1781 | 346 | 9 |

Coverage complete:10/10 episodes,133/133 legs and5791 recorded frames. There are725 trajectory PNGs, plus browser preview screenshots.

## What each view contains

- `comparison.png`: ground truth and one panel per model.
- `*_overlay.png`: individual model overlay.
- `ground_paths.png`: paths in metres and errors over time.
- `keyframe.jpg`: displayed source image.
- `START_HERE_overview.png`: every leg of the episode in one contact sheet.
- `predictions.json`: exact arrays and per-view metrics for the episode.

## Protocol and provenance

Each run trained for500 steps; these images use its best saved validation checkpoint, not necessarily step500:
- Yaw-local reference: selected step400; SHA-256 `c3a596f9dea53863f1d9e354819c0d8dccfc0efecfd03ad3ecc1d464e5557652`.
- Solver + correction: selected step100; SHA-256 `925b5d525f0aa1786316359a1e7d7a9f047677515dbccef313b437c9ba2837ab`.
- Solver + learned weights: selected step500; SHA-256 `e8c1e290755a81ce9c73b5b598fdae64dd03d6c00bcdc20cdbc28edfcfd8cbbb`.

Flow is recomputed once with the original frozen SEA-RAFT forward/backward recipe and saved in normalized units; all three models share identical cached inputs. Predictions use float32,24-pair causal chunks, and predicted yaw to stitch full3-D displacements. No scale or rotation is fitted. No settings are chosen from these images. All recordings, including existing test-scene episodes, are reported as frozen diagnostics rather than architecture-selection data.

Ground/3-D errors exclude the initial origin. Pixel errors score reference-valid canvas points independently of predicted stopping. Short stop/turn legs remain included; the first step has one pair of context. Full-episode and per-leg predictions differ because they reset context at different boundaries.

See `manifest.json`, `render_verification.json`, `stitch_verification.json` and browser `verification.json`. `inputs/poses/` contains byte-verified recorded-pose copies. `input_provenance.json` records original PNG identities and hashes of downloaded keyframes, predictions and poses.

Earlier October images remain in their original folders.
