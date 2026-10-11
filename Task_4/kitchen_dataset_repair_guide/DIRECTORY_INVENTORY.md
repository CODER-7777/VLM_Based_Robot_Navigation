# Directory inventory

Observed on 7 October 2026. This complements the explanations in [README.md](README.md).

This is an inventory of the local Task_4 snapshot and immediate entries in the inspected server roots. It is not a recursive listing of every image, cached model, or dataset file. Historical names do not imply that those files are part of the current build. No meaning is inferred for uninspected experiment scripts beyond their observed names.

## Local Task_4 files

Paths below are relative to `Task_4/`. The guide folder itself is summarized separately.

```text
.gitignore (109 bytes)
README.md (3,578 bytes)
dashboard/author_pov_route.py (50,910 bytes)
dashboard/run.sh (2,152 bytes)
metadata/counters_spec.json (2,650 bytes)
metadata/download_inventory.json (2,052 bytes)
metadata/episodes.tsv (28,183 bytes)
metadata/kitchen_items.txt (1,427 bytes)
metadata/manifest_v15.json (3,886 bytes)
open_visualization.sh (1,484 bytes)
previews/agentA_final1.jpg (230,634 bytes)
previews/agentA_final2.jpg (252,006 bytes)
previews/agentA_final3.jpg (156,411 bytes)
previews/agentA_inv1.jpg (199,901 bytes)
previews/agentA_inv2.jpg (190,953 bytes)
previews/agentA_novel.jpg (202,773 bytes)
previews/agentA_novel2.jpg (202,508 bytes)
previews/agentA_novel3.jpg (298,435 bytes)
scenes/v15/2azQ1b91cZZ.glb (402,235,188 bytes)
visualization_tools/glb_preview.py (1,831 bytes)
visualization_tools/k3d.sh (549 bytes)
visualization_tools/look.py (1,323 bytes)
visualization_tools/mp3d_cams.py (2,725 bytes)
visualization_tools/multiview.py (2,348 bytes)
visualization_tools/product_preview.py (5,151 bytes)
```

## New documentation files

```text
README.md
evidence/README.md
evidence/audit.json
evidence/changes.json
evidence/dashboard_forwarding.json
evidence/object_fit_paths.json
evidence/repair_report.md
evidence/verification.json
images/agentA_resume_compare1.jpg
images/agentA_resume_compare2.jpg
images/agentA_resume_compare3.jpg
images/agentA_resume_novel.jpg
DIRECTORY_INVENTORY.md
```

## Immediate entries in inspected ISL directories

The following output preserves observed file/directory names and symlink targets. `DIR` means directory; `FILE` means file. Many working helper scripts are historical; consult the main guide for the verified workflow.

```text
DIRECTORY /data/robotics/toshith/rxr_author
FILE author_pov_route.py
FILE author_pov_route.py.bak_static
FILE episodes.tsv
FILE orig_004_1.jpg
DIR out
DIR out_interactive
DIR out_kitchen_v11
DIR out_kitchen_v12
DIR out_kitchen_v13
DIR out_kitchen_v15
DIR out_kitchen_v9
DIR out_refined
FILE parts_rt.py
FILE parts_test.py
FILE patch_interactive.py
FILE patch_runsh.py
DIR refined
FILE refined_004_1.jpg
FILE run.sh
FILE run.sh.bak
FILE run.sh.bak_v6
FILE run_004_1.log
FILE run_004_1_interactive.log
FILE run_004_1_refined.log
FILE run_006_1.log
FILE run_006_2.log
FILE run_kitchen_v10.log
FILE run_kitchen_v11.log
FILE run_kitchen_v9.log
DIR rxr_traces
DIR scenes
DIR scenes_interactive
DIR scenes_interactive_v7
DIR scenes_interactive_v8
DIR scenes_v10
DIR scenes_v10base
DIR scenes_v11
DIR scenes_v12
DIR scenes_v13
DIR scenes_v14
DIR scenes_v15
DIR scenes_v7
DIR scenes_v8
DIR scenes_v9

DIRECTORY /data/robotics/toshith/rxr_author/refined
FILE 2azQ1b91cZZ.glb
FILE 2azQ1b91cZZ_v1_unpatched.glb
FILE 2azQ1b91cZZ_v5.glb
FILE add_hulls.py
DIR agentA
DIR agentA_resume
FILE audit_drops.json
FILE audit_points.py
FILE audit_prims.py
DIR audit_v6
DIR audit_v7
DIR audit_v8
FILE bake_finish.py
FILE bake_finish_a.py
FILE bake_finish_b.py
FILE before_after.jpg
FILE blender_overlay.py
FILE blmat.py
FILE blockers.py
FILE blpath.py
FILE chairtex.py
FILE chairuv.py
FILE closed_gal.jpg
FILE closed_gallery.py
FILE compare_13.jpg
FILE compare_views.py
FILE composite_overlay.py
FILE convert.log
FILE convert10.log
FILE convert10base.log
FILE convert11.log
FILE convert12.log
FILE convert13.log
FILE convert14.log
FILE convert15.log
FILE convert2.log
FILE convert3.log
FILE convert4.log
FILE convert5.log
FILE convert6.log
FILE convert7.log
FILE convert8.log
FILE convert9.log
FILE copy_obj.py
FILE counter_edge.py
FILE counter_regions.py
FILE counter_slab.py
FILE counters_build.py
FILE counters_spec.json
FILE dupes.py
FILE export_parts.log
FILE export_parts.py
FILE export_parts_v7.log
FILE export_parts_v8.log
FILE findcab.py
FILE finish_range.json
FILE frames.py
FILE gal1.jpg
FILE gal2.jpg
FILE gal_v7_fixed.jpg
FILE gal_v8.jpg
FILE ghost.jpg
FILE ghost_diag.py
FILE ghost_extract.py
FILE ghost_fix.py
FILE ghost_test.py
FILE glb_preview.py
FILE itemsheet_a.py
FILE k3d.sh
DIR kitchen
FILE kitchen_apply.py
FILE kitchen_bboxes.json
FILE kitchen_bboxes.py
FILE kitchen_obj.py
FILE kitchen_obj_next.py
FILE kitchen_review.py
FILE kitchen_v8.jpg
FILE kitchen_views.py
FILE lathe_a.py
FILE lathe_fixture.py
FILE lathe_fixture_b.py
FILE lathe_obj.py
FILE leafinfo.py
FILE leg13_11.json
FILE legprobe.py
FILE limits.py
FILE look.py
FILE loops_0.jpg
FILE loops_1.jpg
FILE loops_2.jpg
FILE loops_json.py
FILE loopview.py
FILE mask_check.py
FILE mask_check2.py
FILE matchsize.py
FILE matinfo.py
FILE mp3d_cams.py
FILE multiview.py
FILE mv_obj.py
FILE obj_compare.py
FILE obj_place_a.py
FILE opacity.py
FILE open_gal.jpg
FILE p13.json
FILE param_fixture.py
FILE parts_rt.py
FILE parts_test.jpg
FILE parts_test.py
FILE parts_test_full.jpg
DIR parts_v6
DIR parts_v7
DIR parts_v8
FILE patches_0.jpg
FILE patches_1.jpg
FILE patches_2.jpg
FILE patches_3.jpg
FILE patchview.py
FILE photo_audit.py
FILE place_fit.py
FILE placecheck.py
FILE placecheck2.py
FILE planes.py
FILE planes_json.py
FILE prep_usd.py
FILE prim_gallery.py
FILE prim_gallery_ba.py
FILE primitives.py
FILE probe.py
FILE product_export.py
FILE product_fit.py
FILE product_place.py
FILE product_prep.py
FILE product_preview.py
FILE profile_obj.py
FILE proxy_a.py
FILE range_place.py
FILE realism_audit.py
FILE render_depths.py
FILE render_depths_near.py
FILE rxr_door_words.json
FILE rxr_words.py
FILE sink_basin.py
FILE sink_v2.py
FILE slab_synth.py
FILE slab_view.py
FILE sweep.py
FILE sweep12.log
FILE sweep13.log
FILE sweep14.log
FILE sweep15.log
FILE sweep_interactive.json
FILE sweep_v10.json
FILE sweep_v11.json
FILE sweep_v12.json
FILE sweep_v13.json
FILE sweep_v14.json
FILE sweep_v15.json
FILE sweep_v3.json
FILE sweep_v4.json
FILE sweep_v5.json
FILE sweep_v6.json
FILE sweep_v7.json
FILE sweep_v7i.json
FILE sweep_v8.json
FILE sweep_v8i.json
FILE sweep_v9.json
FILE targets.py
DIR test_parts
FILE texfix_spec.json
FILE texture_project.py
FILE to_world.py
FILE typeless.py
DIR usd
FILE usd2glb.py
DIR usd_pose0
DIR usd_v7
DIR usd_v7_pose0
DIR usd_v8
DIR usd_v8_pose0
DIR v10
DIR v10base
DIR v11
DIR v12
DIR v13
DIR v14
DIR v15
DIR v7
DIR v8
DIR v9
FILE vc_cmp.jpg
FILE vc_v7.jpg
FILE vc_v8.jpg
FILE walk.py
FILE walk_1063.jpg
FILE walk_13.jpg
FILE walk_13_v2.jpg
FILE walk_13_v5.jpg
FILE walk_13_v6.jpg
FILE walk_13_v7.jpg
FILE walk_13_v8.jpg
FILE walk_217.jpg
FILE walk_217_v4.jpg
FILE walk_517.jpg
FILE wall_loops.json
FILE wall_planes.json
FILE whichcol.py
FILE whichprim.py

DIRECTORY /data/robotics/toshith/rxr_author/refined/kitchen
FILE all_items.txt
FILE batch_a.log
FILE batch_all.log
FILE batch_b.log
FILE cmp_faucet.jpg
FILE counters.json
FILE counters_build.json
FILE counters_outline.png
FILE counters_spec.json
DIR depth_v10
DIR depth_v12
DIR depth_v8
FILE faucet_main.log
DIR fixtures
FILE grid_1113418419f84a5c80586634f7611f14_i2_4.jpg
FILE grid_1eae5d4a0c0146c2b884d6b96d9b0e16_i2_3.jpg
FILE grid_58348305b0f84dd8b161aaf2d5b945ef_i2_4.jpg
FILE grid_b8a09dcf771a45df8501fa1f19abd2c5_i2_4.jpg
FILE grid_d70e05c20c15468eb93117d496285f82_i1_3.jpg
FILE grid_d70e05c20c15468eb93117d496285f82_i2_0.jpg
FILE grid_e22e764c60c44da28c2ba3e5c93fd44f_i2_4.jpg
FILE grid_f7a060bfa1164b5e9c5cca04284f6d6b_i2_3.jpg
FILE grid_f7a060bfa1164b5e9c5cca04284f6d6b_i2_4.jpg
FILE grid_f7a060bfa1164b5e9c5cca04284f6d6b_i2_5.jpg
FILE grid_side.jpg
FILE hood_views.jpg
FILE i2_0.jpg
FILE i2_1.jpg
FILE i2_2.jpg
FILE items_hood.txt
FILE kitchen_items.txt
FILE kitchen_items2.txt
FILE log_air_gap.txt
FILE log_coffee_machine2.txt
FILE log_hot_tap.txt
FILE log_soap_dish.txt
FILE make_manifest.py
FILE make_manifest_v10.py
FILE manifest.json
FILE manifest_base.json
FILE manifest_v10.json
FILE manifest_v11.json
FILE manifest_v12.json
FILE manifest_v13.json
FILE manifest_v14.json
FILE manifest_v15.json
FILE mv.log
DIR objects
FILE pool_taps.json
FILE pool_taps2.json
FILE pool_text_dispenser.json
FILE pool_text_hood.json
FILE pool_text_tap.json
DIR products
FILE rank_all.log
FILE rank_all2.log
FILE refit.log
FILE refit_items.txt
FILE review10_photos_0.jpg
FILE review10_photos_1.jpg
FILE review10_photos_2.jpg
FILE review10_robot.jpg
FILE review11_photos_0.jpg
FILE review11_photos_1.jpg
FILE review11_photos_2.jpg
FILE review11_robot.jpg
FILE review12_photos_0.jpg
FILE review12_photos_1.jpg
FILE review12_photos_2.jpg
FILE review12_robot.jpg
FILE review13_photos_0.jpg
FILE review13_photos_1.jpg
FILE review13_photos_2.jpg
FILE review13_robot.jpg
FILE review13b_photos_0.jpg
FILE review13b_photos_1.jpg
FILE review13b_photos_2.jpg
FILE review13b_robot.jpg
FILE review13c_photos_0.jpg
FILE review13c_photos_1.jpg
FILE review13c_photos_2.jpg
FILE review13c_robot.jpg
FILE review13d_photos_0.jpg
FILE review13d_photos_1.jpg
FILE review13d_photos_2.jpg
FILE review13d_robot.jpg
FILE review14a_photos_0.jpg
FILE review14a_photos_1.jpg
FILE review14a_photos_2.jpg
FILE review14a_robot.jpg
FILE review14b_photos_0.jpg
FILE review14b_photos_1.jpg
FILE review14b_photos_2.jpg
FILE review14b_robot.jpg
FILE review14c_photos_0.jpg
FILE review14c_photos_1.jpg
FILE review14c_photos_2.jpg
FILE review14c_robot.jpg
FILE review15_photos_0.jpg
FILE review15_photos_1.jpg
FILE review15_photos_2.jpg
FILE review15_robot.jpg
FILE review_photos_0.jpg
FILE review_photos_1.jpg
FILE review_photos_2.jpg
FILE review_robot.jpg
FILE run_batch.sh
DIR texpatch
FILE textsearch.json
FILE textsearch.log

DIRECTORY /data/robotics/toshith/rxr_author/refined/agentA_resume
FILE audit.json
DIR backups
FILE bake_finish_resume.py
FILE blue_jug_v2_bake.log
FILE build.log
FILE build_private.py
FILE build_verified.log
FILE caddy_v2_bake.log
FILE canister_l_v2_bake.log
FILE canister_r_v2_bake.log
FILE changes.json
DIR dashboard
DIR depth
FILE depth.log
FILE frogs_v2_bake.log
FILE grinder_v2_bake.log
FILE kitchen_apply.py
FILE knife_block_round_v2_bake.log
FILE knife_block_v2_bake.log
FILE manifest.json
FILE novel.log
FILE object_fit_paths.json
FILE paper_towel_v2_bake.log
FILE phone_v2_bake.log
FILE photopaint.log
FILE photopaint_final.log
FILE preview.log
DIR previews
FILE range_kettle_v2_bake.log
FILE report.md
FILE resume_kitchen_audit.py
FILE resume_kitchen_bake.py
FILE resume_kitchen_depth.py
FILE resume_kitchen_details.py
FILE resume_kitchen_finalize.py
FILE resume_kitchen_handoff.py
FILE resume_kitchen_objects.py
FILE resume_kitchen_photopaint.py
FILE resume_kitchen_preview.py
FILE resume_kitchen_select.py
FILE resume_kitchen_texture_fix.py
FILE resume_kitchen_validate_paths.py
FILE soap_bottle_v2_bake.log
FILE test.glb
FILE texture_fix.log
FILE toaster_v2_bake.log
FILE verification.json

DIRECTORY /data/robotics/toshith/rxr_author/refined/agentA_resume/dashboard
FILE frame_verified.jpg
FILE launch.json
DIR output
FILE pid
DIR scenes
FILE serve_repaired.py
FILE ui.log
```

## Exact installed source-data locations

```text
/home/guest-isl/rishabh/NAVIDA/data/RxR_VLNCE_v0/val_unseen/val_unseen_guide.json.gz
/home/guest-isl/rishabh/custom/habitat_building_isaac_repaired/source/photos/2azQ1b91cZZ/undistorted_color_images/
/home/guest-isl/rishabh/custom/habitat_building_isaac_repaired/source/photos/2azQ1b91cZZ/undistorted_depth_images/
/home/guest-isl/rishabh/custom/habitat_building_isaac_repaired/source/photos/2azQ1b91cZZ/matterport_skybox_images/
/home/guest-isl/rishabh/custom/habitat_building_isaac_repaired/source/photos/2azQ1b91cZZ/undistorted_camera_parameters/2azQ1b91cZZ.conf
```

## Selected repair objects

These selected paths came from direct inspection of the fit records. `world_mesh` is the measurement geometry; `glb` is the selected render asset.

| Object | Height (m) | Selected GLB basename | World mesh basename |
|---|---:|---|---|
| `toaster_v2` | 0.2000 | `world_resume_final.glb` | `world_resume.ply` |
| `canister_l_v2` | 0.2352 | `world_resume_final.glb` | `world.ply` |
| `canister_r_v2` | 0.2352 | `world_resume_final.glb` | `world.ply` |
| `soap_bottle_v2` | 0.1960 | `world_resume_photo.glb` | `world.ply` |
| `soap_dish_p_v2` | 0.0300 | `world_baked.glb` | `world.ply` |
| `bottles_v20` | 0.1386 | `world_resume_photo.glb` | `world.ply` |
| `bottles_v21` | 0.1386 | `world_resume_photo.glb` | `world.ply` |
| `bottles_v22` | 0.1386 | `world_resume_photo.glb` | `world.ply` |
| `bottles_v23` | 0.1386 | `world_resume_photo.glb` | `world.ply` |
| `knife_block_round_v2` | 0.3253 | `world_resume_final.glb` | `world.ply` |
| `knife_block_v2` | 0.3008 | `world_resume_photo.glb` | `world.ply` |
| `range_kettle_v2` | 0.2400 | `world_resume_final.glb` | `world.ply` |
| `phone_v2` | 0.0900 | `world_resume_photo.glb` | `world.ply` |
| `grinder_v2` | 0.2245 | `world_resume_photo.glb` | `world.ply` |
| `blue_jug_v2` | 0.1050 | `world_resume_baked.glb` | `world.ply` |
| `paper_towel_v2` | 0.3320 | `world_resume_final.glb` | `world.ply` |
| `caddy_v2` | 0.2400 | `world_resume_photo.glb` | `world_resume.ply` |
| `frogs_v2` | 0.3290 | `world_resume_final.glb` | `world_resume.ply` |

Full ISL fit paths: [evidence/object_fit_paths.json](evidence/object_fit_paths.json).
