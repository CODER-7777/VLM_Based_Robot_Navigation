# Source modules and experiment interfaces

## Task 1 — Go2 / Genesis

[run_go2.py](../../Task_1_Simulator_Evaluation/run_go2.py): visual office/floor/robot construction; joint remapping; 45-D observation; scaled position-target inference; stand/walk modes. Dependencies: Genesis, PyTorch, NumPy, CUDA/display, compatible policy and office assets.

## Task 2 — GQFT source repository

| Module in `Task_2/gqft_algorithm_sharing_vivekananda/` | Interface / responsibility |
| --- | --- |
| `step2/models/gqft.py` | Mean/max or attention/max CNN pooling, causal Transformer, displacement and optional yaw, multi-term loss |
| `step2/checkpoint.py` | Detect architecture from config/state keys; reject contradictions; strict state loading |
| `step2/episode_contract.py` | Preserve normalized flow; validate camera/pitch/anchor; ground-axis conversion |
| `step2/dataset.py` | Cached-flow windows, displacement/yaw/pixel labels, explicit sequence-floor/fixed-rig mode |
| `step2/train_gqft.py`, `evaluate_gqft.py`, `infer_gqft.py` | Explicit variants/protocols, validation history study, inference export |
| `tools/verify_cpu_contracts.py` | Strict load/output equivalence, flow masking, pitch/axis, config rejection, optional dataset oracle/backward checks |
| `tools/analyze_failure_conditions.py`, `failure_analysis.py` | Matched validation errors, motion families, regional-flow probe |
| `tools/audit_label_geometry.py`, `plot_failure_evidence.py` | Exact-motion projection oracle and diagnostic figures |
| `maintenance/prepare_controlled_runs.py` | Dry-run paired-supervision plan; execution gated separately |

Dependencies: existing PyTorch environment plus `requirements-analysis.txt`; cached flow/data and matching checkpoints are external runtime inputs. Preserved baseline/historical source snapshots support equivalence tests. `AGENTS.md` records server experiment boundaries. GQFT source has its own Git history.

## Task 3 — SvanM2 source and parent analysis tools

| Source | Responsibility |
| --- | --- |
| `xterra_mjlab/svanm2_moe_stair_sim/checkpoint_policy.py` | Direct student/actor checkpoint reconstruction, update metadata, explicit CPU/CUDA device |
| `.../controller.py`, `run_interactive_sim.py` | Observation history, target mapping/clamp, coupled PD, policy selection/device/timing |
| `xterra_mjlab/scripts/jitter_rewards.py`, `target_rate_reward.py` | Target second difference, clamp pressure, elapsed-time rate excess, reset masking |
| `.../train_other.py`, `m2_algorithm_env.py` | Explicit reward/target/swing profiles, reward-rate telemetry, saved training configuration |
| `xterra_mjlab/.../svanm2/env_cfgs.py` | Task action bounds and reward defaults |
| [Analysis modules](../../Task_3/tools/README.md) | Passive recording, equal-contract comparisons, MoE probes, contact/solver interventions, plots |

Dependencies: source repository's `pyproject.toml` and existing environment; CPU tests additionally use shipped local robot/checkpoint/export assets. Newest91000 weights and raw recording sessions remain local. The parent repository records a submodule revision for the source checkout.

## Task 4 — Repair, physics, and rendering tools

| Folder | Source families |
| --- | --- |
| `kitchen_all_objects_upgrade/evidence/` | Photo/mask fitting, object/phone/jug preparation, scan assembly, counter/wall atlases, surface sampling, final validation, dashboard |
| `toaster_selected_model/evidence/`, `toaster_realism_upgrade/evidence/` | Licensed-model fit/assembly, PBR preservation, Blender appearance bake, previews |
| `toaster_wall_mesh_repair/evidence/` | Bounded clipping, planar patch/texture construction, private scene build |
| `split_render_pipeline/evidence/` | Proxy/NavMesh build, calibrated data preparation, PBR teachers, Gaussian training/cleanup/evaluation, physics and CUDA services |
| `gaussian_corner_repair/evidence/` | Dense surface sampling, fixed-geometry appearance fitting/stabilization, close-up validation, revised services |
| `kitchen_objects_pbr_dashboard/`, `toaster_home_tour/`, `dashboard_restore/` | Browser/gallery/model viewers, route preservation, local tunnel helper and service launchers |
| `kitchen_product_model_replacements/evidence/` | Cached candidate search/download tooling; installation remains separately verified |
| `visualization_tools/`, `dashboard/` | Original Habitat/Blender preview and route-author helpers |

Dependencies are workload-specific: NumPy/Pillow/OpenCV, trimesh/SciPy, Blender `bpy`, Habitat-Sim/Bullet, quaternion, PyTorch/CUDA/gsplat, browser automation, and SSH. These are scripts copied from the existing ISL environments, not a complete local installation. Paths identify their server-side data/build roots; scripts with top-level server/build side effects are checked syntactically rather than imported during local validation.

The source commit set excludes `.venv`, raw images/model archives, scenes, checkpoints, traces, and broad candidate-search payloads. Selected runtime web files and source/license metadata accompany the tools. [SOURCE_MANIFEST.json](SOURCE_MANIFEST.json) indexes selected parent tool source snapshots and hashes; current publication paths are listed separately.

## Analysis → current code changes

| Evidence / defect | Source change | Verification / source reference |
| --- | --- | --- |
| GQFT flow/pitch/checkpoint overlay confounds | `episode_contract.py`, `checkpoint.py`, strict inference/evaluation adapters | CPU variant/output/geometry checks; [SEA-RAFT](REFERENCES.md) |
| GQFT exact-motion projection conflict | Explicit optional label mode in `dataset.py`; oracle audit and paired plan | 3/104 windows; no paired-training improvement claimed |
| Contact setting may differ at runtime from XML | `run_interactive_sim.py`: explicit `--contact-impratio`; `record.py` / `interactive.py`: compiled solver manifest | CPU override/no-override regression; [MuJoCo reference](https://mujoco.readthedocs.io/en/stable/XMLreference.html#option-impratio) |
| Current target limits differ from old successful tests | `catalog_evidence.py`, `verify_current_contract.py`, `summarize_deep_audit.py` | Current 34-case CPU study, checkpoint hashes and tight-limit result |
| Target-rate penalties must account for elapsed time/reset | `target_rate_reward.py`, training profiles | Reward timing/reset/manager tests; thresholds are not actuator specifications |
| Product silhouettes and materials remain approximate | `build_replacements.py`, `build_additional.py`, `refine_appliances.py`, `fix_grinder_texture.py`, `rebuild_glaze.py` | Saved fit/source metadata, calibrated captures and 22 browser selections |
| Multi-material props were treated as scan background | Product `web/home-tour.js` hierarchy-aware material handling | Actual room/model browser reviews; [model authors/licences](../../Task_4/kitchen_product_model_replacements/README.md#sources) |
| Mesh revision differs from Gaussian reconstruction | `merge_products.py`, `products_dashboard.py`, calibrated capture/publication checks | Mesh-only revision; original toaster geometry/maps preserved |

Reproduction/publishing paths: [manual Git commands](presentation/PUBLISH_COMMANDS.md). These commands preserve the user's manual commit/push workflow. Raw output folders and large licensed model assets are excluded from the selected source set.
