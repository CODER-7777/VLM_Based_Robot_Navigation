# Step 8 review desk

This dashboard reviews authored instructions, supplied memories, scene evidence, and navigation. It does **not** collect navigation demonstrations. It adds the five explicitly declared props to one shared live scene before case inspection.

## Open

```bash
bash Task_6/start_step8_review.sh --open
```

The launcher prints a private reviewer link and establishes a localhost SSH tunnel to server port **8896**. Open that reviewer link first; it authenticates the browser and removes the key from the address bar. The other pages are:

- Case review: `http://127.0.0.1:8896/review`
- Prop inspection: `http://127.0.0.1:8896/props`
- Independent blind review: `http://127.0.0.1:8896/blind`
- Naturalness: `http://127.0.0.1:8896/naturalness`

Give independent reviewers only the blind or naturalness link, in a separate browser/profile that has never opened the private reviewer link. The author APIs and labelled comparison sheets require the private reviewer cookie. The blind API omits expected goals, competitor metadata, type labels, author memory-role hints, source instructions, and prop locations. Its navigation view has no route overlay or goal-distance display.

## What the 40 cases mean

There are **40 main Level 3 memory requests**, split by authorship batch:

| Cases | Batch | Meaning |
| --- | --- | --- |
| 01–20 | General pilot | Diverse memory phenomena: aliases, ownership, routines, newer memories, and image references, plus request forms |
| 21–40 | Difficulty types | One main request per approved taxonomy slot; the difficulty code is authored in `phenomenon` |

The general cases also have types. The dashboard maps their original phenomenon descriptions to taxonomy codes and labels that mapping as inferred. It preserves the authored descriptions. [case_types.csv](case_types.csv) lists all 40 cases, their primary and additional types, lengths, and requests.

The cases also contain **27 optional Level 2 everyday needs** and **16 form entries** (10 multi-goal, three next-place, three off-limits). This makes 83 review entries before removing duplicate wording; there are **62 distinct request texts** in naturalness review. The original Level 1 instruction stays in the source data and is not shown in the review interface.

Each selected request has its own guidance, memories, allowed destinations, applicable review questions, notes, and ratings. Off-limits checks appear only for an off-limits request; Level 2 shows its own valid destinations rather than the memory request's goal. Inapplicable fields are hidden and saved as `na`. Switching requests preserves unsaved notes separately and starts a fresh navigation visit. The 3D prop assets are unchanged.

The checklist wording follows the selected taxonomy code: M3 asks whether memories identify the implied pickup and recipient location, while M1 asks whether the stops can be visited in order. Other types emphasize the corresponding routine, alias, ownership, image, condition, or spatial check. Identical Level 3/form wording is labelled **same request**, with an explanation that the review focus changes and ratings remain separate. No authored request or saved judgment is rewritten.

Returning from Props restores the last case, request variant, tab, filters, page/list scroll, and unsaved review draft in the same browser tab. Browser session storage holds this interface state, scoped to the reviewer and source revision, plus an opaque navigation-session token. The current simulator pose remains in server RAM; no poses, actions, or images are stored in the browser checkpoint. If that server session has ended, the interface restores the case and asks the reviewer to open navigation again. Drafts become server judgments only when explicitly submitted.

Taxonomy codes **L2** and **L3** mean *language difficulty*, independently of dataset **Level 2** and **Level 3**.

## Checks for cases 21–40

| Case(s) | Type | What to check |
| --- | --- | --- |
| 21–22 | S1 · spatial relation | The landmark relation picks exactly one of the same-type objects. Inspect the other coffee table/nightstand too. |
| 23 | S2 · nearest to a named place | Compare walking distances from the dining room, rather than from the robot; check the distance margin. |
| 24 | S3 · floor or position | The printer room is identifiable upstairs and the route reaches the correct room. |
| 25–26 | C2 · exclusion | Reject the excluded room and accept **every** allowed destination. The original blind key omitted alternatives. |
| 27 | C3 · household state | The dated leaking-shower memory applies at the request time and overrides the usual bathroom. |
| 28 | M1 · ordered stops | Visit Grandma's couch first, then the great-room fireplace; distinguish both stops. |
| 29 | M2 · fallback search | The crossword book is absent from the first table and present on Grandma's couch. Inspect both. |
| 30 | M3 · implied pickup | Infer the cardigan pickup on the family-room couch and delivery to Grandma's morning location from memory. |
| 31–32 | T2 · time anchor / event order | Select the morning meeting, or coffee before the run, rather than the other dated activity. |
| 33–34 | T3 · day/time routine | The supplied memories must establish a routine that applies now; a single dated event may be insufficient. |
| 35–36 | L2 · reference | Resolve “there,” “our room,” and “in there” from the speaker and earlier memories. |
| 37 | L3 · speaker-relative name | Resolve Mom and Dad relative to Olivia and identify their fireplace. |
| 38 | K1 · place function | Infer the grill/bar sink for soaking grates; check whether another place also fits. |
| 39 | K2 · storage | Storage-room memory and household context support where a spare bulb would be kept. Flag any unresolved alternatives. |
| 40 | K3 · social norm | Stop **outside** Liv's bathroom. A room-level goal alone does not verify the privacy boundary. |

General cases also use L1 (aliases), P1 (ownership), T1 (newer overrides older), T3 (routines), V1 (image references), and C1/M1/M2 forms. The dashboard displays a check tailored to the selected request variant.

## Review procedure

1. **Props first.** Inspect the calculator (case 03), glasses (05), cleat (07), crossword book (29), and cardigan (30). Judge recognition, visibility, support, placement, and consistency across all cases. Confirm each explicitly; the app never marks its own props as approved.
2. **Read each request variant.** Review Level 3, available Level 2, and each extra form separately. Check wording, speaker, time, destination, conditions, and possible alternate readings. Level 2 may accept several places.
3. **Inspect memories.** Case review defaults to the selected request's key and competing memories, with timestamps, speakers, quotes, and clean photos. Selecting an extra form adds its key memories and an earlier photo of its first stop, or a labelled room-photo fallback when no direct photo is linked. Off-limits forms also include an earlier photo memory naming the forbidden room, marked **room to avoid**. This selection is rule based and is not guaranteed complete: open **Check other earlier memories** before judging information missing. The displayed count follows the default selection. Level 2 everyday needs have no authored memory dependency. Check whether every needed name, habit, reference, and override can be understood from the evidence. The independent blind review retains its original earlier timeline without role hints. The family sheet is not a robot input.
4. **Navigate.** Open the first-person scene and use W/S (25 cm), A/D (15°), and arrow up/down (look). Check the actual destination, visibility, approach, stopping boundary, ordered stops, exclusions, and fallback locations. Case review shows a live blue position dot and facing arrow on the original floor plan, including Level 2. Click to enlarge; the same location map is available under Photos & expected places. Between floors it labels the nearest floor. Author mode can turn on the reference route for memory requests. Blind mode retains its original static plans without position or route hints.
5. **Judge even small ambiguities.** Rate eight dimensions: instruction, memory, grounding, navigation, alternate interpretations, form, visuals, and props. “Minor ambiguity” blocks a pass. Add an explanation for every non-pass. Passing requires checking navigation and confirming relevant props. Review each variant independently.
6. **Independent blind review.** A second student resolves each request using only its context, earlier memories/photos, and floor plans, and can navigate without answer overlays. They submit an answer and clarity judgment per variant; no answer is revealed afterward.
7. **Naturalness.** Rate the 62 shuffled texts as yes/odd/no, with an explanation for odd/no. This is currently a house-first-only set; a matched American-English request-first comparison remains to be supplied.

The source protocol sends a failed case back to Step 5 using the same card once, then drops that card if it fails again. Proposed fixes and human judgments belong in the review record; this dashboard does not silently rewrite authored requests or memories.

The reference route does not prove clarity or implement an ordered pickup/delivery. There is no physical pickup/carry control: for case 30 the cardigan stays at its pickup couch while the reviewer walks to the delivery area. Check both places separately. A prop saved as **Major issue** is a saved problem, not a passing approval; the related case can be saved with an issue rating and note.

The other blue marks on the static floor plans are inventory goal objects, not a complete request-specific answer set. Individual chairs are excluded from these markers. An unmarked seat may still be reasonable for a Level 2 need, and a seat at a listed table may be part of that destination. This coverage issue and the case 24 printer-memory photo request are tracked in [REVIEW_MISTAKES.md](REVIEW_MISTAKES.md). The Level 3 hearth-room exclusion must not be applied to Level 2.

## Scene and props

The base is `/data/robotics/toshith/rxr_author/refined/v16p/2azQ1b91cZZ.glb`. The five small GLB review models are added at runtime, together, in every navigation session and refreshed memory view. Downward rendered depth determines actual support height. The cardigan is folded so it fits on the couch seat. Their appearance is procedural and needs explicit human review. This is a reproducible live scene overlay, not a baked replacement of the source GLB.

The foyer cleat is on the actual semantic bench, not at the front door's center. A new close-up reference image for case 07 is rendered from the same cleat model. Cases 15 and 20 retain their place-image requests. Existing 52 real-photo/scan comparison sheets remain available and are labelled as predating the props.

The renderer uses the existing **StreamVLN Python environment**, which has Habitat 0.2.4 and NumPy 1.26.4. The `internnav` environment currently has NumPy 2.2.6 and crashes in the old Habitat sensor bindings. No installed environments were modified. The service defaults to GPU 3; `TASK6_GPU` selects a different GPU when starting it.

## Persistence and files

- Authored source: `/data/robotics/toshith/rxr_author/levels/house_first/`, read-only to this app.
- Server app: `/home/guest-isl/rishabh/task6_step8_review/`.
- Saved judgments: server app `.runtime/judgments.json`; download from **Download judgments** in author mode.
- Source fingerprint: saved with case/blind judgments to identify the reviewed revision.
- Navigation: only the current pose and a transient action count per session in RAM; no drive trace, screenshots, frames, audio, video, or action log is written by navigation.
- Browser QA snapshots are separate developer validation artifacts under local `.runtime/`, not demonstrations or reviewer evidence.

The older `levels/match/route_viewer.py` remains untouched; it saves drives and reveals answers, so it is not used for this workflow. Existing dataset generation scripts and review CSVs are untouched as well.

## Development and verification

A new checkout contains the website and generator, not the source dataset or generated scene assets. Local data/HTTP checks require a private snapshot of four JSON files. With authorized server access, populate the ignored test directory:

```bash
mkdir -p Task_6/step8_review/source
scp \
  guest-isl@172.26.186.222:/data/robotics/toshith/rxr_author/levels/house_first/cases_2azQ1b91cZZ.json \
  guest-isl@172.26.186.222:/data/robotics/toshith/rxr_author/levels/house_first/week_log_2azQ1b91cZZ.json \
  guest-isl@172.26.186.222:/data/robotics/toshith/rxr_author/levels/house_first/inventory_2azQ1b91cZZ.json \
  guest-isl@172.26.186.222:/data/robotics/toshith/rxr_author/levels/house_first/family_2azQ1b91cZZ.json \
  Task_6/step8_review/source/
```

Offline photo serving additionally needs the source floor-plan PNGs and `verify/2azQ1b91cZZ/` images. Live navigation reads those from the authoritative server directory, including `grid_2azQ1b91cZZ.npz`; it also requires the scene GLB/navmesh, semantic `.house` file and RxR guide file referenced in `simulator.py`.

Data/HTTP checks use Python's standard library. Prop generation needs `numpy`, `trimesh` and `Pillow`; live rendering needs the compatible Habitat environment described above. Chrome checks use `/usr/bin/google-chrome` and `/usr/share/nodejs/ws`. Adapt these paths for another workstation. The launcher paths are deployment-specific; `TASK6_SIM_HOST` overrides the SSH host and `TASK6_GPU` selects the server GPU.

```bash
# Local models (trimesh + numpy are already available on this workstation)
python3 Task_6/step8_review/build_props.py

# Reversible deploy; restarting affects this dashboard only
bash Task_6/start_step8_review.sh --deploy --restart

# Data and HTTP contract checks, using local source snapshot
python3 -m unittest discover -s Task_6/step8_review -p test_review.py -v

# Real Chrome against the live dashboard (installed Chrome + system ws module)
node Task_6/step8_review/test_browser.cjs

# Targeted UI checks (no review judgments submitted)
node Task_6/step8_review/test_browser.cjs --variants-only
node Task_6/step8_review/test_browser.cjs --locator-only
node Task_6/step8_review/test_browser.cjs --return-only
node Task_6/step8_review/test_browser.cjs --types-only
```

The ignored `source/` contains a read-only snapshot for local tests; it is not a new authoritative dataset. Without Habitat, `python3 server.py` serves an offline text/photo review only, explicitly rejecting navigation. The live service always reads the server's authored files.
