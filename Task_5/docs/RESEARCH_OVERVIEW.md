# Research overview

## Question and method

Can a navigation agent resolve a household request using relevant memories, visible landmarks and the speaker's context? Examples include an authored school-bag storage location, a room nickname, the speaker's desk, and an intermediate room before a final destination.

1. **Benchmark audit.** Compare instruction counts and distances actually defined by released annotations. The [benchmark table](benchmark_route_lengths.md) records source revisions, exclusions and availability as checked on 14 October 2026. Its distance definitions are not interchangeable.
2. **Long-route screening.** Search both public RxR validation guide splits and sum consecutive 3D graph edges. Check reference edges are included and unobstructed. Preserve original splits/routes and distinguish instructions from unique paths.
3. **Endpoint review.** Render four headings per original goal: 112 views for 28 routes, covering 26 distinct physical endpoints. Furniture visible in a panorama is candidate evidence, not proof of an intended goal or reachable storage surface.
4. **Authored adaptations.** Add fictional routines, ownership and aliases as explicit memories. Investigate placement using support surfaces, normals and object height. Keep original scene assets unchanged and record transforms separately.
5. **Human collection.** Record manual navigation, chosen memories, screen/microphone data and corrected reasoning through a shared authenticated website. Track intermediate stops for multi-destination tasks.

## Findings and interpretation

| Item | Result | Interpretation |
| --- | --- | --- |
| Original validation paths `>=40 m` | 28: 14 seen, 14 unseen | 204 instruction variants; not 204 unique routes |
| Full goal review | 112 rendered headings | 26 distinct endpoints; shared goals are not independent locations |
| Research-owner furniture shortlist | 12 review indices | Supersedes the earlier assistant shortlist; household routines remain authored |
| Contributor presentation tasks | 41.49 m and 45.54 m | Strictly `>40 m` reference lengths for two existing presentation tasks |
| Owner authored cases | Multiple destinations, alias, ownership | Three cases in one scene; approximately 16.57, 21.76 and 21.34 m reference lengths |
| Bedroom-avoidance screening | 25 compatible sources, 2 stronger entrance-adjacent candidates | No nontrivial forced shortcut rerouting was demonstrated |
| Toiletries task | One bed-goal source route with a proposed pickup detour | Adapted path, not an unmodified RxR task |

Details remain in the historical [route search report](../rxr_long_route_search/RESULTS.md) and [room task report](../rxr_long_route_search/room_tasks/RESULTS.md). Their image/result links refer to locally generated artifacts excluded from GitHub. The current 12-index selection is in [reviewed_goal_selection.json](reviewed_goal_selection.json).

## Demonstration protocol

Choose an assigned task and relevant memories, create a sample, then start screen and microphone recording. After Chrome's share chooser closes, use the explicit fullscreen/start action. Navigate manually and explain meaningful decisions using:

> Need → relevant memory → visible evidence → next decision.

Stop at the intended destination. Multi-destination tasks must visit the intermediate location first. Written reasoning is a participant-supplied correction, not automatic speech transcription. Audio and written reasoning are separate modalities and may differ.

Initial selected memory IDs remain in `inputs.json`. Later saved selections/reasoning are recorded as events; they do not silently replace the initial inputs. Screen videos retain their audio; an additional `audio/screen_NNN.m4a` and provenance sidecar support audio-only analysis.

## Limits

This provides collection/review infrastructure, not an evaluated navigation model. It does not establish benchmark success rates, generalization or independent human-study results. Static scenes do not verify named residents, daily routines, carried objects or manipulation. Graph-node room exclusion does not prove every continuous motion avoids that room. Surface-fit measurements do not demonstrate physics-settled placement or visual approval. Backpack appearance/localizations remain candidates for review.

Automated checks cover authentication, account isolation, selection rules, ordered stops, upload/download behavior, fullscreen control flow and synthetic-media extraction. They do not establish that every campus subnet can connect or that a fresh machine has all simulator dependencies installed.
