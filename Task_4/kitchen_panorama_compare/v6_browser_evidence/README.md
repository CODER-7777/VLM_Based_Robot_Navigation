# Kitchen workspace repairs — 2026-10-11

Revision: `kitchen_workspace_v6_20261011`. Every new artifact is inside this project folder under `/data/robotics/toshith/vivekananda`. `/data/robotics/toshith/rxr_author/refined` is a read-only reference input. One worker was used.

The candidate room is `home_pbr_products.glb` (approximately 441 MB). The previous reviewed source room remains available at `/data/robotics/toshith/rxr_author/refined/kitchen_product_replacements/home_pbr_products.glb`. The workspace revision is now **published on port 8774**. Actual Chromium browser verification passed for all 30 room/model selections and 23 calibrated comparisons. The identified older product dashboard was replaced; navigation and Gaussian services were not restarted, and navigation state was preserved.

## Changes

- **Soap bottle v6:** densified the original body, rounded its shoulder using an interpolated radial profile, and exported smooth normals. The original photo-derived label and pump were retained. The finish uses satin-plastic roughness. Fine pump shape remains approximate.
- **Soap dish v6:** rebuilt the straight-sided proxy as a hollow flared elliptical ceramic dish with a thin rounded rim and oblong soap. Moved it 68 mm along raw −X to clear the hot-tap base. Its supporting foot is on the rear counter strip. The photographed dish is larger; the available sink/tap clearance constrains this approximation.
- **Blue creamer v6:** retained the approximately 5 cm photo-fitted scale; rebuilt a hollow cobalt-glazed body, pouring lip and smooth loop handle. Interior and unseen geometry are approximate.
- **Glass kettle v6:** retained its licensed geometry and material definitions, including transmission; translated it 22 mm along raw +Y to clear the tea-tray rim. It remains a substitute with a different lid/body than the photo.
- **Cordless telephone/dock v6:** restored the object removed by an earlier merge. Rounded black housing and charging base, photo-calibrated handset lean, metallic edge trim, and photo-derived front controls. Individual key relief and unseen surfaces remain approximate.
- **TV remote v6:** retained its geometry and texture; translated it 27 mm along raw +Y so the supporting foot stays on the bar slab.

The source room already includes the later canister, stove, paper-towel and articulated-frog repairs. Those were retained, not rebuilt. The workspace removes the unsupported external frog licence claim and synthetic Sketchfab URL from copied metadata; the frogs are identified as an existing photo-guided reconstruction.

## What was checked

`evidence/artifact_verification.json` checks the current saved candidate, not the old placement log. All 40 reference-manifest entries were investigated. **All 40 now have active scene meshes; 33 are props** (the other seven entries are sinks/counters). The initially missing `phone_dock_v3` was traced to the earlier desk-phone merge selecting its name as well. The dock is now restored as `phone_dock_v6`, with photo-calibrated handset lean and photographed front controls. The workspace merge requires an explicit version marker after the full object stem so `phone` cannot select `phone_dock`.

The support audit tests evaluated scene vertices against unions of the actual counter-top triangles, including cutouts, in raw Z-up metres. The candidate has no contact-footprint failures or conservative pairwise overlap flags. Before correction, 1 mm horizontal sections detected up to 3.69 cm² of kettle–tray overlap. This audit screens surface contact and pair overlap; it is not a watertight-solid collision proof for every scanned wall/cabinet.

The original toaster's **11 parts and three texture-map byte hashes** match the actual source room. Geometry accessors and materials also match. The saved standalone models' world bounds match the candidate room for all 40 active fits. glTF buffer/index checks pass.

`comparison/items` contains **23 calibrated photo comparisons and 92 JPEG panels**. The labels are **Real photograph / Earlier repaired mesh / Current repaired mesh**. Earlier is the existing product-repaired room at the start of this continuation. Both rendered columns use the same calibrated camera and crop. Current panels now use actual Three.js browser captures; earlier panels retain their saved OpenGL render. Prior current OpenGL panels are archived in `evidence/opengl_panels`. The photographs are original dataset inputs, copied without retouching.

The local renderer uses actual saved GLB triangles and base-colour, metallic/roughness and normal maps, GGX lighting, a directional shadow map and approximate environment lighting. Glass transmission is approximate. Those original verification renders are preserved as OpenGL evidence. Actual browser captures are now also saved and reviewed in `evidence/browser_captures`. The two extra room angles and studio view for each of the five changed selectable objects are recorded in `evidence/additional_view_cameras.json` and `evidence/additional_views_review.jpg`.

The final contact sheets were visually inspected; `evidence/visual_review.json` records the observations and remaining mismatches for this exact scene hash. The restored cordless phone is an approximate reconstruction: controls, finish and base shape still need refinement. Photograph-derived front details are an asset input, not independent validation evidence.

The dashboards use 23 comparison selections and **30 room/model selections** (four bottles share one selection). Local execution of the real handler checked all 92 panels, model pages/download ranges, vendor JavaScript, scene byte-range delivery and path-traversal rejection. That initial handler check was followed by actual HTTP and Chromium checks during publication; primary live entry points return HTTP 200.

## Live dashboards and launch

The verified workspace dashboard is already running on server port 8774. With the laptop tunnels active, open:

- `http://localhost:8767/` — 23 photo / earlier repaired mesh / current repaired mesh comparisons.
- `http://localhost:8767/models` — 30 room/model selections with interactive model viewers.
- `http://localhost:8767/kitchen-room` — the full repaired mesh with inspection and the existing walking controls.
- `http://localhost:8769/` — five synchronized original-photograph / repaired-room 360° comparisons, with JPEG downloads.

No dataset copy to the laptop is required. Server files are read through SSH port forwarding. If the local ports are free after a reboot, run on the laptop and keep the terminal open:

```bash
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 \
  -L 8767:127.0.0.1:8774 -L 8769:127.0.0.1:8786 \
  guest-isl@172.26.186.222
```

The workspace preview is separately available on server port 8790 (laptop tunnel 8770). To launch a preview on a free server port from a normal server terminal:

```bash
cd /data/robotics/toshith/vivekananda/kitchen_repair_20261011
/data/robotics/toshith/envs/kitchen3d/bin/python launch_products.py --port 8790
```

`evidence/browser_review.json` records the matching scene hash, actual captures, all selection/model checks, zero browser exceptions and the visual review. Passing means the dashboard can be published with its documented approximations; it does not establish complete photorealism. `publication_status.json` records the live PID, port and preserved navigation state. `launch_products.py --publish` checks this review and stops only a positively identified earlier product-dashboard process when a switch is needed.

Panorama artifacts and provenance live in `../kitchen_panorama_compare`; its README explains capture, camera alignment, downloads and limitations. Before is the original dataset photographic skybox, because the historical untouched GLB was unavailable. After is an actual browser PBR room capture, not a Gaussian render.

## Reproduction

Use `/data/robotics/toshith/envs/kitchen3d/bin/python` with `PYTHONDONTWRITEBYTECODE=1` and `XDG_CACHE_HOME` set to this project's `cache`. Original models/photos are inputs; source files are not modified.

1. `scripts/build_repairs.py` builds the three photo-guided shape repairs.
2. `scripts/fix_placement.py` creates the two retained meshes with material-preserving translations, using workspace snapshots of the original fits. The input `objects/glass_kettle_v5` and `objects/tv_remote_v3` remain available.
3. `scripts/restore_phone_dock.py` rebuilds the restored handset/dock from the calibrated reference photo. `scripts/merge_products.py` creates the candidate from the reference room and six workspace replacements.
4. `scripts/prepare_workspace.py` regenerates the active manifest, exact scene/model fits and placement audit. `scripts/add_dock_comparison.py` adds the original cordless-phone photograph and calibrated camera to the comparison catalog.
5. `scripts/capture_comparisons.py` renders the calibrated before/current panels. `scripts/capture_additional_views.py` regenerates extra views and records cameras.
6. `scripts/prepare_dashboards.py` updates the comparison, model and room wrappers.
7. `scripts/verify_artifacts.py` and `scripts/check_dashboard_routes.py` check saved artifacts and local handler behavior.

Retain the already-written versioned objects and the earlier input snapshots when reproducing. The viewport renderer explicitly activates its own EGL context when rendering, allowing room and studio renderers to alternate correctly.

Remaining work includes exact product silhouettes for some retained appliances, fine frog decoration, and scan-background defects (backsplash gaps, missing/distorted room surfaces). Do not claim a complete photorealistic reconstruction. Browser publication is documented separately by the completed browser review and publication records.

## Browser continuation and publication

Actual Chromium browser verification passed for this scene hash. All 30 room/model selections and 23 comparison selections were exercised; no browser exceptions were recorded. `evidence/browser_captures` contains calibrated captures and the inspected contact sheet. Current comparison panels now use those actual browser captures; previous OpenGL panels are retained in `evidence/opengl_panels`. The older sections describe the earlier restricted-runtime checks. Five synchronized original-photograph/repaired-room panoramas are being prepared in the separate workspace `../kitchen_panorama_compare`.
