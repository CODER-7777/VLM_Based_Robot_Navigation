# Original PBR toaster inside the home tour

The live comparison-first dashboard is **http://localhost:8767/**. It first shows matched crops of the real photo and current PBR scene. Click **Show toaster in the kitchen** below the comparison to load an embedded interactive kitchen view, initially focused on the toaster. The full home tour is available at **http://localhost:8767/home-tour**. It shows the complete repaired home mesh with the downloaded toaster's original polygon geometry and PBR textures. You can walk through the kitchen and inspect the toaster on its counter.

The existing `kitchen_all_upgrade/test_pbr.glb` already contained the original 11-part toaster. This work makes that scene available in a direct WebGL home tour, adds walking and inspection controls, and preserves its original toaster materials. It does not train or replace the Gaussian checkpoint.

## Open it on your local computer

Run from the local repository, not from the SSH server terminal:

```bash
cd /home/vivekananda/UGP_1_VLM/VLM_Based_Robot_Navigation
bash Task_4/toaster_home_tour/open_dashboard.sh
```

The launcher creates missing SSH tunnels as detached background connections, so the terminal can be closed. The server presentation listens on remote port 8774 and is forwarded to local port 8767. Existing working tunnels are reused. The local tunnel PID and log are saved as `/tmp/toaster-home-tour-tunnel.pid` and `/tmp/toaster-home-tour-tunnel.log`.

| View | Local browser address | What it displays |
| --- | --- | --- |
| Current comparison | http://localhost:8767/ | Real photo versus current direct PBR scene, followed by an interactive kitchen button |
| Focused kitchen view | http://localhost:8767/kitchen-room | Starts close to the original PBR toaster on its counter |
| Full home tour | http://localhost:8767/home-tour | Full home mesh; original PBR toaster directly on the counter |
| Before/after comparisons | http://localhost:8767/comparisons | Existing photo / previous Gaussian / updated Gaussian panels |
| All repaired models | http://localhost:8767/models | Individual model viewers |
| Isolated toaster | http://localhost:8767/product-viewer?object=toaster_v4 | Original toaster with unrestricted model inspection |
| Gaussian view | http://localhost:8767/gaussian | Existing experimental Gaussian RGB-D view |
| Earlier editor | http://localhost:8767/legacy-editor | Preserved earlier route editor and its scene version |

The `/comparisons` panels and Gaussian view are earlier results. The landing page comparison uses a fresh capture from the current direct PBR renderer at the calibrated photograph camera. It is separate from those earlier Gaussian panels.

## Controls

- **W/S** moves forward/backward. **A/D** turns. Arrow keys turn or tilt the camera. Drag in walking mode turns the camera.
- **Kitchen reference view**, or **R**, returns to the calibrated toaster viewing angle.
- **Inspect toaster** moves the viewing camera close to the toaster inside the kitchen. Drag to orbit; scroll to zoom.
- Inspection stays on the room side of the counter to avoid entering the upper cabinet. The isolated-model viewer offers unrestricted model rotation.
- **Walk through home** resumes the navigation camera. Inspection moves the browser camera only; it does not rotate or move the toaster.
- **Lighting** switches between studio reflections and a photographed kitchen environment. These are approximate lighting environments, rather than a measured reconstruction of the room's light sources.

The first load transfers a roughly 288 MB full-home scene and may take about a minute or longer depending on the connection and computer. Later visits can reuse the browser's cached scene through HTTP cache revalidation.

## What model is used?

The asset is the Hamilton Beach toaster by **AtTheSpeedOf**, distributed under **CC BY 4.0**: [Sketchfab source](https://sketchfab.com/3d-models/toaster-0d39352a32404ce7b71b8ac020844949).

It is a substitute for the Black & Decker toaster visible in the reference photo. Its control layout and proportions differ from that product. Direct PBR rendering preserves the downloaded model's materials; it does not make a different product an exact reconstruction of the photographed toaster.

The 11 parts are background, brackets, buttons, dial base, dial grip, grill, legs, lever, rods, toaster body and toast slot. Their original maps are retained:

| Texture | Resolution | Verification |
| --- | --- | --- |
| Base colour | 2048 × 2048 | Exact image bytes match the standalone original |
| Normal | 2048 × 2048 | Exact image bytes match the standalone original |
| Metallic/roughness | 1024 × 1024 | Exact image bytes match the standalone original |

The minimum toaster height in the browser's Y-up coordinates is **0.92900001365 m**, corresponding to raw scene **z = 0.929 m**. Its height is 0.20 m. The original fitted position and orientation are retained.

## Rendering and navigation

The browser loads triangles and materials from the full-house GLB using Three.js. Environment lighting supplies reflections for the metallic toaster, and a local directional light supplies shadows on the counter. The untouched photographic scan materials use their baked appearance to avoid lighting them a second time.

Walking sends actions to the existing sensorless Habitat navigation service. That service uses the separate collision proxy and NavMesh, and returns the live camera pose. The browser converts the raw MP3D Z-up pose into Y-up coordinates and renders the mesh at that pose. Inspection uses a local orbit camera. The Gaussian GPU process remains a separate, available viewer.

This implementation does not establish 1,000 FPS rendered output or an 8 ms rendering budget. Frame rate depends on the client computer and scene. The surrounding scan still has reconstruction defects, especially at unfamiliar viewing angles, and several other repaired props retain approximate geometry and textures.

The renderer uses the [official GLTFLoader](https://threejs.org/docs/#examples/en/loaders/GLTFLoader) and [PMREMGenerator](https://threejs.org/docs/#api/en/renderers/PMREMGenerator), with Three.js 0.180.0 dependencies served locally on ISL. The dependency's MIT license is retained alongside those files.

## Files on ISL

Base directory: `/data/robotics/toshith/rxr_author/refined/`.

| File | Purpose |
| --- | --- |
| `kitchen/objects/toaster_v4/product_pbr.glb` | Original standalone PBR toaster |
| `kitchen/objects/toaster_v4/world_pbr.glb` | Placed standalone asset |
| `kitchen_all_upgrade/test_pbr.glb` | Existing full-home scene containing the 11-part toaster |
| `toaster_home_tour/home_pbr.glb` | Browser copy of the full scene; photographic colour images use JPEG quality 94 at their existing resolution |
| `toaster_home_tour/browser_scene.json` | Scene preparation record and preserved texture hashes |
| `toaster_home_tour/original_texture_verification.json` | Exact original-versus-in-home texture comparison |
| `toaster_home_tour/web/comparison-first.html` | Comparison-first landing page with an on-demand embedded kitchen view |
| `toaster_home_tour/comparison/` | Original reference photograph, current calibrated PBR render, matched crops and room preview |
| `toaster_home_tour/web/home-tour.html` | Home-tour and focused kitchen page |
| `toaster_home_tour/web/home-tour.js` | Direct PBR rendering, walking and orbit controls |
| `toaster_home_tour/vendor/three/` | Local Three.js modules and MIT license |
| `toaster_home_tour/home_tour_dashboard.py` | Private presentation wrapper preserving existing comparison/model/navigation routes |
| `toaster_home_tour/launch_home_tour.py` | Reusable private launcher |
| `toaster_home_tour/publication.json` | Active publication and before/after navigation pose |
| `toaster_home_tour/active.log` | Dashboard request/startup log |

All geometry buffer bytes remain unchanged in the browser copy. Original toaster images and other material data maps are retained. Recompressing photographic colour atlases reduces transfer from 408,870,232 bytes to 288,400,564 bytes; it is lossy JPEG compression for those colour images.

Shared kitchen manifests, shared scene builds and shared scripts were not modified. The private presentation on remote port 8774 was replaced. The existing physics, Gaussian process and earlier editor were preserved.

## Verification and screenshots

- Chrome loaded the complete scene without JavaScript exceptions, confirmed all 11 toaster parts and their PBR maps, and verified the 0.929 m base height.
- In-kitchen orbit changed the camera while retaining the toaster's bounds. Returning to walking resumed the navigation pose.
- Walking moved 0.20 m backward and 0.20 m forward; a left/right turn pair also worked. The final camera matrix exactly matched the starting matrix.
- The published dashboard, model list, Gaussian view and earlier editor returned HTTP 200. All 28 comparison images were verified as available JPEGs.
- Scene byte-range streaming returned HTTP 206, and unchanged-scene cache revalidation returned HTTP 304.

Evidence is in [evidence/](evidence/). Screenshots: [toaster in the kitchen](images/toaster_in_home.png), [room-side orbit](images/toaster_orbit.png), and [walking view](images/home_walk.png).

The comparison-first browser check is recorded in [evidence/comparison_room_verification.json](evidence/comparison_room_verification.json). Screenshots: [comparison first](images/comparison_first.png), then [embedded kitchen view](images/embedded_kitchen.png). The embedded kitchen uses the same complete scene and starts with the camera near the toaster; the geometry has not been cropped to a room-only file.
