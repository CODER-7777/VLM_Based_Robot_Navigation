# Mesh repair beside and behind the toaster

The reference appliance is a **Black & Decker 2-Slice Toaster, resembling T2030**, as identified by the user. The installed mesh remains the freely available Cuisinart substitute from the preceding pass; this repair changes the surrounding surfaces.

## Problem and evidence

The original scan has missing faces and stretched triangles in the tiled return beside the tall cabinet. Earlier appliance deletion footprints also reach into that wall, enlarging some gaps. The raw source geometry places most of the original return at approximately X=4.375 m, with substantial local scan errors. The finished counter starts at X=4.410 m.

## Repair

A private build clips the damaged scan triangles to a bounded repair volume and removes their interior fragments. It inserts straight, photo-textured surfaces for the tiled return, a narrow adjacent backsplash section, the return's front edge, and a wooden join that closes the gap to the cabinet. The visible replacement return lies at X=4.405 m to align with the finished counter/cabinet boundary. Its bottom is Z=0.929 m and its top is Z=1.435 m. It runs from Y=-5.440 to -4.800 m. The adjacent backsplash repair is limited to X=4.405–4.565 m to preserve the existing electrical outlet.

Replacement surfaces are inserted after appliance replacement, so the old toaster's deletion footprint cannot cut holes in the new wall. Existing props and their placement remain unchanged.

## Texture and limitations

The source is the actual calibrated photograph `58348305b0f84dd8b161aaf2d5b945ef_i2_4.jpg`. An initial depth-filtered texture projection still picked up foreground pixels at the grazing viewing angle; that pass was rejected before publishing.

The final texture uses a clean stone tile sample and the real decorative diamond, rectified from the same photograph. Grout and decorative motif placement are reconstructed and approximate. This fills hidden areas without repeating the outlet or old appliance pixels. It is not a claim that the entire hidden wall texture was observed.

The repair is local. Other scan distortions outside the repaired corner may remain. The toaster's brand/control mismatch and fixed baked reflections also remain as documented in the [toaster report](../toaster_realism_upgrade/README.md).

## Server files

All paths are under `/data/robotics/toshith/rxr_author/refined/toaster_wall_repair/`:

- `test.glb`: private full scene containing the surface repair.
- `wall_patch.glb`, `wall_patch.ply`: replacement surfaces.
- `patch_spec.json`: surface bounds, deletion regions and texture method.
- `geometry_result.json`: number of removed scan faces.
- `manifest.json`: private copy of the toaster manifest.
- `wall_apply.py`, `build_private.py`: private build steps.
- `audit.json`: prop placement audit.
- `previews/`: photo-camera comparison and additional Habitat views.

Shared manifests and original builds remain unchanged. Local scripts and verification evidence are in this folder's `evidence/` directory.

## Viewing

Open http://localhost:8772/ on the development computer. The comparison at the top shows the real photo, the toaster scene before wall repair, and the repaired corner. The previous toaster dashboard stays on http://localhost:8770/ with its session preserved.

If the local tunnel has stopped, run this command in a **local terminal** and leave it open:

```sh
ssh -N -L 8772:127.0.0.1:8772 guest-isl@172.26.186.222
```

![Wall repair comparison](images/toaster_comparison.jpg)

![Additional views of the repaired corner](images/toaster_novel_views.jpg)

## Verification result

The private build removed 161 damaged scan faces and added 4 replacement surfaces. The 32-prop placement audit reports zero issues; a separate check against the bounded repaired wall planes also reports zero new crossings. The final Habitat comparison and two additional views were inspected.

Small scan defects remain outside this local patch, including the counter/cabinet edge below the repaired join and the backsplash farther along the counter. The repair does not certify the entire room mesh.
