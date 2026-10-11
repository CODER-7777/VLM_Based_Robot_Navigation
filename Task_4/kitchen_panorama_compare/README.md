# Kitchen panoramic comparison

This viewer compares original Matterport kitchen photographs with the repaired
`2azQ1b91cZZ` kitchen at five matched camera positions. Drag either panel to rotate
both together, scroll to zoom, and select another position to reveal objects that
are hidden from the current position. Each panorama covers 360°.

## Open the dashboards on this laptop

- Panoramas: http://localhost:8769/
- Object comparisons: http://localhost:8767/
- Interactive room: http://localhost:8767/kitchen-room
- Individual 3D models: http://localhost:8767/models

The server files remain on ISL. You do **not** need to copy the entire dataset or
GLB to your laptop. SSH tunnels forward the browser requests. The current local
tunnels are managed by user systemd services and are already running. If you
reconnect after a reboot and these ports are free, run this in a laptop terminal:

```bash
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 \
  -L 8767:127.0.0.1:8774 -L 8769:127.0.0.1:8786 \
  guest-isl@172.26.186.222
```

Keep that terminal open. An “address already in use” message means a local
process already holds the selected port; inspect the existing tunnel before
starting another one. These localhost addresses work on the laptop running the
tunnels.

## What “before” and “after” mean

**Before** is the original dataset's photographic panorama, assembled from its
six supplied Matterport skybox faces without object replacement or image
retouching. The historical untouched mesh path was unavailable on the server;
this viewer therefore does not claim to display the original scanned mesh.

**After** is an actual Three.js browser capture of the published repaired polygon
mesh, with direct PBR object materials. It is not a Gaussian-splat rendering and
not an AI-generated image. Six 90° camera renders are stitched into an
equirectangular image, retaining the room viewer's lighting and geometry.

Both images are 4096 × 2048. The capture uses 1024 × 1024 cube faces and the
dataset's calibrated `i1_5` camera pose with the published Matterport skybox
rotations. Original panorama stitching can introduce small rig/parallax
differences near objects. A panorama reveals directions around one point; it
does not reveal occluded surfaces or let you move through the room. The separate
interactive room supplies model inspection and existing navigation controls.

The five positions cover sink/toaster, corner/bottles/knife blocks,
range/telephone/grinder, tea/glass kettle, and coffee/cordless telephone.
The visible scan holes and approximate product shapes are retained honestly.

## Server workspace and provenance

All new server artifacts are inside `/data/robotics/toshith/vivekananda`:

| Path relative to that directory | Contents |
| --- | --- |
| `kitchen_repair_20261011/home_pbr_products.glb` | Published v6 repaired room |
| `kitchen_repair_20261011/evidence/browser_review.json` | Browser checks and documented visual limits |
| `kitchen_repair_20261011/evidence/browser_captures/` | Actual calibrated browser frames and reviewed contact sheet |
| `kitchen_repair_20261011/evidence/opengl_panels/` | Previous current-panel verification renders, preserved before replacing them with browser captures |
| `kitchen_panorama_compare/config.json` | Camera packets, original-face hashes, source scene hash and image dimensions |
| `kitchen_panorama_compare/images/` | Original, repaired and vertically paired panorama JPEGs |
| `kitchen_panorama_compare/faces/` | Actual browser cube-face PNG captures |
| `kitchen_panorama_compare/evidence/` | Capture and interactive-viewer verification records |
| `kitchen_panorama_compare/archive/earlier_pbr_capture/` | Earlier repaired-scene panorama captures |

The v6 scene SHA-256 is
`126fbc2d2bc7b17f441e4446da4a13d1d261562bc70ed9e1d59bb029e3e41a4c`.
The capture script checks the live revision/hash against the panorama source
before recording any new after images. Original photographs and reference
scripts under `rxr_author/refined` are read-only inputs.

## Scripts and regeneration

- `panorama_server.py`: server-side skybox conversion, image assembly and viewer
  hosting on loopback port 8786. Requires the existing server kitchen3d Python.
- `capture_panoramas.py`: laptop-side capture through a dedicated Chrome CDP
  instance on port 9240. Uses the live repaired room on 8767 and uploads images
  through the panorama tunnel on 8769. It sends no navigation actions.
- `verify_v6_browser.py`: actual browser verification of the v6 private preview
  on laptop port 8770, with 30 room/model selections and 23 calibrated photos.
- `panorama.js` and `index.html`: synchronized panorama rotation, zoom and JPEG
  downloads. Shared camera orientation keeps the two views aligned.

To regenerate, confirm the desired scene revision is published, update source
provenance if it changes, archive existing derived after images, run the
workspace panorama server, then run `python3 capture_panoramas.py` on the laptop
with its dedicated Chrome and tunnels active. Inspect actual output before
reporting it as complete. Do not replace original skybox inputs.

This continuation publishes only the identified presentation dashboard. The
navigation and Gaussian services are not restarted; the publication launcher
checks navigation state before and after the switch.
