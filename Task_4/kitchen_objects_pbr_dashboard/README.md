# Kitchen objects: direct mesh comparisons and home tour

The dashboard at [http://localhost:8767/](http://localhost:8767/) has one selection per fitted kitchen item. Compare the real photo with a render of the mesh at the same calibrated camera, then click **Show in the kitchen** to inspect that object in its room position. Drag to orbit, scroll to zoom, and select **Walk through home** to navigate with W/S and A/D. Selecting another item reuses the loaded scene. There are 22 selections; the four small bottles form one selection.

This extends the toaster workflow to the already repaired jug, telephone, jars, soap items, bottles, towel, caddy, knife blocks, grinder, kettle, fittings, frogs and preparation-counter objects. It does not mean that every object is a newly downloaded commercial product. Five selections use licensed product substitutes; the others use the existing photo-built fitted geometry with metallic, ceramic, wood or plastic material settings. Their shape limitations appear on each comparison page.

## What changed in this continuation

- Replaced the stale blue-jug part in the full scene with `blue_jug_v4/world_pbr.glb`. Its height is 5.1 cm and its bottom sits at the sink counter height.
- Replaced the older telephone's 11 parts with the latest `phone_v4/world_pbr.glb`: 22 parts including photo-derived controls, height 9.9 cm. Preserved the asset's material maps.
- Created new private fits for the hot tap, sink soap pump and air gap, raising their mounting bottoms by 0.46, 2.79 and 2.96 mm respectively to the final 0.929 m slab. Existing v3 assets remain available.
- Added calibrated photo comparisons, source/credit notes, individual model inspection links and an in-room inspection camera for all 22 selections.
- Preserved photographed countertop texture colours in the browser rather than adding lighting a second time. Separate shadow overlays provide object contact shadows. The object meshes retain their PBR materials, including all three original toaster texture maps and its 11 parts.

The countertop treatment is a browser rendering adjustment. The downloaded full GLB still contains its standard countertop materials, so a different viewer's lighting can change their appearance.

## Where to view it

- [Comparison first, then in-room view](http://localhost:8767/)
- [Blue jug comparison](http://localhost:8767/?object=blue_jug)
- [Telephone comparison](http://localhost:8767/?object=phone)
- [Full home tour](http://localhost:8767/home-tour)
- [All individual models](http://localhost:8767/models)
- [Earlier Gaussian dashboard](http://localhost:8767/gaussian)

If the dashboard is offline, run this from the local repository root:

```bash
bash Task_4/kitchen_all_objects_upgrade/open_dashboard.sh
```

The launcher starts the private presentation server and persistent SSH forwarding through a user service on this machine. The service restarts the tunnel on connection failure and survives a cancelled chat turn. Its unit name is saved in `Task_4/toaster_home_tour/evidence/active_tunnel_service.txt`. Initial scene download is about 292 MB; changing objects afterward does not download the scene again.

## Which representation is being shown?

**Current mesh** means real triangle geometry rendered directly in Three.js. Metallic parts use PBR materials and environment lighting; no conversion to Gaussian splats happens in this dashboard. Photographic room/background textures retain their captured illumination. A studio environment is an approximation to kitchen illumination, so reflections will differ from the reference photo.

**Earlier Gaussian comparison** is an archived comparison from the Gaussian workflow. It is not the original untouched dataset for every object, nor necessarily a conversion of every repaired mesh. The older photo-trained appearance can be more faithful than an approximate replacement mesh, particularly for the frogs and soap bottle. The fitted meshes still show visible approximation errors; the blue jug silhouette, glass kettle faceting/transmission, utensil profiles and wall/counter texture seams need further refinement. These panels remain available for assessing that tradeoff. This continuation does not alter the Gaussian checkpoint or RGB-D renderer.

Habitat continues to supply the walking camera pose and existing navigation through its separate physics service. The browser uses that pose to render the mesh scene. Existing navigation proxies/NavMesh were not rebuilt here, and there is no new physics speed or RGB-D accuracy benchmark.

## Objects and sources

Fit paths below are relative to `/data/robotics/toshith/rxr_author/refined/kitchen/objects/` on isl-server. Source links and available licence credits are in `evidence/catalog.json` and the live item pages.

| Item | Method | Fit paths | Realism limits |
| --- | --- | --- | --- |
| Toaster | downloaded product, fitted and adapted — toaster | toaster_v4/fit.json | Hamilton Beach substitute for the Black & Decker in the photograph. Original three PBR texture maps are preserved. |
| Blue jug / miniature creamer | photo-built fitted mesh | blue_jug_v4/fit.json | Photo-built miniature creamer, about 5.1 cm tall. Glazed finish; its handle, lip and unseen surfaces remain approximate. |
| Telephone | downloaded product, fitted and adapted — Desk Phone01 01 | phone_v4/fit.json | Downloaded desk-phone substitute with photo-fitted controls. Its handset and housing differ from the photographed telephone. |
| Left canister | photo-built fitted mesh | canister_l_v3/fit.json | Photo-built ceramic jar. Lid hardware and the printed motif remain approximate. |
| Right canister | photo-built fitted mesh | canister_r_v3/fit.json | Photo-built ceramic jar. Lid hardware and the printed motif remain approximate. |
| Soap Bottle | photo-built fitted mesh | soap_bottle_v3/fit.json | Photo-built foam-pump bottle. Pump shape, translucency and label remain approximate. |
| Soap Dish | photo-built fitted mesh | soap_dish_p_v3/fit.json | Resized dish and soap to fit the narrow space behind the sink; smaller than the photographed dish. |
| Bottles | photo-built fitted mesh | bottles_v30/fit.json<br>bottles_v31/fit.json<br>bottles_v32/fit.json<br>bottles_v33/fit.json | Four photo-traced bottles with photo-derived labels. Glass and unseen label details remain approximate. |
| Paper Towel | photo-built fitted mesh | paper_towel_v3/fit.json | Photo-built holder and roll. Paper seams and fine paper texture are not reconstructed. |
| Wooden caddy | photo-built fitted mesh | caddy_v3/fit.json | Photo-built caddy with photo-derived decoration. Slats, joinery and partly hidden contents remain approximate. |
| Knife Block | photo-built fitted mesh | knife_block_v3/fit.json | Photo-built wooden block and utensils. Handle shapes and wood details remain approximate. |
| Knife Block Round | photo-built fitted mesh | knife_block_round_v3/fit.json | Photo-built block and handles. Exact knife profiles remain approximate. |
| Grinder | photo-built fitted mesh | grinder_v3/fit.json | Photo-built dark-wood grinder with separate metal parts. Its exact mechanism and wood grain remain approximate. |
| Stovetop kettle | downloaded product, fitted and adapted — 2-Quart Circles Teakettle | range_kettle_v3/fit.json | Licensed teakettle substitute with steel and plastic parts. It stands on the grates at 0.991 m. |
| Hot Tap | downloaded product, fitted and adapted — Misturador Monocomando St. Claire - B02003BW | hot_tap_s4_style_v4/fit.json | Licensed style-matched faucet substitute. Its curved spout differs from the photographed tap. |
| Sink soap pump | photo-built fitted mesh | soap_pump_p_lathe_v4/fit.json | Photo-traced and fitted pump with a metallic finish; unseen details remain approximate. |
| Sink air gap | photo-built fitted mesh | air_gap_p_lathe_v4/fit.json | Photo-traced fitted shape with metallic finish. |
| Frog statues | photo-built fitted mesh | frogs_v3/fit.json | Approximate proxy sculptures. The mesh is less faithful than parts of the earlier photo-trained Gaussian view. |
| Tea Tray | photo-built fitted mesh | tea_tray_v3/fit.json | Photo-built tray and accessories; exact decorative details remain approximate. |
| Glass Kettle | photo-built fitted mesh | glass_kettle_v3/fit.json | Photo-built glass kettle. Transmission, liquid and internal reflections remain approximate. |
| Frother | photo-built fitted mesh | frother_v3/fit.json | Photo-built frother with separate material regions; brand details remain approximate. |
| Coffee Machine | downloaded product, fitted and adapted — Nespresso Coffee Machine | coffee_machine2_v3/fit.json | Licensed Nespresso substitute fitted to the photo. Exact brand/model details and controls differ. |

The coffee-can crop is excluded: the current scene has the fitted frother at that crop, so displaying it as a repaired coffee can would be misleading. No coffee-can replacement is claimed. Frog sculptures, glass transmission, the foam pump and exact brand/control details need further work; a clean mesh is not automatically a faithful or photorealistic reconstruction.

## Validation and placement

`evidence/items_audit.log` records the private audit: **33 fitted props, 0 reported placement issues**. The audit uses tolerances and sampled intersections; this does not prove that every surface or texture is correct. The main faucet and button still have approximately 3 mm mounting inset accepted by that audit.

The browser review also checks actual rendered bounds for all 22 selected meshes against their support heights: sink/range counters 0.929 m, cooktop grates 0.991 m, preparation counter 0.935 m. It checks the latest jug height, 22 telephone parts and 11 toaster parts with the original colour, normal, and metallic/roughness maps. Eight calibrated photo cameras are rendered and each object's in-room inspection view is captured. See `evidence/scene_browser_review.json` for results and `images/all_items_review.jpg` for the visual contact sheet. `evidence/dashboard_browser_review.json` records all comparison images and all 22 item changes inside the loaded room, including two-way selection syncing. Published routes, model downloads and comparison images are checked separately in `evidence/published_http_verification.json`.

## Server directory and private outputs

All paths in this section are on `guest-isl@172.26.186.222`.

| Path under `/data/robotics/toshith/rxr_author/refined/` | Purpose |
| --- | --- |
| `kitchen/objects/<name>/fit.json` | Fitted mesh reference, world mesh, placement, deletion region and available product credit. |
| `kitchen_all_upgrade/published_fits.json` | Prior selected fits, used to find the latest individual object assets. |
| `kitchen_all_upgrade/test_pbr.glb` | Earlier full repaired kitchen with PBR objects; left available. |
| `toaster_home_tour/home_pbr.glb` | Earlier browser scene; kept for rollback. |
| `toaster_home_tour/home_pbr_items.glb` | New private full-home scene used by the expanded tour, with updated jug/telephone and sink mounting heights. |
| `toaster_home_tour/items_manifest.json` | Private fit list with new mount fits, used for the audit. Shared manifests are untouched. |
| `toaster_home_tour/latest_mesh_refresh.json` | Asset hashes, removed/inserted part counts and provenance for jug/telephone. |
| `toaster_home_tour/mount_fit_updates.json` | New mounting fits, source fit paths and exact height shifts. |
| `toaster_home_tour/comparison/items/` | Calibrated catalogue, real photos and render comparison JPEGs. |
| `toaster_home_tour/web_items/` | Expanded comparison page and direct mesh home-tour frontend. |
| `toaster_home_tour/items_dashboard.py` | Private presentation wrapper on remote port 8774, forwarded to local 8767. Preserves older dashboard routes. |
| `toaster_home_tour/launch_home_tour.py` | Owned-process launcher; preserves running physics/Gaussian services and saved camera state. |
| `toaster_home_tour/publication.json` | Published revision, private scene and before/after saved navigation state. |
| `kitchen_all_upgrade/physics_all_server.py` | Existing Habitat navigation service, remote port 8778. |
| `kitchen_all_upgrade/visual_all_server.py` | Existing Gaussian visual service, remote port 8779. |

The new mounting fit replacements in the private manifest are:

- `hot_tap_s4_style_v3/fit.json` → `hot_tap_s4_style_v4/fit.json`
- `soap_pump_p_lathe_v3/fit.json` → `soap_pump_p_lathe_v4/fit.json`
- `air_gap_p_lathe_v3/fit.json` → `air_gap_p_lathe_v4/fit.json`

Jug/phone sources are `blue_jug_v4/fit.json` and `phone_v4/fit.json`; those latest fits were already selected in the prior published list, but their geometry was stale in the full browser scene. This continuation refreshes that geometry. No shared kitchen manifests, shared builds, shared scripts or original photos are overwritten.

## This local folder

- `web/`: exact frontend sources deployed to the private wrapper.
- `evidence/`: private merge/placement/catalog scripts, browser checks, manifest and audit evidence.
- `images/real_photos/`: original calibrated photos copied for review.
- `images/assets/`: cropped photo/mesh comparison JPEGs and scene views used by the dashboard.
- `images/room_*.png`: actual browser captures of the inspection cameras.
- `images/photo_*.png`: actual mesh renders at calibrated real-photo cameras.
- `images/all_items_review.jpg`: a contact sheet assembled by cropping/resizing actual photographs and renders, with no generated or retouched evidence pixels.

The merge and mount scripts are one-off provenance scripts. Do not rerun them on the already corrected scene: the mount script protects existing output folders. The user-facing launcher can be rerun safely.
