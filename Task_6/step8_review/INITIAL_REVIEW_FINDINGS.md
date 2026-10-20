# Initial items requiring Step 8 judgment

These are review candidates found while preparing the tool, not fabricated human ratings or completed walkthrough results. No case has been silently edited or accepted.

| Case / scope | Finding | Required judgment or correction |
| --- | --- | --- |
| 25–26 | Level 3 allows multiple destinations, but the old blind key exports a single `goal_name`. | Dashboard uses the full `valid_ids` set. If the old external key is used, update it before grading. |
| 07 | Missing-cleat request originally names a photo, but no actual case-07 request image existed in the generated package. | Dashboard renders a reference close-up from the added cleat. Check whether it identifies the requested item clearly. |
| 07 | S01 says “My bag's on the bench,” not explicitly that the missing cleat is there. | Decide whether this inference is sufficient or the memory needs a natural explicit cue. |
| 16 | Shared primary bedroom has two nightstands; request says Megan's nightstand. | Check whether a prior memory/photo identifies her side. |
| 34 | N03 is a Monday nap event; request uses Saturday “nap time.” | Check whether earlier evidence teaches a daily routine; the hidden family sheet cannot supply it. |
| 06, 32 | Level 2 says “make some coffee”; stored need is `cook`, whose accepted objects are oven/range/grill. | Review wording and accepted places; a generic cooking set may not fit coffee. |
| 25 / Level 2 | p42 is called a table in the valid eating-place list; previous process notes call it a sideboard with a tea set. | Visually determine whether it is a valid place to sit and eat. |
| 09, 40 | Wording requires stopping outside a private room; stored goal is a room ID. | Verify the exact stopping position and boundary by navigation. |
| 21–22 | The spatial instruction distinguishes a same-room sibling, whereas the stored main competitor is elsewhere. | Inspect the named same-room coffee table/nightstand as well as the metadata competitor. |
| 03, 05, 07, 29, 30 | Props had been declared but the original review report said no props were present. | Five props are now in the live overlay; human placement/recognition judgments remain pending. |
| Documentation | Older sections still mention 10/20 cases, 23 naturalness rows, and incomplete Step 8 generation. | Use the current 40-case JSON, latest report, and 62-row naturalness set. |

Automatic verification reports **331/331** for the source revision. That result does not settle these instruction, memory, or human-interpretation questions.
