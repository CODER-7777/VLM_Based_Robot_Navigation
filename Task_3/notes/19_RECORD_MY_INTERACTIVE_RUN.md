# Record my commands first, then plot what actually happened

Updated **2026-10-03**. This is the current practical workflow. No new training is needed.

**Latest controller edit, at the user's request:** all four hip target bounds are now ±0.735 rad and all four calf upper targets are −0.886 rad. This uses the user's requested calf value; the audit's exact value was −0.88776 rad. Other target entries, J_LEG, gains, torque limits and checkpoint weights were not changed. Restart the viewer and use a new recording directory (for example `user_run_02`) for this condition. Each recording's manifest captures the actual bounds used.

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
