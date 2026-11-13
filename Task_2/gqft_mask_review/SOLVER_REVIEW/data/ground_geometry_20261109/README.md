# Ground-plane solver lab (9 Nov 2026)

Zero-training planar ego-motion from cached SEA-RAFT flow, using the fixed rig (1.2 m, 30° pitch, HFOV 135°).

| File | What |
|---|---|
| `ground_vo.py` | First scipy prototype (`MAX_FLOOR_M` env var sets the floor cutoff) |
| `results_ep629.txt` | Prototype on episode 629 legs at cutoffs 6 / 3 / 2 / 1.5 m |
| `verify_ground_solver.py` | 15 CPU checks for the torch solver and GQFT hybrid mode. Pass an old `models/gqft.py` copy to also check legacy bit identity |
| `verification.json` | Latest check output plus episode 629 solver-vs-GQFT numbers |

Headline (exploratory; cutoff chosen on these windows): solver mean ground error 1.6–3.4 cm vs Attention+Yaw GQFT 3.0–10.2 cm, lower on 3 of 4 legs.

Full context and next experiments: [../../APPROACHES_TRIED.md](../../APPROACHES_TRIED.md).
