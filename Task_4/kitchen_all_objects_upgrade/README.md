# Kitchen repair expanded beyond the toaster

This version is live on ISL and includes the remaining counter items, photo-matched stone on five counters, and repaired low backsplash strips. It has 23 real-photo comparison groups and five additional viewpoints. The private manifest contains 32 props, five counters, two sinks and the rangetop. Several shapes and hidden details remain approximate; this is a reviewed prototype, not a complete photorealistic reconstruction.

## Open the dashboard

Run this on your **local computer**, in the repository folder:

```bash
bash Task_4/kitchen_all_objects_upgrade/open_dashboard.sh
```

The command starts missing private dashboard services on ISL and opens missing SSH forwards. Keep the terminal open when it creates a tunnel.

- [Live repaired kitchen](http://localhost:8767/)
- [Real photo | previous | updated comparisons](http://localhost:8767/comparisons)
- [Vase / blue jug](http://localhost:8767/comparisons#blue_jug)
- [Telephone](http://localhost:8767/comparisons#phone)
- [Rotate models and inspect their finish](http://localhost:8767/models)
- [Separate physics / Gaussian RGB-D](http://localhost:8778/)
- [Earlier full route editor](http://localhost:8767/legacy-editor)
- [Earlier mesh comparison panels](http://localhost:8767/legacy-comparisons)

W/S move forward/backward, A/D turn, and arrow up/down tilt the camera. R returns to the reference camera. Refreshing the page preserves the current pose. Publishing this update preserved frame 83's camera and resumed as frame 84. The earlier full editor on remote port 8776 was preserved.

## What changed

The approved metallic toaster remains the existing `toaster_v4`. The other items now use fitted geometry with denser fixed surface samples and real-photo appearance on visible surfaces. Canister decorations, bottle labels, the caddy's wood and printed sides, and tea/coffee finishes come from the actual kitchen photographs. This improves their recognisability without inventing new advertising imagery.

The telephone uses the existing free desk-phone product, refitted within the counter and wall limits. Its primary silhouette overlap improved from approximately 0.356 to 0.491. It is 9.9 cm high with a 31.6 × 23.0 cm world footprint including handset/cord geometry. The fixed Gaussian phone has 123,294 surface samples; 57,153 front-facing samples receive colours from the real telephone photograph. Its cord and exact controls remain approximate. The standalone GLB and private full stages also use corrected calibrated photo UVs on the front surfaces, replacing the old stretched partial keypad decal; unseen sides use neutral dark plastic.

The blue object is fitted as a small cobalt creamer: 5.1 cm high, maximum world span about 7 cm, and primary silhouette overlap about 0.635. It has a smooth glazed body and a curved handle. The photo does not reveal its entire opening or handle, so those are generic. Its size is a camera-fit estimate rather than a verified manufacturer dimension.

The frog statues still need a closer source model. Their sparse existing photo-trained appearance is retained and moved rigidly inward from the wall, rather than clipping individual points and damaging the shape. Their visible reconstruction and fitted proxy remain approximate. The comparison deliberately exposes this limitation.

The countertop stone is reprojected from calibrated real photos onto the physical slabs. Foreground objects, their old deletion footprints and inconsistent depth observations are masked. Camera exposures are aligned where enough overlapping observations exist. Visible stone is preserved; hidden areas use nearby photographed stone and approximate infill. This matches the surface colour and grain, but cannot recover the exact pattern under an appliance.

The low backsplash is now planar and extends from approximately z=0.932 to 1.400 m. Extending the original short patch closes the visible upper seam. Its visible tile colours come from real images; hidden tiles use approximate repeated photographic grain and grout spacing.

## How the dataset and repair work

The source building is `2azQ1b91cZZ` from Matterport3D, used by the RxR navigation workflow. The source photographs, calibration, scanned geometry and navigation data serve different purposes. RxR supplies navigation-language tasks; it does not supply clean product CAD models for the kitchen props. See the [earlier detailed dataset and directory guide](../kitchen_dataset_repair_guide/) for the broader project explanation.

1. Inspect an object in the actual undistorted photographs. Use its labelled pixel boxes and multiple views to distinguish the object, its occluders and its support surface.
2. Locate damaged scan geometry: warped triangles, disconnected fragments, blurry baked object textures, wall ghosts, wrong proportions and missing parts. The original scan can contain an object's silhouette painted into a wall even after its triangles are deleted.
3. Prefer a suitable licensed product model. Otherwise retain a good fitted mesh or construct a physically sized parametric/lathed shape. A similar product is not automatically the exact original product.
4. Use the supplied camera calibration to project the candidate into the real image. Segmented foreground masks and silhouette overlap guide position, orientation and scale. Counter height, wall limits and plausible physical dimensions constrain the search; shadows and cords must not inflate the appliance itself.
5. Fit visible appearance from the real photographs. Foreground masks and front-facing normals prevent much of the background from being painted onto the object. Occluded intersections remain difficult and are explicitly reviewed.
6. Preserve material parameters for the GLB preview: roughness, metallic finish and glaze/coat where appropriate. The selected toaster retains its original product PBR assets. Other photographic colours can include baked lighting and are not pure relightable albedo.
7. Sample the fitted surfaces densely for the Gaussian renderer. The new geometry is fixed; changing photo colours does not let surfaces drift into clouds. Broad environment/reflection coefficients approximate the fixed kitchen lighting. These Gaussians do not reproduce full physically accurate specular reflection under arbitrary new illumination.
8. Check raw-world support heights, counter footprints, walls and object intersections, then compare calibrated and additional camera views. A numeric placement pass does not prove visual photorealism.
9. Publish only the reviewed private checkpoint and presentation layer. Preserve the shared scene/build scripts, prior editor and user camera.

## Physics and visuals are separate

```text
Navigation action → sensorless Habitat/Bullet + invisible proxy/NavMesh
                              ↓ calibrated 6-DOF camera pose
                         gsplat CUDA renderer
                              ↓
                         RGB + depth + alpha
```

Habitat creates no visual sensors or renderer in this demo. Navigation uses the collision proxy, while a separate CUDA process produces the pixels. The raw MP3D coordinates are Z-up metres; Habitat/glTF use Y-up. The camera bridge converts these frames explicitly and converts the camera's OpenGL axes for the rasterizer.

The depth download is **opacity-weighted expected optical-axis Z depth in metres**. Pixels with alpha below 0.5 are invalid and saved as NaN. Each download includes the validity mask, alpha, intrinsics, pose and frame identifier. It is not an independently measured depth map, nor a guaranteed first surface hit through glass or overlapping splats.

The production startup checked NavMesh loading and a blocked counter/wall movement probe. It measured about 36,835 navigation queries/s on this run. One checked production raster kernel took about 12.1 ms. These are different benchmarks: neither proves 1,000 full RGB-D frames/s. Image conversion, transport and the browser add latency. This static prototype does not synchronise moved objects or articulated doors with the visual checkpoint.

## Internet models and attribution

Free model searches and four downloaded candidate archives are saved in `evidence/` and `source/`. The untextured OFFICE TELEPHONE scan, Medieval Jugs pack, alternative knife holder and alternative coffee grinder were inspected but rejected as closer final replacements. They were **not** silently installed in the kitchen. Their appearance/design did not match well enough. No paid asset was purchased or restricted model viewer extracted.

The phone retains the existing [Desk Phone01 01 by dangkhoa208](https://sketchfab.com/3d-models/desk-phone01-01-0821bac7ef4e4be9a2b26664ffc16213). The selected [Toaster by AtTheSpeedOf](https://sketchfab.com/3d-models/toaster-0d39352a32404ce7b71b8ac020844949) remains the approved substitute; its Hamilton Beach branding differs from the photographed Black & Decker. Original product credits remain in each relevant fit file and in `evidence/published_fits.json`. Archived licensed candidates were obtained individually from the [Sketchfab backup project](https://github.com/traines-source/sketchfab-backup); archive license files and download hashes are retained.

Multiple advertising pictures can guide shape and finish, but different lighting, reflection, cropping and absent camera calibration prevent automatic, guaranteed clean 3D reconstruction. This update uses licensed geometry and calibrated kitchen photos rather than claiming arbitrary web pictures were successfully stitched into exact CAD.

## Files on ISL

Paths below are relative to `/data/robotics/toshith/rxr_author/refined/`.

| Path | Purpose |
| --- | --- |
| `kitchen_all_upgrade/test.glb` | Private complete repaired mesh stage, raw MP3D Z-up export for Habitat |
| `kitchen_all_upgrade/test_pbr.glb` | Private complete stage with restored material parameters |
| `kitchen_all_upgrade/manifest.json` | Private scene composition; shared manifests are untouched |
| `kitchen/objects/*_v3/fit.json`, `phone_v4/fit.json`, `blue_jug_v4/fit.json` | Individual geometry, support, deletion footprint and credit records |
| `kitchen_all_upgrade/scene_refined.npz` | Reviewed 4,378,360-Gaussian visual checkpoint |
| `kitchen_all_upgrade/scene_refined.ply` | Gaussian parameters in PLY format, not a conventional triangle mesh |
| `kitchen_all_upgrade/surface_samples.npz` | Original sampled surfaces, normals and part membership used during construction; subsequent patch ordering is documented by the repair scripts |
| `kitchen_all_upgrade/*_stone.png`, `*_tile.png` | Photo-derived surface atlases |
| `kitchen_all_upgrade/masks/` | Cached foreground masks for the actual source photographs |
| `kitchen_all_upgrade/previews/` | Calibrated and additional-view renders, triptychs and paired depth artifacts |
| `kitchen_all_upgrade/all_dashboard.py` | Presentation/gallery/model viewer on remote 8774 |
| `kitchen_all_upgrade/physics_all_server.py` | Separate physics and camera process on remote 8778 |
| `kitchen_all_upgrade/visual_all_server.py` | Separate CUDA renderer on remote 8779 |
| `kitchen_all_upgrade/launch_dashboards.py` | Starts missing private services; `--activate` publishes a reviewed candidate |
| `split_visuals/proxy.glb`, `proxy.navmesh` | Invisible static navigation geometry |
| `split_visuals/scene_before_all_kitchen.npz`, `.ply` | Pre-publication visual backups |
| `split_visuals/resume_pose.json` | Saved live camera for process replacement/restart |
| `toaster_selected/` | Previous private mesh/editor, preserved |
| `agentA_resume/` | Earlier all-object private build and mesh comparisons, preserved |

The source photos are under `/home/guest-isl/rishabh/custom/habitat_building_isaac_repaired/source/photos/2azQ1b91cZZ/`. Camera parameters are in its `undistorted_camera_parameters/` subdirectory. Cached scan depth is `refined/kitchen/depth_v8/`.

## Files in this local folder

- `open_dashboard.sh`: local launcher; starts missing private services and forwards the two visible dashboard ports.
- `images/`: real-photo comparison panels and additional views.
- `images/browser/`: actual Chrome screenshots of the live page, gallery and model viewers.
- `source/`: four licensed candidate model archives, extracted assets, metadata and license files.
- `evidence/`: copied repair scripts, search results, masks/photo-fit summaries, original and final audits, complete fit records, publication record and browser/depth verification.
- `evidence/fit_paths.txt`: exact final fit paths, one per line.
- `evidence/final_replacements.json`: final mapping from prior object names to the current private replacements.

The large final stage and Gaussian checkpoints stay on ISL. Local images and reports open without SSH. This directory also keeps intermediate scripts for reproducibility; do not rerun patch scripts on an already patched stage, or apply old part-index offsets to a reordered checkpoint. Use the reviewed final checkpoint for deployment.

## Verification and remaining realism limits

The final **private** audit reports 33 objects and zero issues: 32 props plus the rangetop. Counter support, wall and pairwise intersection checks were unchanged. Two generic size thresholds were reviewed explicitly: the miniature creamer uses a 4 cm minimum span, and the desk phone including handset/cord uses a 35 cm maximum span. The original phone-size warning is retained in `audit_before_phone_size_review.log`; both exceptions are documented in `audit_size_exceptions.json`. This result should not be described as an unmodified generic audit pass.

The calibrated previews cover 23 labelled item groups. Five wide views inspect the sink run, jug/caddy corner, telephone counter, prep counter and island. Chrome loaded every gallery image and both phone/jug model viewers, with no recorded JavaScript exceptions. The live RGB and depth images were 800 × 640; the downloaded depth had matching pose/intrinsics and finite values at valid pixels. About 99.0% of depth pixels were valid at the saved production camera. The prior editor remained reachable.

Remaining issues include sparse frog geometry, a generic creamer mouth/handle, approximate phone silhouette and cord, simplified knife handles, photo contamination at some occluded intersections, invented hidden stone/tile detail, and original scan distortion outside the repaired surfaces. The prep-counter “previous” images can be black because that earlier checkpoint covered only the toaster-side corner. The new kitchen includes those counters but still has gaps in untouched background regions. Gaussian metallic appearance uses fixed kitchen lighting; studio model previews do not guarantee equivalent reflections in the live Gaussian view.

## Final prop outputs

All listed meshes were included in the physical-placement audit. The 23 labelled groups also have calibrated Gaussian comparisons. Small ancillary items without a dedicated photo box are shown in wider views/model previews, not claimed as independent close-up photo verifications. Paths in this table are relative to `refined/kitchen/objects/`.

| Prop | Fit file | Support height / note |
| --- | --- | --- |
| `faucet_main_style_v3` | `faucet_main_style_v3/fit.json` | 0.929 m; flange embeds by less than 3 mm |
| `hot_tap_s4_style_v3` | `hot_tap_s4_style_v3/fit.json` | 0.929 m |
| `soap_pump_p_lathe_v3` | `soap_pump_p_lathe_v3/fit.json` | 0.929 m; flange embeds by less than 3 mm |
| `air_gap_p_lathe_v3` | `air_gap_p_lathe_v3/fit.json` | 0.929 m; flange embeds by less than 3 mm |
| `button_p_lathe_v3` | `button_p_lathe_v3/fit.json` | 0.929 m; flange embeds by less than 3 mm |
| `soap_dish_p_v3` | `soap_dish_p_v3/fit.json` | 0.929 m |
| `bottles_v30` | `bottles_v30/fit.json` | 0.929 m |
| `bottles_v31` | `bottles_v31/fit.json` | 0.929 m |
| `bottles_v32` | `bottles_v32/fit.json` | 0.929 m |
| `bottles_v33` | `bottles_v33/fit.json` | 0.929 m |
| `canister_l_v3` | `canister_l_v3/fit.json` | 0.929 m |
| `canister_r_v3` | `canister_r_v3/fit.json` | 0.929 m |
| `coffee_machine2_v3` | `coffee_machine2_v3/fit.json` | 0.935 m |
| `frother_v3` | `frother_v3/fit.json` | 0.935 m |
| `glass_kettle_v3` | `glass_kettle_v3/fit.json` | 0.935 m |
| `knife_block_round_v3` | `knife_block_round_v3/fit.json` | 0.929 m |
| `prep_faucet_v3` | `prep_faucet_v3/fit.json` | 0.935 m |
| `prep_soap_v3` | `prep_soap_v3/fit.json` | 0.935 m |
| `range_kettle_v3` | `range_kettle_v3/fit.json` | 0.991 m |
| `soap_bottle_v3` | `soap_bottle_v3/fit.json` | 0.929 m |
| `tea_tray_v3` | `tea_tray_v3/fit.json` | 0.935 m |
| `toaster_v4` | `toaster_v4/fit.json` | 0.929 m |
| `phone_dock_v3` | `phone_dock_v3/fit.json` | 1.112 m |
| `tv_remote_v3` | `tv_remote_v3/fit.json` | 1.112 m |
| `bread_basket_v3` | `bread_basket_v3/fit.json` | 0.935 m |
| `phone_v4` | `phone_v4/fit.json` | 0.929 m; footprint size exception |
| `grinder_v3` | `grinder_v3/fit.json` | 0.929 m |
| `blue_jug_v4` | `blue_jug_v4/fit.json` | 0.929 m; miniature size exception |
| `paper_towel_v3` | `paper_towel_v3/fit.json` | 0.929 m |
| `caddy_v3` | `caddy_v3/fit.json` | 0.929 m |
| `knife_block_v3` | `knife_block_v3/fit.json` | 0.929 m |
| `frogs_v3` | `frogs_v3/fit.json` | 0.929 m; proxy audited, sparse visual approximate |
