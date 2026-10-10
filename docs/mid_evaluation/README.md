# Mid-evaluation technical artifacts

Evidence cutoff: 10 October 2026. Recorded benchmark metrics are preserved separately from current software regression checks.

| Artifact | Contents |
| --- | --- |
| [Task 1](../../Task_1_Simulator_Evaluation/README.md) | Simulator attempts, Go2 control contract, unresolved collision/performance work |
| [Task 2](../../Task_2/README.md) | GQFT variants, matched metrics, adapter/label defects, controlled supervision hypothesis |
| [Task 3](../../Task_3/README.md) | Reward/gain/contact attempts, recording and traversal definitions, hardware-model gap |
| [Task 4](../../Task_4/README.md) | Calibrated scene repairs, RGB-D architecture, quality/performance limits |
| [CODE_INDEX.md](CODE_INDEX.md) | Relevant source modules, dependencies, source-repository boundaries |
| [EVIDENCE_INDEX.md](EVIDENCE_INDEX.md) | Claim/artifact mapping and protocol definitions |
| `evidence/`, `figures/` | 26 copied records, derived GQFT summary, seven byte-identical figures, source-hash manifests |
| [VALIDATION.json](VALIDATION.json) | Current CPU/source checks and explicit skipped dependencies |
| [REPOSITORY_GUIDE.md](REPOSITORY_GUIDE.md) | Code/data ownership, nested repositories, local/server assets |
| [PRESENTATION_GUIDE.md](PRESENTATION_GUIDE.md) | Separate slide sequence, speaking notes, and demo preparation |

```bash
python3 docs/mid_evaluation/tools/validate_package.py
```

`collect_evidence.py` refreshes only named copies from the original local artifacts. `validate_package.py` checks source-indexed copies, links, and central metric arithmetic. Neither reevaluates a benchmark. Large weights, traces, source-model binaries, environments, and final kitchen checkpoints remain external to this small evidence package.
