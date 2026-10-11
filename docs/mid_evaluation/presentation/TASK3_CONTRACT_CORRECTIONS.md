# Task 3 — September hardware-contract audit and correction inventory

The September 21 report is the source for the findings below. The audit corrected a separate evaluation simulator; it did not change robot firmware, deploy a policy or run new hardware experiments. The current SvanM2 viewer contains important bounds corrections but does not implement every audit correction. [Slide 8](SLIDE_TEXT.md#slide-8--task-3-audit-fixes-improvements-and-analysis) contains the presentation version.

## The +0.5 and hip corrections

| Software target | Historical simulator | September deployed-adapter contract / current important constants | Analysis and rationale |
| --- | ---: | ---: | --- |
| Calf upper | +0.50000 rad | −0.88776 rad | A 1.38776 rad / 79.5° mismatch changes which actions produce reachable commanded targets |
| Hip | ±1.0472 rad | ±0.735 rad | Wider simulator targets give a fixed policy a different action realization from deployment |
| Thigh bounds | Larger/asymmetric conventions required review | September audit used deployed front/rear and left/right bounds; current viewer front [−1.5708, 3.4907], rear [−0.5236, 4.5379] rad | Current front/rear constants alone do not verify every deployed asymmetry |
| Calf lower | Check per-joint contract | Current −2.7227 rad | Retain bounds while verifying full per-joint deployment conventions |

Current [controller.py](../../../Task_3/xterra_mjlab/svanm2_moe_stair_sim/controller.py) explicitly contains the corrected hip and calf-upper constants. These are commanded-position clamps. They do not establish physical joint-stop angles, verified safe mechanical ROM or a firmware-limit change.

The command pipeline is `raw action → clip ±6 → q0 + scale × action → target bounds → coupled PD → torque clamp`. Scale is [0.15, 0.15, 0.30] per leg. History retains the clipped raw action, not the final clamped position target. Changing that history would change the policy's observation contract.

## Other findings, corrections and their scope

| Audit point | Analysis → correction / outcome | Current status / qualification |
| --- | --- | --- |
| Policy identity / history order | 34 export fixtures and 30,175 exact hardware I/O frames passed replay; max recorded-action difference 2.29e−5 | Verified from saved replay; not a reason to substitute weights or reverse current oldest-first input |
| Operator command shaping | Reproduce deadzone, neutral/X enabling, shared input budget, slew and release; caps vx±0.5 m/s, vy±0.6 m/s, yaw±0.4 rad/s | Implemented in the separate September audit, not established as complete current-viewer parity |
| Training command distribution | Saved 90k lateral range ±0.3 m/s versus hardware profile ±0.6 m/s; paired simulated HF RMS about 0.61→0.43° when vy reduced to 0.3 | Evaluate within trained range or deliberately retrain expanded distribution; no hardware cap changed |
| Policy/PD/physics timing | Separate 50 Hz policy, 200 Hz external PD and integration resolution; nominal 5 ms delivery delay with 0/15 ms probes | September audit conventions; actual motor firmware servo rate remains unverified |
| Sensor state | Explicit refresh before observations avoids prior-integration sensor state | September audit corrected; current viewer provides optional `fresh`, default `legacy` |
| Full reset | `mj_resetData` clears time/control/warm-start state | September audit corrected; current controller reset still edits pose/history and calls `mj_forward`, so full-reset parity remains open |
| Nonfinite policy output | Treat invalid output as offline failure | September audit corrected; current viewer still substitutes zero raw action |
| Stair evidence | Replace one-second pre-stair runs with contact and full-foot traversal checks; preserve lane exits/stalls/tips | September audit and later controlled studies use documented criteria; interactive screen/video progress is a different measure |
| Contact timeconstant | With default safety rule, solref .002 at 5 ms integration acts with a minimum 10 ms timeconstant | Use explicit/fixed contact constants in resolution probes; changing integration can otherwise change the plant |
| Effective friction | Priority-1 feet override lower-priority terrain values | Change effective foot parameters for friction sensitivity; terrain-only edits can be ineffective |
| Target saturation | Calf occupancy FL/FR/RL/RR: 17.7/20.0/19.4/64.8% in moving hardware samples | Analyze requested/clamped targets and asymmetric reachability; occupancy does not prove physical stop contact |
| Coupled PD | Thigh torque-estimate RMSE about 0.69–0.83 Nm coupled versus 1.66–2.88 Nm diagonal | Retain coupling; telemetry is not load-cell actuator identification |
| Torque clamp semantics | Estimated hardware thigh peaks around 23.2 Nm exceed modeled 12 Nm joint clamp; motor-space alternative tested | Sensitivity model only; exact firmware saturation law unverified |
| Firmware status telemetry | Nonzero values 98/99/100/102 in 500 rows, 422 motion rows | Decode with firmware-specific information; repeated samples are not independent fault events |
| Physical plant | ROM, friction, payload, inertia, backlash and loaded servo dynamics are incompletely identified | Hardware calibration remains necessary; simulator consistency is not a hardware repair |

## Attempt outcomes that belong in the presentation

- **September:** 120 offline rollouts; corrected-contract straight-command ascents at 10/15/18 cm each achieved 0/2 valid traversals. Legacy wider targets also failed, so correcting bounds alone did not solve stairs.
- **Filtering:** 20 ms filter flat HF RMS 0.546→0.507° (about −7%), with worse tracking and two 15 cm stair tips. 40 ms filter increased flat RMS to 0.802° (about +47%). No smoothing deployment was performed.
- **Resolution:** same-contact 1 ms physics reduced flat RMS to about 0.42°, but 0.5 ms remained about 0.46°; not established convergence or a hardware fix.
- **Reward bundle90500:** training target second-difference/saturation costs improved 6.57%/59.65%; physical jitter mixed, stair completions 0/12.
- **October current tighter bounds:** isolated contact ratio 100→10 reduced four primary flat joint-band RMS measures 63.5–70.5%; six matched policy/start stair cases 0/6→3/6. Original-policy lateral speed worsened. This is separate from the older wider-bound 4/4 result.

Next: verify the complete deployment contract and actuator/contact model, then evaluate one-factor changes with tracking, heading, saturation, support and traversal alongside RMS. Do not widen hardware targets to match the historical +0.5 allowance.

## Sources and plots

[September report snapshot](../evidence/task3/hardware_audit_report.md) · [Original audit](../../../Task_3/moe_jitter_audit_20260921/REPORT.md) · [Hardware diagnostic plot](assets/task3_hardware_diagnostics.png) · [Historical ablations](assets/task3_historical_ablations.png) · [Replay record](assets/task3_hardware_replay.json) · [Current comprehensive audit](../../../Task_3/notes/23_DEEP_JITTER_ANALYSIS_20261010.md).

All values come from retained reports, code and artifacts. No training, firmware change or hardware experiment was performed for this documentation update.
