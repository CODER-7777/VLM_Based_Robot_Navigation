# GQFT model attempts

| Variant | Training-time best val ADE px | Fixed-history test ADE/FDE px | Current interpretation |
| --- | ---: | --- | --- |
| Released baseline | 9.093834 | 9.630945 / 15.847433 | Reproduced reference |
| Historical aug_v1 | 9.093834 | Not established here | Archived/discontinued |
| Historical aug_20260909 | 8.775427 | Not established here | Validation-only improvement |
| Historical aug_v2 | 8.737493 | Not established here | Validation-only improvement; history table in previous tracker was inconsistent |
| Attention | 8.073720 | 10.090982 / 16.591120 | Test regression; validation history gate fails |
| Attention + Yaw | 9.152868 | 8.783099 / 13.322794 | Recovered fixed-history result; history-selection mismatch |

Training-time validation and standardized window/history evaluation are different measurements. Current matched CPU validation and metric definitions are in [README.md](README.md). The next controlled comparison varies only pixel-label ground-plane anchoring; extra architecture changes remain pending.
