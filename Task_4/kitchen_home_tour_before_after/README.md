# Before and after inside the home tour

The home-tour room now supports three versions through **Room version**:

1. **After — repaired + 3D models:** the current saved room with downloaded and
   photo-built meshes, including original toaster PBR textures.
2. **Before — earlier saved mesh:** the earliest available room export before
   the current replacement-model nodes.
3. **Before / After — side by side:** both meshes rendered with one shared camera.

Changing version preserves the current camera position, orientation and walking
frame. Walking and item inspection use the same controls in all three modes.
Split view draws the earlier mesh on the left and the repaired mesh on the right,
using the same perspective camera. It is a live 3D scene comparison, not a pair
of fixed panoramic photographs. A camera can turn in any direction, and the
existing walking service supplies movement.

## Open on the laptop

- Compare while walking: http://localhost:8767/home-tour?version=compare
- Compare around the toaster: http://localhost:8767/kitchen-room?object=toaster&version=compare
- Existing room: http://localhost:8767/kitchen-room

Refresh existing room tabs to load the added version selector. The earlier mesh
loads on first selection and is cached in that tab for subsequent switches.

## Baseline and fidelity

Before reads
`/data/robotics/toshith/rxr_author/refined/2azQ1b91cZZ_v1_unpatched.glb`.
That file has 9,012 nodes, no current `Kitchen_` replacement nodes, and aligned
raw Matterport Z-up coordinates. It is a Blender-exported early room, **not a
verified untouched original Matterport dataset mesh**. The historical original
mesh location was unavailable. Its provenance and SHA-256 are recorded in
`evidence/baseline.json` on the server.

Loading both full-resolution rooms exhausted the verification browser's memory.
The browser-only `before_browser.glb` therefore limits earlier photographic
atlases to 1024 pixels on their longest edge. The before geometry, scene nodes,
accessors, UVs and non-image buffer bytes are unchanged; the preparation script
checks this. Before may look softer because of this texture reduction. The
current repaired GLB and its PBR maps are unchanged. No models are added to the
before scene.

The original photographic 360° comparison remains separately available at
http://localhost:8769/. It uses real dataset skyboxes and is a different baseline
representation from this saved-mesh comparison.

## Files

All new server artifacts are under
`/data/robotics/toshith/vivekananda/kitchen_home_tour_before_after`.

- `prepare_before.py`: creates the memory-conscious earlier-mesh derivative and
  verifies geometry preservation.
- `before_browser.glb`: earlier-room browser derivative, generated on the server.
- `web/home-tour.html` and `web/home-tour.js`: reviewed scene selector and split
  rendering implementation.
- `products_dashboard.py`: workspace wrapper adding `/before-home-scene.glb` and
  `/before-scene-info`; existing repair, model, comparison and navigation routes
  are retained.
- `evidence/`: baseline provenance, preparation report, actual browser captures
  and verification.
- `backup/`: previous workspace dashboard files saved before publication.

The published files are in the existing personal
`../kitchen_repair_20261011` workspace. Only the positively identified personal
presentation process is restarted for publication. Navigation and Gaussian
services are not restarted. No shared reference scripts, manifests or GLBs are
modified.

## Verify or reproduce

Run `prepare_before.py` with the server's
`/data/robotics/toshith/envs/kitchen3d/bin/python`, with
`PYTHONDONTWRITEBYTECODE=1`. Preview on server port 8791 with
`KITCHEN_TOUR_WEB` pointing to this folder's `web` and `KITCHEN_DASH_PORT=8791`.
The local preview tunnel uses port 8771. `verify_tour.py` uses the dedicated local
Chrome CDP endpoint on port 9240 and records actual browser screenshots; it sends
no navigation actions. Review the captures before publishing.
