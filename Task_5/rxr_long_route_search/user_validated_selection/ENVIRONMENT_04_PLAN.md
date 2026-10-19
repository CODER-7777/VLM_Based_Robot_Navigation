# Environment 04: two school-bag placements

User validation, 2026-10-15: accept review images **4, 5, 6, 7, 8, 9, 10, 16, 17, 18, 26, 27**. This selection supersedes the assistant's earlier furniture shortlist. Image numbers are contact-sheet indices, not episode IDs.

First scene: **SN83YJsR3w2**, RxR **val_seen**, **path 12519**. Original guide route length: **47.31 m**, ending at the double-door threshold. This length does not establish the shortest navigable distance to either sofa.

User-requested objects:

1. `bag_brown_sofa`: one school bag on the brown seating visible in goal heading 90 degrees.
2. `bag_pink_sofa`: one school bag on the pink upholstered seat beside the fireplace, visible in goal heading 0 degrees.

## Implementation sequence

1. Load the original scene and route in an isolated scenario configuration. Keep the original scene assets and RxR annotations intact.
2. Render close views plus depth around each seat. Identify a seat-cushion support point in simulator world coordinates from depth/raycasting and inspect nearby mesh geometry. Do not infer exact 3D placement from the contact sheet alone.
3. Add the downloaded textured backpack as a separate simulator object at each seat. Begin with its approximately 44 cm height. Align its bottom with the cushion, orient it naturally and check that it neither floats nor intersects the furniture. Record model, object IDs, position, rotation and scale in a placement configuration. Distinct appearance can be used if needed; the two downloaded models have different scale/format requirements.
4. Render both bags from close views, the original goal and several navigable approach positions. Inspect support contact, occlusion, size and visibility; save labeled previews for the user.
5. Define accessible standing goals beside each seat; the robot goal is on navigable floor, not on the cushion. Check connectivity from the original start and report the original guide length separately from each resulting navigable route length. Recheck the >=40 m requirement for the chosen route metric.
6. Use explicit authored school-bag memory to distinguish Riya's target when both bags are present. For example, one trial assigns Riya's bag to the brown sofa; a second assigns it to the pink seat. The situational instruction can remain “Quick! Riya's bus is here! But she still needs her school bag.” If either bag is allowed, define both as valid goals instead. A two-target task must not silently use a one-target success check.

Current status, after the user's approval: **both objects inserted into an isolated simulator and rendered; placements visually checked**. Measured coordinates, previews and reachable approach goals are saved in `../environment_04/`. The original scene assets and active dashboard were not changed. The shortest approach paths are 19.15 m and 22.99 m, although the original RxR guide length is 47.31 m; the original long guide route has not been fully reproduced on the current continuous navmesh. See `../environment_04/README.md` for measurements and limitations.
