# Level 3 manual collector V2

The original dashboard remains on **port 8876** in `level3_manual_collector/`.
This independent copy runs on **port 8878** in `level3_manual_collector_v2/`.
Both render on the already-approved physical GPU 0. Neither loads a navigation
policy nor runs VILA inference. MP4 conversion runs on CPU.

Open `http://localhost:8878`. From the browser computer, if needed:

```bash
ssh -N -L 8878:127.0.0.1:8878 guest-isl@172.26.186.222
```

## Choose an environment

The Environment and Episode selectors use the same authored cases as
`awarevln_levels_1_2_3_presentation/presentation.html`: 10 Level-3 episodes in
4 scenes (`QUCTc6BB5sX`, `2azQ1b91cZZ`, `TbHJrupSAjP`, `EU6Fwq7SyZv`). Choose
an environment, then its episode. The scene, authored start pose, task/time,
three memories, relevant-memory label and voice examples update together.
Environment changes require STOP & save and completed MP4 exports first.

Episode numbers are global presentation numbers, not local counts within a
scene. The friendly environment labels use the presentation's characters,
not official physical-house names. Scan IDs remain in the task metadata and
dataset files. Labels describe the Level-3 requests while preserving the
source titles and IDs in collected data.

| Environment label | Scene ID | Presentation episodes |
| --- | --- | --- |
| Mary & Riya | QUCTc6BB5sX | 1, 2, 6 |
| Asha & Maya | 2azQ1b91cZZ | 3, 7, 9 |
| Nora & Leo | TbHJrupSAjP | 4, 5 |
| Riya, Oliver & Sam | EU6Fwq7SyZv | 8, 10 |


The clothes episode retains your carrying-dirty-clothes assumption. Other
episodes start with their own presentation context; review any additional
carried items yourself. Saved sessions reload their own environment and memories.
Sample inputs and manifests include scene and episode IDs for dataset tracking.
Relevant-memory selection comes from authored labels, not new model inference.

The server reads the source presentation at startup. `sample_case.json` remains
the laundry default/fallback; the source presentation and scene files are
needed for the full catalog. `presentation_cases.py` performs this import without
changing the original presentation.

## Collect a sample

1. Enter your username, for example `Vivekananda_01`. Saved sessions and the
   latest recording load automatically. Saved samples and download controls sit
   at the bottom of the setup page and update automatically when samples and
   MP4 exports finish. The selected saved sample stays selected during updates. There is no Returning user button.
   Completed human samples were copied from V1; imported media was converted to
   MP4 in the copy. Original files and deleted samples in V1 were not changed.
2. Choose your Environment and Episode before starting. The relevant memory
   is selected automatically from the stored episode label
   or the last sample's selection. You can review or change that selection.
   This is an authored label, not a new model prediction.
3. Click **Create new sample**. A completed sample cannot be continued as a new
   recording: the dashboard prompts you to create a new sample first.
4. Click **Record screen + microphone** to enter actual browser fullscreen
   with navigation UI hidden. Click **Start recording** in the fullscreen
   dialog, choose the dashboard tab or window, and allow microphone access.
   The second click supplies a fresh browser interaction for screen capture.
   If fullscreen is declined by the browser, press F11 and continue. The view
   contains the scene, task/current state, and numbered memories.
5. Memory 1/2/3 are expandable tree entries. Each contains the full continuous
   statement, such as `Mary said "This is where I usually do the laundry."`,
   images with their original view numbers, and the retained descriptions.
   Scroll the image strips, use their arrows, or click a view to enlarge it.
   The **☰ Memories** button toggles the sidebar. **☰ Recording tools** opens
   the transcript and download panel while the scene remains in view.
6. Use W for forward 25 cm, A for left 15°, and D for right 15°. S is disabled.
   Twelve D turns rotate 180°. Rapid individual taps are queued rather than
   discarded. Holding a key issues further steps without building a long stale
   repeat queue. There is no maximum action count or episode duration.
7. Use **Record reasoning** for spoken explanations. The only clip type is
   Reasoning. Stop the clip, enter its corrected transcript, and save the text.
   Automatic speech recognition is not enabled.
8. On arrival, explain the visible match and press **STOP & save** (or Space).
   This stops screen capture and microphone clips together, ends navigation,
   and saves their uploads. A video preview appears in Recording tools after
   saving. It prefers the screen recording and lets you select the navigation
   replay. Press Play to review it. Wait for MP4 preparation. Downloads and the ZIP contain MP4 recordings, not WebM files.
9. Download navigation MP4, screen MP4 with narration, reasoning audio MP4, or
   the whole sample ZIP. Voice MP4s contain audio only. Saved events are in a
   collapsed dropdown. Delete removes a sample from this copy and preserves
   it in this copy's `deleted_sessions/` folder.

## Share with contributors

The current collector has one shared simulator and one active sample. Schedule
contributors one at a time; different usernames label their recordings but do
not create separate simulators or authenticated accounts.

For contributors who can reach the server through the institute network or
VPN and have an authorized SSH account:

1. Open a terminal on the contributor's own computer and run:

   ```bash
   ssh -N -L 127.0.0.1:8878:127.0.0.1:8878 <ssh-user>@172.26.186.222
   ```

   Replace `<ssh-user>` with their authorized server account. Leave the terminal
   running. A user with already-authorized access as `guest-isl` may use that
   account; do not send credentials along with this guide.
2. Open `http://localhost:8878` in desktop Chrome or Edge. This address uses
   the tunnel on that contributor's computer; sending the URL alone does not
   create access.
3. Use a distinct dataset username, create a new sample, and record screen plus
   microphone. Choose the dashboard tab/window and allow microphone access.
4. Navigate with W/A/D, explain the need, relevant memory, visible evidence,
   and next decision, then press STOP & save. Enter and save a corrected
   transcript, wait for MP4 conversion, and download the complete sample ZIP.
5. Close the tunnel when finished and tell the next contributor the collector
   is free. Recordings remain on the server under `sessions/<username>/`.

For a browser link usable outside the institute without SSH, the collector
needs an HTTPS entry point and authenticated access. Simultaneous collection
also needs separate simulator/sample state for each contributor. These are
additional deployment changes; the current single shared collector is not
configured for public or simultaneous access.

## Voice template

Before moving:

> I already have the dirty school clothes with me. Mary said, “This is where I
> usually do the laundry.” I will use the landmarks from that memory to find
> the laundry area.

At a decision:

> I see [actual feature]. This [matches / differs from] the laundry memory.
> I will [turn left / turn right / move forward] because [visible evidence or
> immediate navigation objective].

Passing through the bedroom:

> This appears to be a bedroom. It is not my laundry destination, but I can
> pass through it to reach the hallway.

At arrival:

> I see [actual matching evidence]. This matches the place Mary showed me
> for laundry. I will stop here.

Clothes are an assumed carried item; no manipulation is simulated. A destination
notice appears when the authored goal is approached closely. It does not replace
the demonstrator's visual verification. Evaluation coordinates and optional
route aid stay separate from model input.

## Recording and performance

The action response includes its JPEG frame, removing a second image request.
Each step uses the observation returned by Habitat instead of rendering again.
HTTP handles uploads and downloads on separate threads, while a single renderer
thread owns the Habitat context. PNG writing happens on a dedicated worker; every action retains its own PNG,
timestamp and pose. MP4 exports happen on a separate CPU worker so they do not
block the simulator's control loop. The recorded action ledger is authoritative;
the navigation replay holds observations to their wall-clock durations.

Browsers may internally produce WebM when native MP4 recording is unavailable.
That temporary upload is converted to H.264/AAC MP4 and removed after success.
WebM is not offered for download or included in sample ZIPs. If conversion fails,
the temporary source stays in `.uploads/` for recovery and is not included in the
sample ZIP. Wait for successful export before treating a sample as complete.

Saved data is independent of V1:

```text
level3_manual_collector_v2/
  sessions/<username>/<timestamp>/
    inputs.json, frames/, trajectory.jsonl, events.jsonl
    memory_images/, audio/voice_*.mp4, screen/screen_*.mp4
    navigation.mp4, manifest.json, evaluation_only.json
  deleted_sessions/
```
