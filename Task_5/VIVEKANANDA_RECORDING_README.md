# Vivekananda — record the three authored cases

Website: **https://172.26.186.222:8443**. Sign in with your existing **vivekananda** account. Finish any old active sample/uploads before signing out or refreshing. The current assignment replaces your ten-episode collection menu with these three cases; old recordings remain reviewable.

Your environment is **Iyer–Malhotra household · three recording cases** (`2azQ1b91cZZ`). Raj and Priyansh retain their original two tasks; these three cases are assigned only to you.

| Episode | Request | Selected reference route |
| --- | --- | ---: |
| `house_first_L3_MULTI` | Take the snacks from the kitchen to the couch in the TV room. | 16.57 m |
| `house_first_L3_ALIAS` | Bring this blanket to the couch in the screen room. | 21.76 m |
| `house_first_L3_SIMPLE` | Take this notebook to my desk, please. | 21.34 m |

These three authored routes are below 40 m. They are your separate three-case assignment, not Raj/Priyansh's two longer routes. Starts, initial rotations, source-path prefixes and annotated memory images are preserved from the source dataset. Task objects, handoffs and carrying are conversational context; manipulation is not simulated.

## For each case

1. Select the episode and read its speaker, request, current state and annotated memory images. Check the memory or memories you actually use.
2. Click **Create new sample** while still at the starting point.
3. Click **Record screen + microphone**. Choose the dashboard tab/window in Chrome, click **Share**, and allow the microphone. After those prompts close, click **Enter full screen & start recording** in the dashboard. This restores full screen before the video begins. Begin moving after recording is running.
4. Use **W / A / D** or the on-screen movement buttons. Explain the task/memory at the start, your decisions at junctions or corrections, and visible evidence at arrival.
5. For **L3_MULTI**, navigate to the kitchen first and then the TV-room couch in the **same sample**. Do not press STOP at the kitchen. The site tracks the intermediate authored navigation stop and shows **Intermediate navigation stops: 1 / 1** when you pass within 0.65 m navigable distance of it. If that counter remains 0, the authored intermediate waypoint has not been registered. The optional route aid targets the current required stop; using it is logged. Check the memories and your observations before using that aid.
6. For the blanket and notebook cases there is one final destination. Follow the speaker and household memory evidence rather than assuming identical objects belong to the same person.
7. At the final destination, explain your observation and click **STOP & save**. Wait for uploads and MP4 preparation.
8. Enter one corrected reasoning transcript for the whole sample and click **Save reasoning text**. Mention any mistakes, help or route-aid use honestly.
9. Play the saved screen recording to check video and microphone audio. The navigation replay itself is silent. A separate `audio/screen_000.m4a` is now extracted automatically and included in the sample ZIP. Existing standalone `voice_*.mp4` clips are preserved.
10. Repeat with a new sample for the next case. Do not close the browser or sign out with pending uploads.

Detailed browser controls, certificate installation and recovery instructions are in [the participant guide](campus_collector/PARTICIPANT_GUIDE.md). Its two-task assignment applies to Raj/Priyansh; use the three-case table above for your own recordings.

## Server storage

Your new samples save directly under:

```text
/home/guest-isl/rishabh/bench/experiments/level3_manual_collector_v2/data_collecting/data/contributors/vivekananda/sessions/vivekananda/
```

The source dataset stays at `/home/guest-isl/rishabh/rxr_author_levels/house_first/step23_all/step5_8_l3/`. No human demonstrations have been fabricated or recorded by the setup process. Independent human review of the authored cases is still pending; your recordings contribute to that review.
