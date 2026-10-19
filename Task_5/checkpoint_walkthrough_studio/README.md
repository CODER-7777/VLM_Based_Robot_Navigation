# Checkpoint Walkthrough Studio

> Source publication: images, recordings, generated catalogs, dataset assets and runtime reports referenced below stay local. See the Task 5 reproducibility guide for required inputs.

Open **http://127.0.0.1:8900/** on this computer.

This is a separate app using the voice/video workflow in `level3_manual_collector_v2` as a reference. Its source, launcher, recordings, camera, and ports are independent of V2 and the earlier trajectory review dashboard.

## Start

From any terminal:

```sh
/home/vivekananda/UGP_1_VLM/VLM_Based_Robot_Navigation/Task_5/start_checkpoint_walkthrough.sh
```

The script opens the dashboard and reuses its existing services. Add `--no-open` to start without opening a browser, or `--status` to check the local web server. It starts a separate tmux supervisor under the current desktop user. It does not install login/autoboot startup. Services remain available after the terminal closes.

The recorded walkthrough, map, and panoramas work without the simulation server. **Live WASD** requires SSH/VPN access to `guest-isl@172.26.186.222`, the existing Habitat environment and scene assets. The supervisor retries this connection. Set `TASK5_SIM_HOST` before starting if the server address changes.

## Available tours and slower rotation

The default tour is **2azQ1b91cZZ · ground floor**: 20 annotated ground-floor rooms, 152.72 m, 14:38.25, 17,565 rendered frames, 96 checkpoints and 192 JPEGs. Sixteen room inspections each rotate 360° over 24 seconds. All video poses stay within the validated ground-floor height band; upper-floor rooms are excluded.

Use the tour dropdown to switch to **Environment 04 · slow turns** (108.8 seconds). That reference replays stationary turning frames four times while preserving the original walking timing and poses. It has repeated frames during turns, rather than newly rendered intermediate angles. The original 80-second reference and its downloads remain archived at `assets/pilot_04/`. Existing saved samples are preserved.

The rotation selector defaults to **15°/s** (24 s per full turn), with 10°/s and 30°/s options. It changes stationary-turn playback independently of walking speed. Live WASD turns use time-limited increments; key repeat does not multiply their speed. Panorama dragging is also less sensitive. The new tour’s source video natively renders turns at 15°/s. A faster/slower playback selection changes review playback, not the original downloaded file.

New tour: http://127.0.0.1:8900/?tour=ground_2az

Video: http://127.0.0.1:8900/assets/ground_2az/walkthrough.mp4

Checkpoint ZIP (192 images + detailed guide + template): http://127.0.0.1:8900/assets/ground_2az/checkpoint_images.zip

The selected tour’s guide, video, CSV, plan and timeline downloads update together. New samples store the selected tour ID, scene and reference plan. Save an active sample before switching tours.

Rebuild a tour ZIP using `python3 -B tools/package_checkpoints.py --assets assets/ground_2az --filename checkpoint_images.zip`. Reproduce ground-floor planning/rendering with `tools/record_ground_tour.py` on the simulation server using GPU 0 and the scene catalog. The room route uses floor-validated navmesh paths; the final video and panoramas were validated against the plan.

## Original reference: download all checkpoint images

The walkthrough and photos are **already recorded**. Watching or downloading them does not require creating a sample. The optional recording panel is collapsed by default; use it only to add your own voice or make a new recording. The existing walkthrough has no spoken narration.

Click **All checkpoint images ZIP (60 images)** at the top, or open:

http://127.0.0.1:8900/assets/pilot_04/checkpoint_images_all_30.zip

The ZIP contains all 30 full panoramas and 30 forward-view JPEGs, grouped under `checkpoints/C01/` through `checkpoints/C30/`, plus the checkpoint CSV, plan JSON, detailed `RECORDING_AND_REASONING_GUIDE.md`, reasoning template and README. Rebuild after replacing pilot images with `python3 -B tools/package_checkpoints.py`. The video has its own separate download button.

## Original reference: pilot details

Environment 04 is `SN83YJsR3w2`. The authored sequence is **1 → 2 → 3 → 4 → 5 → 4 → 3 → 6**, with a six-second stationary 360° turn at 5. The newly authored navmesh route is **45.6868 m**. The source RxR validation guide, path 12519, is **47.3105 m**, a separate measurement.

- Walkthrough: 80 seconds, 1600 frames, H264 MP4, 768×512 at 20 fps, 85° horizontal FOV, 1.5 m eye height, nominal 0.65 m/s translation. Camera turns and inspection add stationary time. This is a scripted simulator pilot, not a policy rollout.
- Map/checkpoint rows seek the video. There are 30 checkpoints: regular 2 m path-distance samples plus required anchors/endpoints. Extra anchors subdivide intervals; they are not additional 2 m steps. The return leg visits some physical locations again.
- 360° panorama: drag to look, scroll to change FOV. Images are 2048×1024 equirectangular cubemap renders of the actual scene. Camera movement does not occur in panorama mode.
- Live WASD: click the view, then W/S move and A/D turn; up/down arrows tilt. On-screen buttons also work. Movement uses the scene navmesh. Select a checkpoint and press **Jump to checkpoint** to teleport there; this is logged as inspection, not walking. This independent renderer has one shared camera across tabs/contributors.
- Distances are along the planned navmesh polyline; straight-line intervals are stored separately. The map is an X/Z projection. Rendered bag placements remain review candidates; the original Matterport assets are not changed.

The video and checkpoint photos are generated from Habitat, not AI image generation or scraped replacements. Original source assets stay at their existing server locations.

## Collect voice and video for the selected tour

Use Chrome on localhost. Enter a contributor name, task, and context/memory, then **New sample**.

1. **Record voice** records microphone audio.
2. **Record scene + voice** records the current first-person view (video, panorama, or live camera) with microphone audio and an on-frame timestamp. It does not capture the surrounding interface.
3. **Record tab + voice** opens Chrome's chooser. Choose this dashboard tab to include its interface. Microphone audio is used; system/tab audio is not requested.
4. **Include written reasoning with each submitted sample.** Press **Insert reasoning template**, replace the placeholders, and add an entry at each important checkpoint or decision change. Include the checkpoint/time, task, visible observations, supplied memory/constraint (or “not provided”), chosen action, brief reason, uncertainty and result. Use your own words and distinguish observations from assumptions. Automatic transcription is not enabled; audio alone does not supply reasoning text. **Save reasoning text** persists the explanation as `transcript.txt` and in `manifest.json`; both are included in the sample ZIP. Text-only samples are supported, with no microphone recording required. The downloadable template is `assets/reasoning_template.txt`.
5. **Stop & save sample** stops the recorders and all their tracks, uploads media to this computer, and converts it to browser-playable H264/AAC MP4 (voice-only AAC MP4). Wait for the ZIP button to appear, then download it. Ending screen sharing also stops/saves the sample.

Recording is never automatic. Voice/scene/tab recordings can be combined in one sample. The 80-second scripted pilot is available separately and is not silently counted as a new human demonstration. Starting a recording in Walkthrough mode records playback only when you play the video. Live actions and checkpoint teleports are distinguished in the event ledger.

Contributor labels are not accounts or authentication. Recordings stay in this application's local `sessions/<contributor>/<UTC timestamp>/` folder. Samples contain:

- `manifest.json`: task, context, transcript, media paths and status;
- `transcript.txt`: user-written transcript;
- `events.jsonl`, `trajectory.jsonl`: UTC and elapsed timestamps, source mode, video time, camera pose, movement actions/teleports, and periodic recording poses (4 Hz);
- `voice/`, `scene/`, `screen/`: the requested media;
- `pilot_plan.json`: reference route/checkpoint metadata;
- `sample.zip`: generated on download.

In video mode, camera poses reference the recorded pilot. In panorama mode, they describe the selected fixed observation camera and viewing direction. Live mode reports simulator camera poses and accumulated walking distance. The trajectory ledger is sampled at 4 Hz; it is not claimed to contain an independently rendered live frame for every encoded video frame. The source pilot has a complete 20 Hz frame-pose timeline in `assets/pilot_04/timeline.json`.

Raw in-progress media stays in `.uploads/` until successful conversion. Conversion failures preserve those uploads. Do not close the tab during an active recording or upload. Files are served only over loopback. Source code and recordings are not published to external hosting.

## Files and operation

- `web/`: interface; `server.py`: local storage, media conversion, Range-enabled video serving, proxy.
- `assets/pilot_04/`: walkthrough, 30 panoramas, forward photos, plan, checkpoint CSV with camera coordinates, and frame timeline.
- `tools/scene_service.py`, `renderer_catalog.json`: dedicated on-demand Habitat camera, physical GPU 0.
- Local web `8900`, local SSH tunnel `8912`, server renderer `8914` (server loopback). No V1/V2 or earlier review service is restarted.
- `.runtime/web.log`, `.runtime/tunnel.log`: local logs. Supervisor: `tmux -L checkpoint-walkthrough-studio attach -t studio`. Renderer log: `/tmp/checkpoint_walkthrough_studio_20261016_v2/renderer.log` on the server.
- Stop this app's local supervisor with `tmux -L checkpoint-walkthrough-studio kill-session -t studio`. It stops its owned local web/tunnel processes; the separate lazy server camera remains reusable. Stop only after saving active recordings.

## Verification

Ground-floor measurements and checks are in `.runtime/ground_verification.json`. The original reference regression script explicitly opens `?tour=pilot04`; its 80-second/30-checkpoint assertions do not describe the new ground-floor tour.


`python3 -B tools/verify_studio.py` exercises the real browser and dedicated Habitat camera with synthetic microphone/tab input. No real person or desktop is recorded during QA. Synthetic samples are clearly named `QA_synthetic_media` and kept separate from contributor samples. Checks/results and desktop/mobile screenshots are in `.runtime/verification.json`, `.runtime/desktop.png`, and `.runtime/mobile.png`.

Validated: 30 panorama files; every regular 2 m checkpoint; path interval ≤2 m and straight-line distance ≤path interval; 120 stationary frames spanning a full 360° turn; source H264 video/1600 poses; video seeking; live turn/movement; voice/scene/tab MP4 conversion; microphone/capture tracks ending on save; transcript/ZIP persistence; desktop/mobile layout. `ffprobe` confirmed AAC voice and H264/AAC scene/tab recordings.
