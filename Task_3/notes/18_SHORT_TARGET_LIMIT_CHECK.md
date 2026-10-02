# Could the tighter target limits explain worse stair climbing?

Checked **2026-10-03**. This is a short decision guide based on the saved traces, not a new limits experiment. No controller, training or server code was changed.

## What changed

| Target limit | Old demo | Current viewer |
| --- | ---: | ---: |
| Hip minimum/maximum | ±1.0472 rad | ±0.735 rad |
| Calf upper target | +0.50000 rad | −0.88776 rad |

These are allowed **requested positions**, not a change to gears or J_LEG. Tightening a limit can change the gait when it removes a requested position. Therefore, the user's observation is a reasonable hypothesis to test.

## The useful numbers, without reading long plots

I checked the twelve distinct stair traces in [the repeats folder](../tools/results/20261002_stair_repeats_v1/). Six use the current candidate (three starts, each under viewer and refreshed-observation conditions).

For the candidate:

- **Hip:** zero clipped policy ticks from startup through the interval before first stair contact, in all six cases. During the moving approach, the largest absolute hip requests were 0.241–0.332 rad, comfortably within ±0.735. Widening the hip limits alone would not alter those recorded approach commands. It can still affect later recovery when requests become larger.
- **Calf:** the upper target limit removed requests in **28.2–30.7% of calf command samples** during the approach. The lower calf limit did not clip in these approach windows. The percentage counts all four calves at 50 Hz policy ticks from simulation time 4 s to first contact; it is not a percentage of complete trials or physical hard-stop contacts.
- **First collision:** the contacting front leg was not target-clipped at that instant. This does not exclude an earlier calf restriction changing its posture, timing or support.

For the original 90000 policy evaluated with current limits, calf target removal was about **40.1–42.5%** during the corresponding approaches, while hip target removal was again zero before contact. These values are descriptive checks, not a direct comparison with the old wider-limit simulator.

**Conclusion:** immediate hip restriction is not supported as the explanation for the recorded approaches. Calf restriction is a plausible contributor and needs a controlled limits-only test. We have not yet proved that either limit change caused a loss of full stair-climbing ability.

## What to do next

Before retraining or changing clearance rewards, run the same checkpoint in four isolated simulation conditions:

| Case | Hip bounds | Calf upper target | Purpose |
| --- | ---: | ---: | --- |
| A | ±0.735 | −0.88776 | Current baseline |
| B | ±1.0472 | −0.88776 | Test hip change alone |
| C | ±0.735 | +0.50000 | Test calf change alone |
| D | ±1.0472 | +0.50000 | Test both old limits and their interaction |

Use the exact October 2 `latest.pt`, the same initial pose, 10 cm stairs, observation convention, gains, friction, policy/physics rates and scripted command: zero for 3 s, ramp over 1 s to vx 0.30 m/s, vy/yaw command zero. Keep all other target bounds and J_LEG fixed. Retain a separate limit profile and output directory per case; do not overwrite the normal controller or previous results. No training is required for these comparisons.

First inspect one matched start per case; repeat across the three existing starts before trusting an apparent improvement. If testing the historical 90000 behavior, repeat these same conditions with 90000 separately. Do not compare old 90000/wide limits to new 90500/tight limits and attribute the difference solely to limits.

Keep the summary short: first-contact foot height; highest supported step/progress; full traversal; fall/stall/lane exit; and matched-window measured joint oscillation. Getting a front foot onto one step is not full ascent. Before contact, compare raw versus clamped calf targets too.

If C improves consistently over A, the calf limit contributes to behavior in this simulation. That does not establish physically valid hardware bounds. Keep the intended robot's verified command range as the eventual contract and train useful stepping within it. If no meaningful improvement appears, stop blaming limits and continue with the sensing/delay and clearance/support investigations in [note 17](17_REVIEW_OF_ACTUATOR_DELAY_AND_GATE_SUGGESTIONS.md).

**Next decision:** isolate limits first, then select the next training change from the outcome. This updates the immediate order in notes 16–17; their reward proposals remain pending.
