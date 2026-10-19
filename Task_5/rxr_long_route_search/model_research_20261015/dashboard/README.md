# RxR Route & Object Studio

> Source publication: images, recordings, generated catalogs, dataset assets and runtime reports referenced below stay local. See the Task 5 reproducibility guide for required inputs.

Live local URL: **http://127.0.0.1:8894/**

The portable dashboard contains 28 reviewed validation routes, the user's original 12 selected indices, 19 curated school-backpack/model-reference options, and the two revision 03 environment 04 placement candidates. Routes are drawn from their actual MP3D connectivity poses; their displayed lengths are annotated guide-route lengths, not shortest navigation distances.

Tabs:

- **Trajectories:** filter the original 12 or all 28; inspect the four original goal headings, guide instructions, actual viewpoint graph, and elevation at each route point.
- **Backpack models:** public creator/seller previews, exact source links, download/account/price/license status, and comparison for up to three models. Three local GLBs can be inspected interactively: two newly downloaded CC-BY scans and the prior canvas baseline.
- **Environment 04:** brown and pink seat candidates with front, side, cushion-level and back views. Record your own assessment.

Selections and notes persist in this browser's local storage. **Export review** downloads a JSON file with selected routes/models, notes and placement assessments. It does not modify source annotations or activate a simulation trial.

## Restart

From the Task_5 folder:

```sh
python rxr_long_route_search/model_research_20261015/dashboard/serve_dashboard.py --port 8894
```

Open the HTTP URL above. The server serves only `dist/` and binds to loopback. Core galleries and maps work locally; author iframe viewers require internet. The local GLB viewer uses a pinned vendored Google model-viewer 4.1.0 distribution. Meshes can also be downloaded directly from the model detail dialog.

## Research evidence

See `../RESEARCH_REPORT.md`, `../downloads.json` and `../MODEL_OPTIONS.csv`. The two new GLBs came from the official AllenAI Objaverse distribution. The public search returned 54 model records; this was a targeted search across multiple sources rather than an exhaustive web crawl. The archived local scan textures are 1024×1024. 4K claims on other cards are marked as advertised until actual files can be obtained and inspected.

License and attribution remain with the original authors. Several marketplace items require checkout or carry no-AI limitations; their previews are comparison references, not approved research assets. No purchases or protected-viewer mesh extraction were made.
