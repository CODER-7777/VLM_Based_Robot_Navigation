# Selected licensed toaster: installation and materials

The user's selected [toaster by AtTheSpeedOf](https://sketchfab.com/3d-models/toaster-0d39352a32404ce7b71b8ac020844949) has been downloaded, fitted and inserted into a private copy of the repaired kitchen. This replaces the earlier Cuisinart substitute. The rest of the repaired kitchen and local wall/cabinet repair are retained.

## View it

- [Full repaired kitchen editor](http://localhost:8767/)
- [Photo / previous scene / selected toaster comparisons](http://localhost:8767/comparisons), including the earlier vase/jug, caddy, frogs and other counter objects below.
- [Rotate the downloaded toaster with its original metallic PBR material](http://localhost:8767/product-viewer).

The PBR viewer loads a local copy of Google's model-viewer 4.0.0 and the actual downloaded GLB. Its model loaded successfully and rendered in a real browser check. An initial headless screenshot taken before the asynchronous model load was complete was discarded.

![Selected toaster comparison](images/toaster_comparison.jpg)

## Source and license

The official Sketchfab download API requires an authenticated account. This exact CC-BY model was instead available in a [public Creative Commons archive](https://github.com/traines-source/sketchfab-backup), whose maintainer permits individual model downloads. The downloaded glTF archive includes `license.txt`, geometry and the original texture maps. The author and UID match the selected listing.

- Author: **AtTheSpeedOf**.
- UID: `0d39352a32404ce7b71b8ac020844949`.
- License: **CC BY 4.0**.
- Archive: https://mirror.traines.eu/sketchfab-backup/0d/0d39352a32404ce7b71b8ac020844949.zip
- SHA-256: `b3f607a8c129b16f8ba08b6aaf96108dbe6d1125385119066f3e1e1d3a506ebc`.
- Local original archive and extracted files: `source/`.
- The original embedded branding is Hamilton Beach; the source photograph was identified by the user as Black & Decker, resembling T2030. This is an explicitly chosen approximate product match.

Credit: This work is based on “toaster” by AtTheSpeedOf, licensed under CC BY 4.0. Changes: uniform scaling and placement; separate kitchen-lighting bake for Habitat. The original PBR maps are retained in a separate export.

## Geometry and fit

The model already provides actual 3D geometry, including its bread-slot interiors, guides, lever, dial and buttons. Marketing screenshots were not stitched together or represented as a new measured reconstruction. The calibrated kitchen photograph determines the pose; a uniform scale locks the height at 20 cm.

Final world dimensions are approximately **17.4 × 29.1 × 20.0 cm**. The base is approximately **(4.520, −5.190, 0.929) m**. Its lowest vertex is on the counter surface to floating-point tolerance. The leftmost vertex is X≈4.4325 m, clear of the repaired return at X=4.405 m. The private 32-prop audit reports zero physical-placement issues.

Only the named `Kitchen_toaster_v3_...` node was removed from the private wall-repaired input. All 6,639 other mesh nodes were retained. Shared manifests and original builds were not modified.

## Metal appearance

The asset includes 2K base-color, metallic/roughness and tangent-normal maps. Those maps and the original UV layout are preserved in `world_pbr.glb` and `product_pbr.glb`.

The existing Habitat stage pipeline does not provide the same environment lighting as the artist's viewer. A separate Cycles combined bake uses the photo-derived kitchen panorama plus approximate broad fill lighting to recover highlights clipped by the JPEG panorama. It is an appearance fit, not a measured HDR reconstruction. The dashboard variant therefore has fixed reflections. The standalone PBR viewer uses neutral studio lighting and retains view-dependent metal shading.

![Browser-verified PBR inspection](images/pbr_viewer.png)

The [separate physics / Gaussian visual prototype](../split_render_pipeline/README.md) is a further experiment. Its spherical harmonics approximate the selected toaster's view-dependent appearance from PBR teacher renders; they are not a relightable metallic BRDF.

## ISL files

Root: `/data/robotics/toshith/rxr_author/refined/`.

| Path | Contents |
|---|---|
| `kitchen/objects/toaster_v4/fit.json` | Fit, attribution, support height, union deletion footprint and realism notes |
| `kitchen/objects/toaster_v4/world.ply` | Fitted raw-Z-up mesh for placement checks |
| `kitchen/objects/toaster_v4/world_pbr.glb` | World-positioned original PBR variant |
| `kitchen/objects/toaster_v4/product_pbr.glb` | Centered PBR model for standalone inspection |
| `kitchen/objects/toaster_v4/world_baked.glb` | Separate Habitat-compatible reflection bake |
| `toaster_selected/test.glb` | Private full repaired scene with the selected toaster |
| `toaster_selected/manifest.json` | Private manifest: `toaster_v4` replaces `toaster_v3` |
| `toaster_selected/audit.json` | 32 props; zero placement issues |
| `toaster_selected/assembly.json` | Named replacement and other-node retention evidence |
| `toaster_selected/previews/` | Real-camera comparison and three additional Habitat angles |
| `toaster_selected/dashboard/` | Independent editor on server port 8776 |

The existing presentation proxy on server port 8774 exposes the editor through local port 8767. Earlier simulator sessions remain running; the proxy change does not erase their routes.
