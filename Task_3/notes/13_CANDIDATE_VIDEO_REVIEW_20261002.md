# Recorded 10 cm stair attempt: visual review

Reviewed: **2026-10-02**. Main workflow: [README.md](README.md).

**Observation:** the robot stays broadly upright on the flat approach, but the first visible stair attempt develops a large tilt and a low body posture. The second attempt repeatedly works near the first step without completing the staircase. This recording identifies stair entry and support transfer as the immediate diagnostic region. It does not establish the cause of joint jitter or a percentage improvement over the original policy.

## Recording and evidence

- Original video: [2026-10-02 18-50-10.mp4](../Videos/2026-10-02%2018-50-10.mp4).
- Duration: **35.267 seconds**, 1920 × 1080, **30 frames/second**, 1,058 encoded video frames. It also contains an audio track; this report concerns the visual evidence.
- Video SHA-256: `62788a5fe1cc214d16be2abbaf0c3c414526b8b824d2541aaebf7d5ea55a7f78`.
- Review method: decoded-frame timeline every **0.5 s** across the recording, plus **5 fps** crops around stair-entry, body-drop and later stepping intervals. Full-resolution selected frames were inspected to read the HUD. This is a visual review, not a joint-telemetry audit.
- **All timestamps below are recording time, not simulation time.**
- Readable HUD frames identify **Track 1 (10 cm)**. The source viewer defines twelve steps for this track.
- Session context is the new combined candidate at update **90500**. The video does not show the terminal's loaded checkpoint path/update, so checkpoint identity cannot be independently proved from the recording alone. Retain that startup output with future videos.
- The local candidate checkpoint was previously confirmed at `xterra_mjlab/evaluation_runs/20261002_moe_target_bundle_updates90500/latest.pt`. Its existence does not by itself prove which file the recorded viewer loaded.

The local controller now has hip target bounds **±0.735** and calf upper targets **-0.88776**, following the user's authorized hip edit. These are verified source settings at review time; a video cannot prove that an already-running process loaded a subsequent source edit.

[Whole-video overview](video_review_20261002_candidate90500/overview_3s.jpg).

## Timestamped observations

| Recording time | Directly visible evidence | Interpretation and limits |
| --- | --- | --- |
| 0–1 s | Recording application and a window transition are visible. | The full pre-recording startup and settling period are unavailable. |
| Approximately 1–8 s | Robot is broadly upright on the flat approach. At 3 s the HUD reads base Z 0.34 m, tilt about 0.8°, `vx=+0.10`, `vy=0`, `yaw=0`. Forward command increases during this approach, reaching +0.45 m/s in the later readable frames. | Gross balance on the approach is better than during stair entry. Foot motion alone does not establish high-frequency jitter; much of it can be normal stepping. |
| Approximately 8–9.6 s | Front legs reach toward/onto the first tread while rear feet remain near the runway. Repeated changes in leg placement occur. | Inspect the transition between flat-ground support and stair support. Contact forces, slip and specific supporting feet cannot be determined reliably from the render alone. |
| 9.8 s | HUD says `On Stairs (Step 1/12)`, Z 0.35 m, tilt about 40.2°, `vx=+0.45`. | The base briefly reaches the first-step region. This HUD region is based on base x, not all-feet traversal. |
| 10.0 s | Robot tilts sharply; HUD reads about **58.0° tilt**, Z 0.31 m, `vx=+0.45`, with zero lateral/yaw commands. | A major balance excursion is visible. This is one sampled value, not a measured maximum or a formal fall-threshold result. |
| 10.4–12.6 s | Body drops low near the first stair and makes further leg corrections. At 12 s HUD Z is **0.18 m**, tilt about 18.3°, and `vx=+0.45`. | Lower tilt after the excursion does not mean successful recovery or ascent: height and useful progress matter too. |
| Approximately 13 s | Robot abruptly returns to the approach with zero command. | A reset/teleport is visible. Do not count this as a spontaneous recovery from the low posture. The exact key used is not recorded. |
| Approximately 13–20 s | Another broadly upright approach; the command increases to **+0.30 m/s** in readable frames. | This attempt uses a different forward command from the first. It is not a controlled speed comparison. |
| Approximately 20–27 s | Robot repeatedly lifts/repositions legs near the lower step. No sequence shows all four feet progressing up the staircase. The torso's orientation also changes. | Lack of stair progress is a task problem even while the body remains upright. Quantitative heading, slip and target oscillation require telemetry. |
| 27.2 s | HUD reads about **29.9° tilt**, Z 0.38 m and `vx=+0.30`. | Another substantial body excursion occurs during the lower-step attempt. Its initiating cause is unresolved. |
| Approximately 28–32 s | Robot remains near the stair/runway and changes position/orientation; recording controls partly cover the viewer. At 29 s the HUD still reads `vx=+0.30`, Z 0.34 m and tilt about 2.5°. | Do not infer that an apparent pause or movement away from the stair is a requested stop. The readable command remains nonzero at 29 s. |
| Approximately 32.5–35.27 s | Robot is again at the approach, with `vx=0`, `vy=0`, `yaw=0`; at 32.5 s Z is 0.34 m and tilt about 0.7°. | Another reset/teleport is visible. No complete stair ascent is shown before recording ends. |

There are two visible approach/stair-entry attempts, separated by a reset. The later attempt is interrupted rather than observed through a standardized time limit. This single recording should not be turned into a statistical stair success rate.

## Evidence images

- [Flat approach at 3 s](video_review_20261002_candidate90500/frame_03s.png).
- [First stair entry and tilt, 8.0–10.2 s](video_review_20261002_candidate90500/first_contact_5fps.jpg).
- [58° HUD reading at 10 s](video_review_20261002_candidate90500/frame_10s.png).
- [Low posture, 10.4–12.6 s](video_review_20261002_candidate90500/first_tip_5fps.jpg).
- [0.18 m base-height HUD at 12 s](video_review_20261002_candidate90500/frame_12s.png).
- [Second stair entry, 20.2–22.4 s](video_review_20261002_candidate90500/second_attempt_5fps.jpg).
- [Later second-attempt corrections, 25.4–27.6 s](video_review_20261002_candidate90500/second_attempt_later_5fps.jpg).
- [Second reset/zero command at 32.5 s](video_review_20261002_candidate90500/frame_32_5s.png).

Whole-recording 0.5 s timeline sheets: [0–5.5 s](video_review_20261002_candidate90500/timeline_01.jpg), [6–11.5 s](video_review_20261002_candidate90500/timeline_02.jpg), [12–17.5 s](video_review_20261002_candidate90500/timeline_03.jpg), [18–23.5 s](video_review_20261002_candidate90500/timeline_04.jpg), [24–29.5 s](video_review_20261002_candidate90500/timeline_05.jpg), [30–35 s](video_review_20261002_candidate90500/timeline_06.jpg).

## What we can infer

1. **Stair entry and support transfer need investigation.** Large body excursions occur around the first tread, followed by low posture or repeated lower-step corrections.
2. **The task remains unresolved in this recording.** No full twelve-step traversal is visible. Being upright during parts of the second attempt is not sufficient.
3. **A smoothness reward alone has not demonstrated a complete task fix.** If this is the intended 90500 candidate session, this is evidence that its recorded stair behavior still needs improvement. It does not prove that the new penalties caused the difficulty.
4. **The important signals need synchronizing at stair entry.** The first attempt's 8–12.6 s region and the second attempt's 20–28 s region are useful targets for future trace/video alignment.

The recording does not establish an 8–30 Hz oscillation amplitude, joint-angle RMS, target-clipping occupancy, torque saturation, contact impulse, a damaged motor or a particular MoE expert causing the motion. No matching original-90000 video with the same command schedule was supplied in this folder. A percentage improvement or regression relative to the original policy cannot be calculated.

At 30 fps, this screen recording cannot resolve the full 8–30 Hz band, and projected rendered leg motion is not a direct joint-angle measurement. The old audit's actual-joint plots came from recorded numerical traces, not reconstructed video angles. No corresponding simulator trace was found with this recording.

## Next diagnostic work before another reward change

1. **Record the loaded checkpoint identity and an identical evaluation schedule.** Use original 90000 and candidate 90500, Track 1, the same target profile, zero lateral/yaw command and a fixed +0.30 m/s forward command. Use fresh viewer processes rather than mixing resets into one scored trial. Retain incomplete/fallen trials and judge full traversal, stalls and lane retention.
2. **Add local trace logging.** The current viewer has no numerical audit recorder. At each policy update retain raw/clipped action, requested target, clamped target and command; at the 200 Hz physics rate retain joint position/velocity, applied torque, base position/orientation/velocity and foot contacts/positions/forces. Log simulation and wall timestamps, episode/reset identifiers and policy-update identifiers.
3. **Verify sensor-state timing and reset semantics while preparing the logger.** The existing controller reads `sensordata` for gyro and directly reads q/qvel. Establish that these represent the intended same observation state. Fresh processes reduce reset carry-over but do not automatically validate sensor freshness.
4. **Plot matched windows before contact and during contact.** Inspect q versus requested/clamped targets, target differences, target/torque saturation, foot clearance relative to terrain, contacts, body tilt/height, heading and commanded versus measured speed. Use joint telemetry for the 8–30 Hz measured-motion comparison. Specify how 50 Hz held targets are represented if showing their spectra.
5. **Choose the next change from the recorded failure.** Rapid target reversals motivate reviewing smoothness contributions; large requested/clamped gaps motivate reviewing saturation pressure; stair-edge clearance errors motivate inspecting clearance definitions; torque saturation or contact-response problems motivate later actuator/contact investigation. These are conditional diagnoses, not findings already established by the video.

Keep the current reward weights and actuator settings while establishing this evaluation evidence. The next concrete improvement to the investigation is synchronized trace logging, not another coefficient chosen from appearance alone.

## Scope of this review

Only local analysis images and Markdown notes were created/updated. No simulator or training Python was changed in this review, no simulation was launched, and no server action was performed.

Code references: [viewer HUD and stepping loop](../xterra_mjlab/svanm2_moe_stair_sim/run_interactive_sim.py), [target/PD controller](../xterra_mjlab/svanm2_moe_stair_sim/controller.py), [command/reset handling and base-x region label](../xterra_mjlab/svanm2_moe_stair_sim/teleop.py), [track dimensions](../xterra_mjlab/svanm2_moe_stair_sim/build_scene.py). These explain the displayed fields; they are not a substitute for the recorded session's provenance or telemetry.
