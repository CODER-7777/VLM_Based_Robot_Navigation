# Understanding the kitchen dataset and repair workflow

Latest local wall/cabinet mesh repair: [report and previews](../toaster_wall_mesh_repair/README.md).


Latest toaster-only upgrade: [free model, metallic finish, verification and previews](../toaster_realism_upgrade/README.md).


Prepared for this project on **7 October 2026**. This guide describes the files and code inspected in this workspace and on `guest-isl@172.26.186.222`. It separates the previous worker's handoff, the continuation repairs, and the later dashboard update.

The project repairs the kitchen in building **`2azQ1b91cZZ`**, a Matterport3D scene used by the RxR navigation task. We compare its scanned 3D objects against original photographs, replace damaged or unrecognizable objects, correct their appearance and placement, and export a revised scene that Habitat can display.

**The current repaired scene is on ISL at:**

```text
/data/robotics/toshith/rxr_author/refined/agentA_resume/test.glb
```

The local file `Task_4/scenes/v15/2azQ1b91cZZ.glb` is an **earlier snapshot**. Updating the dashboard did not update that local GLB automatically.

## Contents

1. [What dataset are we using?](#1-what-dataset-are-we-using)
2. [What your previous prompt asked for](#2-what-your-previous-prompt-asked-for)
3. [What is being edited](#3-what-is-being-edited)
4. [How we identify a problem and choose a repair](#4-how-we-identify-a-problem-and-choose-a-repair)
5. [How a photograph is matched to the 3D scene](#5-how-a-photograph-is-matched-to-the-3d-scene)
6. [How replacement objects are made](#6-how-replacement-objects-are-made)
7. [How old scan geometry is removed](#7-how-old-scan-geometry-is-removed)
8. [How color, labels, and metal finishes are repaired](#8-how-color-labels-and-metal-finishes-are-repaired)
9. [How wall and counter texture patches work](#9-how-wall-and-counter-texture-patches-work)
10. [How placement and realism are verified](#10-how-placement-and-realism-are-verified)
11. [What changed for each kitchen object](#11-what-changed-for-each-kitchen-object)
12. [Local directory guide](#12-local-directory-guide)
13. [ISL directory guide](#13-isl-directory-guide)
14. [Files inside one object folder](#14-files-inside-one-object-folder)
15. [Script guide](#15-script-guide)
16. [How the scene is built and reaches the dashboard](#16-how-the-scene-is-built-and-reaches-the-dashboard)
17. [What is complete and what remains](#17-what-is-complete-and-what-remains)
18. [How to inspect the results yourself](#18-how-to-inspect-the-results-yourself)
19. [Terms and references](#19-terms-and-references)

For an observed file listing, see [DIRECTORY_INVENTORY.md](DIRECTORY_INVENTORY.md). For the detailed object report, see [evidence/repair_report.md](evidence/repair_report.md).

## 1. What dataset are we using?

There are several layers. They serve different purposes.

| Layer | What it provides | Example in this project |
|---|---|---|
| Matterport3D | Photographs, depth, camera calibration, and reconstructed indoor buildings | Building `2azQ1b91cZZ` and its kitchen |
| RxR, or Room-Across-Room | Language instructions and demonstrations for navigating those buildings | An instruction describing a route past the kitchen, chairs, couch, and windows |
| RxR in continuous environments | Navigation episodes adapted for movement through reconstructed scenes | `RxR_VLNCE_v0/val_unseen/val_unseen_guide.json.gz` |
| Habitat / Habitat-Sim | Loads the building, renders camera observations, and handles navigation | The first-person dashboard image and movement controls |
| Our repair files | Replacement meshes, appearance corrections, deletion regions, and validation | `refined/kitchen/objects/*/fit.json` |
| Route-author dashboard | Lets a person explore and author routes or obstacle cases | `author_pov_route.py` and the repaired-scene wrapper |

### 1.1 Matterport3D: the building and its photographs

Matterport3D is a research dataset of scanned indoor buildings. The original release contains 90 building-scale scenes, 10,800 panoramic views, and 194,400 RGB-D images. RGB means color; depth describes distance from the camera. The dataset also includes reconstructed surfaces and camera information. These are the visual and geometric foundations of our kitchen work. [Official Matterport3D project](https://niessner.github.io/Matterport/)

The building ID is a dataset identifier. `2azQ1b91cZZ` names the entire building, not one toaster, one episode, or one kitchen image.

The inspected photo directory for this building contains 3,870 undistorted color-image files, 1,290 skybox-image files, one camera-parameter file, and 48 undistorted depth-image files. These are counts in **this installed directory**, not a claim that every original depth image has been downloaded.

### 1.2 RxR: language linked to movement

RxR is a vision-and-language navigation dataset in Matterport3D environments. It includes instructions in English, Hindi, and Telugu, together with guide/follower annotations and pose traces. A guide describes a route; a follower attempts to follow it. These records connect words such as “kitchen,” “couch,” and “window” to visual observations along a path. [Official RxR repository](https://github.com/google-research-datasets/RxR)

Our dashboard uses an RxR guide-episode file. “Guide” identifies the annotation type; “val_unseen” identifies a validation split with environments held out from training. It does not mean that our kitchen repair has already been evaluated as a navigation benchmark result.

### 1.3 What continuous environments means

Graph-based navigation moves between predefined viewpoints. Continuous-environment navigation instead moves an agent through reconstructed 3D space, subject to movement and collision rules. VLN-CE supplies this setting using Habitat; RxR was also ported to it. [Official VLN-CE repository](https://github.com/jacobkrantz/VLN-CE)

Our dashboard maps a forward action to 25 cm and a turn to 15 degrees. Those are this application's controls, not universal properties of RxR.

### 1.4 The exact installed episode file

On ISL, the running application uses:

```text
/home/guest-isl/rishabh/NAVIDA/data/
  RxR_VLNCE_v0/val_unseen/val_unseen_guide.json.gz
```

Inspection found **11,006 episodes across 11 scene IDs** in that file. These counts describe this installed split, not the complete RxR release.

The dashboard currently uses episode **218**, instruction ID **590**, language **`en-IN`**, and scene:

```text
mp3d/2azQ1b91cZZ/2azQ1b91cZZ.glb
```

Its instruction begins by describing an open space beside a kitchen, then continues past chairs and a couch toward other rooms and windows. The complete instruction is already displayed in the dashboard.

| Episode field | Meaning |
|---|---|
| `episode_id` | Identifier for one navigation task; currently `218` |
| `trajectory_id` | Identifier linking the task to a trajectory |
| `scene_id` | Relative building asset path |
| `start_position` | Agent's initial 3D position |
| `start_rotation` | Initial orientation, stored as a quaternion |
| `goals` | Goal positions and acceptance radii |
| `instruction` | Text, language, instruction ID, and associated annotation information |
| `reference_path` | Recorded reference route through the scene |
| `info` | Additional task metadata |

Episode 218 starts at approximately `[3.0425, 0.1271, 1.5784]` in the episode/Habitat coordinate convention. Its goal is approximately `[12.2306, 0.1271, 10.4219]`, with radius `3.0` in this record. These are **agent/goal positions**, not the height or location of the kitchen props.

### 1.5 What “fixing the dataset” means here

The work repairs a **derived scene asset** used with those episodes. It does not modify the official Matterport3D release, rewrite the original RxR instructions, regenerate the entire dataset, or train a navigation model.

The same relative `scene_id` can resolve to a different GLB when `--scenes-dir` changes. That is how the original episode can be explored in a repaired copy of the building.

Changing scene appearance can affect model observations and benchmark comparability. If the repaired scene is used for experiments, record its version alongside the original episode split. A prettier scene alone does not establish improved navigation performance.

## 2. What your previous prompt asked for

Your pasted text was a **worker handoff for an ongoing repair task**. “You are a forked worker” described the previous assignment. It was not a navigation instruction from the RxR dataset.

Its practical requirements were:

1. Repair objects on the sink-wall L counter and the range-side counter in `2azQ1b91cZZ`.
2. Use the **real photographs** to understand each object's identity, shape, orientation, color, and context.
3. Prefer a suitable product model or a photo-informed lathe/parametric model.
4. Use meaningful real-world dimensions. Permit size changes when needed for plausible placement.
5. Put objects directly on the correct support surface, without floating, sinking, or colliding.
6. Bake suitable finishes so metals remain recognizable in Habitat.
7. Save object outputs and a `fit.json` describing their integration.
8. Compare renders to the photos and inspect additional viewpoints.
9. Report remaining realism problems instead of calling every result perfect.

It also imposed coordination restrictions: avoid shared manifests/build scripts, avoid the shared route sweep, avoid relaunching the UI during that repair assignment, and use separate outputs. The handoff later said one worker should finish. No additional worker was spawned during this continuation.

Your later instruction to update the dashboard authorized the dashboard work. We started a separate repaired-scene session, switched the local connection to it, and left the prior session running so its unsaved route survived.

### What the two repair stages did

| Stage | Starting state and result |
|---|---|
| Previous worker, as recorded in your handoff | Built 15 replacement-object entries, including four individual bottles. Left the wooden caddy, wooden knife block, and frogs as scan geometry. Reported a 30-prop audit with no issues. |
| Continuation inspected here | Found those 15 replacements already represented in v15. Added the caddy, wooden knife block, and frog/tray assembly; corrected finishes, orientation, labels, and scan cleanup. The private integration audit covered 32 props. |
| Dashboard update | Loaded the private repaired GLB in a new Habitat session and added expandable comparison images. Kept the old session accessible separately. |

The difference between **18 repair entries** and **32 audited props** is expected: the audit also includes other kitchen props and fittings already in the integration manifest. Eighteen entries do not mean exactly eighteen physical components: the frogs, tray, and bowl form one assembly entry.

## 3. What is being edited

A reconstructed building has several parts:

| Part | Plain-language meaning | Typical repair |
|---|---|---|
| Mesh geometry | Triangles that define the surfaces | Replace a melted-looking appliance or remove floating triangles |
| Texture image | Image pixels painted over those triangles | Remove a leftover silhouette painted onto the wall |
| UV coordinates | Instructions mapping texture pixels onto the mesh | Project a label onto the correct visible surface |
| Material | Surface color and rendering behavior | Correct dark plastic, ceramic, wood, or metal appearance |
| Transform | Position, rotation, and scale | Turn the toaster toward the correct camera and put its feet on the slab |
| Navmesh | Surface representation used for agent navigation | Recompute after scene/obstacle changes when required |
| Semantic annotations | Labels such as furniture categories and object identities | These were not comprehensively reannotated in this repair |
| Episode JSON | Instructions, starts, goals, and paths | Original records are retained; dashboard saves create separate derived records |

A scan may contain recognizable furniture but poor small objects. Thin knife handles, shiny taps, transparent bottles, and partially hidden objects are difficult to reconstruct accurately. Their image can also be projected onto a nearby wall during texture creation. This explains why one object can need both a geometry replacement and a texture cleanup.

No new physical scan of the kitchen was made. Hidden surfaces, tiny lettering, and exact product dimensions cannot always be recovered from the available photos. Some replacement details therefore remain approximate.

## 4. How we identify a problem and choose a repair

### 4.1 The initial suspect regions come from the assignment and photo annotations

The object list in your prompt and `kitchen_items.txt` identify where to inspect. An actual line is:

```text
toaster 58348305b0f84dd8b161aaf2d5b945ef_i2_4.jpg 649 100 833 380
```

It means: inspect the toaster in that photograph, inside pixel box `(649,100)` to `(833,380)`. Pixel coordinates are an image location, not a location in meters.

This annotation is a starting region. It can contain shadows, a cable, neighboring objects, or a knife crossing in front of a jug. We inspect the photograph before treating the whole rectangle as the object.

### 4.2 Visual comparison finds appearance and shape problems

We render the scan/repaired scene from the camera associated with the real photo. Then we compare:

| Observation | Likely problem | Response |
|---|---|---|
| Real photo shows a phone; render shows an indistinct lump | Damaged or missing object geometry | Find or build a recognizable phone |
| Object outline is too large | Wrong scale, placement, or contaminated mask | Constrain dimensions and refine its pose |
| Toaster controls face away from the photo camera | Orientation mismatch | Rotate the object and recheck clearances |
| Blue jug has an angular or missing handle | Poor tracing or occlusion | Build a smooth handle explicitly |
| Black plastic renders nearly white | Texture/bake calibration failure | Correct texture calibration rather than enlarging or moving the object |
| Old shape remains after replacement | Remaining scan faces or a texture ghost | Determine which kind before deleting or painting |

This is **guided inspection**, supported by code. We do not have a single autonomous detector that finds every bad triangle or proves where every texture patch is needed.

### 4.3 Geometry measurements find physical problems

The code measures the object's lowest points, footprint, full bounds, and intersections with nearby geometry. A render can look acceptable while the toaster penetrates a tall cabinet or the kettle floats over the cooktop. The numerical checks help reveal those problems.

### 4.4 Geometry problems and texture ghosts must be distinguished

To decide whether a remaining artifact needs a patch:

1. Inspect its shape from the original photo view.
2. Inspect a second view and the surface geometry/depth.
3. Determine whether there are independent triangles making the artifact.
4. If it is a flat image stuck to an otherwise correct wall, inspect the wall's texture mapping.
5. Compare the local wall/tile pattern with clean neighboring areas.

Movement/parallax is a useful clue: a protruding fragment changes its relation to the wall across views, while a painted ghost stays attached to the wall. This clue supports inspection; it is not an automatic classifier in the current code.

The old soap-bottle image behind the replacement is one visible example of a backsplash texture problem. Removing more bottle geometry would not erase pixels already painted onto the wall.

## 5. How a photograph is matched to the 3D scene

### 5.1 We use camera calibration supplied with the photographs

The source contains:

```text
source/photos/2azQ1b91cZZ/
  undistorted_color_images/
  undistorted_camera_parameters/2azQ1b91cZZ.conf
```

The `.conf` file associates each photograph with:

- **Intrinsics**: focal lengths and image center, describing how the camera projects points into pixels.
- **Extrinsics**, represented by `c2w`: camera position and orientation in the building.

`mp3d_cams.py` loads these values and places a Habitat camera at the corresponding pose. We can then compare the real photo with a render from the same nominal viewpoint.

The primary color images used by the fitting code are 1280 × 1024. Faster previews may use smaller images with correspondingly scaled projection parameters. Some helper renders assume centered principal points and an approximate focal length; comparisons are calibrated working references, not a proof of perfect pixel registration.

### 5.2 The coordinate systems are different

In the repair code, raw Matterport coordinates use **Z as vertical**. The helper conversion to the Habitat/glTF convention is:

```text
raw (x, y, z) -> helper Habitat/glTF coordinates (x, z, -y)
```

For example, a raw point `[6.0, -5.0, 0.929]` maps to `[6.0, 0.929, 5.0]` under this conversion.

The scene-export path has an additional convention: the full building is exported with `export_yup=False` to preserve its raw MP3D scene coordinates, while inserted object GLBs are prepared for Blender's glTF import conversion. `frames.py`, `mp3d_cams.py`, and the private build script encode these choices. Do not apply the conversion twice or assume every PLY, GLB, and episode JSON uses an identical frame.

### 5.3 Segment the object in the photograph

The workflow uses **SAM2**, prompted with an object box, to obtain a foreground mask. A mask marks which pixels are believed to belong to the object. In `kitchen_obj.py`, the highest-scoring predicted mask is selected.

SAM2 helps isolate the object; it does not supply its exact 3D geometry, real-world dimensions, or guaranteed identity. White objects against pale walls and objects crossed by handles can still be segmented incorrectly.

### 5.4 Estimate the base using the counter, not the broken object's depth

The seed code samples rendered scan depth in a ring around the object's mask, especially near its foot. The surrounding countertop is often more trustworthy than the malformed object itself. It estimates a support plane and casts a camera ray through the object's bottom pixels.

For a horizontal support plane at height `zc`, the ray intersection is:

```text
P(t) = camera_origin + t * ray_direction
t = (zc - camera_origin.z) / ray_direction.z
```

This gives an initial base position in meters. If the final slab height is known, that known height takes precedence over a noisy seed.

In this kitchen, the final sink-run and range-side slab surface is **raw z = 0.929 m**. The kettle's support is the cooktop grate at **raw z = 0.991 m**.

The counter specification also contains lower reference elevations such as `0.927`. Do not use those numbers interchangeably with the finished slab top or the `keep_below_z` scan-deletion threshold.

### 5.5 Fit a candidate's projected silhouette

The placement tools vary rotation, scale, and horizontal position, render the candidate's silhouette, and compare it with the photo mask. A common score is intersection over union:

```text
IoU = area(rendered_mask AND photo_mask)
      / area(rendered_mask OR photo_mask)
```

The general `product_fit.py` also scores boundary agreement. Its implemented score combines silhouette IoU and a boundary F-score, each with weight 0.5. The boundary term helps thin spouts and handles matter instead of letting a large generic body dominate the score.

Candidate orientation can be searched over different up axes and yaw angles, followed by local refinement. Where several usable photos exist, agreement across views helps constrain pose. Some objects have only one strong primary view, so manual interpretation and new-angle checks remain necessary.

### 5.6 Real-world constraints override misleading image fits

The previous worker found that shadows and cords could reward oversized toaster, phone, or grinder models. Locking a plausible height prevents the optimizer from growing the object just to cover those extra pixels.

The final repair uses a 20 cm toaster, a 9 cm phone, and a roughly 22.4 cm grinder. These are meaningful reconstruction choices; they are not manufacturer-verified measurements of the original products.

An object must satisfy both visual fit and physical placement. A high silhouette score alone cannot justify a toaster inside the tall cabinet.

## 6. How replacement objects are made

Three reconstruction methods were used. Each object gets the method that best preserves its recognizable features with the available evidence.

### 6.1 Use a suitable product model

For recognizable appliances such as the toaster, phone, and kettle, an existing detailed model provides parts that would be slow to reconstruct from scratch. Candidate assets are searched in the available Objaverse/product pool, checked against the photos, normalized, sized, and placed.

Matching means comparing category, profile, handles, controls, proportions, and material regions. It does not mean that we identified the exact original manufacturer's model.

The selected asset's source and credit are recorded in `fit.json` under `product`. The toaster, phone, and kettle retain CC-BY attribution metadata. The kettle author's username contains “cc0,” but its recorded license is `by`; the username does not determine the license.

The earlier grinder product was later rejected because its brown lidded shape did not match the photographed black drawer body and open metal hopper. That grinder is now a parametric reconstruction.

### 6.2 Lathe reconstruction for mostly round objects

A lathe model revolves a radius-versus-height profile around a vertical axis:

```text
profile: radius r at height z
vertex around a ring: (r*cos(theta), r*sin(theta), z)
```

Many rings connected by triangles make a bottle or jug body. A profile may be traced from a photo or designed from the observed form. Smooth interpolation avoids abrupt steps.

This is suitable for the four oil bottles and the jug body. Bottle labels and glass colors can be taken from the photo. A handle or pump is not rotationally symmetric, so those parts need separate geometry. A knife crossing the jug in the photograph cannot be treated as part of the jug's profile.

### 6.3 Parametric reconstruction for structured objects

Parametric builders assemble boxes, cylinders, curved tubes, ellipsoids, and custom surfaces with explicit dimensions.

Examples from `resume_kitchen_objects.py`:

| Object | Constructed parts |
|---|---|
| Wooden caddy | Base, spaced slats, posts, rails, handle, apple-shaped ends, and leaf detail |
| Wooden knife block | Sloped wooden wedge, slots, metal bolsters, black handles, and scissors |
| Grinder | Drawer body, trim, drawer knob, metal hopper, spindle, and crank |
| Blue jug | Outer and inner curved walls, base, rim/spout detail, and curved C-handle |
| Frogs/tray assembly | Bodies, heads, eyes, bent limbs, webbed feet, supported tray, and bowl |

The dimensions can be adjusted directly, which is useful for avoiding overlaps and ensuring contact with the counter. This is procedural 3D modeling guided by the photographs. It is not a complete photogrammetric reconstruction of every hidden detail.

`kitchen_obj.py` also contains an optional TRELLIS image-to-3D generation path. Its presence in the repository does **not** mean the final continuation props were all generated with TRELLIS. The continuation primarily used existing product/lathe assets and explicit parametric builders.

## 7. How old scan geometry is removed

Inserting a replacement without removing the original scan leaves two overlapping objects. The integration step must remove the old fragments while retaining the slab and wall.

Each `fit.json` stores a deletion region:

| Field | Purpose |
|---|---|
| `delete_aabb` | Axis-aligned 3D bounding box containing old fragments to remove |
| `delete_polygon` | Optional tighter XY footprint that limits deletion inside the box |
| `keep_below_z` | Protects geometry below the deletion floor, especially the supporting counter |
| `delete_mode` | Selects face-based deletion behavior |
| `protect_backsplash` | Enables explicit wall-edge protection in the private integration copy |

The new and old object footprints are combined so moving or resizing an object does not leave its previous scan footprint behind. The implementation often takes the convex hull of that union, with a small margin. This is a conservative enclosing region rather than an exact outline of every original triangle.

### Two deletion modes

- **Default/all-vertices mode** removes a face only when all of its vertices lie inside the deletion volume. This is conservative but can leave triangles crossing the boundary.
- **Centroid mode** removes a face when its center lies inside the volume. This can catch boundary-straddling fragments, including the leftover paper sheet, but still requires careful region limits.

The private `kitchen_apply.py` protects specified backsplash boundaries for fits that enable the flag. This reduces accidental wall removal. It also means fragments close to the wall can remain; the flag is not a general semantic understanding of every wall.

The deletion is applied to the imported scan meshes collected before replacements are inserted. Later replacement objects are not treated as old scan fragments in that same pass.

The result is local mesh surgery: remove selected scan faces, import the clean object, apply its transform, and export the combined building. It does not automatically regenerate or retopologize the entire building mesh.

## 8. How color, labels, and metal finishes are repaired

### 8.1 Colors are informed by the real photographs

We compare material regions such as cream ceramic, black plastic, blue glaze, dark wood, and steel. A useful product model may still have the wrong colors, so its finish is adjusted to match the photographed scene.

The appearance is checked in the actual Habitat render. A material that looks good under Blender studio lighting can look different in the dashboard.

### 8.2 Why the metal finish is baked

In this pipeline, stage objects do not receive the same environment-reflection setup as a studio product render. A fully metallic shader can look too dark or fail to resemble the photographed metal.

The workflow bakes a recognizable finish into an image texture. The scene integration then uses matte material settings—metallic 0 and roughness 1—so Habitat shows that baked appearance consistently with the scanned surroundings.

This preserves useful visual cues but limits physically correct reflections. The toaster and kettle therefore remain less mirror-like than the real objects. Baking improves their appearance in this renderer; it does not make the final material a physically exact reproduction.

### 8.3 What went wrong with the earlier color bake

During inspection, dark phone/toaster areas became too pale, and some material colors shifted. The issue was not always the chosen target color. Empty space between UV islands—called atlas gutters—was influencing texture statistics.

The private correction samples **inside mesh triangles** in UV space and weights the samples by face area. It estimates a representative brightness from actual surface samples, then preserves bounded shading variation while applying the photo-informed target color.

That avoids calibrating a black appliance using mostly irrelevant atlas background. The fix is in the private continuation workflow; the shared bake script was not overwritten.

### 8.4 Projecting photograph detail onto an object

For labels and selected visible surface details, the workflow:

1. Reads a point on the replacement mesh associated with a texture pixel.
2. Projects that 3D point into the real photo using its calibrated camera.
3. Checks that the photo pixel belongs to the intended object mask.
4. Uses rendered scene depth to reject surfaces hidden from that camera.
5. Rejects unsuitable viewing angles and restricts projection to chosen material/height regions.
6. Blends the source color into the object's texture.

The final phone projection is restricted to a control-panel polygon, excluding the cord. The wooden knife block receives photo detail only on the lower wood face, preventing photographed knives from being stamped onto its top. Grinder detail is restricted to the lower body, keeping the metal hopper separate.

The visibility test uses depth rendered from the current reconstruction. It is helpful, but it is not independent original-depth ground truth for every surface. A bad reconstructed shape can still produce a bad projection, so visual review remains essential.

### 8.5 Why some projected versions were rejected

If the replacement shape differs from the real object, copying the whole photo onto it can stamp shadows, cables, knives, or the old silhouette onto the wrong surface. That happened in trial variants.

The selected toaster, canisters, frogs, and kettle use cleaner final baked variants. The selected jug is specifically **`world_resume_baked.glb`**. Other unused experiments may still be present in an object folder. The authoritative selected file is the `glb` field in `fit.json`, not the filename that sounds newest.

The canister motifs use small photo-derived transparent label geometry. They preserve some printed detail but remain visibly approximate at close range; illegible lettering was not invented.

## 9. How wall and counter texture patches work

This section explains the existing patch mechanism and how a patch area is chosen. The continuation did **not** complete all visible backsplash ghosts.

### 9.1 A texture ghost is an old object image on another surface

Suppose the scan texture contains a soap-bottle silhouette painted onto the backsplash. Replacing the bottle's 3D geometry does not remove that silhouette, because those pixels belong to the wall's texture.

A texture patch changes the affected wall pixels while retaining the wall geometry. This differs from deleting scan triangles or projecting a label onto a new bottle.

### 9.2 How the area needing a patch is identified

The process combines the user's object list, matched-camera comparisons, additional views, and inspection of the wall/counter texture mapping. We identify a particular leftover silhouette or stain and locate it on the relevant surface.

In the existing `ghost_fix.py`, the target region is supplied through boxes in `SPEC.json`. Those boxes are chosen after inspection. The script does not autonomously discover all ghosts or decide that every dark region is wrong.

For plain counter regions, a brightness threshold helps select dark pixels **inside an already chosen box**. Dark stone pattern, real shadows, and valid labels must not be erased just because they are dark.

### 9.3 Rectify the surface into a flat working image

A texture atlas packs many disconnected surfaces into one image. Editing the raw atlas blindly can affect the wrong wall or create seams.

The patch tool uses an `.npz` mapping containing triangle positions, triangle UVs, normals, texture identities, and source image paths. It selects approximately coplanar faces:

- Backsplash wall: approximately Y-normal, displayed in the raw X–Z plane.
- Countertop: approximately Z-normal, displayed in the raw X–Y plane.

It creates a straight-on, metric image at **2 mm per pixel**. A grid links the displayed patch area to world-space meters. This makes the backsplash easier to inspect than its scattered atlas islands.

The selection logic targets these specific surface orientations. A different wall orientation may need an adapted selector; the tool is not a universal patcher for every surface in the building.

### 9.4 Fill the selected region

| Surface | Existing repair method | Reason |
|---|---|---|
| Repeating tile/wall pattern | Clone a clean region displaced by a pattern period | Maintains the repeating decoration |
| Plain stone/counter | OpenCV Telea inpainting of selected dark ghost pixels | Extends nearby appearance across a small damaged area |

For cloning, the code checks source coverage, compensates for local brightness differences, and feathers the border. For inpainting, it limits the change to the selected region and uses neighboring image information.

These operations infer missing background appearance. They do not recover an independently photographed hidden wall pixel with certainty.

### 9.5 Write the change back to the original UV mapping

Using barycentric coordinates inside each triangle, the tool maps the edited surface image back to only the corresponding texture pixels. It writes patched texture copies and a mapping file:

```text
patches.json = { original_image_name: patched_image_path, ... }
```

A manifest entry such as `{"texpatch": ".../patches.json"}` tells `kitchen_apply.py` which imported images to replace before the scene is exported.

The exact imported image names matter. A name mismatch can silently select the wrong image in poorly guarded workflows; the integration code checks for missing mapped images. Replacement-object textures are also renamed to avoid collisions such as multiple unrelated `Image_0` textures.

### 9.6 What is still unpatched

The continuation report flags old soap-bottle/canister/frog imagery on the backsplash and residual fragments near some walls. A geometry audit cannot certify those pixels. The existence of `ghost_fix.py` and earlier `texpatch` outputs does not mean every newly observed ghost was patched in `agentA_resume/test.glb`.

## 10. How placement and realism are verified

### 10.1 Verify the support surface

We measure the mesh itself after its transform, not just the claimed `base` field:

```text
support_gap = minimum raw mesh z - intended support z
```

Counter objects should have a gap near zero relative to `0.929`. The kettle should have a gap near zero relative to `0.991`. The private audit reports an issue when the absolute support gap exceeds **4 mm**.

### 10.2 Verify the footprint and wall clearances

The audit builds a footprint from vertices near the bottom and checks containment against the counter polygons. For the 0.929 m props, the allowed off-counter area threshold is **0.00002 m²**, or **0.2 cm²**. It also checks full-object extents against the specified backsplash/right-wall boundaries, and checks the toaster against the tall-cabinet limit.

These are explicit geometric tests with particular assumptions. The counter containment check uses the union of counter outlines; it is not an exhaustive mesh-level proof of all sink holes, decorative edges, or structural supports. Known sink/tap clearances were also inspected separately.

### 10.3 Verify neighboring objects

A large bounding box around the frogs and tray includes empty space. Treating that box as a solid object would incorrectly reject bottles under or near the tray.

The private audit instead splits each mesh into connected components, computes a convex volume for each component, and checks sampled vertices against neighboring volumes. Pairwise penetration uses a **2 mm** tolerance after an initial bounds check.

This better represents multi-part assemblies, but it has limits: convex approximations can overfill concavities, and sampled-vertex tests can miss some intersections. “Zero issues” means no issue under these implemented checks. It is not a mathematical proof that every triangle is collision-free.

### 10.4 Inspect matched-camera and new-angle renders

Each comparison sheet shows:

```text
real photo | previous v15 build | repaired private build
```

Additional views reveal thin-sheet geometry, unsupported parts, hidden overlaps, and texture stretching that a primary photo can hide.

![Sink counter: real photo, previous scene, repaired scene](images/agentA_resume_compare1.jpg)

![Corner counter: real photo, previous scene, repaired scene](images/agentA_resume_compare2.jpg)

![Range counter: real photo, previous scene, repaired scene](images/agentA_resume_compare3.jpg)

![Additional views of the repaired kitchen](images/agentA_resume_novel.jpg)

### 10.5 Verify the build really succeeded

Blender can return a successful process exit without treating every Python failure as a failure unless configured accordingly. An earlier failed export left an old GLB in place, which could produce misleading previews.

The corrected invocation uses **`--python-exit-code 1`**. Verification checks the export log, selected asset paths, final scene file, and preview timestamps. The final saved GLB is **409,290,516 bytes**. The preview verification record lists six fresh renders and their hashes.

The final recorded component-aware audit reports **32 props and zero placement issues**. It does not evaluate photorealism, original-depth accuracy, semantic-label consistency, navigation success, or all background scan defects.

The shared route sweep was not run during this repair continuation. Earlier `sweep_v15.json` files belong to their earlier build states and cannot automatically certify this private build.

## 11. What changed for each kitchen object

Paths below are relative to `refined/kitchen/objects/`; each folder's `fit.json` selects the actual output. Dimensions are approximate reconstruction values.

| Object / fit folder | Method and result | Remaining limitation |
|---|---|---|
| `toaster_v2` | Product model, 20 cm high; corrected controls orientation and steel/black bake; clears tall cabinet | Product controls/profile differ; reduced reflectivity |
| `canister_l_v2` | Rounded cream ceramic jar, about 23.5 cm high; corrected lid and photo motif | Generic clamp/lid and visible label patch |
| `canister_r_v2` | Same approach as left canister | Same approximation |
| `soap_bottle_v2` | Pump bottle, 19.6 cm high; grey-blue finish and selected photo detail | Approximate pump/body; backsplash ghost remains |
| `soap_dish_p_v2` | Retained accepted black oval dish and white soap, 9.3 × 6.7 cm | Smaller than photographed object; simplified finish |
| `bottles_v20` | Photo-traced bottle, about 13.9 cm high; photo label detail | Hidden side uses approximate ring colors |
| `bottles_v21` | Second separately placed bottle | Same hidden-side limitation |
| `bottles_v22` | Third separately placed bottle | Same hidden-side limitation |
| `bottles_v23` | Fourth separately placed bottle | Same hidden-side limitation |
| `knife_block_round_v2` | Parametric oval block, corrected cap/finish, moved clear of cooktop | Generic steel handles |
| `knife_block_v2` | New wood wedge with five knives and scissors, about 30 cm overall | Approximate handle arrangement and nearby scan traces |
| `blue_jug_v2` | New smooth hollow jug, curved handle, baked blue glaze, about 10.5 cm high | Generic creamer profile |
| `range_kettle_v2` | Product model, 24 cm high; baked finish; base on grate at 0.991 | Shape differs and is less reflective than photo |
| `phone_v2` | Product model, 9 cm high; dark plastic and restricted panel photo detail | Screen/key layout differs from original |
| `grinder_v2` | New black drawer body, open hopper, spindle/crank, about 22.4 cm high | Approximate metal profile and crank |
| `paper_towel_v2` | Holder/roll, 33.2 cm high; wider scan cleanup removed old sheet | Fine paper texture not reproduced |
| `caddy_v2` | New slats/rails/apple ends and handle, roughly 34 × 18 × 24 cm | Hidden grain/decorations approximate; wall-adjacent fragments |
| `frogs_v2` | New supported frog pair, tray, and bowl assembly, about 33 cm high | Stylized figures/patina; old wall imagery remains |

Examples of changes driven by physical constraints include shrinking the soap dish to fit the narrow rear strip and clearing the hot-tap flange, shifting the round knife block away from the cooktop, and moving appliances away from cabinet/wall intrusions.

The additional jug/coaster cluster visible elsewhere remains scan geometry. This pass did not replace every small item in the whole kitchen.

## 12. Local directory guide

Your local repository is:

```text
/home/vivekananda/UGP_1_VLM/VLM_Based_Robot_Navigation/
```

At the repository level, `Task_1_Simulator_Evaluation`, `Task_2`, and `Task_3` contain other project work. `Task_4` holds the kitchen visualization snapshot and this explanation. The repository is not a complete local copy of the ISL repair environment.

```text
Task_4/
├── README.md                         Earlier visualization instructions
├── open_visualization.sh             Local SSH port-forwarding launcher
├── .gitignore                        Excludes large/local dataset artifacts
├── dashboard/
│   ├── author_pov_route.py            Copied original dashboard source
│   └── run.sh                         Server-side launcher reference
├── scenes/
│   └── v15/2azQ1b91cZZ.glb            Earlier self-contained local scene
├── previews/                         Earlier worker's saved images
├── metadata/
│   ├── download_inventory.json       What the earlier download copied
│   ├── episodes.tsv                  Folder/shard/episode lookup
│   ├── kitchen_items.txt             Object/photo/pixel-box annotations
│   ├── counters_spec.json            Counter outlines and reference elevations
│   └── manifest_v15.json             Earlier integration list; ISL paths
├── visualization_tools/              Copied Habitat/render helper scripts
├── glb_visuals/                      Empty when inspected
└── kitchen_dataset_repair_guide/      This new documentation folder
    ├── README.md                     Detailed explanation you are reading
    ├── DIRECTORY_INVENTORY.md        Observed local/server file listing
    ├── images/                       Continuation comparison images
    └── evidence/                     Repair report and validation snapshots
```

### What each local folder is for

| Path | What it contains and how to interpret it |
|---|---|
| `scenes/v15/` | Earlier GLB, 402,235,188 bytes. Useful offline, but different from the repaired private build. |
| `previews/` | Earlier `agentA_*` images. Filenames alone do not make them current continuation images. |
| `metadata/` | Reference copies. Their absolute asset paths refer to ISL, not local files. |
| `metadata/episodes.tsv` | Mapping used by `run.sh`: download-group/folder, shard, and episode ID. Folder IDs such as `001` are organizational labels, not scene IDs. |
| `dashboard/` | A copied application and launcher. Running this source requires the server dependencies/data paths unless deliberately adapted. |
| `visualization_tools/` | Helpers that retain server paths and Habitat dependencies. Copying them does not install those dependencies. |
| `open_visualization.sh` | Opens/reuses a tunnel to an already running server dashboard. It neither repairs scenes nor restarts Habitat. |
| `kitchen_dataset_repair_guide/images/` | Latest continuation comparison images copied for this document, not a full source-photo dataset. |
| `kitchen_dataset_repair_guide/evidence/` | Snapshot evidence. Useful for tracing this report, not a live synchronization service. |

The earlier `Task_4/README.md` describes remote port 8767. After the dashboard update, the **repaired** server session is on port **8768**, while local **8767** forwards to it. Use the current connection instructions in section 18 if the tunnel must be recreated.

## 13. ISL directory guide

### 13.1 Main server roots

| Server path | Purpose |
|---|---|
| `/data/robotics/toshith/rxr_author/` | Route-author application, scene-selection wrappers, repair workspace, and route outputs |
| `/home/guest-isl/rishabh/NAVIDA/` | Navigation project/configuration used to launch Habitat |
| `/home/guest-isl/rishabh/NAVIDA/data/RxR_VLNCE_v0/` | Installed navigation episode data |
| `/home/guest-isl/rishabh/custom/habitat_building_isaac_repaired/source/photos/2azQ1b91cZZ/` | Original photo references and camera calibration used here |
| `/data/robotics/toshith/k3d_cache/` | Product/Objaverse and related model caches used by the modeling workflow |
| `/data/robotics/toshith/envs/kitchen3d/` | Python environment for geometry, segmentation, and fitting tools |
| `/home/guest-isl/rishabh/VLA-paper/.navida-env/` | Habitat/navigation Python environment used for rendering and dashboard |

These environments serve different dependency sets. A geometry helper that works in `kitchen3d` does not imply Habitat is installed there.

### 13.2 Route-author root

```text
rxr_author/
├── author_pov_route.py          Shared first-person route application
├── run.sh                      Episode selection / launch helper
├── episodes.tsv                Folder/shard/episode lookup
├── parts_rt.py                 Runtime for separately exported moving parts
├── scenes/                     Original/reference scene organization
├── scenes_v7/ ... scenes_v15/   Version-specific dataset-style scene wrappers
├── scenes_interactive*/        Scene wrappers for door/drawer variants
├── rxr_traces/                 Trace-related stored artifacts
├── out/                        Original route-author outputs
├── out_refined/                Outputs from refined-scene sessions
├── out_interactive/            Outputs from interactive-parts sessions
├── out_kitchen_v*/             Outputs/logs associated with kitchen versions
└── refined/                    Geometry, texture, repair, and build workspace
```

The observed file inventory lists the actual version names. The `*` and ellipsis here describe families, not literal folder names.

`scenes_v15/mp3d/2azQ1b91cZZ/2azQ1b91cZZ.glb` is a symlink to the v15 scene under `refined/v15/`. The `.house` and `_semantic.ply` companions link to existing scene resources. A `.navmesh` stores navigation geometry. A symlink references a target file; it is not another independent 400 MB scene copy.

Repaired geometry does not automatically regenerate matching semantic annotations. Retaining original annotation companions helps the existing application run but does not certify every replacement's instance labels or selection bounds.

### 13.3 The `refined/` workspace

```text
refined/
├── usd*/                       Source/working USD scene variants
│   └── usd_v8/building_habitat.usdc
├── v7/ ... v15/                Exported GLB version directories
├── parts_v*/                   Exported door/drawer parts for interactive work
├── audit_v*/                   Earlier version-specific audit artifacts
├── kitchen/
│   ├── objects/                Replacement objects and their fits
│   ├── products/               Product candidates, caches, rankings
│   ├── fixtures/               Fixture-related work assets
│   ├── texpatch/               Texture-mapping extracts and patched copies
│   ├── depth_v*/               Scene-rendered depth caches used by fitting
│   ├── kitchen_items.txt       Main annotated object/photo boxes
│   ├── counters_spec.json      Counter support outlines/specification
│   ├── manifest*.json          Shared/versioned integration lists
│   └── review*.jpg, grid*.jpg   Previous review and photo-grid images
├── agentA/                     Previous worker's private build area
├── agentA_resume/              Continuation build, evidence, backups, dashboard
├── product_*.py                Product preparation, fitting, placement, preview
├── lathe_*.py, param_fixture.py Shape-construction helpers
├── bake_finish*.py             Finish/baking tools and worker variants
├── kitchen_apply.py            Shared integration step
├── usd2glb.py                  Shared full-scene export step
├── ghost_*.py                  Texture-ghost inspection/patching tools
├── realism_audit.py            Shared placement audit
├── look.py, multiview.py        Render inspection tools
├── sweep*.json, sweep*.log      Earlier route-sweep records
└── convert*.log, *.jpg          Historical export logs and inspection images
```

Version numbers such as v14 and v15 identify saved project revisions. They do not mean RxR dataset versions. File families such as `convert*.log` and `review*.jpg` are records, not the currently selected scene.

The active continuation build was created from `usd_v8/building_habitat.usdc` with the private integration manifest. v14 was a prescribed preview base in the earlier assignment; v15 was used for before/after comparisons. Those roles are distinct from the source used for the private full-scene export.

### 13.4 The continuation directory

```text
refined/agentA_resume/
├── test.glb                    Final private repaired building
├── manifest.json               Private integration list
├── object_fit_paths.json       Exact 18 repair-fit paths
├── changes.json                Existing/new entries and integration notes
├── audit.json                  32-prop placement-audit result
├── verification.json           Export/preview verification evidence
├── report.md                   Detailed continuation report
├── backups/                    Previous fit/assets saved before changes
├── previews/                   Three comparisons, new views, full comparisons
├── depth/                      Rendered depth for photo-visibility checks
├── build_private.py            Private Blender scene exporter
├── kitchen_apply.py            Private integration copy
├── bake_finish_resume.py       Private bake variant
├── resume_kitchen_*.py         Continuation helper copies
├── *.log                       Build, bake, texture, and render logs
└── dashboard/
    ├── serve_repaired.py        Wrapper for repaired-scene dashboard
    ├── launch.json              Exact launch argument list
    ├── pid                      Recorded process ID at launch
    ├── ui.log                   Application startup/runtime log
    ├── frame_verified.jpg       Live-frame verification snapshot
    ├── scenes/mp3d/2azQ1b91cZZ/
    │   ├── 2azQ1b91cZZ.glb      Symlink to agentA_resume/test.glb
    │   └── ...                 Original annotation companions / runtime assets
    └── output/218/              Separate output location for this new session
```

The backup report explicitly distinguishes directly saved originals from reconstructed earlier bottle-fit selections. Read the backup notes rather than assuming every backup was captured by an identical procedure.

## 14. Files inside one object folder

A typical example is:

```text
refined/kitchen/objects/toaster_v2/
  fit.json
  world_mesh variants such as world.ply or world_resume.ply
  world_col.glb
  world_baked.glb
  world_resume_final.glb
  finish*.json
  other intermediate variants/previews
```

The exact contents vary. Some names above are common variants rather than a promise that every object folder contains all of them.

| File or field | Meaning |
|---|---|
| `fit.json` | Object's integration recipe and selected asset |
| `glb` | Path to the renderable object model, including appearance |
| `world_mesh` | Raw-world geometry used by measurements/audits, often a PLY |
| `matrix` | Additional 4 × 4 transform applied during integration |
| `base` | Intended support reference position in raw coordinates |
| `height` | Recorded object height |
| `views` / `photo_box` | Photo references used for matching |
| `pose` | Recorded orientation/scale information |
| `delete_*` / `keep_below_z` | Controlled scan-removal rules |
| `product` | External source attribution, where applicable |
| `realism_notes` | Documented approximations or issues; also consult the report if absent |
| `finish*.json` | Desired appearance values for named material parts |
| `world_resume_photo.glb` | A photo-detail variant; selected only where it proved useful |
| `world_resume_final.glb` | A calibrated baked variant; not universally the selected file |

For the toaster, the current selected GLB is `world_resume_final.glb`, the base is `[4.53, -5.19, 0.929]`, the recorded height is 0.20 m, and the yaw is about 87.26 degrees. The object is already in world placement with an identity integration matrix.

Do not apply recorded `pose.scale` again to an already transformed world mesh. Some fit fields document the fitting history; the actual render path is determined by the selected model and its integration matrix.

A manifest is simply an ordered list of fit paths, with optional entries for texture patches or deletion-only operations. It does not contain all geometry itself.

Although the shared manifest JSON and existing v15 GLB were left unchanged, several existing `objects/*_v2/fit.json` files were updated with backups. A future rebuild that follows those same fit paths can therefore see the updated selections. “Private build” does not mean that every referenced object file is isolated from all shared references.

## 15. Script guide

### General repair and viewing tools

| Script | Role |
|---|---|
| `kitchen_obj.py` | Photo/camera utilities, segmentation, depth seed, silhouette fitting, optional image-to-3D generation |
| `product_prep.py` | Prepare candidate product assets for scene use |
| `product_place.py` / worker placement copies | Fit/position product candidates |
| `product_fit.py` | Rank products using photo silhouettes and boundary agreement |
| `lathe_fixture.py`, worker lathe copies | Construct turned profiles for suitable objects |
| `param_fixture.py` | Parametric parts such as curved tubes |
| `frames.py` | Coordinate conversion and object-export conventions |
| `bake_finish.py` and private variants | Bake material appearance into textures |
| `blender_overlay.py`, `composite_overlay.py` | Render/compose object previews against reference images |
| `product_preview.py` | Compare candidate objects and scene renders with photo views |
| `mp3d_cams.py` | Load photo cameras and render Habitat at corresponding poses |
| `look.py` | Render a scene from explicit eye/target viewpoints |
| `multiview.py`, `glb_preview.py` | Additional inspection/preview helpers |
| `counter_regions.py`, counter build helpers | Counter-region measurement and constructed slab geometry |
| `ghost_extract.py`, `ghost_diag.py`, `ghost_fix.py` | Inspect texture mappings, diagnose ghosts, and apply selected surface patches |
| `kitchen_apply.py` | Delete old scan faces, import replacements, and apply texture patches |
| `usd2glb.py` | Shared full-scene conversion/export; not used in place during continuation |
| `realism_audit.py` | Shared placement checks |
| `sweep.py` | Route-oriented checks used in other build stages; not run in this continuation |

Some roles in this table are broad descriptions of the tool families; the exact implementation and arguments should be read before rerunning them. The observed inventory includes many historical probes and variants that are not part of the current build path.

### Private continuation helpers

| Script in `agentA_resume/` | What it does |
|---|---|
| `resume_kitchen_objects.py` | Backups, parametric object construction, initial private build setup |
| `resume_kitchen_bake.py` | Batch finish-bake operations |
| `resume_kitchen_details.py` | Labels, toaster orientation, frog orientation, caddy support adjustment |
| `resume_kitchen_texture_fix.py` | Surface-sampled color calibration and selected cleanup settings |
| `resume_kitchen_depth.py` | Depth renders used by photo-visibility checks |
| `resume_kitchen_photopaint.py` | Restricted foreground photo projection onto selected objects |
| `resume_kitchen_select.py` | Select cleaner variants after rejecting contaminated projections |
| `resume_kitchen_validate_paths.py` | Check selected models exist; correct selected jug path |
| `resume_kitchen_audit.py` | Component-aware support/footprint/clearance/intersection checks |
| `resume_kitchen_preview.py` | Fresh photo-versus-v15-versus-private comparisons |
| `resume_kitchen_handoff.py` | Machine-readable list of fits and integration changes |
| `resume_kitchen_finalize.py` | Final evidence and preview/build verification |

These helper files document an iterative editing session. Several modify files or apply relative rotations, so they are **not all idempotent**. Rerunning them in an arbitrary order can undo final selections or move objects twice. This guide is an explanation, not a one-command rebuild promise.

## 16. How the scene is built and reaches the dashboard

### 16.1 Scene assembly

```text
Original photos + calibrated cameras + existing scan/working scene
                              |
                 inspect, segment, model, fit
                              |
         object meshes + baked/photo textures + fit.json files
                              |
                  private integration manifest
                              |
       Blender imports working USD, removes selected scan faces,
       inserts replacements, and applies selected texture patches
                              |
                agentA_resume/test.glb
                              |
         Habitat loads scene and renders first-person JPEG frames
                              |
                  SSH tunnel -> local browser
```

The final export used the private `build_private.py`, a private integration copy, and a separate output path. Shared manifests and v15 scene exports were not overwritten during this continuation.

### 16.2 How the dashboard actually displays the result

The dashboard is a server-rendered Habitat view. The browser receives HTML and JPEG frames from `/frame.jpg`. When you press W/A/S/D, the browser posts an action to the server; Habitat updates the agent and renders a new frame.

Your browser is not loading the entire 409 MB GLB directly as a WebGL viewer. Habitat on ISL loads it. That is why the local machine can view the result without downloading the full scene.

The new wrapper imports the shared route-author application, adds a “Repaired kitchen scene loaded” banner, exposes selected comparison images, and provides `/scene-info` for the loaded-scene path. It leaves the shared application source unchanged.

### 16.3 The current ports

| Browser address on this computer | Tunnel target on ISL | Session |
|---|---|---|
| `http://localhost:8767/` | `127.0.0.1:8768` | Repaired scene |
| `http://localhost:8769/` | `127.0.0.1:8767` | Previous v15 session, retained with its unsaved route |

These addresses depend on the SSH tunnels and server processes remaining alive. Port numbers are not scene versions. The dashboard update verified the private scene path, a live JPEG frame, four comparison images, and continued access to the old session.

The previous route had over a thousand actions during the switch. It was retained in its running process. That is **not the same as saving the route permanently**; use the dashboard save controls if you need it after a process or server shutdown.

### 16.4 What the save controls create

| Dashboard action | Output meaning |
|---|---|
| Move/turn | Updates the current agent, frame, and in-memory route |
| Mark landmark | Adds a note at the current route position |
| Save NaVIDA episode | Writes a separate compressed episode JSON with the driven path and instruction |
| Add/remove objects | Changes the running authoring session and navigation conditions |
| Save matched case | Writes baseline/blocked episode records for a case |
| Reset route | Returns to the episode start and clears the driven route in that session |

These controls are separate from the offline kitchen mesh/texture repair. Saving a navigation episode does not automatically rebuild the GLB or patch the original RxR annotations.

The repaired session's output location is `agentA_resume/dashboard/output/218/`. Output filenames such as `pov_route.json.gz`, `baseline.json.gz`, or `blocked.json.gz` describe configured save destinations; they need not exist until the corresponding save operation occurs.

## 17. What is complete and what remains

### Completed and recorded

- Eighteen selected repair entries, including the three newly reconstructed assemblies.
- Photo-informed object placement, dimensions, finish correction, and selected label detail.
- Controlled removal of old scan fragments in the specified regions.
- Component-aware audit across 32 props with no issues at its implemented thresholds.
- Successful private export and fresh comparison/new-angle renders.
- Repaired scene connected to the local dashboard, with the previous route session retained.

### Remaining limitations

- Old object imagery is still visible in parts of the backsplash texture.
- Some wall-adjacent scan fragments remain behind the caddy/knife area and elsewhere.
- Range-deck scan geometry still has visible defects outside the prop pass.
- Frogs, knife handles, jug, and several product profiles remain approximate.
- Metals have a baked, less reflective appearance.
- Hidden-side textures and small lettering are limited by the source views/resolution.
- Original semantic annotations were not comprehensively regenerated for new objects.
- No full navigation benchmark evaluation or route sweep was completed for this private build.

The scene is improved and usable for inspection. The available evidence supports a placement-checked repair pass, not a claim that the whole dataset is now geometrically perfect or fully photorealistic.

## 18. How to inspect the results yourself

### 18.1 Open the current dashboard

On your local computer, open:

```text
http://localhost:8767/
```

Look for **“Repaired kitchen scene loaded”** and expand **“View kitchen repair comparisons.”** The first-person session begins at episode 218's original start, so the initial camera need not point directly at the repaired counter.

### 18.2 Recreate the repaired-scene tunnel if needed

Run from the local repository directory:

```bash
VIS_REMOTE_PORT=8768 bash Task_4/open_visualization.sh
```

This connects to the repaired server session if no dashboard tunnel is already reachable. The launcher reuses an accessible dashboard without checking its scene version; if one is already open, verify the banner or `/scene-info`.

Equivalent direct command, also on your **local computer**:

```bash
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 \
  -L 127.0.0.1:8767:127.0.0.1:8768 guest-isl@172.26.186.222
```

Use an unused local port if 8767 is occupied. For example:

```bash
VIS_LOCAL_PORT=18767 VIS_REMOTE_PORT=8768 bash Task_4/open_visualization.sh
```

Then open `http://localhost:18767/`. This opens a connection to an already running service; it does not restart a stopped Habitat session.

### 18.3 Reconnect to the previous session

If the old route tunnel needs recreating, run locally:

```bash
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 \
  -L 127.0.0.1:8769:127.0.0.1:8767 guest-isl@172.26.186.222
```

Then open `http://localhost:8769/`, provided that original server process is still running. Do not start a duplicate tunnel if the port is already served.

### 18.4 Check which scene is loaded

Open the repaired dashboard's scene-information endpoint:

```text
http://localhost:8767/scene-info
```

The selected path should end in:

```text
/refined/agentA_resume/test.glb
```

### 18.5 Open the latest GLB offline

The latest GLB has not been copied into this guide folder. To download it separately, run on your local computer:

```bash
scp guest-isl@172.26.186.222:/data/robotics/toshith/rxr_author/refined/agentA_resume/test.glb \
  ~/Downloads/kitchen_repaired.glb
```

In Blender, use **File → Import → glTF 2.0** and choose that file. This project's full-building export preserves its source coordinate convention; if a generic viewer presents an unexpected orientation, use its orientation controls rather than modifying the source asset. [Blender glTF documentation](https://docs.blender.org/manual/en/5.1/addons/import_export/scene_gltf2.html)

### 18.6 Read one object's actual selection

After SSHing into ISL, this read-only command displays the toaster fit:

```bash
python3 -m json.tool \
  /data/robotics/toshith/rxr_author/refined/kitchen/objects/toaster_v2/fit.json
```

For the final audit:

```bash
cat /data/robotics/toshith/rxr_author/refined/agentA_resume/audit.json
```

For the repaired dashboard log:

```bash
tail -n 30 /data/robotics/toshith/rxr_author/refined/agentA_resume/dashboard/ui.log
```

These commands inspect the existing state. They do not rebuild or modify the scene.

## 19. Terms and references

### Terms

| Term | Meaning |
|---|---|
| RGB-D | Color image plus depth information |
| Mesh / face / vertex | A surface made of triangles / one surface element / a point defining it |
| GLB | Binary glTF asset containing geometry and usually embedded appearance resources |
| USD / USDC | Scene-description format / its binary representation used by the working scene |
| PLY | Geometry file used here for measurable world-space meshes and scene annotations |
| PNG/JPG | Images used for textures, reference photographs, or previews |
| NPZ | Compressed NumPy arrays, used for cached geometry, cameras, or texture mappings |
| JSON / JSON.GZ | Structured metadata / compressed structured metadata |
| Mask | Foreground-pixel selection for an object or region |
| Silhouette | The projected outline/filled shape of an object |
| UV / texel | Coordinates in a texture image / one texture pixel |
| Bake | Store rendered surface appearance in a texture |
| Parametric | Geometry controlled by explicit dimensions and construction rules |
| Lathe | Geometry created by revolving a profile |
| AABB | Axis-aligned bounding box |
| Convex hull | Smallest enclosing convex shape; can include empty concave space |
| Navmesh | Representation of surfaces an agent can navigate |
| Symlink | File-system reference to another path |
| Manifest | List of integration inputs and operations |
| Patch | A localized geometry, appearance, or code correction; context determines which |

### Public primary sources

- [Matterport3D project](https://niessner.github.io/Matterport/) — source dataset and reconstructed-building context.
- [Official RxR repository](https://github.com/google-research-datasets/RxR) — instructions, guide/follower annotations, and pose traces.
- [Official RxR exploration page](https://ai.google.com/research/rxr/explore) — annotation process and original examples.
- [Official VLN-CE repository](https://github.com/jacobkrantz/VLN-CE) — continuous-environment task and episode/scene organization.
- [Blender glTF documentation](https://docs.blender.org/manual/en/5.1/addons/import_export/scene_gltf2.html) — GLB import/export support.

### Project evidence used for this explanation

- Original user-provided worker handoff and its restrictions.
- Local `Task_4/README.md`, launchers, metadata, and copied visualization tools.
- Installed episode file, inspected directly for fields and counts.
- Photo directory and `.conf` camera-loading code.
- Actual selected `fit.json` files for the eighteen repair entries.
- Shared/general fitting tools and the private construction, calibration, projection, integration, audit, and preview code.
- [Continuation repair report](evidence/repair_report.md).
- [Integration changes](evidence/changes.json), [export/preview verification](evidence/verification.json), and [dashboard connection verification](evidence/dashboard_forwarding.json).

The evidence files and images in this folder are snapshots for understanding this repair. Future edits on ISL can change the active scene without changing this document.
