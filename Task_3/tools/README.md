# Start here: fresh MoE failure analysis

**Current workflow:** [record your own interactive viewer session, then plot the saved data](../notes/19_RECORD_MY_INTERACTIVE_RUN.md). `run_interactive_sim.py --record` enables passive live measurements; [plot_interactive.py](jitter_analysis/plot_interactive.py) reads those saved logs without running a new simulation. New recordings stay under `results/interactive/`; existing suites below retain their scripted provenance.

Created 2026-10-02. This folder contains isolated local measurement tools. The old audit is a source of hypotheses, **not ground truth**. These tools import the current controller without editing it, run fresh simulations, and save raw data before interpreting it. No training or server access is performed by these tools.

**Need the graphs explained?** Read [the simple-English plot guide](../notes/15_HOW_TO_READ_THE_PLOTS.md), added 2026-10-03. The dashboard pages now show these explanations directly above each plot, including the speed request, actual speed, height, tilt, heading, contacts and frequency graphs. Refresh the page to see them. The requested speed is deliberately held at 0.30 m/s after the startup ramp so comparisons use the same task.

Open the [first matched comparison](results/20261002_matched_v1/index.html) and its [findings](results/20261002_matched_v1/REPORT.md). The original video review is [note 13](../notes/13_CANDIDATE_VIDEO_REVIEW_20261002.md). Its source is exactly `Task_3/Videos/2026-10-02 18-50-10.mp4`; screen-recording timestamps and simulation timestamps are different.

**Completed:** 20 local evaluation executions (16 distinct conditions), plus a smoke run and four passing validation tests. The [three-start dashboard](results/20261002_stair_repeats_v1/index.html) shows that candidate jitter changes are mixed, although early speed tracking and target removal improve. None of the twelve distinct stair cases completed ascent. Begin with the [first-contact plot](results/20261002_matched_v1/candidate90500_stairs_viewer_start0/08_first_contact.png), then the [controlled flat/stair comparison](results/20261002_matched_v1/candidate90500_stairs_viewer_start0/09_flat_comparison.png). These measured results motivate checking clearance/support/heading and observation timing before another reward change.

## Do the changed angle limits require a changed J_LEG?

**No. A permitted target range and a mechanical transmission ratio describe different things.** Changing hip targets to ±0.735 rad or calf targets to a maximum of −0.88776 rad restricts the angles requested by the policy. It does not change the assumed gears or belt routing.

The current [stair controller](../xterra_mjlab/svanm2_moe_stair_sim/controller.py) and [training actuator](../xterra_mjlab/xterra_mjlab/actuators/svanm2_actuator.py) implement this mapping, for one leg:

```text
motor_hip   = 8 × q_hip
motor_thigh = 8 × q_thigh
motor_calf  = 16 × (q_calf + 0.5 × q_thigh)

J_LEG = [[8, 0,  0],
         [0, 8,  0],
         [0, 8, 16]]
```

For a calf target change of 0.10 rad, with thigh unchanged, the desired calf motor coordinate changes by 1.6 rad. The same conversion applies before and after changing the allowed target interval. The torque mapping follows virtual work: `tau_joint = J_LEG.T @ tau_motor` for column vectors (equivalently `tau_motor @ J_LEG` for the row representation in this controller).

This constant transmission matrix is **not the configuration-dependent foot-position Jacobian** used to relate joint velocities to foot velocities. Do not substitute one for the other. Reconsider the transmission model only if gear ratios, belt direction/routing, coordinate signs, or measurements show it is incorrect. Agreement between two source files proves implementation agreement, not hardware calibration.

With kp=20 and the present gain conversion, `J.T @ diag(kp/gear²) @ J` is `[[20,0,0],[0,25,10],[0,10,20]]`. Thigh and calf are coupled. The actuator file's prose saying every effective diagonal equals the configured gain is too broad: the thigh diagonal here is 25. The implemented calculation and the test make this explicit; no production code was changed.

In the supplied MuJoCo screenshot, **Joint** shows measured joint angles. **Control** shows actuator inputs. In this scene the actuators are gear-one torque motors, so values such as `0.951` are torque inputs, not a hip angle violating ±0.735. Requested/clamped position targets must be read from the controller trace, not that Control panel.

## Files and outputs

| File | Purpose |
| --- | --- |
| [jitter_analysis/record.py](jitter_analysis/record.py) | Fresh simulation and synchronized joint, target, torque, contact, command, body-state and gate logging |
| [jitter_analysis/analyze.py](jitter_analysis/analyze.py) | Seven figures, per-phase metrics and a per-run HTML page |
| [jitter_analysis/first_contact.py](jitter_analysis/first_contact.py) | Event-level geometry/target/torque inspection and optional matched flat comparison; two additional plots |
| [jitter_analysis/compare_starts.py](jitter_analysis/compare_starts.py) | Paired starting-pose sensitivity plot, keeping improvements and regressions visible |
| [jitter_analysis/plot_help.py](jitter_analysis/plot_help.py) | Simple-English plot explanations for new pages; can also update existing HTML pages without rerunning experiments |
| [jitter_analysis/run_suite.py](jitter_analysis/run_suite.py) | Original/candidate × flat/stairs × existing/refreshed observation timing; comparison CSV/JSON/dashboard |
| [jitter_analysis/test_analysis.py](jitter_analysis/test_analysis.py) | Passive recording, known-frequency RMS, traversal and transmission checks |
| `results/<suite>/<case>/trace.npz` | Numeric arrays, with common simulation timestamps; no pickle needed |
| `contacts.jsonl` | Contact geometry names, positions, frames and solver force vectors |
| `manifest.json`, `status.json` | Checkpoint path/update/hash, code hashes, model settings, outcome and numerical warnings |
| `source/` | Recorder/controller/policy/scene-builder snapshots used for that case |

The original checkpoint is `xterra_mjlab/checkpoints/svanm2_moe/model_90000.pt`. The candidate is `xterra_mjlab/evaluation_runs/20261002_moe_target_bundle_updates90500/latest.pt`. The loader prints the actual path and saved update; the viewer banner is not used as evidence.

## Read the plots in this order

| Plot | Question | What would justify a next experiment? |
| --- | --- | --- |
| `01_motion.png` | Does it advance, track speed, stay upright, keep heading? When does the failure start? | Localize the failure before inspecting joint-level signals; distinguish a stall, lane exit and fall |
| `04_contacts.png` and `05_feet.png` | Which foot meets a riser or tread? Does support change before tilt grows? | Repeated loaded riser contact suggests checking swing clearance/placement, not blindly adding smoothness |
| `02_angles.png` | Are requests outside bounds? Do physical joints track clamped targets? | Separate policy request, target limiting, and tracking/contact response |
| `03_torques.png` | Is commanded torque actually clipped at the critical event? | Sustained clipping plus tracking error supports an effort-limit investigation; lack of clipping weakens that explanation |
| `06_policy.png` | When do costs, sensor discrepancies and soft expert weights change? | Timing/gating associations are leads; controlled intervention is needed to assess causality |
| `07_spectra.png` | How much rapid joint motion exists in comparable intervals? | Compare the same frequency band, sample rate and motion phase, alongside task performance |
| `08_first_contact.png` | Was the first foot high enough, and was its target or torque clipped at impact? | Inspect initial placement and subsequent correction; the target-pose curve is static forward kinematics, not a dynamic prediction |
| `09_flat_comparison.png` | What changes when the same policy encounters stair collisions? | A controlled terrain intervention isolates the effect on the full feedback loop, not its internal root cause |

Do not identify the cause from one plot. A target can change because contact already disturbed the body, and that change can then influence the next contact. A physical joint can differ from its target under load even with an accurate controller. A foot x/z projection does not show lateral position and is not a collision detector; use named contact records.

## Measurement contract

- Fresh `MjData` and fixed Track 1 spawn for every run; no interactive reset or steering rescue.
- 3 s zero command with the MoE active, then a 1 s linear ramp to +0.30 m/s forward, zero lateral/yaw. No separate stand-controller blend. This is an explicit protocol, not an exact replay of joystick startup or the supplied video.
- Up to 30 simulation seconds; 5 ms physics/PD steps (200 Hz), policy every 4 steps (50 Hz). GPU inference, ordinary CPU MuJoCo physics.
- Both policies use the same **current** target limits, scale, kp/kd, transmission, torque limits and scene. This compares saved policies in this evaluation plant, not the original training environments.
- Flat runs disable only compiled stair/platform/curb collisions. No XML file is edited.
- Each row: state and target at `t`, plus forces from the solve for `[t,t+dt]`. `policy_tick` marks actual 50 Hz inferences. `raw_action` is before raw clipping; `action` is clipped to ±6, and remains the previous-action observation convention.
- Fresh body/foot kinematics are computed on a copied `MjData`; the main physics state is untouched. The passive test compares original and instrumented trajectories exactly for 240 CPU steps.
- `viewer` observations reproduce the existing controller's timing. `fresh` changes only its observation source, using the freshly forwarded copy. MuJoCo computes dynamics before integrating, so derived values left after a step can correspond to the pre-integration state. [MuJoCo simulation documentation](https://mujoco.readthedocs.io/en/stable/programming/simulation.html)
- Contact force components are in the contact frame, using `mj_contactForce`. Normal magnitudes are summed per foot. A riser contact means a named step contact with `abs(normal_z)<0.3`; rounded edges may have diagonal normals and are omitted from this narrow classification. [MuJoCo API documentation](https://mujoco.readthedocs.io/en/stable/APIreference/APIfunctions.html)
- Foot clearance is sphere-bottom height minus the surface under its center, for the axis-aligned scene. It can jump when x/y crosses a step edge; it is not signed shortest-distance clearance. Foot radius is 0.022 m.
- Measured-joint HF RMS: 8–30 Hz, using 200 Hz samples and Welch PSD integration. Target HF RMS: **8–20 Hz**, using 50 Hz policy ticks. No unsupported target spectrum above the 25 Hz Nyquist frequency. Do not compare the two amplitudes as equal-band measurements.
- Need at least 2 contiguous seconds for HF metrics. Short intervals yield `null`. This band measures rapid motion, not all gait movement; impacts and transient corrections can also contribute.
- First foot/stair contact requires >1 N normal force on a named step. Full traversal requires all feet past the last riser, all having made loaded contact with the platform, reasonable tilt/clearance and staying inside the lane, held for 0.5 s. This is a conservative recorded criterion, not just base x passing a line.
- Stop on sustained >60° tilt, base clearance <0.12 m, or foot lane departure after stair contact (each 0.25 s), or traversal. A timeout is incomplete; it is not automatically a fall or a stall.
- `flat_completed` only means the time horizon completed without those stop conditions. Tracking/heading must still be checked.
- The fixed 4–8 s dashboard window provides equal-duration early-motion comparisons. Event-aligned approach/contact phase durations are also saved and can differ. Do not interpret a shorter failure trace's average as an improvement.

## Run locally

```bash
cd /home/vivekananda/UGP_1_VLM/VLM_Based_Robot_Navigation/Task_3
M2_LOCAL_PY="$PWD/xterra_mjlab/.venv/bin/python"

# Validate the tools (CPU checks; does not train).
"$M2_LOCAL_PY" -B tools/jitter_analysis/test_analysis.py

# Eight matched runs and plots. Choose a NEW result directory each time.
"$M2_LOCAL_PY" -B tools/jitter_analysis/run_suite.py \
  --device cuda:0 --out tools/results/my_next_comparison

# One candidate run, using existing viewer observation timing.
"$M2_LOCAL_PY" -B tools/jitter_analysis/record.py \
  --checkpoint xterra_mjlab/evaluation_runs/20261002_moe_target_bundle_updates90500/latest.pt \
  --terrain stairs --sensors viewer --device cuda:0 \
  --vx 0.30 --out tools/results/my_single_candidate
"$M2_LOCAL_PY" -B tools/jitter_analysis/analyze.py tools/results/my_single_candidate
"$M2_LOCAL_PY" -B tools/jitter_analysis/first_contact.py tools/results/my_single_candidate

# Repeat the relevant stair cases at three small, matched starting-pose offsets.
"$M2_LOCAL_PY" -B tools/jitter_analysis/run_suite.py \
  --device cuda:0 --terrains stairs --starts 3 --out tools/results/my_stair_repeats
"$M2_LOCAL_PY" -B tools/jitter_analysis/compare_starts.py tools/results/my_stair_repeats

# Serve results. Leave the terminal running; Ctrl+C stops only the web server.
python3 -m http.server 8000 --bind 127.0.0.1
```

Open <http://127.0.0.1:8000/tools/results/20261002_matched_v1/index.html>. If port 8000 is already serving Task_3, use that existing server. A terminal command does not need to be run again just to reopen the website.

## Decision checklist

- [x] Review the actual file in `Task_3/Videos` and save timestamped observations.
- [x] Distinguish target limits from the transmission matrix; leave J unchanged without mechanical evidence.
- [x] Build isolated logging, provenance and plotting tools.
- [x] Validate that passive instrumentation preserves the original trajectory in the tested case.
- [x] Read fresh matched results and identify the earliest reproducible failure event: front-foot contact low on the first riser, then unsuccessful adaptation.
- [x] Repeat relevant cases with small matched spawn offsets: both policies fail all three stair starts in each observation mode; oscillation comparisons have mixed signs.
- [ ] Choose the next change from measured evidence: observation timing, foot clearance/placement, support/tracking, or actuator/contact calibration.
- [ ] Only then choose another reward experiment and compare with the same protocol. Keep raw logs, failures and exact model hashes.

The existing candidate changes several things together. An improvement or regression cannot be attributed uniquely to either new reward, action-rate weight, or target clipping. Reward losses decreasing during training also do not establish that physical joint oscillation or stair success improved.
