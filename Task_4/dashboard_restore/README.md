# Restored full repaired-scene dashboard

Open **http://localhost:8767/**.

The current dashboard loads `/data/robotics/toshith/rxr_author/refined/toaster_selected/test.glb` through its private editor on ISL port 8776. It retains the complete repaired kitchen and local wall repair and replaces the earlier substitute toaster with the user's selected AtTheSpeedOf asset. The private audit reports 32 props and zero placement issues.

The first-person scene, movement controls and object controls are the main view. [The comparison gallery](http://localhost:8767/comparisons) contains the latest toaster first and the earlier vase/jug, caddy, frogs, knife blocks and counter objects below. [The PBR viewer](http://localhost:8767/product-viewer) shows the actual selected asset with its metallic maps.

A presentation proxy on ISL port 8774 forwards requests to 8776, provides the gallery, and collapses the large comparison banner in the editor HTML. Earlier simulator sessions and their route states remain preserved. The separate [Gaussian RGB-D prototype](../split_render_pipeline/README.md) runs on 8778; its visible artifacts and poor held-out views are documented there.

From the local repository, reconnect with:

```sh
bash Task_4/open_visualization.sh
```

Or, in a local terminal:

```sh
ssh -N -L 127.0.0.1:8767:127.0.0.1:8774 guest-isl@172.26.186.222
```

The launcher and `Task_4/README.md` use this presentation proxy. `verification.json` is the historical pre-toaster restoration check; the current selected-scene check is `../toaster_selected_model/evidence/dashboard_verification.json`.
