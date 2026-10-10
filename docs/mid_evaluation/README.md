# Mid-evaluation documentation package

**Evidence cutoff: local workspace reviewed on 10 October 2026.** This package summarizes existing work; it does not contain a new training run, simulator evaluation, hardware experiment, or server-health check.

Start with [the project README](../../README.md), then use [the slide-by-slide presentation guide](PRESENTATION_GUIDE.md). The task reports contain the experiment history, methods, outcomes, caveats, code map, and remaining work:

| Task | Report | Main result |
| --- | --- | --- |
| 1 — Simulator evaluation | [Task 1](../../Task_1_Simulator_Evaluation/README.md) | Genesis/Go2 demonstration and collision-memory workaround; quantitative scene benchmarking remains open |
| 2 — Trajectory estimation | [Task 2](../../Task_2/README.md) | Baseline reproduced; recovered Spatial + Yaw fixed-history ADE improves 8.80%; adapter/label defects identified |
| 3 — Locomotion investigation | [Task 3](../../Task_3/README.md) | Logged control/reward diagnostics; controlled contact-setting tests change vibration and stair outcomes; hardware fix unvalidated |
| 4 — Scene repair / RGB-D | [Task 4](../../Task_4/README.md) | Repaired kitchen and split physics/visual prototype; final held-out photorealism still needs evaluation |

## What is included

| Path | Purpose |
| --- | --- |
| [PRESENTATION_GUIDE.md](PRESENTATION_GUIDE.md) | Suggested 12-minute presentation, speaker notes, figures, and likely questions |
| [EVIDENCE_INDEX.md](EVIDENCE_INDEX.md) | Claim-to-artifact mapping, superseded statements, metric definitions, and comparability rules |
| [REPOSITORY_GUIDE.md](REPOSITORY_GUIDE.md) | Folder responsibilities, nested repositories, offline/server artifacts, and preservation rules |
| `evidence/task2/`, `evidence/task3/`, `evidence/task4/` | 25 copied JSON/CSV metric artifacts, the historical hardware-audit report, and a derived GQFT summary; per-task manifests record source paths and hashes |
| `figures/` | Seven byte-identical copies of existing experiment figures and comparison images |
| [tools/collect_evidence.py](tools/collect_evidence.py) | Rebuild snapshots from the original local artifacts; launches no research workloads |
| [tools/validate_package.py](tools/validate_package.py) | Check current report links, snapshot hashes, JSON/CSV shape, and central numeric claims |

The presentation copies are intentionally small. Checkpoints, environments, full traces, videos, source-model archives, and final server scenes stay in their original locations. Some extended source reports are local working-tree artifacts; the committed task summaries, figures, and evidence copies form the portable review package.

## Reading the evidence

Use “measured” for a result in a metric artifact under its stated protocol, “recorded observation” for historical reports or videos, “hypothesis” for an explanation that has not been isolated, and “planned” for work with no completed result. A copied JSON establishes what was recorded; its hash alone does not independently validate the experiment.

The strongest defensible project conclusion is that the component studies have produced reproducible evidence and identified concrete integration/contract problems. **A complete language-to-quadruped-navigation system has not been demonstrated by these artifacts.**

## Verify or refresh the package

From the repository root:

```bash
python3 docs/mid_evaluation/tools/validate_package.py
```

With the original local research folders available, refresh the copied evidence before validating:

```bash
python3 docs/mid_evaluation/tools/collect_evidence.py
python3 docs/mid_evaluation/tools/validate_package.py
```

Both utilities use Python's standard library. They do not import simulator/model packages, use GPUs, open SSH connections, or reevaluate locked-test data. The collector overwrites only its explicitly named presentation snapshots and figures.
