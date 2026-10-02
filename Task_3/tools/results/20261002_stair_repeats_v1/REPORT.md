# Three-start sensitivity results — 2026-10-02

Read the [main fresh-data report](../20261002_matched_v1/REPORT.md) for the interpretation and exact measurement definitions. This dashboard adds starting-pose sensitivity; it is not a new training run.

| Starting pose | Lateral offset | Yaw offset |
| --- | ---: | ---: |
| 0 | 0 m | 0 rad |
| 1 | −0.03 m | −0.02 rad |
| 2 | +0.03 m | +0.02 rad |

Both checkpoints use every pose and both observation modes. There were no full traversals in these twelve cases.

| Policy | Viewer timing: 3 starts | Refreshed observations: 3 starts |
| --- | --- | --- |
| Original 90000 | 2 lane exits, 1 tip | 2 incomplete timeouts, 1 lane exit |
| Candidate 90500 | 2 lane exits, 1 tip | 2 incomplete timeouts, 1 lane exit |

The [paired-start figure](paired_starts.png) shows measured joint oscillation, speed error and target removal in the same 4–8 s window. Candidate oscillation changes have mixed signs; lower target removal and speed error are more consistent. These three deterministic poses are not confidence intervals or independent trained policies.

Use [comparison.csv](comparison.csv) for the compact table, [comparison.json](comparison.json) for all phase metrics, and each run's `trace.npz`, `contacts.jsonl` and `first_contact_analysis.json` for evidence. First-contact heights were approximately 3.7–6.3 cm for the foot center. Every first contact was with a front-foot riser, with no target/torque clipping on that contacting leg at that instant.
