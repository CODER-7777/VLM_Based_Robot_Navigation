# Product-model search after the toaster experiment

**Update:** the selected AtTheSpeedOf model has now been obtained from a legitimate public CC archive, fitted, audited and inserted into the private repaired scene. Its original PBR maps are retained. See [the installed-model report](../toaster_selected_model/README.md). The search notes below describe the earlier investigation and its then-current authenticated-download limitation; they are historical, not the current installation status.

The user wants real product models of the kind used in advertising, with convincing metallic materials, and has requested **free models**. The reference appliance is identified by the user as a **Black & Decker 2-Slice Toaster, resembling T2030**.

## Results

| Source | What was verified | Decision |
|---|---|---|
| [Black & Decker manufacturer product page](https://blackanddeckerappliances.com/products/bd-toaster-2-slc-wide-ss) | Public Shopify product media for the current TR0011SSA contains six images and no model media entry. This is a current product, not an exact T2030 listing. | Useful photographs; no downloadable 3D asset found on this page. |
| [Toaster by AtTheSpeedOf](https://sketchfab.com/3d-models/toaster-0d39352a32404ce7b71b8ac020844949) | Live public metadata lists CC Attribution and download availability. Artist describes Blender modeling and Substance Painter texturing. Public render shows convincing stainless steel, separate controls and a lever; the shape is still an approximation to the reference. | Strongest new free candidate found in this search. Preview and metadata saved. Actual files have not been obtained. |
| [TOASTER by Pratham on Fab](https://www.fab.com/listings/503368b3-fd49-4a09-bff6-d99f508955b3) | Listed free with FBX and converted GLB/glTF/USDZ formats. Public preview inspected. | Preview is less suitable for the photographed appliance. Not selected or downloaded. |
| [Toaster by Rasmus.Eist](https://sketchfab.com/3d-models/5b811d33065a417c95e8f2ddaf6c0e4f) | Cached licensed catalog entry is CC BY and describes a modeled interior and cable. | Additional candidate; no evidence of an exact Black & Decker match. |
| [Black Decker 4-Slice Toaster Oven](https://www.cgtrader.com/3d-models/interior/kitchen/black-decker-4-slice-toaster-oven) | Model listing has PBR maps and downloadable formats. | Wrong appliance category: an oven, not the photographed pop-up toaster. Rejected. |

No exact, freely obtainable T2030 model file was verified in this search. Retail/product photographs and a rotatable preview are not proof that a reusable model file is publicly offered.

## Download limitation for the strongest candidate

AtTheSpeedOf's toaster UID is `0d39352a32404ce7b71b8ac020844949`. It is marked downloadable with CC Attribution in the current Sketchfab metadata. The official download API requires an authenticated account. No authenticated Sketchfab download access is available in this session. A legitimate fallback through the installed Objaverse archive was attempted; the UID is absent from that archive.

Consequently, **the promising candidate has not been downloaded, fitted, physically audited or inserted**. Its advertising-style render is evidence of the artist's preview, not evidence of how it will render in Habitat. The currently installed experimental Cuisinart substitute is unchanged.

To continue with this candidate, obtain its authorized GLB/glTF download through the listing. The original texture maps and license/author attribution must accompany the model. Once the files are available, preserve its original base-colour, metallic, roughness and normal maps, fit it at a realistic size, check the slot interior and counter clearances, and compare actual Habitat renders against the real photo. Avoid flattening all parts to a single colour. The current Habitat scene pipeline also needs appropriate handling of reflective lighting; an advertising render will not automatically reproduce in the matte/baked stage pipeline.

## Evidence

- `evidence/manufacturer_product.json`: public manufacturer product metadata inspected for model media.
- `evidence/sketchfab_black_decker.json`: public licensed model search for the brand; no matching pop-up toaster in those results.
- `evidence/sketchfab_toaster.json`: current downloadable-toaster search results.
- `evidence/new_candidate.json`: full public metadata and author/license for the strongest new candidate.
- `images/free_candidates.jpg`: contact sheet of official artist preview thumbnails inspected.
- `images/fab_toaster.jpg`: Fab's public render, inspected and rejected as a weaker match.

![Strongest new free candidate, artist preview](images/0d39352a32404ce7b71b8ac020844949.jpg)

The earlier full repaired-scene dashboard is restored separately; see [dashboard notes](../dashboard_restore/README.md).
