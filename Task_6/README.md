# Task 6 — house-first Step 8 review

The review dashboard checks whether authored household requests, earlier memories, photos and scene destinations are understandable and navigable. It reads the 40 cases for scene `2azQ1b91cZZ` on `isl-server`: **20 general pilot cases and 20 named difficulty-type cases**. Human review is ongoing; automatic checks are not acceptance results.

Start or reconnect from the repository root:

```bash
bash Task_6/start_step8_review.sh --open
```

This requires campus network/VPN, SSH access and the existing server deployment. The launcher prints a private reviewer link and opens a tunnel on localhost port 8896. Use that link to authenticate before opening `/review` or `/props`.

| Page | Purpose |
| --- | --- |
| Props first (`/props`) | Rate the calculator, glasses, cleat, crossword book and cardigan; save each judgment. A saved issue is not an approval. |
| Case review (`/review`) | Review each Level 3, available Level 2 and extra form; inspect memories and navigate before saving. |
| Independent blind review (`/blind`) | A separate reviewer resolves requests without expected answers or author type/role hints. |
| Naturalness (`/naturalness`) | Rate 62 distinct request texts, shuffled without case/type labels. |

## Current dashboard behavior

- **Scope:** 40 main requests, 27 optional Level 2 needs and 16 forms, giving 83 review entries. Repeated wording is labelled as the same request; separate entries retain separate ratings.
- **Dynamic checks:** questions follow the selected type, including M3 implied pickup versus M1 stop order. Level 2 uses its own destinations and has no authored memory dependency.
- **Memories:** default selection uses authored links plus first-stop and forbidden-room photo lookups. This is not a completeness guarantee. Open **Check other earlier memories** before judging information missing; later memories are excluded.
- **Navigation:** WASD/arrow controls, live position/facing marker and enlarged floor plan. The map's other blue marks are inventory objects, not a complete list of valid answers; individual chairs are currently omitted.
- **Returning from Props:** restores the case, request, tab, scroll, draft and active navigation session in the same browser tab. A server restart or expired session requires opening navigation again.
- **Persistence:** explicitly submitted judgments go to server JSON. Browser session storage holds interface state and drafts. Navigation poses, actions and images are not recorded to disk.

The reference route is an author inspection aid; it does not prove the instruction is clear, mark every stop, or physically move objects. The simulator has no pickup/carry interaction. Props coexist in the scene as procedural review assets and still require human approval.

## Review status and follow-up

Every slight ambiguity needs a note. Keep a case as **needs attention** when a relevant prop has a saved issue; do not change a prop to pass merely to remove a gate. Compare with expected places after forming an interpretation from the permitted request/memory/scene evidence.

[REVIEW_MISTAKES.md](step8_review/REVIEW_MISTAKES.md) records the case 24 printer-memory photo improvement and case 25 Level 2 chair/map coverage issue. [Initial findings](step8_review/INITIAL_REVIEW_FINDINGS.md) also track ownership, routine, boundary and destination-set questions. These entries are open findings, not completed source or prop fixes.

The original authored package reported **331/331 automatic checks**. Dashboard validation includes 13 behavioral tests and targeted live Chrome checks for navigation, filtering, type-specific questions and returning from Props. See the [validation record](step8_review/VALIDATION.md) for dates and limits.

## Files and reproduction

| Files | Purpose |
| --- | --- |
| `step8_review/index.html`, `app.js`, `style.css` | Website shell, review UI and layout |
| `step8_review/server.py`, `model.py` | HTTP/authentication, source adapter and judgment persistence |
| `step8_review/simulator.py`, `build_props.py` | Transient Habitat rendering, location map and reproducible prop generation |
| `start_step8_review.sh`, `step8_review/launch.py` | SSH tunnel, deployment and service launch |
| `step8_review/test_review.py`, `test_browser.cjs`, `test_live.py` | Contract, browser and simulator verification |

The authoritative dataset is `/data/robotics/toshith/rxr_author/levels/house_first/`. The server app is `/home/guest-isl/rishabh/task6_step8_review/`. Git contains the website source, generator, checks and review documentation. Local `source/`, generated prop assets and `.runtime/` (keys, judgments, browser state, QA images and logs) are ignored.

[Case-by-case types](step8_review/case_types.csv) · [Full setup, reviewer protocol and type checks](step8_review/README.md) · [Task 5 demonstration collector](../Task_5/README.md).
