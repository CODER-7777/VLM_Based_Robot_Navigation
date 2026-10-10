# Toaster realism upgrade

Latest local wall/cabinet mesh repair: [report and previews](../toaster_wall_mesh_repair/README.md).


This pass replaces only the toaster in scene `2azQ1b91cZZ`. It follows the user's instruction to use a freely available model and evaluate one object before extending the process to other kitchen items.

## Model and license

- Model: **Cuisinart Toaster**, by **siotech2011**.
- Source: https://sketchfab.com/3d-models/bc62dbead31f4a3293f4e17df6f342f7
- Objaverse UID: `bc62dbead31f4a3293f4e17df6f342f7`.
- License in the retrieved metadata: **CC BY-NC** (attribution, noncommercial use). Free download does not grant unrestricted commercial rights. Original metadata and attribution are retained in the object fit file.
- Original downloaded model remains in `refined/toaster_upgrade/candidates/` on ISL.

The user identifies the photographed reference as a **Black & Decker 2-Slice Toaster, resembling the T2030**. The earlier Cuisinart CPT-160 identification was an incorrect inference. The installed free mesh remains a Cuisinart substitute. The free model has a different lever recess and branding. It is an approximation, not an exact product reconstruction.

## What changed

The previous toaster had a flat, almost white front with little surface detail. The replacement has separately modeled feet, switches, knob, lever, lettering, case and toaster slots. Its case uses polished steel on the front/top and dark plastic on the sides/base, guided by the real photograph rather than the original white model finish.

The downloaded shell originally allowed the backsplash to show through the top. Dark internal toasting chambers and thin steel bread guides were added to close that hole and give the slots depth.

The placed size is approximately **18.3 × 27.5 × 20 cm**. Its base is at raw coordinates `(4.52, -5.19, 0.929)` metres. Its width was adjusted to keep it clear of the tall cabinet and nearby canister. Placement is measured from the actual geometry, not only its origin.

## Why metallic materials alone were insufficient

Reflective metal needs something to reflect. A metallic slider with unsuitable lighting can appear dark or flat. The current full-building renderer uses baked scene appearance, so this pass keeps two representations:

1. `world_pbr_textured.glb`: a true metallic material asset with roughness and fine brushed normal maps, intended for a renderer configured with environment lighting.
2. `world_baked.glb`: kitchen reflections baked into a texture for the existing Habitat/dashboard pipeline. This is the representation inserted into the scene.

The lighting panorama was reconstructed from 18 calibrated perspective photographs belonging to the source panorama. It is an approximate LDR environment, not a measured HDR light probe. Blender Cycles renders and bakes the metallic appearance from the principal photograph's camera. Surface colour/brightness is not flattened to a single median colour.

**Limitation:** baked reflections stay fixed when the viewer moves. The PBR version supports moving reflections when displayed under suitable environment lighting. This pass improves the existing renderer's appearance; it does not add real-time PBR lighting to the dashboard.

## Outputs on ISL

Paths below are relative to `/data/robotics/toshith/rxr_author/`:

| Output | Purpose |
|---|---|
| `refined/kitchen/objects/toaster_v3/fit.json` | Placement, deletion footprint and source credit |
| `refined/kitchen/objects/toaster_v3/world.ply` | Geometry in raw Z-up coordinates for measurement/audit |
| `refined/kitchen/objects/toaster_v3/world_baked.glb` | Dashboard-compatible toaster |
| `refined/kitchen/objects/toaster_v3/world_pbr_textured.glb` | Metallic asset with normal/roughness maps |
| `refined/kitchen/objects/toaster_v3/toaster_materials.blend` | Editable Blender materials and lighting |
| `refined/kitchen/objects/toaster_v3/kitchen_reflections.png` | Baked appearance texture |
| `refined/kitchen/objects/toaster_v3/brushed_normal.png` | Brushed normal texture |
| `refined/kitchen/objects/toaster_v3/brushed_roughness.png` | Roughness texture |
| `refined/toaster_upgrade/manifest.json` | Private manifest replacing the prior toaster entry |
| `refined/toaster_upgrade/test.glb` | Full scene with the new toaster |
| `refined/toaster_upgrade/audit.json` | Placement audit |
| `refined/toaster_upgrade/previews/` | Actual Habitat photo-camera comparisons and additional views |

The shared manifests, original v15 GLB, and previous repaired scene are preserved. The replacement deletion footprint includes the old and new toaster footprints; the build is regenerated from the private manifest rather than stacking a new toaster over the previous one.

## Verification

The placement audit checks support height, counter containment and component collisions with a 2 mm collision tolerance. It reports **32 props, zero issues**. This is a geometry check; it does not certify visual photorealism or detect ghosts baked into the room texture.

Final visual evidence is produced using Habitat, the same rendering family used by the dashboard. Compare the photograph, previous repaired scene and new scene in `images/toaster_comparison.jpg`. Additional viewing angles are in `images/toaster_novel_views.jpg`.

The object remains an approximation: its branding/control recess differs from the photo, its width is adjusted for physical clearance, and exact photo silhouette alignment is constrained by the scanned cabinet geometry. These differences should be reviewed before extending the method to other objects. Additional views also reveal existing holes and distorted triangles in the surrounding backsplash/cabinet scan. They remain visible and require a separate room-surface repair; this toaster pass does not fix them.

## Reproduction scripts

`evidence/` contains the preparation, Blender bake and Habitat preview scripts used for this pass. They refer to ISL paths and existing server environments; they are not standalone installers. The free source asset, source photographs, private build helper and simulator environment are required.

## Viewing the result

Open **http://localhost:8770/** on the development computer. The comparison appears at the top of the dashboard. Expand the additional views to inspect the toaster inside the full scene. This dashboard loads `refined/toaster_upgrade/test.glb`.

The previous repaired dashboard remains at http://localhost:8767/ with its route session preserved.

If the local SSH tunnel is no longer running, run this in a terminal on your local computer and leave it open:

```sh
ssh -N -L 8770:127.0.0.1:8770 guest-isl@172.26.186.222
```

Then open http://localhost:8770/ in your browser. This forwards the dashboard already running on ISL; it does not rebuild the scene.

## Images

![Real photograph, previous repair and new toaster](images/toaster_comparison.jpg)

![Additional Habitat viewing angles](images/toaster_novel_views.jpg)
