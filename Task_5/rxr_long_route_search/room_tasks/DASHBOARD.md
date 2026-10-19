# Interactive trajectory review

Open **http://127.0.0.1:8890/room_tasks/review.html**.

The dashboard includes all **28 original validation routes ≥40 m**, your **12 selected school-bag cases**, both stronger Nora candidates, all **25 broadly compatible Nora sources**, and the **8 toiletries source routes**. The trajectory selector exposes all **123 authored variants** under their original source. Variants are not counted as new original RxR routes.

Click the first-person view: **W/S** moves forward/backward on the navmesh, **A/D** turns, **Q/E** strafes, mouse dragging looks around, and the up/down arrows change pitch. Start, goal, pickup, candidate Nora-room and placed-object buttons jump to inspection views. The route slider and preview button jump between guide cameras; they do not execute navigation. The map includes floor selection, original/selected paths, pickup, goal and current camera position. Four original source-goal photos remain available for every source route; secondary authored goals are labelled as requiring validation.

## Task_4 analysis and implementation choice

Read `Task_4/README.md`, `dashboard_restore/README.md`, `kitchen_objects_pbr_dashboard/README.md`, the product replacement `web/home-tour.js`, the home-tour server wrapper and launcher, and the existing author dashboard. Task_4 combines object selection, in-room inspection, W/S movement, A/D turning, mouse look and a separate Habitat navigation service. Its product tour renders a full scene directly in Three.js.

This review follows those interactions while rendering the actual scene with Habitat on demand and returning JPEG camera frames through a localhost SSH proxy. This supports all 12 existing scenes without downloading each large GLB into the browser. It uses a separate simulator on physical GPU 0, one loaded scene at a time. Task_4 files, existing collector sessions and original scene files were not modified. This is a mesh view; it is not a Gaussian-splat reconstruction.

## Files and operation

- `review.html`, `dashboard.js`, `dashboard.css`: interactive interface.
- `review_gallery.html`: retained image/document gallery.
- `build_dashboard_catalog.py`: joins original routes, user selections, room evidence and authored variants into `dashboard_catalog.json`.
- `interactive_scene_service.py`: separate render worker, all OpenGL operations on one thread; no policy, data collection or robot control.
- `dashboard_server.py`: local static files and narrowly scoped review API relay.
- `start_live_review.py`: starts/retains the localhost server and SSH tunnel in detached processes. It only replaces commands identified as belonging to this review.
- `verify_interactive_dashboard.py`: real-browser checks, with evidence in `dashboard_browser_verification.json` and `dashboard_desktop.png`.

Local port **8890** serves the review; local **8892** forwards to the separate review service on server port **8894**. The existing remote service is `/tmp/rxr_review_dashboard_20261015` on `guest-isl@172.26.186.222`, using the `navila` Python environment. `/tmp` is temporary; the local scripts, catalog and evidence are retained here.

To reconnect the existing remote service and keep the local dashboard live:

```bash
python3 -B start_live_review.py
```

The current renderer has one shared inspection camera, so use a single active walking tab. Maps and photo panels work without the remote render service. Object props currently exist in scene 04 (two school bags) and scene 06 (conditioner tube and boxed eye cream). Other scene candidates are not presented as having already placed toiletries. Room identities and routines are authored, and inspecting Nora's room is distinct from obeying its task restriction. Approximate nearest-panorama room labels are not a continuous forbidden-room audit.

## Verification

The browser check covers all route/variant counts and filters, live camera images, keyboard turning, navmesh movement, route-step jumps, pickup and Nora inspection, switching to another scene, both school-bag placements, all four source-goal photos, and the mobile layout. It does not establish autonomous task completion, grasping, carrying, physical stability or dataset-wide navigation success.
