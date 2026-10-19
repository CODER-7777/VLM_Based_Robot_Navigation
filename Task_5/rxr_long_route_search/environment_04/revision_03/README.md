# Environment 04 · revision 03

This candidate replaces the prior blue bag and the floating revision 02 poses. Start with `replacement_preview.jpg`; the four original RxR goal cameras and four full-resolution near-seat views are included.

Two instances of the photo-textured 3D backpack lean against the brown seat back and pink chair back. Their lower fabric follows the exact cushion triangles extracted from the Matterport scene. The measured base rims sit 0.5–1.0 mm above those triangles; each mesh was shifted off the armrest and its uneven scanned hem compressed. A subtle alpha contact patch conforms to the same support mesh.

This is a geometric placement in Habitat, not a physics-settled drop. Inspect the rendered seat-level images before approving the localizations. Original scene files and RxR annotations remain unchanged.

- `prepare_contact_fit.py`, `add_contact_shadows.py`: create the individual fitted meshes and contact patches.
- `place_backpacks.py`: render the isolated Habitat scene.
- `placement_request.json`: transforms and asset paths.
- `contact_checks.json`, `shadow_checks.json`, `verification.json`: measurement and render checks.
- `placed/`: rendered views, depth maps, object transforms, navigation results.
- `assets/`: 40 cm photo-textured bag variants and exact chair triangles. Attribution is in `model_sources.json`.

RxR original guide length: 47.31 m. This describes the annotated route and is not the shortest navmesh path.
