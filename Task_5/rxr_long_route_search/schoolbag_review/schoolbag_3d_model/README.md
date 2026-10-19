# School-bag 3D assets

Downloaded on 2026-10-14. No bag has been placed in any RxR/Matterport scene. The user will choose the placement locations.

## Primary: blue JanSport school backpack

- File: `jansport_backpack.glb`
- Original author: Google LLC, Google Scanned Objects.
- Original asset: https://app.gazebosim.org/GoogleResearch/fuel/models/Jansport_School_Backpack_Blue_Streak
- Distributor: https://sceneview.github.io/models/platforms/jansport_backpack.glb
- License/attribution evidence: https://sceneview.github.io/credits.html and the saved `catalog.json`.
- License: Creative Commons Attribution 4.0, https://creativecommons.org/licenses/by/4.0/
- Attribution: **“JanSport School Backpack Blue Streak” by Google LLC, distributed by SceneView, licensed under CC BY 4.0.**
- The downloaded GLB is unchanged. SceneView converted/distributed the source asset; do not describe this file as the original raw scan.
- Bounds: approximately 0.358 m wide × 0.440 m high × 0.369 m deep, Y up, base at Y=0. The distributor identifies it as a real-scale asset. Confirm the placement transform when integrating it.
- Geometry: 30,092 triangles; one embedded 2048×2048 JPEG texture; no external texture/buffer dependencies or required glTF extensions.
- `jansport_four_views.jpg` and `jansport_view_*.jpg` render the actual geometry and embedded texture, with an orthographic camera and neutral background. No AI-generated or repaired details. These previews do not simulate the eventual room lighting.
- Public interactive preview: https://sceneview.github.io/view.html?url=https%3A%2F%2Fsceneview.github.io%2Fmodels%2Fplatforms%2Fjansport_backpack.glb

## Alternative: black school backpack

- File: `school_backpack.glb`
- Author: MadeByYeshe.
- Source: https://sketchfab.com/3d-models/school-backpack-524d7fc724094ead9f203ed06bae76e1
- Distributor: https://sceneview.github.io/models/platforms/school_backpack.glb
- License: CC BY 4.0, https://creativecommons.org/licenses/by/4.0/
- Attribution: **“School Backpack” by MadeByYeshe, distributed by SceneView, licensed under CC BY 4.0.**
- The downloaded GLB is unchanged; author/source/license also appear inside its asset metadata.
- Geometry: 66,344 triangles; three embedded 1024×1024 WebP textures. Requires `EXT_texture_webp` support.
- Asset coordinates are not school-bag dimensions: its native height is approximately 6.934 units and its base is offset. Recenter and explicitly scale a placement instance before use. Prefer the JanSport model for this task.

`model_verification.json` records GLB header validation, embedded images, geometry, bounds and SHA-256 digests. `source_manifest.json` records source attribution. `inspect_models.py` regenerates validation and four JanSport views using numpy, trimesh and Pillow.

The license for these models is CC BY 4.0; SceneView's code license does not replace their asset licenses. Preserve attribution when sharing renders or modified models, and identify any subsequent modifications.
