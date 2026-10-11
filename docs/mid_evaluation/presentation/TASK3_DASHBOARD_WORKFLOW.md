# Task 3 — investigating residual oscillation with interactive runs

## Workflow

**Operate → record → inspect the dashboard → identify the event → repeat under controlled conditions.**

The interactive recorder saves keyboard commands and controller/physics traces without changing the control law. Each reset creates a separate attempt. Session manifests identify the checkpoint, target bounds, gains, observation timing and active contact settings. Per-attempt plots and metrics support reviewing successful progress and retained failures.

Record raw actions, requested position targets, clamped targets, measured angles/velocities, commanded and actual motion, applied torque, foot heights and contact forces. Align traces to first recorded stair contact rather than averaging the whole attempt immediately.

## How to read the dashboard

| Panel | What to compare | Question answered |
| --- | --- | --- |
| [Overview](assets/task3_interactive_overview.png) | Commanded/actual speed, tilt, trajectory and contact markers | Did smoother motion preserve useful movement? |
| [Joint-event plots](assets/task3_interactive_joint_event.png) | Requested target, clamped target and measured joint angle around contact | Does disagreement originate before limiting, at the software bound or in the physical response? |
| [Contact/control plots](assets/task3_interactive_contacts.png) | Foot heights, riser forces, removed target magnitude and raw/applied torque | Does the response coincide with impact, target limiting or torque saturation? |
| [Attempt metrics](assets/task3_interactive_metrics.json) | Target/torque clipping fractions, tracking errors and band RMS | Which joints/behaviors need a controlled follow-up? |

## Findings from the saved operator-run attempt

Checkpoint91000, contact ratio 10, kp18/kd0.7, tight target bounds and legacy observations. Four attempts were recorded; attempt 4 contains the meaningful stair sequence. It lasts 81.17 s, uses forward commands up to 0.50 m/s and includes yaw steering, ascent, turnaround and descent.

- First recorded stair contact is about 4.825 s after reset. Contact-aligned measured-joint 8–30 Hz RMS rises from about 0.14° during approach to 0.58° during early impact/recovery, then about 0.49° during ascent and 0.03° during quiet platform settling.
- First-contact shared-band 8–20 Hz RMS is about 1.90° in commanded targets versus 0.57° in measured joints. Target and joint bands must be matched: policy targets are sampled at 50 Hz; measured joints at 200 Hz.
- Across the full attempt, FL/RR calf targets are clipped in about 61%/63% of samples. Torque clipping is rare, with brief thigh clipping near impact. Software target occupancy is not proof of physical-stop contact.
- Ascent peak tilt is about 30.8°; actual forward speed averages about 0.42 m/s for a 0.50 m/s request in the reviewed ascent interval. The recording shows stair progress, not automatically verified repeatable full-foot traversal.

These observations focus the next test on contact recovery, target reachability and steering/command effects. They do not establish a causal improvement from contact ratio 10 because the saved run is not a matched A/B intervention.

## Controlled follow-up

Keep checkpoint, bounds, gains and observation convention fixed. Use the same start; ramp vx to exactly 0.30 m/s, keep vy/yaw zero, and retain the command through approach, ascent and settling. Record every attempt. Then compare contact ratio 10 versus 100 with all other settings fixed.

Inspect contact-aligned target/joint RMS, tilt, actual speed, heading, per-joint saturation, foot support and full-foot traversal together. This experiment is proposed; it was not executed while preparing the documentation. Verify bounds against deployment before changing safe target ranges.

[Source analysis](../../../Task_3/notes/23_DEEP_JITTER_ANALYSIS_20261010.md#11-new-user-operated-recording-update-91000-at-impratio10) · [Portable dashboard overview](assets/task3_interactive_overview.png) · [Saved attempt metrics](assets/task3_interactive_metrics.json).

The full original attempt dashboard is retained locally at `Task_3/tools/results/interactive/newest91000_impratio10_20261011_022418/attempt_004/plots/index.html`, alongside the external raw recording.
