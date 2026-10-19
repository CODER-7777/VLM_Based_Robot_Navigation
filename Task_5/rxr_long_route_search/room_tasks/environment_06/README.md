# Environment 06: toiletries delivery candidate

Scene `VFuaQ6m2Qom`, source `val_seen / path 5721`, original guide length **41.517564 m**. This is review image **06**, separate from the brown/pink seating scene 04.

The authored task is: “Riya is packing for her trip. Bring her toiletries to her bed.” The combined variant adds: “Don't go through Nora's room; she's sleeping!” Proposed identities: Riya's bed is region 21 / object 447; Nora's bedroom is region 26. Toiletries are placed beside the downstairs sink in bathroom region 20. These names and household routines are new scenario assumptions.

The original path does not visit the bathroom. The new path inserts a pickup detour while preserving every original guide step, for **51.132731 m** in original graph coordinates. All 23 adjacent pairs connect after floor snapping; their navmesh geodesic sum is **51.632739 m**. Neither figure is an executed episode. This scene does not demonstrate that the forbidden room forms a shortcut; the exclusion is a negative constraint.

## Review

- [Front/side placement preview](placement_preview.jpg)
- [Original room views and all candidate lists](../review.html)
- [Transforms, measured heights and normals](placements.json)
- [Verification and limits](verification.json)
- [Waypoints, instruction and authored memories](scenario.json)
- [Object sources and credits](asset_credits.json)

The new objects are a scanned conditioner tube, 19.21 cm tall, and a scanned eye-cream retail carton, 4.90 cm tall. Both retain their physical scale and original photographic textures. They are static 3D objects on the sink counter. They have not been grasped, carried, or delivered to the bed. Missing wall/mirror geometry is already present in the Matterport scan. No cast/contact shadows were added.

RGB-D patches measured the marble counter normal and height independently beneath each prop. Fitted-plane residuals at the 95th percentile are 1.73 mm and 1.46 mm; the lowest base vertex is placed 0.5 mm above its fitted plane. This is geometric placement evidence, not a physics stability test or a full mesh collision audit.

## Reproduce on the existing simulation server

The complete local assets and scripts are in this folder. The render copy used in this session is `/tmp/rxr_room_tasks_20261015/placement` on `guest-isl@172.26.186.222`; `/tmp` is temporary. Original MP3D scene assets on the server were not modified.

From a copy of this folder on that server:

```bash
CUDA_VISIBLE_DEVICES=0 PYTHONDONTWRITEBYTECODE=1 \
  /home/guest-isl/rishabh/bench/envs/navila/bin/python -B \
  render_toiletries.py \
  --out toiletries_placed \
  --placements placements.json \
  --scenario scenario.json
```

This command performs a static render/connectivity review on physical GPU 0. It does not run a robot, navigation policy, or data collector.
