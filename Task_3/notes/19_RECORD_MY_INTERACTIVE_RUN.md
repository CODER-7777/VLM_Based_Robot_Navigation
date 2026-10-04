# Record my commands first, then plot what actually happened

Updated **2026-10-05**. No new training is needed for recording or plotting.

## Start the original90000 versus newest91000 comparison

The **actor's final linear layer** produces the 12 numerical joint actions: `CheckpointPolicy.actor = MLP([77,512,256,128,12])` in [checkpoint_policy.py](../xterra_mjlab/svanm2_moe_stair_sim/checkpoint_policy.py). The MoE mixes eight latent feature vectors into 32 normalized values; the actor combines them with the latest 45 observations. [controller.py](../xterra_mjlab/svanm2_moe_stair_sim/controller.py) clips the numerical actions, scales them/adds Q0, clamps targets, then applies coupled PD torque. The velocity graphs are actual robot response, not network outputs.

Training already has action-rate, physical-target second-difference, target-rate-excess and target-saturation costs in the newest candidate. They are soft objectives, not hard target-speed limits. Second differences of **position targets** are acceleration-like, not position jerk. Smoothness gains must retain motion/tracking, heading and support; zero movement is not a successful smooth policy. Do not add duplicate terms or change actor/gate architecture before the comparison.

**First pair: +Y = 0.15 m/s.** Run on the local graphical computer, not an SSH-only terminal. Paste the first block. Close that viewer before pasting the second launch; this also avoids queued terminal text being interpreted as movement keys. The recorder creates the output folders; do not create them manually.

```bash
cd /home/vivekananda/UGP_1_VLM/VLM_Based_Robot_Navigation/Task_3
M2_PAIR="tools/results/interactive/comparison_y015_$(date +%Y%m%d_%H%M%S)"

xterra_mjlab/.venv/bin/python xterra_mjlab/svanm2_moe_stair_sim/run_interactive_sim.py \
  --checkpoint-file xterra_mjlab/checkpoints/svanm2_moe/model_90000.pt \
  --track 1 --device cuda:0 --observation-timing legacy \
  --log-dir "$M2_PAIR/original90000"
```

After closing the original viewer, paste this in the **same terminal**:

```bash
xterra_mjlab/.venv/bin/python xterra_mjlab/svanm2_moe_stair_sim/run_interactive_sim.py \
  --checkpoint-file xterra_mjlab/evaluation_runs/moe_swing013_latest/latest.pt \
  --track 1 --device cuda:0 --observation-timing legacy \
  --log-dir "$M2_PAIR/candidate91000"
```

For **each** viewer: wait 3 simulation seconds, focus the terminal, tap A exactly three times, check `vx=0, vy=+0.15, yaw=0`, release the keys and hold that request for **12 simulation seconds**, then Space and close normally. Do not reset/teleport or use steering rescue. Both launches are fresh processes. Retain bad motion and falls; wait out the recording if it falls rather than silently discarding that attempt. Verify the printed update is 90000 then 91000. Current simulation bounds/gains are used for both; neither controller nor hardware limits are modified by these commands. Actual obstacle contacts are checked in the comparison, because vx=0 does not guarantee zero forward drift.

After **both** viewers close, paste in the same terminal:

```bash
for M2_SESSION in "$M2_PAIR/original90000" "$M2_PAIR/candidate91000"; do
  xterra_mjlab/.venv/bin/python tools/jitter_analysis/plot_interactive.py "$M2_SESSION"
  xterra_mjlab/.venv/bin/python tools/jitter_analysis/diagnose_updates.py "$M2_SESSION" --device cuda:0
done

xterra_mjlab/.venv/bin/python tools/jitter_analysis/compare_policy_runs.py \
  "$M2_PAIR/original90000" "$M2_PAIR/candidate91000" \
  --command 0 0.15 0 --settle 1 --seconds 8 --out "$M2_PAIR/comparison"

printf 'http://127.0.0.1:8000/%s/comparison/index.html\n' "${M2_PAIR#tools/results/}"
```

The last line prints the browser URL for the existing server rooted at `tools/results`. Open it. If starting the server yourself, in another terminal use `python3 -m http.server 8000 --bind 127.0.0.1 --directory tools/results` from Task_3. Do not start a second process if port 8000 is already serving this directory. If you use a new terminal for plotting, set `M2_PAIR` to the actual saved directory rather than a new timestamp.

The comparison uses eight continuous seconds after one second settling under the exact requested command. It checks model identities, initial recorded state, target limits/scales, PD/transmission, friction/contact settings, scene and controller sources, sensing timing and duration. It flags the same weights used twice, a first recording not at 90000, short holds and configuration mismatches. It preserves results for incomplete holds rather than presenting them as an equal-duration comparison. Manual command ramps/timing can still differ; one pair is not a success-rate estimate. No physics or inference runs during comparison.

Read the table in this order:

1. `Same recorded contract and full duration: True`; `No stair contact...: True`. Otherwise inspect why before calling it a flat matched comparison.
2. Mean body vy close to 0.15 and lower vy RMSE: successful lateral tracking. Check unwanted vx and yaw as well.
3. Joint 8–30 Hz RMS lower: less measured rapid joint motion. Use identical sample rates/bands.
4. Lower p99 target steps/second-difference cost: fewer sharp target changes; judge alongside tracking, not alone.
5. Tilt, heading drift and torque clipping do not worsen. A stopped, tilted or fallen robot is not an improvement even if its eventual trace is smooth.

Next pairs use the **same two launches with a new `M2_PAIR` directory**, changing only keys and the expected comparison command:

| Test | Keys after standing | Comparison `--command` |
| --- | --- | --- |
| −Y 0.15 | D three times | `0 -0.15 0` |
| +Y 0.30 | A six times | `0 0.30 0` |
| −Y 0.30 | D six times | `0 -0.30 0` |

Repeat each pair in fresh processes for at least three starts before claiming a consistent improvement. Later do forward/stair trials separately: at vx=0.30 the 1.5 m runway reaches stairs in roughly five seconds of ideal tracking, so a 12-second forward run in this scene is not a flat-only test.

## Current workflow: sideways recordings (+Y and −Y)

The existing recorder saves all three velocity commands and body/world motion, q/dq, targets, torques, contacts, observations and gates. The October 5 plot update adds actual sideways speed, actual yaw rate, world y position, lateral/yaw tracking errors and joint detail around motion onset when no stair event occurs. It changes only offline plots/analysis. Positive body Y is left relative to the robot; negative Y is right. World Y differs after the robot turns.

Start a fresh process for each direction/speed to avoid reset carry-over. Use a unique directory; it is created by the recorder:

```bash
cd /home/vivekananda/UGP_1_VLM/VLM_Based_Robot_Navigation/Task_3
M2_SIDE_LOG="tools/results/interactive/sideways_91000_$(date +%Y%m%d_%H%M%S)"
xterra_mjlab/.venv/bin/python xterra_mjlab/svanm2_moe_stair_sim/run_interactive_sim.py \
  --checkpoint-file xterra_mjlab/evaluation_runs/moe_swing013_latest/latest.pt \
  --track 1 --device cuda:0 --observation-timing legacy \
  --log-dir "$M2_SIDE_LOG"
```

1. Keep vx and yaw requests zero; wait roughly 3 simulation seconds standing.
2. For +Y, tap **A three times** in the terminal (viewer Left arrow): vy +0.15 m/s. For a separate −Y run, tap **D three times** (viewer Right arrow): vy −0.15 m/s. Check the displayed command; holding a key can repeat it.
3. Release the keys, observe about 10 seconds of steady motion, then press Space to zero commands. Avoid steering rescue in the reference attempt. Close the viewer normally to flush the files. Retain shaking/drift/failures.
4. Repeat in a new process for the other direction. Then test ±0.30 using six taps. Diagnose within the saved ±0.3 m/s training range before testing ±0.6 separately. Check recorded obstacle contacts and world x drift: requesting vx=0 does not guarantee that the feet avoid stairs.
5. In the same terminal, plot the saved data:

```bash
xterra_mjlab/.venv/bin/python tools/jitter_analysis/plot_interactive.py "$M2_SIDE_LOG"
xterra_mjlab/.venv/bin/python tools/jitter_analysis/diagnose_updates.py "$M2_SIDE_LOG" --device cuda:0
```

Each attempt has `plots/index.html` and `plots/update_diagnostics.html`. With the existing server rooted at `tools/results`, open `http://127.0.0.1:8000/interactive/<printed-session-folder>/index.html`. If using another terminal, replace `$M2_SIDE_LOG` with its actual path printed at recording startup. Plot after closing the viewer. The offline tools do not simulate a new trajectory.

For a separate sensing comparison, repeat identical commands/checkpoint/bounds/gains/contact settings with `--observation-timing fresh`. Keep the gate/policy at 50 Hz and PD/physics at 200 Hz. Test a frequency/gate intervention separately if the evidence justifies it. The fixed candidate used above is the new 91000 retry, SHA `dec9775d4b368b69964dde679985455d8b723d5af7fb2d24e8798fa4fdd66da4`, not the older `20261004_moe_time_rate_updates91000` candidate. The loader prints actual path/update and the manifest saves hash/bounds.

**Current controller bounds:** hips ±1.0472 rad, calf upper +0.500 rad, matching the newest recorded simulation. The October 3 sections below describe historical tighter-limit instructions, not the current setup. J_LEG, gains, limits, inference frequency and model weights were not changed for sideways support.

**Historical October 3 controller edit:** all four hip target bounds were ±0.735 rad and all four calf upper targets −0.886 rad. This used the user's requested calf value; the audit's exact value was −0.88776 rad. Each recording's manifest captures the actual bounds used. These bounds were subsequently reverted at the user's request.

## 1. What we know now

When recording was added, the local controller had hips ±1.0472 rad and calf upper +0.5000 rad. The user reported better stair climbing after restoring these values, with similar visible jitter. The latest tighter-limit edit is recorded above. That suggests climbing and shaking need separate measurements; it does not yet prove that target limits have no effect on jitter.

The earlier suites used scripted forward commands and saved actual simulated data. The new mode uses **your real keyboard inputs in the interactive viewer**, logs the resulting MuJoCo states, and later plots only those saved logs. It still measures a simulator, not physical hardware. No commands, curves or outcomes are invented by the plotter.

## 2. Run and record the viewer

On the local graphical desktop:

```bash
cd /home/vivekananda/UGP_1_VLM/VLM_Based_Robot_Navigation/Task_3

xterra_mjlab/.venv/bin/python xterra_mjlab/svanm2_moe_stair_sim/run_interactive_sim.py \
  --checkpoint-file xterra_mjlab/evaluation_runs/20261002_moe_target_bundle_updates90500/latest.pt \
  --track 1 --device cuda:0 \
  --log-dir tools/results/interactive/user_run_01
```

This loads the October 2 combined candidate at update **90500**, starts the 10 cm track and logs the session. Verify the printed checkpoint path, update, GPU and `[RECORD]` output directory. The banner now displays the loaded update too. Policy inference uses GPU; standard MuJoCo physics runs on CPU.

The output directory must be new. For the next session use `user_run_02`, or replace `--log-dir ...` with `--record` to get an automatic timestamp under `tools/results/interactive/`.

Drive naturally with your own commands. Terminal `w/s` changes forward speed, `a/d` changes lateral speed, `q/e` changes yaw rate, and Space zeros the commands. Viewer keys also work. `r`, track-number keys and `t` reset/teleport and automatically create a new attempt. Do not edit MuJoCo physics/joint/actuator values through its GUI during a diagnostic recording; the saved controller configuration is captured at session start.

Close the viewer or press Ctrl+C in its terminal to finish. Look for `[RECORD] Data saved: ...`. Closing normally flushes the last samples. Chunks are also saved every 1,000 steps (about 5 simulation seconds), so a hard kill leaves earlier chunks available but can lose the last unsaved chunk. No retraining or automatic rescue is performed.

## 3. Plot afterward

After the viewer has closed, from the same Task_3 directory:

```bash
xterra_mjlab/.venv/bin/python tools/jitter_analysis/plot_interactive.py \
  tools/results/interactive/user_run_01
```

This reads the raw chunks and creates three plots for each attempt. It does not load a checkpoint or advance MuJoCo. If you want a short section only:

```bash
xterra_mjlab/.venv/bin/python tools/jitter_analysis/plot_interactive.py \
  tools/results/interactive/user_run_01 --episode 1 --start 5 --stop 15
```

The times are seconds since that attempt's reset. This replaces only that attempt's generated plots/metrics with the selected window; raw recordings remain unchanged. Select at least two seconds for the frequency metric. A very short attempt still gets time plots, but no invented oscillation number.

## 4. Open the graphs

```bash
python3 -m http.server 8000 --bind 127.0.0.1
```

Open <http://127.0.0.1:8000/tools/results/interactive/user_run_01/index.html>. If the server is already running from Task_3, just open the link; do not start a second server on the same port.

Read only these three views first:

1. **Overview:** what you requested versus actual forward speed, all keyboard commands, progress/body height, tilt and heading. The `vx sent to policy` curve is the actual command sampled at inference, not a predefined constant. A held keyboard command naturally remains constant until you change it.
2. **Joint event:** requested target, clamped target and measured joint angle in a short interval around first stair contact (one second before to three after). If there is no contact in the selected interval, it uses the first four selected seconds.
3. **Contacts/control:** foot heights, vertical riser forces, target removal and torque magnitudes. Check whether shaking begins before or after foot impacts, and whether requests or torque are being clipped.

The page explains each figure. A red dotted line means the first recorded riser/stair contact for that attempt; it is absent if no contact occurs in the selected interval. The dashed height in the contact plot is the approximate first-tread clearance threshold, not the height needed for every later step.

The 8–30 Hz joint RMS uses 200 Hz state samples at the current timestep. It includes impacts and useful corrections within the selected window, so lower RMS alone is not successful locomotion. There is no automatic assertion of full stair traversal. Preserve videos alongside the logs to review feet reaching the top, falls, stalls and any steering intervention.

## 5. What gets saved

```text
tools/results/interactive/user_run_01/
  manifest.json           checkpoint identity, limits, gains, timestep, code hashes
  events.jsonl            actual terminal/viewer keys, commands and resets
  source/                 source/scene snapshots for this session
  status.json             session closure/error
  index.html              generated after plotting
  attempt_001/
    manifest.json         track and initial pose for this attempt
    status.json           chunks, samples and first-contact timestamps
    contacts.jsonl        contact geometry, position and solver forces
    raw/chunk_*.npz       numeric samples captured during your run
    plots/                three PNGs, metrics.json and explained index.html
  attempt_002/             created if you reset or teleport
```

Raw data include q/dq, raw and clipped actions, requested/clamped targets, actual applied torque, contacts, foot/body movement, the policy's observation readings, fresh diagnostic readings, gate weights, simulation time and wall time. State is recorded at the start of a physics interval; applied torques and contact forces belong to that interval. Previous raw-action history semantics and the current controller's sensor timing are retained. Fresh diagnostic readings are evaluated on a copy of simulation data and are never fed back to the policy.

Recording mode queues keyboard events to apply them between physics steps, rather than allowing another thread to reset the robot during a solver/measurement operation. Keys retain the existing increments and limits; policy commands still update at 50 Hz. The event log distinguishes input time from the command actually sampled by the policy. Logging/disk work adds wall-clock overhead; simulator timestamps and measured wall timestamps are both saved. This is not a model of hardware latency.

## 6. Clean folder layout and validation

Follow [Task_3/README.md](../README.md) for the folder map. Four loose files were grouped without changing contents: the plan's two screenshots went to `notes/assets/` and the old debug dump/screenshot went to `tools/archive/debug_exports_20260926/`. PLAN.md image links were updated. [The move manifest](../tools/archive/organization_20261003.json) records original locations and hashes. Checkpoints, videos, old dashboards and numerical results were retained in place. Editor swap files were left alone.

The new recording path was verified against an uninstrumented controller over 240 CPU physics steps, including queued command changes and a reset: positions, velocities and targets matched exactly. The test also checked chunk loading, separate attempts, command sampling and saved-data-only plot generation. Validation data were temporary and are not presented as your recording. A graphical run with your commands still needs to be recorded by you.

**Next:** record the wider-limit run using this workflow. Then, if needed, make a separate tighter-limit recording with the same checkpoint and comparable commands. Save both exact manifests. Compare climbing success and matched jitter windows separately before making another reward or actuator change.
