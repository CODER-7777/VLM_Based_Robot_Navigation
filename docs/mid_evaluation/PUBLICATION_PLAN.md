# Ten-commit publication plan

The main repository receives ten focused commits. The SvanM2 nested repository requires one separate source commit for its existing controller/contact changes; its revision is recorded in parent commit 4. Existing GQFT source is already committed. Push source repositories before the parent so every referenced revision is retrievable.

| Parent commit | Scope |
| --- | --- |
| 1 | Generated-file exclusions, submodule input boundaries and repository layout |
| 2 | Simulator feasibility, collision limitation and comparison diagrams |
| 3 | GQFT results, Transformer explanation and proposed masking experiment |
| 4 | Explicit contact settings, passive recording and regression checks; SvanM2 source revision |
| 5 | Hardware/control/gate analysis, compact saved measurements and locomotion reports |
| 6 | Product fitting, material/asset inspection tools and selected verification metadata |
| 7 | Shared-camera tours, panoramas and v7/v8 appliance/tray repair source |
| 8 | Portable evidence, source hashes, diagram generation and consistency validation |
| 9 | Presentation PDF, speaking script, episode examples and review assets |
| 10 | Main README plots, supervisor direction, integration milestones and publication record |

The [explicit path plan](PUBLICATION_PLAN.json) is prepared with `python3 docs/mid_evaluation/tools/prepare_publication.py`. Preparation reads Git status and writes review metadata; it does not stage, commit, push or run research. Commit groups use named paths and stop on errors. No history rewriting or force-push is part of this plan.

## Published versus local artifacts

Publish current source, task READMEs, retained analysis reports, selected fit/licence/verification JSON, compact gate-analysis figures, portable evidence, independent diagrams, and the user-designed PDF/script. Raw arrays, NPZ traces, interactive recordings, model/scene binaries, videos, environments, native Blender files and downloaded archives remain local. Existing tracked historical artifacts are preserved.

## Validation

CPU checks cover the GQFT adapter/strict architecture loading and SvanM2 passive recording, contact overrides, reward interfaces and checkpoint parity. Syntax checks cover selected Python, shell and JavaScript source. The evidence validator checks hashes, links and central numeric claims. Masked attention and integrated VLM navigation are proposed; no new GPU training, server publication or hardware measurement is performed.

The ten commits are a planned grouping until Git history and remote verification confirm publication. [Technical evidence package](README.md) · [Integration plan](../INTEGRATION_PLAN.md).
