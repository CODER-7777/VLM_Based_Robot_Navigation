# Environment 04: revised backpack and leaning placements

This is the current **candidate for user review**, following rejection of the blue backpack and initial placements. Start with `replacement_preview.jpg`; individual 1024×1024 front and side views are in `placed/*_detail.png`.

## What changed

- Replaced the blue model with a real canvas-backpack photogrammetry scan, published by WV_ArtDev and credited to scanner SmallpolyArt.
- Confirmed the original brown support point was on a raised armrest, about 19 cm above the actual seat. Added overhead and frontal depth views to locate the lower cushion.
- Fitted cushion and backrest planes separately. Bags follow each chair's actual orientation and lean against the back cushion, as requested. Approximate resulting lean angles are 26.5 degrees for brown and 15.8 degrees for pink.
- Removed the scan's display-base/underside artifacts, baked the source node transforms and normalized the prepared bag to 40 cm tall.
- Replaced the previous dark material lighting with the scan's baked photo-texture rendering. No AI images, invented textures or pasted 2D bags were used.

`placement_request.json` is the runnable input. `scenario.json` records the actual applied transforms and reachable front-facing standing goals. `surface_planes.json`, `contact_checks.json` and `verification.json` preserve the measurements.

## Contact and rendering limits

The placement uses actual mesh vertices and measured depth surfaces. A 2% vertex-sample allowance lets loose strap/underside tips enter the coarse reconstructed soft cushion so they do not hold the main bag above the seat. The remaining body samples meet the fitted seat/backrest surfaces within millimetres. The deepest thin/stray samples enter a fitted cushion plane by approximately 3.7 cm on brown and 3.3 cm on pink. This is a visual placement approximation, **not a physics-settled support guarantee**.

The legacy renderer does not add new bag-to-chair contact shadows. The underlying Matterport room textures and geometry remain rough. These limitations can still make the result look less integrated than a photograph; this revision is not marked user-approved or final photorealism.

The downloaded Objaverse copy has 1024-pixel maps. The separate HotFrost school-bag candidate advertises 4K textures but has **not** been downloaded: its official download API requires Sketchfab authentication. Its author preview is included only for comparison.

The four no-bag baseline PNGs still exactly match the original goal images. Original scene assets, RxR annotation files and the active dashboard were not changed. Original RxR guide length remains 47.31 m; refer to `placed/navigation_results.json` for the shorter approach paths and guide/navmesh limitations rather than claiming a >=40 m shortest path.

## Files and rerun

- `place_backpacks.py`: legacy/modern Habitat-compatible renderer.
- `fit_surfaces_and_prepare_model.py`: local-workspace surface fitting and scan cleanup.
- `build_review.py`: checks actual applied transforms and creates the review sheet.
- `assets/canvas_backpack_baked_clean_40cm.glb`: prepared, textured 3D object.
- `assets/wv_backpack_photogrammetry.glb`: unmodified downloaded source scan.
- `model_sources.json`: source URLs, license, hashes and genuine download status.

The server copy is in `/tmp/rxr_schoolbags_env04_20261015/environment_04/revision_02`. Run:

```sh
CUDA_VISIBLE_DEVICES=0 PYTHONDONTWRITEBYTECODE=1 \
  /home/guest-isl/rishabh/bench/envs/navila/bin/python -B \
  /tmp/rxr_schoolbags_env04_20261015/environment_04/revision_02/place_backpacks.py \
  --mode place \
  --scene /data/robotics/toshith/vln_baselines/data/scene_datasets/mp3d/SN83YJsR3w2/SN83YJsR3w2.glb \
  --out /tmp/rxr_schoolbags_env04_20261015/environment_04/revision_02/placed --gpu 0
```

## Attribution and alternatives

**“Backpack Photogrammetry” by WV_ArtDev, scanned by SmallpolyArt, licensed under CC BY 4.0.** Downloaded from the official AllenAI Objaverse distribution. Modified for this scenario by cleaning underside/display artifacts, baking transforms, changing scale and positioning; source textures retained.

- Original: https://sketchfab.com/3d-models/backpack-photogrammetry-b8037798633640e7bf040aac16ea8d45
- Public model distribution: https://huggingface.co/datasets/allenai/objaverse/resolve/main/glbs/000-069/b8037798633640e7bf040aac16ea8d45.glb
- License: https://creativecommons.org/licenses/by/4.0/
- Alternate remastered PBR scan, SmallpolyArt: https://sketchfab.com/3d-models/backpack-photogrammetry-d4b6b11d41ea401e98384401df735c12
- Alternate ordinary school-bag photoscan, HotFrost (Atharva Taras), CC BY 4.0, author lists 4K maps: https://sketchfab.com/3d-models/school-bag-backpack-photoscan-64249ba38f5045bdaabbb5749aa30033
