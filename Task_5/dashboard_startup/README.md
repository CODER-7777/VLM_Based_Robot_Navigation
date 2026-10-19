# Individual local dashboard startup scripts

Run any launcher from any directory. It starts/reuses the dashboard's dedicated tmux session, waits for the HTTP endpoint, then opens the desktop browser automatically.

| Script | Dashboard | URL |
| --- | --- | --- |
| `start_voice_video.sh` | Current voice/video collection | http://localhost:8878/ |
| `start_original_collector.sh` | Original collector | http://localhost:8876/ |
| `start_research.sh` | Selected RxR routes and backpack models | http://127.0.0.1:8894/ |
| `start_trajectory_review.sh` | Interactive trajectory and room review | http://127.0.0.1:8890/room_tasks/review.html |
| `start_all.sh` | All four | Opens each ready dashboard |

From Task_5:

```sh
./start_task5_dashboards.sh
./dashboard_startup/start_voice_video.sh
./dashboard_startup/start_research.sh
./dashboard_startup/start_trajectory_review.sh
./dashboard_startup/start_original_collector.sh
```

Add `--no-open` to run without opening browser tabs, or `--status` to inspect availability without starting anything. Rerunning a launcher reuses its session and existing healthy services. Current collector samples are not reset. The local collector launchers use the owner's existing SSH access; contributor access through the new campus website is a separate setup in `../campus_collector/`.

The dedicated tmux socket is `task5-dashboards`. Inspect a session with:

```sh
tmux -L task5-dashboards list-sessions
tmux -L task5-dashboards attach -t task5-voice-video
```

Detach with **Ctrl-b**, then **d**. Session names are `task5-voice-video`, `task5-original-collector`, `task5-research`, and `task5-trajectory-review`. Logs are in `.runtime/`. A user service manages the tmux server so it survives chat-tool cleanup. The launchers do not configure boot/login autostart.

When a remote collector has actually stopped, its worker checks and starts only that backend, using GPU 0. A listening backend is preserved. The trajectory review requires its existing remote `/tmp/rxr_review_dashboard_20261015` installation; if the server reboot removed it, the launcher reports the missing files instead of uploading source automatically. VPN/network reachability and existing authorized SSH credentials are required for local remote-service launchers.
