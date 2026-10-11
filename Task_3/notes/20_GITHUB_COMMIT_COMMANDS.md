# Commit the current Task_3 work in six groups

Historical Task 3-only commands. The current whole-repository update is defined by the [ten-commit publication plan](../../docs/mid_evaluation/PUBLICATION_PLAN.md).

Updated 2026-10-05 after inspecting the parent repository. Branch: `main`; remote: `https://github.com/CODER-7777/VLM_Based_Robot_Navigation.git`. The index was empty when inspected. These are commands for the user; the assistant has not staged, committed or pushed anything.

Use this current sequence instead of the older broad directory additions. It includes only selected tools, notes and two small comparison dashboards (approximately 0.6 MB of images). Large recordings, videos, environments, checkpoints, the nested xterra_mjlab checkout and unrelated Task_2/root changes stay outside these commits. Keep raw recordings locally: these published comparison summaries contain metrics and checkpoint hashes but are not the full reproducibility dataset.

Run from the parent repository. Execute one group at a time; stop if a command fails. Check that the index is empty before starting. Each staged-path review must contain only the listed group. Do not use `git add .`, `git add -A`, or `git commit -a`.

```bash
cd /home/vivekananda/UGP_1_VLM/VLM_Based_Robot_Navigation
git branch --show-current
git diff --cached --name-only
```

## 1. Record actual keyboard commands and plot all movement directions

```bash
git add -- Task_3/tools/jitter_analysis/interactive.py Task_3/tools/jitter_analysis/plot_interactive.py Task_3/tools/jitter_analysis/test_interactive.py Task_3/notes/19_RECORD_MY_INTERACTIVE_RUN.md
git diff --cached --stat
git commit -m "feat(task3): record and plot forward sideways and turning commands"
```

## 2. Diagnose policy updates, gates, input sensitivity and actuator response

```bash
git add -- Task_3/tools/jitter_analysis/diagnose_updates.py Task_3/tools/jitter_analysis/inspect_policy_spikes.py Task_3/tools/jitter_analysis/test_analysis.py
git diff --cached --stat
git commit -m "feat(task3): diagnose recorded policy spikes and MoE contributions"
```

## 3. Compare recorded policies under checked evaluation conditions

```bash
git add -- Task_3/tools/jitter_analysis/compare_policy_runs.py Task_3/tools/jitter_analysis/review_interactive.py
git diff --cached --stat
git commit -m "feat(task3): compare recorded policies with contract and duration checks"
```

## 4. Inspect target rates and validate the optional reward experiment

```bash
git add -- Task_3/tools/jitter_analysis/audit_target_rates.py Task_3/tools/jitter_analysis/target_rate_reward.py Task_3/tools/jitter_analysis/test_target_rate_reward.py Task_3/tools/jitter_analysis/smoke_target_rate_env.py
git diff --cached --stat
git commit -m "test(task3): add target rate diagnostics and reward integration checks"
```

The tools-side `target_rate_reward.py` is the proposal/reference copy. Active training uses `xterra_mjlab/scripts/target_rate_reward.py`. Tests and replay tools depend on the local xterra_mjlab installation; these tools-and-notes commits do not publish the complete training implementation or its environment.

## 5. Document findings, interpretation limits and the next experiment

```bash
git add -- Task_3/notes/12_REVIEW_OF_SMOOTHNESS_AND_MOE_REPORT.md Task_3/notes/16_NEXT_CHANGES_FROM_THE_PLOTS.md Task_3/notes/17_REVIEW_OF_ACTUATOR_DELAY_AND_GATE_SUGGESTIONS.md Task_3/notes/21_INTERACTIVE_RUN_REVIEW_AND_OBSERVATIONS.md Task_3/notes/22_TIME_AWARE_TARGET_PENALTY.md Task_3/notes/README.md Task_3/notes/20_GITHUB_COMMIT_COMMANDS.md Task_3/tools/README.md
git diff --cached --stat
git commit -m "docs(task3): explain jitter evidence reward tradeoffs and next experiments"
```

Notes dated Oct 2–4 describe their historical settings and measurements. The latest Oct 5 matched sideways findings are at the top of note 17; earlier recommendations are not proof that a fix worked.

## 6. Preserve the two compact sideways comparison dashboards

```bash
git add -- Task_3/tools/results/interactive/comparison_y015_20261005_015702/comparison/index.html Task_3/tools/results/interactive/comparison_y015_20261005_015702/comparison/comparison.csv Task_3/tools/results/interactive/comparison_y015_20261005_015702/comparison/comparison.json Task_3/tools/results/interactive/comparison_y030_20261005_021830/comparison_equal4s/index.html Task_3/tools/results/interactive/comparison_y030_20261005_021830/comparison_equal4s/comparison.csv Task_3/tools/results/interactive/comparison_y030_20261005_021830/comparison_equal4s/comparison.json
git add -f -- Task_3/tools/results/interactive/comparison_y015_20261005_015702/comparison/comparison.png Task_3/tools/results/interactive/comparison_y030_20261005_021830/comparison_equal4s/comparison.png
git diff --cached --stat
git commit -m "data(task3): preserve matched sideways tracking and jitter comparisons"
```

Only these two named PNGs need `-f` because the root ignore rules exclude PNG images. The original incomplete eight-second +Y0.30 comparison is retained locally; the committed four-second comparison has complete equal-duration windows. Manual command ramps and gait phase can still differ.

## Review and publish

After all six commits succeed:

```bash
git log -6 --oneline
git diff --name-only HEAD~6 HEAD
git status --short
git push origin main
```

The six-commit path review should list only Task_3/tools and Task_3/notes paths. Unrelated local changes should remain unstaged. If GitHub has newer commits and rejects the push, stop and inspect the error; do not force-push.

## What to show at today's deadline

Show the +Y0.15 and +Y0.30 comparisons together, including actual speed and heading. At +Y0.15 the candidate has 65% lower joint-band vibration but 58% lower mean sideways speed and nearly stops. At +Y0.30 it moves slightly faster but has 37% higher joint-band vibration and greater heading drift in the equal four-second pair. These are measured single-pair outcomes, not a general success-rate estimate.

A defensible result is: "I implemented and measured smoothness penalties. The candidate reduced vibration at a small command while sacrificing movement; the improvement did not generalize to the larger command. I established matched recording/analysis and identified the next reward-balance experiment." Do not claim a completed jitter fix. Preserve model_90000.pt. The next proposed training experiment removes the added time-rate term while holding all other settings fixed, using an independent continuation from 90000; its outcome is unknown.
