> Historical overview preserved before the 10 October mid-evaluation review. Use [the current task report](../README.md). Links below were originally relative to Task_4/.

# RxR kitchen visualization

## Latest: all kitchen objects and matched counter materials

The live presentation now includes the remaining kitchen objects, photo-matched stone, the full comparison gallery and rotatable material previews. See [the update report and local evidence](kitchen_all_objects_upgrade/README.md).

Run locally from the repository:

```bash
bash Task_4/kitchen_all_objects_upgrade/open_dashboard.sh
```

Open [the live kitchen](http://localhost:8767/) or [the complete comparison gallery](http://localhost:8767/comparisons). The earlier full route editor is preserved at [its dashboard link](http://localhost:8767/legacy-editor).

## Open the first-person dashboard whenever you need it

Run this **on your local computer**, from the repository directory:

```bash
bash Task_4/open_visualization.sh
```

Then open **http://localhost:8767/** in your browser. Keep the terminal open while viewing. Use **W/S** to move forward/backward and **A/D** to turn.

The launcher reuses an accessible dashboard tunnel; otherwise it opens one. It connects to `guest-isl@172.26.186.222`, forwarding local port `8767` to the repaired-kitchen presentation on server port `8774`. You need network access to ISL, which may require campus Wi-Fi or VPN, and your usual SSH credentials.

`localhost` means your own computer. The URL works while both the SSH tunnel and the dashboard process on ISL are running. After a laptop restart, terminal closure, or lost connection, run the launcher again. Closing the browser alone does not stop the tunnel. A server reboot can also stop the dashboard; reopening the tunnel does not restart it.

Equivalent manual command:

```bash
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 \
  -L 127.0.0.1:8767:127.0.0.1:8774 guest-isl@172.26.186.222
```

If port 8767 is occupied by another application:

```bash
VIS_LOCAL_PORT=18767 bash Task_4/open_visualization.sh
```

Then open **http://localhost:18767/**.

## Saved local files

- `scenes/v15/2azQ1b91cZZ.glb`: saved kitchen scene, about 384 MiB. Open Blender, choose **File → Import → glTF 2.0**, select this file, and use Material Preview to see textures. No SSH or running dashboard is needed for this copy.
- `previews/`: photo comparisons and alternate-angle images; open directly in any image viewer.
- `dashboard/`: copied dashboard source and original server launcher for reference. `run.sh` uses server paths and an older default scene; use the local tunnel launcher above to access the running v15 dashboard.
- `visualization_tools/`: copied rendering helpers for the Habitat/Blender environment on ISL. These retain their original dependencies and server paths.
- `metadata/`: copied v15 manifest and counter/object descriptions. Absolute paths refer to ISL; this folder is a reference snapshot rather than a complete local Habitat installation.

The dashboard now loads the complete repaired scene from `refined/toaster_selected/test.glb`, retaining the other repaired objects and wall repair while installing the selected AtTheSpeedOf toaster. It uses its private editor on server port **8776**, presented through port **8774**. Earlier editor sessions remain preserved. The copied v15 files are an older snapshot; later server repairs do not update them automatically.

- [All object comparisons, including vase/jug, caddy and frogs](http://localhost:8767/comparisons)
- [Selected toaster with original metallic PBR materials](http://localhost:8767/product-viewer)
- [Selected model, source attribution and fit details](toaster_selected_model/README.md)
- [Separate physics and Gaussian RGB-D prototype, results and connection instructions](split_render_pipeline/README.md). This experimental view uses local port 8778 with its own tunnel forwarding; it still has visible reconstruction artifacts and poor unseen-angle results.
- [Latest toaster-corner distortion repair](gaussian_corner_repair/README.md): dense geometry, sharper RGB-D, Reference-view button and [Gaussian before/after gallery](http://localhost:8778/corner-comparisons). Run `bash Task_4/gaussian_corner_repair/open_dashboard.sh` locally to reconnect both dashboards.
- [Detailed dataset and kitchen repair guide](kitchen_dataset_repair_guide/README.md)

## If the page stops opening

1. Confirm campus/VPN connectivity and test `ssh guest-isl@172.26.186.222`.
2. Run the local launcher again and check its terminal output.
3. If SSH connects but the page still fails, check the dashboard **on ISL**:

   ```bash
   ss -ltn | grep -E ':8776|:8774'
   ```

   No listener means the server dashboard needs restarting. Its environment is `/home/guest-isl/rishabh/VLA-paper/.navida-env`, and its source is `/data/robotics/toshith/rxr_author/author_pov_route.py`. Check for an existing process before restarting to avoid duplicate sessions. The local launcher only manages the connection.

## Public resources

- [Matterport3D house browser](https://aspis.cmpt.sfu.ca/scene-toolkit/scans/matterport3d/houses), linked from the [official Matterport3D project](https://niessner.github.io/Matterport/).
- [Official RxR first-person visualization instructions](https://github.com/google-research-datasets/RxR/tree/main/visualizations).

These public resources show the original dataset; your repaired kitchen is in the ISL dashboard and the saved GLB.
