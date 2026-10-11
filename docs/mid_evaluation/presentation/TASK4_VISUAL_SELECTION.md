# Task 4 — panorama, POV and important comparisons

[Slide 9](SLIDE_TEXT.md#slide-9--task-4-beforeafter-panoramas-and-home-tour-views) covers the polygon/PBR branch. Slide 10 covers the Gaussian branch. Do not label the repaired PBR panorama as Gaussian output.

## Primary images

| Image | Representation and revision | What it establishes |
| --- | --- | --- |
| [Panorama overview](assets/task4_panorama_before_after.jpg) | Original photographic panorama above; repaired PBR scene below | Whole-room comparison from one calibrated position; scan gaps remain |
| [Sink/toaster POV pair](assets/task4_panorama_sink_pov.png) | Actual saved v6 panorama viewer screenshot | Matched direction, toaster/material/support differences and remaining wall gaps |
| [Range/phone/grinder POV pair](assets/task4_panorama_range_pov.png) | Actual saved v6 panorama viewer screenshot | Placement and approximate shape differences across several important props |
| [Home walkthrough](assets/task4_home_tour_walk.png) | Earlier home-tour browser screenshot | First-person inspection interface; not current v6 evidence |
| [Toaster inspection](assets/task4_home_tour_toaster.png) | Earlier home-tour browser screenshot | In-room product inspection and retained toaster materials |
| [Blue jug photograph](assets/task4_blue_jug_real.jpg) / [v6 room capture](assets/task4_v6_blue_jug_pov.png) | Original photograph versus actual v6 browser capture | Rendered cobalt body/handle; generic proportions remain |
| [Phone dock](assets/task4_v6_phone_dock_pov.png) | Actual v6 browser room capture | Restored active handset/dock; base and controls remain approximate |
| [Product contact sheet](assets/task4_product_comparisons.jpg) | Earlier saved product revision, three-column comparisons | Real photograph / earlier repaired mesh / current repaired mesh within that revision |
| [Gaussian corner comparison](../figures/task4_corner_before_after.jpg) | Separate earlier Gaussian revision | Changed local floating/speckled artifacts; does not validate latest all-kitchen novel views |

The before panorama is assembled from original dataset skybox photographs, not an untouched scanned mesh. The after panorama comes from browser PBR room captures. The original untouched mesh was unavailable. Both full panoramas are 4096×2048, assembled from six directions; this does not reveal occluded geometry or demonstrate navigable robot collisions.

Five saved camera positions cover sink/toaster, corner/bottles/knife blocks, range/telephone/grinder, tea/glass kettle and coffee/cordless phone. The sink and range screenshots give useful detail at presentation scale; the overview conveys coverage. Images are copied unchanged, not retouched.

## What the visual analysis suggests

- Replaced props have inspectable polygon geometry and explicit materials, but some substitute silhouettes differ visibly from the photographs.
- The sink comparison still exposes missing/distorted wall/cabinet regions. Object replacement does not repair the full scan automatically.
- The range pair makes placement and shape differences visible without changing viewpoints independently. Lighting and local stitching/parallax can still differ.
- The restored dock is a geometry/catalog fix, not proof of exact product recovery.
- Material/browser publication checks and calibrated photo comparisons do not establish photorealistic novel-view accuracy or collision-valid robot interaction.

## Evidence and next measurement

[Panorama verification](assets/task4_panorama_verification.json) records five synchronized positions, linked rotation/zoom/reset, no browser errors and coverage of 23 photo-comparison objects. [v6 browser review](assets/task4_v6_browser_review.json) records 30 room/model selections, 23 calibrated captures and remaining visual approximations. These are saved checks, not a new server access or live browser verification.

Next: freeze camera poses and compare silhouettes, support/scale, missing surfaces and material appearance. Evaluate Gaussian held-out RGB/depth separately. [Original panorama methodology](../../../Task_4/kitchen_panorama_compare/README.md).
