# RxR bedroom avoidance and toiletries delivery

> Source publication: images, recordings, generated catalogs, dataset assets and runtime reports referenced below stay local. See the Task 5 reproducibility guide for required inputs.

Scope: both complete RxR validation guide splits; original guide length >=40 m. All 22,465 instruction records / 2,761 distinct paths were rechecked. Exactly 28 distinct original paths (204 instruction variants) pass the length filter. Length is the 3D connectivity-edge sum, not shortest distance or a robot rollout.

## Individual task 1: avoid Nora's sleeping room

The statement is a **constraint**, without a destination. For standalone screening we retain each RxR route's existing destination and propose a separate bedroom as Nora's room. Nora's identity and sleeping state are authored memories.

**25 compatible source routes**, of which **2 are stronger entrance-adjacent candidates**. The other 23 only have an avoidable bedroom elsewhere in the connected scene. They are weak compatibility matches, not validated avoidance challenges.

| Split | Scene | Path | Original m | Candidate Nora region | Evidence |
|---|---|---:|---:|---|---|
| val_seen | E9uDoFAP3SH | 15740 | 46.67 | 0 | Original start has a graph connection into this bedroom; route stays out. Bed visually checked. |
| val_seen | EDJbREhghzL | 11513 | 40.46 | 6 or 12 | Route passes graph connections into these bedrooms; stays out. Both beds visually checked. |

All compatible IDs and proposed rooms: [CSV](nora_all_25_compatible_routes.csv), [per-room JSON](nora_compatible_original_routes_room_options.json). Three excluded source routes: B6ByNegPMKs/13062, dhjEzFoUFzH/4176, ur6pFq6Qu1A/15896 (no assignable bedroom in the route's connected graph component).

**No nontrivial bedroom-shortcut avoidance case was demonstrated** among these 28 routes: removing a traversed bedroom either blocks the required connection, or the candidate forbidden room is not on the reference/shortest route. Do not claim the constraint forces a reroute. Node exclusion also does not prove an edge or continuous trajectory never clips a room.

## Individual task 2: bring toiletries to Riya's bed

**1 original bed-goal source route**: val_seen / VFuaQ6m2Qom / path **5721**, **41.517564 m**, bedroom region **21**, bed object **447**. The original goal panorama is about **0.420 m** from the annotated bed box; all four original goal views were reviewed and show the bed. The variants disagree on the original stop cue (bed/door/portrait/living area); the new task uses the physical bed, not an alleged original toiletries instruction.

**0 unmodified original routes already satisfy bathroom pickup followed by a bed goal.** Path 5721 needs a pickup detour. A storage routine is an authored assumption; the original scene does not establish Riya's ownership or visible toiletries at that location.

## Combined task and concrete candidate

> Riya is packing for her trip. Bring her toiletries to her bed. Don't go through Nora's room; she's sleeping!

Proposed memory: Riya's toiletries are beside the downstairs bathroom sink (region 20), her bed is in region 21, and Nora's bedroom is region 26.

The adapted path preserves every original guide step in order, inserts a bathroom pickup, and ends at the original bed-adjacent goal. **51.132731 m** (extra **9.615167 m**). This is **one authored source-route adaptation**, not another original RxR route. It stays outside region 26 at all graph nodes. Nora's room is a negative constraint here; no shortcut conflict is demonstrated.

[Scenario, exact path and memories](environment_06/scenario.json); [all pickup/forbidden-room variants](all_authored_pickup_adaptations.json). These 38 variants share one original source route and must not be counted as 38 distinct RxR trajectories.

Navmesh adjacent pairs connected: True. Floor-snapped edge geodesic sum: 51.632739186286926. This is a separate metric, not an executed route or continuous forbidden-room verification.

## Additional bathroom-route adaptations

Seven other original long routes visit a bathroom but end elsewhere. Appending a bed delivery leg changes their goal. These are secondary authored candidates, not original bed-goal matches. Some pass the delivery room early and then travel elsewhere; preserving their whole guide path is inefficient and must not be described as a shortest fetch route.

| Split | Scene | Source path | Original m | Shortest added-leg version total m | New bed region |
|---|---|---:|---:|---:|---:|
| val_unseen | 2azQ1b91cZZ | 720 | 40.28 | 45.82 | 21 |
| val_unseen | EU6Fwq7SyZv | 1119 | 48.94 | 86.94 | 1 |
| val_unseen | QUCTc6BB5sX | 4468 | 40.26 | 43.74 | 6 |
| val_unseen | QUCTc6BB5sX | 5255 | 46.07 | 59.29 | 5 |
| val_unseen | QUCTc6BB5sX | 11065 | 47.24 | 63.34 | 5 |
| val_unseen | QUCTc6BB5sX | 11830 | 41.17 | 57.27 | 5 |
| val_unseen | QUCTc6BB5sX | 12136 | 46.24 | 76.67 | 6 |

[All bed/forbidden-room extension options](bathroom_source_delivery_extensions.json), [one best unconstrained extension per source](toiletries_7_bathroom_route_extensions.csv). Images and continuous movement for these new goals still need validation before use.

## Images, placement and reproducibility

[Room images (PDF)](room_evidence.pdf); [image review](review.html). All room images are static renders of original MP3D geometry, not AI-generated reconstructions. Missing geometry and black mirror regions are source scan artifacts.

The toiletries placement uses two photographic Google Scanned Objects models, a conditioner tube (19.21 cm) and boxed eye cream (4.90 cm), with original physical scale and CC BY 4.0 attribution. The cream is a retail carton, not an unpackaged jar. [Credits](environment_06/asset_credits.json), [measured support normals/heights and transforms](environment_06/placements.json), [placed front view](environment_06/toiletries_placed/sink_front.png), [side view](environment_06/toiletries_placed/sink_side.png). These are newly added task props, not original observed toiletries. Static placement is distinct from grasping, carrying and delivery execution.

Every original route and rejection remains in [28-route audit CSV](all_28_room_audits.csv) and [JSON](all_28_room_audits.json). Sources: cached official RxR guides/connectivity; existing server MP3D .house/GLB assets. The official [.house format and room labels](https://github.com/niessner/Matterport/blob/master/data_organization.md) define the room evidence. No policy, collector or training run was changed.

Rebuild: `python3 -B search_room_tasks.py`, `python3 -B prepare_adaptations.py`, prepare/render the scene assets, then `python3 -B build_review.py`. The simulator renderer requires the existing server Habitat environment. Geometry fit does not certify physical stability or manipulation.
