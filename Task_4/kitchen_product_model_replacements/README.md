# Kitchen product models and surface refinement

The new scene is staged on ISL at `/data/robotics/toshith/rxr_author/refined/kitchen_product_replacements/home_pbr_products.glb`. This file renders polygon meshes and PBR materials directly. It is separate from the experimental Gaussian renderer. The calibrated browser review passed for all 22 selectable objects; the corrected grinder also passed its final full-scene review. The verified scene is now published on remote port 8774 through the local port 8767 tunnel. Ten objects were revised; the other objects remain clearly labelled as retained.

## What changed

The photographs guide the object silhouette, finish and scale. Free downloadable models were reviewed from Sketchfab/Objaverse and BlenderKit. A candidate was rejected when its product shape was less faithful, even if it had more polygons. The reviewed high-detail C90 coffee machine and the closed crank grinder therefore were not substituted for the existing closer silhouettes.

| Object | Fitted folder | Triangles | Method and remaining differences |
|---|---|---:|---|
| glass_kettle | `objects/glass_kettle_v5/` | 32446 | Downloaded glass electric-kettle substitute with clear glass transmission, detailed spout and curved handle. The photo has a rounder body and a different lid. |
| knife_block | `objects/knife_block_v5/` | 27120 | Downloaded detailed knife holder and five knives, with rounded black handles, steel rivets, baked wood grain and the native sharpening stone. The holder profile and missing scissors differ from the photo. |
| range_kettle | `objects/range_kettle_v5/` | 128972 | Original licensed kettle restored as separate steel and plastic parts, with a subdivided curved body and true reflective PBR metal. The body profile remains a substitute. |
| knife_block_round | `objects/knife_block_round_v5/` | 65844 | Photo-built oval holder with smoothly rounded stainless-steel handles. Small rim bevels preserve the holder profile; the exact knife blades and cap slots remain approximate. |
| grinder | `objects/grinder_v5/` | 28156 | Photo-built open-hopper grinder retained for silhouette fidelity. Licensed wood texture applied to its dark case; edges beveled and metal parts smoothed. The texture source is a knife holder, not a downloaded grinder model. |
| phone | `objects/phone_v5/` | 39948 | Existing licensed desk phone retained with its photo-fitted labels and controls. Casing edges receive a small physical bevel and smooth shading. Alternative free phones were reviewed, but did not improve the photographed layout. |
| tea_tray | `objects/tea_tray_v5/` | 107304 | Downloaded ceramic teapot with curved handle and spout, photo-coloured reactive glaze. Tray retained; sugar jar rebuilt from the photo. Decorative glaze details remain approximate. |
| hot_tap | `objects/hot_tap_s4_style_v5/` | 57848 | Licensed antique-faucet spout combined with a photo-shaped slim stem, flange and lower lever. Bronze patina texture is procedural; the exact original tap is not reproduced. |
| coffee_machine | `objects/coffee_machine2_v5/` | 12272 | Earlier licensed Nespresso substitute retained because it more closely matches the photographed silhouette. Curved housing receives two levels of Catmull-Clark subdivision with hard-edge creases, and chrome is restored to reflective PBR. Fine controls still differ. |
| frother | `objects/frother_v5/` | 37308 | Downloaded Aeroccino ribbed body and lid adapted to the handle-free black photographed type, with a photo-shaped subdivided base and chrome collar. Exact logo, lid and power cable details remain approximate. |

## Smoothing and subdivision

- Coffee-machine housing: two Catmull-Clark levels, with creases on construction edges. The rounded housing is refined while retaining its existing layout.
- Licensed stovetop kettle: one Catmull-Clark level on the curved body, smooth normals, original separate steel and plastic meshes.
- Glass kettle: one Catmull-Clark level on its glass shell; original lid, spout, handle and measuring marks remain separate.
- Teapot: one Catmull-Clark level. The sugar jar uses an interpolated lathe profile and an additional subdivision level.
- Downloaded knife set: native subdivision modifiers evaluated at at least two levels on the rounded handles. The holder retains its artist-supplied edge treatment.
- Round holder: dense lathed handles with one subdivision level; small bevels preserve the holder rim.
- Frother: native detailed ribbed body and lid, with a dense subdivided photo-shaped base. The handle and large buttoned base were removed to resemble the photographed handle-free type.
- Telephone and grinder: small physically sized bevels and smooth normals. Flat housings and labelled keys are preserved rather than indiscriminately subdivided.

Subdivision changes geometry. It cannot invent an exact product shape or recover unseen lettering. Some objects therefore remain approximate substitutes.

## Materials

Metal uses reflective PBR metallic/roughness values. The camera-dependent highlights remain a renderer calculation; they are not painted into a flat replacement texture. The glass model exports transmission, although browser transmission is still an approximation.

The licensed knife holder supplies real wood texture detail. Its wood material was baked as base colour for glTF export. The grinder uses the original packed tileable diffuse wood image on its photo-built dark case, with a darker PBR colour factor, while retaining its earlier photo-derived drawer detail. The baked knife-holder UV atlas is not reused as a tiling texture. This is a wood-texture adaptation, not a newly downloaded exact grinder model. The tea setting uses procedural turquoise/brown reactive-glaze colour, and the tap uses procedural bronze-patina colour. Multi-object colour baking uses distinct UV atlas tiles to avoid one object overwriting another. Reflections and lighting are not baked into these colour maps.

Imported multi-material GLBs can become groups containing several meshes in Three.js. The viewer now recognizes those groups and their descendants as kitchen props so their PBR materials remain active. Previously a child without a `Kitchen_` name could be mistaken for a photographic scan surface.

## Placement and verification

Counter support heights are 0.929 m for the sink/range-side runs, 0.935 m for the preparation counter and 0.991 m for the stovetop grates. Bounds are recomputed after subdivision and evaluated modifiers. Object scales use meaningful metre dimensions. The new fit files use identity placement matrices because their PLY geometry is already in the world frame. Deletion polygons are convex unions of old footprints and new extents.

The staged manifest contains 33 audited props. The latest audit reports no support/contact or overlap failures. Two generic size flags remain: the telephone bounding box includes its cord (about 0.316 m), and the retained miniature creamer is about 0.051 m tall. These are recorded, not silently called a zero-issue audit.

The original toaster retains its 11 mesh parts and all three original PBR texture-map bytes. `original_material_verification.json` on ISL records their SHA-256 hashes.

`capture_products.py` checked all 22 selectable objects, counter contact and original toaster maps in Chrome, then captures calibrated photograph viewpoints and additional room views. These real browser captures produce the new comparisons. Generated or retouched raster images are not used as evidence.

## Views and provenance

- Live comparison dashboard: `http://localhost:8767/`.
- Kitchen object view: `http://localhost:8767/kitchen-room?object=range_kettle`.
- Standalone models: `http://localhost:8767/models`.
- Independent saved-model review: `http://localhost:8768/`; this is a studio model view, not a full-room after comparison.
- The new comparison labels mean **Real photograph / Earlier repaired mesh / Current repaired mesh**. The earlier column already contains repairs from the prior work. It is not the untouched dataset and is not a Gaussian view.
- Older Gaussian comparisons remain available through the archive links. No Gaussian training or splat conversion is performed by this revision.

## Sources

| Asset | Author | Licence | Source |
|---|---|---|---|
| Electronic Kettle | Grifonov | by | [Listing](https://sketchfab.com/3d-models/bba458a4a294440b95c7fe486d3a3d45) |
| Knife Holder with a Cutting Board | Patrik  | royalty_free | [Listing](https://www.blenderkit.com/asset-gallery-detail/967b767b-cd43-44f8-94c4-e3af008da71b/) |
| 2-Quart Circles Teakettle | cc0archviz | by | [Listing](https://sketchfab.com/3d-models/631ac0b616974530a481b3390fd72b82) |
| Desk Phone01 01 | dangkhoa208 | by | [Listing](https://sketchfab.com/3d-models/0821bac7ef4e4be9a2b26664ffc16213) |
| Ceramic teapot | pityafinwe | by | [Listing](https://sketchfab.com/3d-models/0deff0a5da2546f9a52cdd42dcc2d4fb) |
| antique faucets | hemantcbr | by | [Listing](https://sketchfab.com/3d-models/c30c4323bb124630bd49c3d9073880a3) |
| Nespresso Coffee Machine | ekorneeff | by | [Listing](https://sketchfab.com/3d-models/nespresso-coffee-machine-5fb141555e74489ba79e588838f8562a) |
| Aeroccino 4 Milk Frother | Andy Machin | royalty_free | [Listing](https://www.blenderkit.com/asset-gallery-detail/b6507fb3-8156-40ee-9825-9dca8edfb85a/) |

Exact brand and product matches are not claimed. The fitted licence and source credit are stored in each `fit.json`. The free-model search did not find a faithful replacement for the photographed paired frog sculptures; their existing approximate mesh is retained and labelled as such. The scan background still has missing/distorted geometry, which this object refinement does not fully reconstruct.

## Directory contents

`sources/` contains downloaded originals. `prepared/` contains source inspection reports and images. `current/` holds the earlier fits and meshes needed for comparison. `objects/` contains each new standalone model, world-placed model, audit geometry and fit file. Draft native Blender snapshots are archived on ISL under `kitchen_product_replacements/native_versions/`; final GLBs and texture-correction scripts are authoritative because later material and silhouette corrections followed those snapshots. `images/` contains source thumbnails, isolated inspection renders and actual browser captures. `web/` contains the private presentation pages. `evidence/` contains modelling, placement, merge, audit, capture and publication scripts plus logs.

Shared kitchen manifests, shared converters and the Gaussian/navigation services are preserved. New files and an owned presentation wrapper carry this revision.

## Final publication checks

The published HTTP check verifies seven routes, 88 JPEG panels, 25 fitted-model files, GLB range delivery and lossless compressed scene delivery. The published browser check covers all 22 object selections and their three comparison panels, room links and individual-model links. Publication preserved the existing navigation camera state and did not restart the navigation or Gaussian services.
