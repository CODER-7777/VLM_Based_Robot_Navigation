# Recording examples — three authored household cases

Website: **https://172.26.186.222:8443**. Sign in with your existing account. Administrators now have the complete catalog; the three cases below are recording examples within it. Finish any active sample and uploads before signing out or refreshing. Existing recordings remain reviewable.

These examples use scene `2azQ1b91cZZ`. For account creation and private assignments, use the [admin dashboard](https://172.26.186.222:8443/admin) and [admin guide](campus_collector/ADMIN_GUIDE.md). Participant assignments are confidential and are not listed here.

| Episode | Request | Selected reference route |
| --- | --- | ---: |
| `house_first_L3_MULTI` | Take the snacks from the kitchen to the couch in the TV room. | 16.57 m |
| `house_first_L3_ALIAS` | Bring this blanket to the couch in the screen room. | 21.76 m |
| `house_first_L3_SIMPLE` | Take this notebook to my desk, please. | 21.34 m |

These three authored routes are below 40 m. They are independent examples, rather than a complete account assignment. Starts, initial rotations, source-path prefixes and annotated memory images are preserved from the source dataset. Task objects, handoffs and carrying are conversational context; manipulation is not simulated.

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

Detailed browser controls and recovery instructions are in [the launcher guide](campus_collector/STUDY_LAUNCHER_GUIDE.md). Use the tasks displayed in your account; private participant assignments are not part of this guide.

## Server storage

Your new samples save directly under:

```text
<data_root>/contributors/<contributor_id>/sessions/<contributor_id>/
```

The source dataset stays at `/home/guest-isl/rishabh/rxr_author_levels/house_first/step23_all/step5_8_l3/`. No human demonstrations have been fabricated or recorded by the setup process. Independent human review of the authored cases is still pending; your recordings contribute to that review.
