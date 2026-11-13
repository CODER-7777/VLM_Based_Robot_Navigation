# Why GQFT trajectories go wrong: root-cause analysis (12 Nov 2026)

Inputs: GPU-4 pilot gallery `trained_episode_overlays/20261111T220751Z_gpu4/all_episodes_20261111T223221Z`. It covers 10 recorded episodes, 133 legs and 5,658 steps, with three models trained 500 steps each:
- yaw-local reference GQFT
- solver + correction
- solver + learned weights

All 19 images in `Task_2/images_for_analysis` were viewed. Pink = recorded ground truth; violet = solver + learned weights. Numbers come from each episode's `predictions.json` via `decompose_leg_errors.py` (output: `leg_error_breakdown.json`). No new inference or training was run.

## Summary

| # | Cause | Evidence | Share of the problem |
|---|---|---|---|
| 1 | **Camera height is not 1.2 m in upper-floor recordings** (data/render contract) | Episodes with `floor_y` > 1 m (837, 1031, 1781) are the only scale outliers. All three models, including pure geometry, undershoot distance by the same factor (median 0.64 on ep837, 0.75 on ep1031). Same house `2azQ1b91cZZ`: ground floor ep1395 ratio 0.99, upper floor ep1031 ratio 0.75. Every pose file says `mesh_floor_offset_applied: False` | **≈68% of the solver's summed leg error**; 37 of 133 legs |
| 2 | **Phantom motion when turning on the spot** (old GQFT only) | 1,252 of 5,658 steps (22%) are turn-in-place. Reference GQFT adds +7.5 m of distance and 0.68° yaw error per step there; solver +1.2 m and 0.02° per step | Fixed by the solver |
| 3 | **Heading drift on straight stretches in narrow spaces** (solver) | 13 legs with end-heading error > 20°. Error builds up while ground truth is nearly straight (e.g. 1481 leg01: solver turns 72° vs ground truth 34° over 68 straight steps), at a steady 1–2° per step. All are corridors, bathrooms or stairways with walls or furniture close to one side | Main remaining error on ground-floor episodes |
| 4 | **Stairs / non-flat floor** | 478 leg06, 1689 leg10, 837 stairwell. Ground truth is planar (0 legs with vertical motion > 5 cm), but the camera views stairs | A few legs |
| 5 | **Chunk stitching on full episodes** | 24-pair chunks, history restarts at 1 pair, heading committed per chunk. Full-episode errors (0.2–8.8 m) are much larger than per-leg errors | Full-episode views only; not yet isolated |

**The Transformer is not the bottleneck.** The solver-based models win most legs, but their best checkpoints were at step 100 and step 500 and they are almost identical, so the learned correction adds little. The old Transformer's main failure is cause 2, which comes from training motion that never turned on the spot, not from its architecture.

## Results with cause 1 separated

| Model | Ground-floor episodes (96 legs): mean / median error | Upper-floor episodes (37 legs): mean |
|---|---|---|
| Yaw-local reference GQFT | 0.094 m / 0.059 m | 0.300 m |
| Solver + correction | **0.067 m / 0.011 m** | 0.371 m |
| Solver + learned weights | **0.064 m / 0.014 m** | 0.365 m |

On correctly recorded episodes the solver models are better than the reference by about 30% in mean and 4–5× in median error. On mis-recorded episodes every model fails, and the solver fails slightly more because it trusts the 1.2 m height exactly.

## Per-episode distance ratio (predicted / ground-truth path length, legs > 0.3 m)

| Episode | Scene | floor_y | Solver | Reference | Implied camera height |
|---|---|---|---|---|---|
| 478 | oLBMNvg9in8 | 0.18 | 0.94 | 0.98 | 1.28 m |
| 629 | zsNo4HB9uLZ | 0.17 | 0.92 | 0.94 | 1.30 m |
| 753 | QUCTc6BB5sX | 0.36 | 0.93 | 0.98 | 1.30 m |
| **837** | TbHJrupSAjP | **1.54** | **0.64** | 0.65 | **1.88 m** |
| **1031** | 2azQ1b91cZZ | **1.60** | **0.75** | 0.72 | **1.59 m** |
| 1285 | zsNo4HB9uLZ | 0.17 | 0.97 | 0.97 | 1.23 m |
| 1395 | 2azQ1b91cZZ | 0.13 | 0.99 | 1.00 | 1.21 m |
| 1481 | zsNo4HB9uLZ | 0.17 | 0.99 | 1.00 | 1.21 m |
| 1689 | oLBMNvg9in8 | 0.06 | 1.07 | 1.04 | 1.13 m |
| **1781** | x8F5xyUWy9e | **1.05** | 1.44 | 1.18 | 0.83 m (1 leg only) |

Implied height = 1.2 m / ratio. This assumes the flow scale error comes only from camera height, which is a hypothesis to confirm on the server (check C1).

## What each image shows

| Image | What goes wrong | Cause |
|---|---|---|
| ep837_full, leg03, leg05, leg08, leg11, leg19 | Path shape right, violet consistently shorter than pink; full view crosses a stairwell | 1 (upper floor, ratio ~0.55–0.65), plus 4 on the stairs |
| ep1031_leg02, leg04 | Straight path stops at ~half length; elevated view down into an atrium | 1 (ratio 0.46–0.73) |
| ep1781_leg01 | Good until a sharp final turn, then violet swings left too far | 1 (upper floor) plus heading error in a tight corridor |
| ep1781_leg08, ep753_leg00 | Camera faces a wall or bed; tiny path | Short or turn-in-place legs; little floor visible |
| ep1689_leg10 | Narrow stair corridor; violet drifts left near the end (solver yaw +79° vs ground truth −27°) | 3 and 4 |
| ep1689_leg11, ep1481_leg01 | Narrow corridor / bathroom; endpoint rotated | 3 |
| ep478_leg06 | Ground truth turns at the staircase; violet goes straight up the stairs | 4 |
| ep1689_leg00, ep1285_leg00, ep1481_leg06 | Close match, small endpoint offset | Mostly correct; small heading drift (3) |

## Checks to confirm (server, CPU)

- **C1, camera height.** Read how `render_frames.py` / `build_poses.py` place the camera on upper floors (`floor_y`, `mesh_floor_offset`). Then, for frame 0 of ep837, ep1031 and ep1395, render depth at the bottom-centre pixel (or read saved depth): height = depth × (ray · world-up). Expected: ~1.2 m on ep1395, ~1.6–1.9 m on ep837/1031.
- **C2, heading drift.** On cached episode flow, rerun the solver with the floor window limited to pixels in front of the robot (|lateral| < 0.6 m), and separately estimate yaw only from distant pixels. Decide with ground-floor episodes only. Never tune on 629 alone.
- **C3, stitching.** `tools/episode_diagnosis.py` compares chunked and sliding-window inference.

## Fixes, in order

1. **Fix or exclude the mis-recorded episodes.** Re-render upper-floor episodes with the floor offset applied (or the true camera height), or report them separately as a "height-contract violation" set. No algorithm can recover metric scale from one camera if the assumed height is wrong. This alone removes about two thirds of the solver's leg error.
2. **Rotation from distant pixels, translation from near floor** (Guided Feature Selection, P04, adapted). Pure rotation moves every pixel the same way regardless of depth; translation needs the known floor. Estimating yaw from far pixels avoids wall contamination in the near-floor window. A cheaper alternative is a laterally limited floor window. Test one at a time.
3. **Sliding-window inference** for full episodes, if C3 confirms the benefit.
4. Keep the solver backbone: it already solves turn-on-the-spot and gives 4–5× lower median error on correctly recorded episodes.
