# Critical episode review — 12 October 2026

These observations come from saved, historical `visualizations/final_overlays/` images, not a new prediction run. Existing flow-normalization/pitch/anchor/provenance defects mean the images cannot establish a current model's error, nor which pixels are unreliable. Coloured overlays and text are visualization annotations, not model inputs. The labelled endpoint errors refer to the other methods in their legends, not automatically to orange GQFT.

| Episode / inspected leg | Visible pattern | Diagnostic to run with raw inputs |
| --- | --- | --- |
| 629 / 0 | Orange path curves but stays to the right of the magenta route and ends short; close wall occupies much of the view | Check temporal confidence/validity, retained left/right spatial support and heading/translation errors separately |
| 629 / 2 | Orange path has a strong sideways excursion near the start, followed by an early endpoint | Inspect frame-pair reliability around the excursion; inspect chunk boundaries and yaw integration as separate possibilities |
| 629 / 3 | Orange roughly follows the straight direction but ends short | Compare displacement scale before/after masking; check whether informative flow was lost |
| 629 / 4 | Orange is displaced left and ends early on a near-straight route | Check coverage imbalance, translation scale and confidence distributions |
| 837 / 7 | Orange and green both end short relative to magenta | Qualitative reporting only: scene `TbHJrupSAjP` is the released locked test scene |
| 1285 / 23 | Magenta bends left; orange captures part of the bend but follows a different curvature and endpoint | Check turning-frame reliability and yaw; shared scene with episode 629 does not make it a validation scene |
| 1689 / 10 | Staircase route; orange/green differ visibly in direction and endpoint | Check height/ground-projector assumptions separately from masking |

All four locally saved episode-629 leg overlays were inspected (0, 2, 3, 4). The other episode folders remain in the diagnostic set; representative legs above were inspected visually, not every frame or leg.

Scene labels in the images: 629/1285 `zsNo4HB9uLZ`, 837 `TbHJrupSAjP`, 1689 `oLBMNvg9in8`. The released manifest declares training scenes `17DRP5sb8fy`, `5q7pvUzZiYa`, `VLzqgDo317F`, `mJXqzFtmKg4`, validation `D7G3Y4RVNrH`, test `TbHJrupSAjP`. External episode scenes do not automatically inherit a safe training/validation designation.

Do not mask an entire wall, sofa or distant background merely because it looks unrelated to the path. Static textured regions can supply camera-motion evidence. The first implementation rejects invalid/low-confidence flow per frame, without any manual ROI fitted to a ground-truth trajectory. Whether reflections, texture defects, occlusion, or dynamic motion explain a particular failure remains a hypothesis until the raw flow maps and aligned poses are inspected.

The legacy episode runner maps episode IDs to indices `{629: 3, 837: 0, 1285: 7, 1689: 6}` and expects `/data/robotics/toshith/flowvo_compare/frames/b10_A_drivefix_idx{idx}_20260829_114756` plus corresponding pose NPZ files. `/data` is absent on this laptop. No Task_2 flow NPZ cache is locally available. Existing images and prediction JSONs are preserved; no masked episode improvement is claimed.
