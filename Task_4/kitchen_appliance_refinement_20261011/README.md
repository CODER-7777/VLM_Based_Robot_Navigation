# Kitchen glaze and appliance repairs — 11 October 2026

The white tea set was an export bug. The earlier Blender builder connected a
Geometry Position node to a colour ramp, then connected that ramp to the glaze
base colour. Its GLB contained neither a base-colour image nor vertex colours.
The exported `Photo_reactive_ceramic_glaze` material also had no colour factor,
so the browser correctly used glTF's default white. The earlier coffee-machine
side material similarly lost its procedural wave/rib shader.

These are direct polygon/PBR room renders. Gaussian splatting is a separate
experimental dashboard and did not cause this particular problem.

## Repairs

| Object | Geometry and finish | Remaining limits |
| --- | --- | --- |
| Tea setting | Retained licensed teapot; embedded turquoise/brown reactive-glaze colour and roughness maps; smooth, smaller sugar jar; glossy white tray retained | Different teapot silhouette and approximate decorative glaze pattern |
| Frother | Retained licensed ribbed body; smooth chrome collar normals; photo-shaped shallow clear lid, rounded gasket and dark interior | Exact rim, logo and cord details differ; partly occluded by the kettle in the calibrated view |
| Coffee machine | Photo-shaped smooth semicylindrical black housing, bevelled ribbed metal panels, oval capsule bin/cup platform and smooth chrome lever; retained licensed dispensing fitting | Exact product identity, hidden reservoir and controls remain approximate; foreground bar occludes lower parts in one reference camera |

The coffee model's prior source label was incorrect. The actual imported model
was **Cafetera Nespresso Japan by furiadesignerone**, rather than the separately
listed low-poly Nespresso model by ekorneeff. The new fit records credit the
actual retained fitting. Public model previews and licence/API metadata are
saved in `evidence/model_search.json`. Additional Pixie previews were not
downloadable; a free Aeroccino download required authenticated access. No gated
viewer assets were extracted, and no purchased model was used.

The glaze and brushed-metal maps describe material colour, roughness and relief;
they do not bake studio reflections into the surfaces. Lighting remains dynamic
in the PBR room. Dense curved surfaces and smooth normals are used where they
improve shape; subdividing an incorrect silhouette alone does not repair it.

Blender's supported glTF material/export workflow is documented in the
[official glTF manual](https://docs.blender.org/manual/en/3.4/addons/import_export/scene_gltf2.html).

## Artifacts and verification

New server files stay under
`/data/robotics/toshith/vivekananda/kitchen_appliance_refinement_20261011`.

- `objects/tea_tray_v7`, `frother_v7`, `coffee_machine2_v7`: fitted GLB, world-space
  PLY and fit JSON, with source credits and union deletion footprints.
- `textures/`: embedded glaze and metal maps, also saved separately for inspection.
- `home_pbr_products.glb`: private merged room; existing toaster parts and all
  three original texture maps preserved.
- `private_manifest.json`: 40 reconciled active entries. Shared manifests remain
  untouched.
- `web/`, `products_dashboard.py`: personal comparison, model and home-tour pages.
- `evidence/placement_audit.json`: support footprints against actual counter
  surfaces and conservative pairwise overlap screening, across 33 props.
- `evidence/artifact_verification.json`: geometry, buffer and texture-preservation
  checks for the saved scene hash.
- `evidence/browser_review.json`, `evidence/browser/`: actual Three.js camera
  captures and exported-material checks. Earlier rejected visual tests are
  archived locally in the first/second/third review directories.
- `scripts/build_finishes.py`, `prepare_candidate.py`, `verify_browser.py`: local
  source copies; the server builder/preparer also live at the project root.

Counter contact is at **z = 0.935 m** for these three prep-counter objects. The
tea tray's previous 3.98 mm sinking was corrected. This is a different support
surface from the sink-wall counter at 0.929 m. Placement screening is not a
watertight collision proof. Existing scan gaps and photo-texture ghosts remain
outside these object repairs.

## Dashboard

Published revision: **kitchen_workspace_v7_20261011**. Scene SHA-256:
`5ed7766ed49259522106e6ecd47866fde111ad38a98c2e18580127ec5da48a04`.
Actual browser checks cover 23 photographic views and 30 model routes; placement
screening covers 33 props with zero flags. Navigation state was preserved during
publication; navigation and Gaussian processes were not restarted.

- Photo comparison: http://localhost:8767/?object=tea_tray
- Tea set in the actual room: http://localhost:8767/kitchen-room?object=tea_tray
- Coffee machine: http://localhost:8767/kitchen-room?object=coffee_machine
- Frother: http://localhost:8767/kitchen-room?object=frother
- Model inspection: http://localhost:8767/models
- Existing before/after home tour: http://localhost:8767/home-tour?version=compare
- Updated five-position photographic 360° comparison: http://localhost:8769/

The 360° dashboard now uses this same v7 scene hash, with 30 browser-rendered
cube faces assembled into five 4096 × 2048 panoramas. Its original-photo before
views are retained. Panorama source and publication records are in the server
project's `panoramas/` folder; local review images are in `evidence/panoramas/`.

Refresh an already-open room tab after publication to load the new GLB. Room
version switching retains the same camera. The before tour remains the earlier
saved mesh, not a verified untouched original dataset mesh. Navigation and
Gaussian services are retained separately.

If a tunnel is needed, run this on the laptop, leaving the terminal open:

```sh
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 \
  -L 8767:127.0.0.1:8774 -L 8769:127.0.0.1:8786 guest-isl@172.26.186.222
```

Use an existing working tunnel if port 8767 is occupied. Copying the GLB to the
laptop is unnecessary for browsing the dashboard.
