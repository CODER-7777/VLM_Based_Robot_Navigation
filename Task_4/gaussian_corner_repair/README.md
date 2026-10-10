# Toaster corner: Gaussian distortion repair

The live dashboard now uses a revised Gaussian scene that removes the severe speckled halo around the toaster and gives the local counter/wall geometry consistent depth. The toaster remains at its physically audited placement. The main repaired-object editor and earlier comparisons are also running.

This is a substantial local distortion repair, **not a claim that the entire room is photorealistic**. The existing canister models still have simplified materials, the repaired counter has a visible boundary with the old reconstruction, and farther regions retain the earlier Gaussian artifacts.

## Open it

- [Updated Gaussian RGB-D dashboard](http://localhost:8778/): press **R** or **Reference view** for the calibrated photo camera. W/S move, A/D turn, up/down tilt.
- [Gaussian before/after and three close-up angles](http://localhost:8778/corner-comparisons).
- [Complete repaired kitchen editor](http://localhost:8767/) and [all earlier object comparisons](http://localhost:8767/comparisons).
- [Original metallic PBR toaster viewer](http://localhost:8767/product-viewer).

Refresh an already open RGB-D tab to load the new controls. The live camera was preserved during publication. Browser verification confirmed that both 800 × 640 images load and the comparison link/button are present; an isolated physics instance verified the Reference action without moving the live user's camera.

If the page is unavailable later, run **on your local computer, from this repository**:

```bash
bash Task_4/gaussian_corner_repair/open_dashboard.sh
```

The script preserves reachable tunnels and opens only missing forwards. Keep its terminal open if it starts SSH. ISL connectivity may require campus network/VPN. The services on the server must also be running.

![Previous versus repaired Gaussian corner](images/comparison0.jpg)

![Close-up: previous versus repaired](images/comparison4.jpg)

## What changed

The earlier training masked out the old toaster, but sparse and underconstrained local Gaussians did not adequately replace the removed object/background. Optimized appearance coefficients and displaced points produced holes, bright speckles and unstable close-up views. A prior surface-distance cleanup removed some points but did not solve the missing coverage.

The new repair removes 18,013 local Gaussians and samples the actual repaired mesh surfaces densely. Triangles are clipped to the repair region while interpolating their UVs, so their original textures remain attached to the geometry. The region includes the complete neighbouring canisters to avoid cutting an object at its boundary. It adds 713,050 surface samples, including 236,546 toaster samples; the complete checkpoint has **1,044,504 Gaussians**.

The new samples stay fixed on the mesh. Appearance refinement cannot move the toaster, stretch the wall or change its support height. The toaster's lowest sampled surface is Z≈0.929 m, matching the counter. The underlying GLB and all 32 audited prop placements are unchanged.

For the counter, calibrated photographs provide a median exposure/colour adjustment to the continuous existing UV texture. Directly blending photo colours point by point was rejected after it created patches. Soft contact shading is computed by tracing sampled ambient rays against the actual toaster geometry; it is an approximate ambient-occlusion treatment rather than measured room illumination.

For the metal, ten usable training-camera renders of the original PBR asset supervise a 2,200-step appearance fit. The unconstrained fit looked good at the reference camera but rippled in novel close-ups. The published version smooths its appearance residual over nearby samples with similar normals and blends it conservatively at 30% with the original baked appearance. Gaussian spherical harmonics approximate view dependence; the standalone PBR viewer retains the actual metallic/roughness/normal material.

## Verification and limits

Five identical before/after camera poses were checked: the calibrated reference, the saved user angle and three closer views. The following depth errors are relative to ray intersections with the **repaired mesh**, not independent measured physical truth.

| View | Previous finite depth on sampled local surfaces | Repaired finite depth | Previous median error to mesh | Repaired median error |
|---|---:|---:|---:|---:|
| Saved user angle | 82.0% | 100% | 9.9 mm | 3.6 mm |
| Close-up 1 | 84.2% | 100% | 7.6 mm | 3.3 mm |
| Close-up 2 | 76.5% | 100% | 8.5 mm | 3.4 mm |
| Close-up 3 | 73.7% | 100% | 53.5 mm | 2.7 mm |

These percentages use sampled pixels whose reference rays hit the local repair. They do not describe the whole image. The isolated published reference check at 800 × 640 has **98.9% valid depth across the complete image**. Camera reproduction error is approximately 5.4e-7; RGB/depth intrinsics, pose and frame ID agree, and invalid depth remains NaN. The appearance stabilization changes no positions, opacity or scales.

CUDA rasterization measured approximately 10.5 ms at the preserved user pose and 12.5 ms in the published reference check at 800 × 640. These are individual measurements excluding encoding, network transfer and physics. The denser scene costs more than the earlier sparse model; 1,000 FPS RGB-D is not demonstrated.

The full-image photo-agreement gate remains unsuccessful. At 640 × 512, reference masked PSNR is now 18.79 dB, compared with 27.52 dB for the earlier photo-fitted baseline. The new physically clean mesh surfaces and simplified canister/counter appearances do not reproduce the original photograph's pixels as well. Held-out scores remain only 7.28 and 10.48 dB. Measured reference depth error is 10.9 mm median and 23.2 mm mean over valid evaluated pixels. These measurements are separate from the mesh-consistency test above.

The local silhouette/depth improvement should therefore be assessed alongside the remaining appearance mismatch. Next realism work needs better canister materials, a seamless counter/background texture fit and broader calibrated reconstruction coverage. Outside this local repair, the earlier distorted Gaussian room has not been rebuilt.

![Browser-verified live dashboard](images/dashboard.png)

## Files and restarting

Server root: `/data/robotics/toshith/rxr_author/refined/split_visuals/`.

| Server path | Contents |
|---|---|
| `scene.npz`, `scene.ply` | Active revised checkpoint and Gaussian PLY export |
| `scene_before_dense_corner.npz`, `.ply` | Previous live checkpoint retained for rollback |
| `corner_v2/scene.npz` | Dense surface candidate before appearance refinement |
| `corner_v2/scene_refined.npz`, `.ply` | Published stabilized variant |
| `corner_v2/scene_pbr_fit_unfiltered.npz` | Unfiltered metallic appearance fit, retained for comparison |
| `corner_v2/previews/` | Before/after RGB, depth arrays and published reference view |
| `corner_v2/construction.json` | Surface counts, region, source scene and sampled mesh nodes |
| `corner_v2/appearance.json`, `stabilization.json` | Appearance fit and conservative stabilization settings |
| `corner_v2/geometry_validation.json` | Five-pose depth-to-mesh and support-height checks |
| `corner_v2/published_validation.json` | Isolated Reference-button and synchronized RGB-D checks |
| `corner_v2/global_evaluation.json` | Current reference/held-out photo metrics |
| `active_visual.json` | Published revision, construction and review evidence |
| `physics_corner_server.py`, `visual_corner_server.py` | Revised private services: ports 8778 and 8779 |
| `launch_corner_services.py` | Start services while preserving already occupied ports |

Local `evidence/` contains the implementation scripts and JSON reports. Local `images/` contains the actual saved outputs. The earlier [split pipeline report](../split_render_pipeline/README.md) describes the architecture and initial baseline; its earlier measurements are historical.

After a server reboot, connect using SSH and run **on ISL**:

```bash
cd /data/robotics/toshith/rxr_author/refined/split_visuals
/data/robotics/toshith/envs/kitchen3d/bin/python launch_corner_services.py
```

The launcher starts missing private services. Its `--activate` mode was used to publish the reviewed candidate, back up the previous checkpoint and preserve the existing camera. It verifies private process IDs before stopping anything. The main full-scene editor, earlier sessions, shared manifests, source GLBs and UI routes were retained.

The source toaster remains [AtTheSpeedOf's CC BY 4.0 model](https://sketchfab.com/3d-models/toaster-0d39352a32404ce7b71b8ac020844949), documented in the [selected-model report](../toaster_selected_model/README.md). Its Hamilton Beach branding differs from the Black & Decker photograph; the user explicitly selected this approximate model.
