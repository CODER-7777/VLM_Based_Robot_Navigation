# Task 4 — MP3D kitchen repair and Gaussian RGB-D

Objective: repair derived scene `2azQ1b91cZZ` for RxR continuous-navigation observations, preserving calibrated camera geometry and plausible static object placement. The scene repair does not modify the official RxR annotations or establish language-navigation improvement.

## Attempts and outcomes

| Attempt | Result | Remaining limitation |
| --- | --- | --- |
| Calibrated-photo / scan audit | Identified warped triangles, texture ghosts, missing objects and support/scale errors | Hidden geometry/appearance incompletely observed |
| Private object replacement | Continued 15 inherited entries; repaired caddy/knife block/frog assembly and finishes | Parametric/scan substitutes remain approximate |
| Toaster substitute and licensed-model search | Selected AtTheSpeedOf CC BY 4.0 toaster; original PBR maps retained | Hamilton Beach branding differs from photographed Black & Decker |
| Wall/cabinet patch | 161 scan faces removed, four photo-informed surfaces inserted | Bounded local repair; hidden texture reconstructed approximately |
| Material viewers / route comparison | Actual GLBs, browser/gallery/navigation checks recorded | Studio PBR shading differs from baked/Gaussian appearance |
| Sensorless physics + separate Gaussian renderer | Static proxy/NavMesh, calibrated pose bridge, synchronized RGB/depth/frame export | No articulated robot or dynamic object synchronization |
| Initial Gaussian reconstruction | 349,467 Gaussians after cleanup; reference PSNR 27.52 dB, held-out 7.31/10.48 dB | Novel-view quality fails |
| Dense corner repair | 1,044,504 fixed-surface Gaussians; inspected local finite depth reaches 100% | Reference PSNR drops to 18.79 dB; held-out 7.28/10.48 dB |
| All-kitchen expansion | 4,378,360 Gaussians; 23 comparison groups; five wide views | Final revision lacks matched held-out quality evaluation |
| Additional product-model candidates | Cached/BlenderKit searches and candidate downloads for remaining props | Candidate availability is not evidence of final fitting/insertion |

## Geometry and appearance pipeline

`Calibrated photo/mask → silhouette-constrained fit → support/wall/intersection audit → bounded scan deletion → replacement mesh/PBR → fixed surface samples → Gaussian appearance refinement`.

Latest saved composition: 32 props, five counters, two sinks, rangetop. Reviewed audit: 33 checked objects including rangetop, zero issues after explicit 4 cm minimum / 35 cm maximum size exceptions for miniature creamer and phone. Toaster dimensions ≈17.4×29.1×20.0 cm, supported at z=0.929 m. Fixed samples preserve support geometry; view-dependent appearance uses spherical harmonics, not a relightable metallic BRDF.

## Rendering architecture and measurements

`Action → sensorless Habitat/Bullet + static proxy/NavMesh → pose/K/frame_id → CUDA gsplat → RGB + expected depth + alpha`.

Proxy: 120,000 faces from 1,876,726. Raw frame is MP3D Z-up metres; explicit Habitat/OpenGL/OpenCV conversions. Depth is opacity-weighted expected optical-axis Z in metres, not guaranteed first-surface depth; alpha<0.5 or Z outside 0.05–12 m is invalid/NaN.

| Saved check | Result | Scope |
| --- | ---: | --- |
| Latest 800×640 production-frame valid depth | 99.0068% | One camera; coverage, not accuracy |
| Latest CUDA raster | 12.0576 ms | Kernel only; encoding/transport/browser excluded |
| Static NavMesh queries | ~36,835/s | Isolated query benchmark, not rendered FPS |
| 2 m counter/wall probe | Blocked at ~0.392 m | Static navigation constraint |
| Calibrated camera transform error | ~5.4e−7 | Numerical frame consistency |
| Dense-corner close-up median mesh-depth error | 7.6–53.5→2.7–3.4 mm | Sampled local surfaces against repaired mesh |

No 1,000 FPS end-to-end RGB-D or articulated robot/contact benchmark is established. Dense-corner quality scores belong to an earlier revision; final all-kitchen photorealism must be evaluated independently.

## Current hypothesis and pending work

Fixed geometry plus calibrated multi-view appearance should reduce floating/distorted reconstruction while retaining recognizable props. Pending: closer product models/materials for remaining objects; uncontaminated masks and denser calibrated coverage; final matched held-out RGB/measured-depth evaluation; full application latency; scene-edit synchronization; articulated robot collision/contact integration.

## Source and artifacts

Repair/build tools: `kitchen_all_objects_upgrade/evidence/`, `toaster_wall_mesh_repair/evidence/`, `toaster_selected_model/evidence/`. Physics/Gaussian tools: `split_render_pipeline/evidence/`, `gaussian_corner_repair/evidence/`. Dashboard/runtime: `all_dashboard.py`, `physics_all_server.py`, `visual_all_server.py`, launchers and local SSH helpers. [Code index](../docs/mid_evaluation/CODE_INDEX.md) · [Metric evidence](../docs/mid_evaluation/evidence/task4/).

Final large scene/checkpoints remain on ISL at `/data/robotics/toshith/rxr_author/refined/kitchen_all_upgrade/`; local `scenes/v15/` is an older snapshot. Tool scripts retain server paths/dependencies. Saved publication records do not verify current server availability. Source/license metadata and selected original model archives remain in the corresponding asset folders.
