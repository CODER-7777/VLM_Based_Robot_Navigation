# Step 8 review mistakes and requested improvements

Record reviewer findings here for later fixes. An entry is not a completed fix or a passing judgment.

## Case 24 — Megan's office memory photo does not show the printer

- Recorded: 21 October 2026.
- Case: `2azQ1b91cZZ_case24`, S3 (floor or position).
- Request: “Take this printer paper upstairs, to the room with the printer.”
- Relevant memory: **T04**, Megan, D0 Sun 11:15: “My office is up here. I work here every morning.”
- Observed problem: The T04 memory photo shows mostly cupboards. No printer is clearly visible, so the photo does not clearly connect Megan's upstairs office to the printer described in the request. The comparison memory T03 does not show a printer either.
- Reviewer observation: The printer is in Megan's office, but the relevant memory image does not show it clearly enough to recognize the requested room.
- Requested improvement: Reframe the T04 memory photo to clearly show the actual printer together with enough of the office surroundings to identify its location. Check the view in the actual scene before accepting the replacement.
- Review consequence: Record this as a memory-photo clarity issue. A printer visible in navigation or under Photos & expected places does not by itself make the existing T04 memory image clear.
- Status: **Open — improvement requested; photo not changed.**

When reviewing similar cases, distinguish an object that is missing from the scene from an existing object that is missing or unclear in its relevant memory photo.

## Case 25 Level 2 — Chairs are not individually marked on the floor plan

- Recorded: 21 October 2026.
- Request: “Where can I sit down and eat something?”
- Reviewer observation: White chairs in the hearth room may provide reasonable seating, but do not appear as individual destination markers on the map.
- Verified implementation: The static inventory map marks only objects with `goal: true`. All 24 inventory chair objects have `goal: false`, including the chairs in room 7. The blue marks are inventory object markers, not the selected request's complete set of acceptable destinations.
- Answer-list limitation: This Level 2 request lists table/island destinations, rather than individual seats. A chair at a listed table may already belong to that destination area; a separate chair is not explicitly represented by the current list.
- Requested improvement: Make the map legend and destination coverage clear. Review suitable seating against the actual wording before treating an unmarked chair as invalid. Check whether the table-based answer list is too narrow for “sit down and eat something.”
- Scope: The hearth-room destination exclusion belongs to Level 3 and must not be transferred to this Level 2 request.
- Status: **Open — review requested; source answer list and floor-plan images not changed.**
