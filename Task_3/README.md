# Task 3: MoE stair navigation and jitter investigation

**Current workflow: drive the viewer yourself → save its raw data → plot the saved data.** Start with [the interactive recording guide](notes/19_RECORD_MY_INTERACTIVE_RUN.md). The candidate checkpoint is the October 2 combined run at update 90500. At the user's latest request, viewer targets are now hips ±0.735 rad and calf upper −0.886 rad (the audit's exact calf value was −0.88776). The user previously reported better climbing with wider targets and persistent jitter; that observation is not yet a quantified matched comparison. Use separate recording directories for different limit conditions.

## Where things belong

| Folder | Contents |
| --- | --- |
| [xterra_mjlab/](xterra_mjlab/) | Simulator, training code and Python environment. Existing checkpoint paths are retained. |
| [xterra_mjlab/evaluation_runs/](xterra_mjlab/evaluation_runs/) | Copied trained candidates and their saved training configuration |
| [notes/](notes/README.md) | Learning notes, experiment history and current instructions; images are grouped in `notes/assets/` |
| [tools/jitter_analysis/](tools/jitter_analysis/) | Recording, saved-data plotting and diagnostic scripts |
| `tools/results/interactive/<session>/` | Your new keyboard-controlled recordings, one folder per session |
| [tools/results/](tools/results/) | Existing scripted comparisons; their provenance distinguishes them from your new interactive recordings |
| [tools/archive/](tools/archive/) | Loose historical debug exports and an exact record of files reorganized |
| [Videos/](Videos/) | Your screen recordings; not numerical sensor logs |
| [moe_jitter_audit_20260921/](moe_jitter_audit_20260921/index.html) | Historical audit, retained in place so existing links work |

No checkpoints, videos or results were deleted or renamed. New runs must use a new session directory; the recorder refuses to overwrite an existing one. Keep raw data under its session and put generated plots in each attempt's `plots/` subfolder. Do not drop new plots/debug dumps into this directory or the code repository root.

The historical scripted results are actual MuJoCo measurements under assistant-selected commands, not fabricated curves. They are not measurements of your keyboard-operated attempt. The interactive recorder makes that distinction explicit in its manifests.
