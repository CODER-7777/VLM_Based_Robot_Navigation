# RxR routes at least 40 m: school-bag and sofa search

> Source publication: images, recordings, generated catalogs, dataset assets and runtime reports referenced below stay local. See the Task 5 reproducibility guide for required inputs.

Searched both complete public validation guide splits from the [official RxR release](https://github.com/google-research-datasets/RxR), using the authors' [Matterport navigation graphs](https://github.com/peteanderson80/Matterport3DSimulator/tree/589d091b111333f9e9f9d6cfd021b2eb68435925/connectivity). No full scene/model download or model inference was needed. Existing server semantic files and cached goal views were reused.

| Split | Guide instruction records searched | Distinct paths searched | Paths >=40 m | Instruction variants on those paths |
| --- | ---: | ---: | ---: | ---: |
| val_seen | 8,813 | 1,244 | 14 | 78 |
| val_unseen | 13,652 | 1,517 | 14 | 126 |

All 204 long-route annotations and 28 distinct paths are saved. English annotations cover 25 paths; three seen paths have only Hindi/Telugu instructions. Their endpoints were also checked with scene semantics. All reference edges passed included/unobstructed graph checks.

## Shortlist

| Use | Split / scene | Original RxR path / instruction ID | Reference route (m) | Direct (m) | Endpoint evidence and limit |
| --- | --- | --- | ---: | ---: | --- |
| Riya school-bag adaptation | val_unseen / 2azQ1b91cZZ | 5495 / 14610 | 41.476140 | 9.148139 | Same-region side table object 351, 0.447 m from the goal panorama to its oriented box. Cached views show the door and side table; no visible bag. The routine must be an authored memory. |
| Sofa candidate | val_seen / VFuaQ6m2Qom | 4224 / 123271 | 49.367640 | 16.136824 | English variants 123270/123271 name brown sofas at arrival. Semantic couch 316 is in the same region, 2.018 m from the goal panorama to its box. Variant 86347 names a chair, and a chair is closer. Rendered goal views contain both sofa and chairs; strict sofa-only labeling remains ambiguous. |
| Sofa-adjacent backup | val_seen / VzqfbhrpDEA | 1662 / 4025 | 40.200356 | 24.908583 | Semantic couch 1618 is in the same region, 0.836 m from the goal panorama to its box. Original stop cues are fireplace/TV/window, not the sofa itself. |

The first route is already in your collector catalog as **RxR-CE episode `2azQ1b91cZZ_4240`**, with its stored continuous-environment reference-waypoint length **41.491573 m**. Original RxR instruction ID **14610** and RxR-CE episode ID **4240** are different identifiers. The small length difference comes from their respective saved coordinates. Sofa IDs above are original RxR IDs; a corresponding RxR-CE episode ID has not been verified.

### School-bag conclusion

No >=40 m English validation instruction explicitly identifies a school-bag destination or documents where children routinely keep bags. A generic bag is explicitly mentioned at the endpoint of unseen **QUCTc6BB5sX / path 7767 / instruction 21792**, but that route is only **7.952043 m**. It fails the length requirement and does not establish that the bag belongs to a child.

The unseen 41.48 m hallway-table route is a usable **authored adaptation**, not a confirmed original school-bag task. Suggested task: “Quick! Riya's bus is here! But she still needs her school bag.” Suggested memory: “Riya said: I usually leave my school bag on this little table beside the door.” Treat that memory as a new scenario assumption. No bag pickup or bag visibility is established by these cached views.

Your previous **EU6Fwq7SyZv_10664** school-things scenario has a stored RxR-CE sparse reference length **39.206777 m**, so it does not meet >=40 m under that metric. Its original endpoint is near a bed, chair and ottoman; it is not an original bag-location annotation.

### Sofa conclusion

The strongest instruction-supported >=40 m sofa candidate is **seen-validation path 4224**. It is not unanimously labeled: English variants disagree between a sofa and a chair. Path 1662 is a physically sofa-adjacent backup with a different original stop landmark. The third same-region sofa-near endpoint, seen path 7512 (**43.430021 m**, couch box **2.511 m** away), explicitly stops at steps and was not selected as a strict sofa goal.

No confirmed sofa endpoint was found among the **14 original unseen guide paths >=40 m**. A sofa mentioned along the route does not make it the goal. Labels such as `sofa#chair` with normalized category `chair` were excluded from true-sofa checks. Geometry alone does not establish line of sight, accessibility to the furniture, or object interaction.

## Files and metric

- [Shortlisted routes with full original instructions, reference positions, viewpoints, and evidence](shortlisted_routes.json)
- [All 28 long trajectories](all_long_validation_trajectories.csv)
- [All 204 original instruction records on long routes](all_validation_routes_ge40m.json)
- [Endpoint semantic checks](semantic_endpoint_checks.json)
- [Entry-table cached goal views](goal_evidence/bag_table_goal_contact_sheet.jpg)
- [Route diagrams](shortlisted_route_maps.png)
- [Official source URLs, revision and SHA-256 hashes](search_summary.json)

Route length is the **sum of 3D distances between consecutive original guide viewpoints**. It is not model rollout length, direct distance, shortest-path length, or RxR-CE dense action-trace length. None of the paths were lengthened or joined to meet 40 m. MP3D positions are **Z-up**; do not paste them into Habitat's Y-up agent pose without conversion and the source episode's height convention. Exact original viewpoint sequences and heading are retained in JSON. Semantic distances use the `.house` panorama center and object oriented box; they are geometric proximity checks, not traversable/geodesic distances. All instructions retain their original split; sofa results are explicitly **val_seen**, not unseen.

The live collector and its unfinished sample were not changed.

## Complete goal-image review

All 28 routes now have four static RGB goal views each (**112 PNG images**), rendered from the existing Matterport scene files on physical GPU 0 without a navigation policy or changes to the collector. The images cover **26 distinct physical endpoints** because two endpoint pairs are shared. These are all long-route goals, not 28 established school-bag locations.

- [All 28 goal contact sheets: PDF](goal_images_28/all_28_goal_contact_sheets.pdf)
- [All original PNG images and metadata: ZIP](rxr_28_goal_images.zip)
- [Overview](goal_images_28/overview_all_28.jpg)
- [Image verification](goal_images_28/image_verification.json)

The rendered patio goal for path 4224 shows both sofas and chairs. The path 1662 goal shows a couch beside the fireplace/TV. The school-bag adaptation remains an authored memory, not a verified household routine.

## School-bag furniture refinement

The user clarified that a bag need not be visible: tables, sofas, sofa chairs, beds and chairs can establish a plausible school-bag place when paired with the appropriate memory. Every one of the 112 goal views was reviewed individually within the full-resolution route contact sheets. The resulting visual selection keeps **8 routes / 7 distinct goal locations**, separates **6 weaker routes**, and rejects **14 routes**. The current decision table and images are in [schoolbag_review/README.md](schoolbag_review/README.md); [eight kept route images](schoolbag_review/schoolbag_candidates_8.pdf). This supersedes broad generic-bag/storage interpretations and a visible-backpack requirement. No original RxR household routine is asserted.
