# Publication validation — 19 October 2026

These checks were run against the selected source, including a separate exported copy without private deployment inputs.

| Check | Result |
| --- | --- |
| Manifest paths, selected Python syntax and JSON parsing | Passed |
| Selected JavaScript syntax (`node --check`) | Passed |
| Selected shell syntax (`sh -n`) | Passed |
| Git-visible files agree with the explicit manifest | Passed |
| Private keys, prepared image cases, live configuration, account DB and recording paths ignored | Passed |
| Collector unit/integration suite | 19 tests passed |
| Same suite in source-only export | 19 tests passed without authored case files or scene assets |
| Synthetic screen conversion produces separate audio | Passed |
| Audio-only download and sample ZIP contents | Passed |
| Repeat extraction preserves existing audio/video/standalone voice | Passed |
| Silent video produces no fabricated audio clip | Passed |

The publication check scans selected text for recognizable key/token/password material and embedded image payloads. It allows the tiny synthetic pixel fixture in an older browser test. This check is not a comprehensive security audit.

Full simulator rendering, live campus reachability, certificate installation and participant microphone capture were not rerun for this publication. No server service was deployed or restarted, and no human recordings were included or modified. Historical runtime reports remain local.

Commands and prerequisites are in [REPRODUCIBILITY.md](REPRODUCIBILITY.md). Re-run the checks after changing the source; this file records this publication's validation, not a promise about later revisions.

## Source publication update — 25 October 2026

The publication selection contains 144 research/application files. Generated verification scripts, the browser-only QA fixture, poster prompts, credentials, deployment data and built packages remain local. Previously tracked verification scripts are removed from the current Git index without deleting their working copies or rewriting history.

A fresh source-only export passed all 31 Python unit tests, the launcher Go unit tests and JavaScript syntax checks. The Go compile used an owner-supplied public CA only in the temporary test export, as documented in the launcher build notes; that certificate is not part of the Git selection. Recognizable secret-pattern checks found no matches in the selected source or the previous Task 5 HEAD snapshot. These checks are not a comprehensive security audit.

This publication does not modify or restart the production service. Windows/macOS runtime pilots and human recording validation remain separate from source compilation and synthetic tests. Development-only browser, audio and lifecycle reports remain local.
