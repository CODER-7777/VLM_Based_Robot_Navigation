# School-bag places: visual review of every goal view

User criterion: the school bag need not be visible. A plausible usual school-bag spot may be a table, sofa, sofa chair, bed or chair, with a memory establishing that Riya leaves her school bag there.

Reviewed all **112 views** at the 28 original RxR goals, using original-resolution four-view contact sheets and recording a separate observation for each heading. Furniture close to the goal was assessed; furniture passed earlier along the route does not qualify. Bathroom, garage/golf-equipment, church and bare outdoor-door goals were excluded. Merely seeing another kind of bag, general cupboards or storage does not qualify.

**Keep: 8 routes, 7 distinct physical endpoints.** These are plausible indoor furniture candidates, not original RxR school-bag task labels. Six weaker routes (5 distinct endpoints) are preserved separately. Fourteen routes were rejected. No school-bag visibility requirement was imposed, and no bags or objects were added to the images.

| Review image number | Split | Scene | RxR path | Length (m) | Furniture to use |
| --- | --- | --- | ---: | ---: | --- |
| 04 | val_seen | SN83YJsR3w2 | 12519 | 47.31 | Living-room end table |
| 06 | val_seen | VFuaQ6m2Qom | 5721 | 41.52 | Bedroom bed or desk/chair |
| 10 | val_seen | VzqfbhrpDEA | 1662 | 40.20 | Indoor sofa / ottoman |
| 16 | val_unseen | 2azQ1b91cZZ | 1233 | 40.76 | Living-room chair or side/coffee table |
| 17 | val_unseen | 2azQ1b91cZZ | 5495 | 41.48 | Hallway table beside door |
| 18 | val_unseen | 2azQ1b91cZZ | 9926 | 45.53 | Indoor armchair or side table |
| 26 | val_unseen | QUCTc6BB5sX | 11065 | 47.24 | Study desk / padded chair |
| 27 | val_unseen | QUCTc6BB5sX | 11830 | 41.17 | Study desk / padded chair |

**Best school-departure match: image 17 / 2azQ1b91cZZ / path 5495**, the hallway table beside the door. For a study-chair setting, images 26 and 27 are different routes to the same study. For a bed setting, image 06 is the bedroom. For a sofa setting, image 10 is the indoor lounge sofa.

Each selection requires a specific authored memory naming the chosen item, e.g. “Riya said: I usually leave my school bag on this table beside the door.” This is the supplied scenario context, not a claim that the photographs independently establish a child's routine. Some original RxR stop landmarks are a doorway/window/fireplace; the furniture is nearby. If the chosen furniture requires moving the endpoint, recompute the route after that move instead of retaining the original length automatically.

Files:

- `schoolbag_candidates_8.pdf`: the eight kept route contact sheets.
- `keep_8/`: 32 original PNG views, annotated contact sheets and selection metadata.
- `schoolbag_weaker_candidates_6.pdf` and `weaker_6/`: office, patio, kitchen/bar and loft alternatives with reasons.
- `all_28_schoolbag_decisions.csv/.json`: keep/weaker/reject reason for every route.
- `all_112_image_reviews.csv`: separate observation for every goal image.

Earlier “28 routes” referred to all >=40 m validation paths, not 28 school-bag matches. This review supersedes broad generic-bag/storage-place interpretations. Original RxR files and the complete 28-route image collection are preserved.

## Downloaded school-bag models

`schoolbag_3d_model/jansport_backpack.glb` is the primary blue textured school backpack, approximately 44 cm tall, from Google Scanned Objects via SceneView (CC BY 4.0). `schoolbag_3d_model/jansport_four_views.jpg` previews its actual geometry and texture. A black school-backpack alternative is included as `school_backpack.glb`. See `schoolbag_3d_model/README.md` for source links, attribution and validation. `schoolbag_3d_models.zip` packages both models, previews, metadata and attribution. No model has been placed; localization and furniture selection remain with the user.
