# Level 3 manual laundry collector

This collector uses the existing Habitat environment and the laundry case
`QUCTc6BB5sX_8247`. It loads no navigation policy and runs no VILA inference.
Cached, reviewed memory descriptions are copied from the current presentation.

The demonstration assumes the person is carrying dirty school clothes and
navigating to the laundry area. Clothing is not rendered or manipulated. This
is a user-authored scenario variation, distinct from the original benchmark's
clean-clothes pickup annotation. The benchmark files remain unchanged.

## Open the collector

The server listens on loopback, port 8876. From the computer where you will use
the browser and microphone, open a terminal and leave this tunnel running:

```bash
ssh -N -L 8876:127.0.0.1:8876 guest-isl@172.26.186.222
```

Open `http://localhost:8876` in Chrome or Firefox. A localhost tunnel also gives
the browser a secure context for microphone and screen recording permissions.
If you are physically using the server's desktop, open that URL directly.

## Collect the first human sample

1. Enter an annotator ID such as `vivek_01`, and choose **New user**. Returning
   users can list and download their finished sessions. Interrupted sessions
   are preserved on disk, but partial-session resume is not implemented.
2. Review the request and the assumed current state. Mark `uniforms` as the
   relevant memory, while leaving all three memories supplied.
3. Click **Start new sample**. All subsequent movements are saved. Choose the
   Request clip type, click **Record voice**, read the request, then stop the
   voice recording. Type its corrected transcript and save the text.
4. Choose Reasoning, record your initial explanation, stop the clip, then save
   its corrected transcript. Use the templates below.
5. Click **Record screen + microphone** and choose the collector tab/window in
   the browser prompt. You can narrate the demonstration as you move. Screen
   narration is separate from the shorter reasoning clips.
6. Click the scene, then use **W** to move forward 25 cm, **A** to turn left 15°,
   and **D** to turn right 15°. Twelve D presses turn 180°. **S is disabled**.
   Buttons work as well. A blocked forward step is recorded as a collision.
7. Record short reasoning clips at landmarks, turns, or corrections. Type the
   corrected transcript and click **Save reasoning text**. You can pause
   movement while talking; this is useful supervision.
8. At the laundry area, record why the visible evidence matches the memory.
   Stop the voice clip and wait for its saved-event entry.
9. Press **Space** or **STOP & save**. This saves the final state and exports
   `navigation.mp4`. You may keep screen recording active through STOP to show
   the save operation. Then stop screen recording and wait for its upload.
   Use **Download complete sample ZIP** to save locally.

You can also download videos directly from the dashboard: **Download navigation
MP4** appears after STOP. **Download screen recording** appears once a screen
recording has uploaded. Returning users can select an older session and use the
same individual video links. The navigation MP4 shows the robot view; the screen
recording shows the dashboard with microphone narration.

To remove a completed sample, click **Delete this saved sample** below its
downloads, or choose a session under **Returning user** and click **Delete
selected sample**. Confirm the displayed sample ID. The entire sample moves to
`deleted_sessions/<annotator>/<timestamp>/` and disappears from the saved list;
its files remain recoverable. Stop and save a recording before deleting it, and
finish voice/screen uploads first. Deletion of an older sample leaves a different
active recording untouched. A matching folder must not already exist in
`deleted_sessions`, so deleted copies are never overwritten.

If you need help finding the destination, expand the optional route aid. It
uses simulator geometry to suggest the next key. Its use is logged separately.
Do not provide these oracle suggestions or evaluation coordinates to a model.

## Voice / reasoning template

**Request clip**

> Could you help the kids get their clothes ready before school starts?

**Initial reasoning clip**

> I am carrying dirty school clothes. Mary said that she usually does the
> laundry at the place shown in memory two. That is relevant to my task. The
> food-storage and exercise-room memories concern other activities. I will
> navigate to the laundry area using its remembered visual landmarks.

**Before a movement or at a junction**

> I see [what is actually visible]. This [matches / does not match] the laundry
> memory because [visible evidence]. I will [turn right / turn left / move
> forward] to [immediate navigation objective].

**Correction**

> I expected [landmark], but I see [actual landmark]. This does not match my
> target. I will turn around using right turns and return to [known location].

**Arrival**

> I see [actual evidence, such as the washing machine and cabinets]. This
> matches Mary's laundry memory. I have reached the laundry area with the
> assumed clothes, so I will stop here.

These are annotation templates, not generated model outputs. Only describe
visible evidence when it is visible. The carried clothing is an explicit
scenario assumption. No laundry operation or clothing placement is simulated.

## Saved sample structure

```text
sessions/<annotator>/<UTC timestamp>/
  inputs.json                 # request, state, supplied memories, chosen IDs
  memory_images/*.png         # copied memory views, available offline
  frames/*.png                # one lossless frame per executed action
  trajectory.jsonl            # actions, wall time, poses, collisions
  events.jsonl                # annotations and audio/screen timing
  audio/voice_*.webm|ogg|mp4   # original microphone clips
  screen/screen_*.webm|mp4     # screen recordings with microphone narration
  navigation.mp4              # 5 FPS replay with wall-clock holds
  evaluation_only.json        # original geometry; exclude from model input
  manifest.json               # recording provenance and final evaluation
```

The PNG/action ledger is authoritative. The MP4 holds each captured view until
the next action's timestamp. Very fast consecutive actions can share a video
frame; their individual PNGs and action entries are preserved. Audio timestamps
use the browser session clock, and server events use the server monotonic clock;
both are recorded rather than pretending network delay is zero.

Speech recognition is not enabled: you save raw voice and correct its transcript
manually. The browser's permission prompts are expected. If the upload fails,
the UI offers a local emergency download of the recorded media.

For a model training sample, use the instruction/current state, memory evidence,
selected observations, human reasoning labels, and executed actions. Keep poses,
reference paths, original goal coordinates, and oracle aid out of model input.
Validate human demonstrations before treating them as expert supervision.

## Restart the server, if needed

The approved renderer uses physical GPU 0 only. Do not start a second server
while the existing one is running. On the server:

```bash
cd /home/guest-isl/rishabh/bench/experiments/level3_manual_collector
CUDA_VISIBLE_DEVICES=0 OMP_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1 \
  /home/guest-isl/rishabh/bench/envs/navila/bin/python -B collector.py --port 8876
```

The initial `--prepare` command is CPU-only and only copies source data. Run it
when intentionally refreshing this collector's sample inputs, not during an
active session. No packages were installed for this collector.
