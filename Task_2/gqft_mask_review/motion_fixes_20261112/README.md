# Motion failure controls — 12 November 2026

The central-floor control has a positive validation result without retraining. The height issue is confirmed in the reconstruction pipeline, but the proposed uniform “upstairs” grouping is not supported for every named episode. Separate height-corrected RGB recordings have been rendered for the five episodes whose complete support audit is unambiguous. Other episodes remain unresolved; their heights are not guessed.

All work belongs to `Task_2/gqft_mask_review/motion_fixes_20261112`. The server copy is under `/data/robotics/toshith/vivekananda/gqft_algorithm_sharing_vivekananda/gqft_mask_review/motion_fixes_20261112`. These are frozen inference experiments on the existing 500-step pilot checkpoints. No new training or augmentation ran. Physical GPU4 was already authorized by the user. Released baseline, original RGB/poses, checkpoints and previous galleries are preserved.

## What changed and why

| Requested fix | Implementation | Evidence and current decision |
| --- | --- | --- |
| Correct actual camera clearance | Audit mesh support at each pose; reconstruct a separate per-frame `agent_y`; rerender with sensor mount 1.2 m above that support | Five complete recordings rendered. Five have uncertain support and are excluded from automatic correction. Original lost world-Y is not recovered |
| Avoid false translation during pure turns | Retain the existing floor solver; test synthetic pure yaw in the new directional implementation | Synthetic yaw produces negligible translation. The pasted empirical 0.02°/0.68° comparison was not independently reproduced in this audit |
| Separate usable spatial cues | Add a central near-floor solver, and separately a far-ray yaw / near-floor translation solver | Central floor improves validation. The split branch is worse; leave it experimental |
| Replace 24-pair resets | Add sliding context: consume the most recent ≤24 pairs, emit only the newest local increment, integrate each increment once | Tested on 26 full validation sequences. No clear improvement over chunked context; retain chunked as the displayed control |
| Handle poor floor fits | Add a residual/support quality gate blending solver with an independent frozen yaw-local model | Overall validation is worse than the neural rolling control. No claim that the two named stair legs are fixed |

The active implementation is [step2/motion_controls.py](../../gqft_algorithm_sharing_vivekananda/step2/motion_controls.py); the validation entry point is [tools/evaluate_motion_controls.py](../../gqft_algorithm_sharing_vivekananda/tools/evaluate_motion_controls.py). Existing model and solver defaults are unchanged. Runtime overrides are applied explicitly **after strict checkpoint loading**, with all parameter keys and values retained, and recorded separately from the checkpoint's training configuration.

### What “central floor” means

For a pixel ray, the calibrated camera and the assumed ground plane give forward distance `f` and left displacement `l`. Keep solver weights only where `f > 0` and `abs(l) <= 0.5*f`, in addition to the existing near-floor range/confidence/validity weights. This restricts fitting to the forward wedge; it does not alter the image, CNN activations or the saved model parameters. The 1.0 m floor-range setting comes from the earlier fixed training-subset selection. The wedge ratio 0.5 was fixed before this validation run.

This is a geometric experiment inspired by task-specific feature selection in P04, not a reproduction of its recurrent dual-branch architecture. A ground-intersection range is a prior, not measured object depth. The far-ray branch cannot assume that every selected pixel actually observes a distant wall; its validation failure reinforces that limitation.

### How sliding and fallback work

`neural_local_steps(..., mode='sliding')` calls the same frozen model for each rolling prefix and uses only that window's newest local translation/yaw increment. `integrate_local_steps` rotates each displacement using the previous accumulated predicted yaw about the calibrated world-up axis, then sums once. No ground-truth heading is supplied. Vertical increments are retained. The first 23 frames necessarily have less than 24 pairs of history.

`quality_fuse` uses the solver residual and usable weight support, with a fixed transition between 2 and 5 pixel residual. Empty/nonfinite support falls back to the independent neural estimate. A small learned correction to the same solver is not an independent fallback. The tested gate is a hypothesis, not a calibrated uncertainty model.

## Validation results

### Full observed sequence control

[Raw results](full_sequence_validation.json): all 26 validation sequences in scene D7G3Y4RVNrH, 48 observed flow pairs each, context24, float32, fixed query(480,809), canvas960×810. No locked-test data was used for algorithm selection. This full-sequence diagnostic is separate from the historical H24/reference30 evaluation and its history gate.

| Method | Mean ground error cm | Pixel ADE | Endpoint yaw error degrees |
| --- | ---: | ---: | ---: |
| Frozen neural, chunked |9.471|14.249|9.013|
| Same neural, sliding |9.509|14.406|8.911|
| Original joint floor solver |13.547|20.862|16.885|
| **Central-floor solver** |**6.407**|**9.523**|**4.794**|
| Far-ray yaw + central translation |11.534|16.181|22.913|
| Residual/support quality fusion |11.011|16.367|9.384|

Central floor improves 20/26 sequences over the original joint solver. The paired sequence-bootstrap mean change is −7.140 cm, 95% interval [−10.467, −4.201] cm. On the approximately planar group, jointly considered, mean error falls from12.493 to5.742 cm over24 sequences. On the two height-changing sequences it falls from26.195 to14.378 cm. These are one-house results, not proof of cross-house generalization.

Sliding versus chunked changes ground error by +0.038 cm, bootstrap interval [−0.230,+0.304] cm. The split branch is worse than central joint fitting by5.127 cm. Quality fusion does not establish a general gain over the neural model; its mean change is+1.502 cm, interval [−0.365,+3.540] cm.

### Existing trained hybrids, matched H24

[Raw results](trained_center_h24.json): same104 overlapping windows from26 sequences; reference30, observed24, one fixed anchor, sequence-floor labels, float32. The only within-hybrid change is the explicit spatial solver weight rule.

| Frozen checkpoint | Original solver ADE px | Central-floor ADE px | Original → central mean ground error cm |
| --- | ---: | ---: | ---: |
| Solver + bounded correction |15.6188|5.8393|6.329 → 2.189|
| Solver + learned weights |15.4479|4.6543|6.321 → 1.713|
| Yaw-local neural reference |10.9090|Not changed|4.325|

The trained learned-weight model's central control is a useful candidate. This follow-up uses the same validation scene as previous experiments and is not an independent replication. Earlier pilot values used CUDA bfloat16; compare the two float32 columns above directly, rather than mixing precision protocols.

### Original history acceptance rule remains unsatisfied

[Seven-history audit](center_history_gate.json): the original H4/8/12/16/20/24/30 protocol, CUDA bfloat16, reference30 and unchanged ambiguity/tolerance thresholds. Both hybrids still return `shortest_sufficient_history: null`.

AtH24, central correction has ADE5.4751px and ambiguity0.73077; central learned weights has ADE4.5194px and ambiguity0.71579. The latter has68 ambiguous queries among95 cosine-near retrieved queries, while104 queries were eligible. These denominators are distinct. Improving projected trajectories does not establish a useful terminal-state signature.

Do not lower the gate threshold or replace its result after looking at these numbers. A separate audit of terminal versus temporally pooled states, centering, effective rank and full-reference versus observed-prefix gaps is still needed. A local motion head need not encode all historical information in its last token, but that is a hypothesis here, not a demonstrated explanation.

## Height investigation and separate corrected recordings

The original [build_poses.py](original_build_poses.py) saves `(world_x, world_z, yaw)` and one scalar `floor_y` from the first leg; it drops the per-frame world-Y trace. The original [render_frames.py](original_render_frames.py) then holds agent Y fixed to that scalar for every frame and adds the 1.2m sensor mount. Therefore a configured mount of1.2m does **not** establish that the camera was1.2m above the visible local floor, especially when replaying stairs.

Absolute `floor_y` alone cannot diagnose this either. The audit intersects scene triangles vertically at each footprint and four5cm offsets, checks horizontal support and reports ambiguous overhead/object surfaces, changing support or missing support explicitly. Original MP3D GLB vertices are transformed to Habitat's world convention by `(x,y,z) → (x,z,-y)`, a fixed asset-coordinate rule, not a fitted rotation. See the [Habitat asset loader](https://github.com/facebookresearch/habitat-sim/blob/main/src/esp/assets/Asset.cpp) and [coordinate-frame documentation](https://aihabitat.org/docs/habitat-sim/coordinate-frame-tutorial.html).

An initial untransformed mesh audit is retained on the server as invalid historical evidence; only `height_audit_habitat/` is used here. Floor-like triangles can still be objects: these measurements are not semantic floor truth.

| Episode | Unambiguous measured frames / total | Median original camera clearance on those frames m | Automatic full rerender |
| --- | ---: | ---: | --- |
|629|418/418|1.369|Completed|
|753|521/521|1.436|Completed|
|1285|1431/1431|1.368|Completed|
|1395|128/128|1.325|Completed|
|1481|382/382|1.369|Completed|
|837|1033/1170|2.751|Deferred: uncertain support; locked-test scene|
|1031|228/314|2.794|Deferred: uncertain support|
|1781|152/346|1.294|Deferred:190 frames lack support|
|478|407/445|1.408|Deferred: objects/changing support|
|1689|587/636|1.290|Deferred: changing/missing support|

This supports checking837/1031 carefully, but does not justify treating1781 as the same uniform height failure. Nor does it establish that height correction will remove two thirds of the aggregate error. No scale is fitted from the reference trajectory.

The existing Habitat runtime was found at `/data/robotics/toshith/vln_baselines/envs/habitat38/bin/python`; no installation was needed. [Unchanged replay verification](legacy_replay_verification.json) passes on episode629 frames0,139,337: RGB correlations0.99957,0.99956,0.99970, mean absolute RGB errors below0.88/255. This checks rendering conventions before changing heights; it does not prove every mesh intersection is a floor.

[render_corrected_frames.py](render_corrected_frames.py) verifies the audit's original pose hash and requires every frame to have measured support. It writes new NPZs with `agent_y`, `camera_y`, `local_floor_y` and explicit provenance, preserves X/Z/yaw and the camera orientation/FOV, and renders into a fresh output. It refuses uncertain plans and existing output paths.

[Height-render receipt](height_render_status.json): complete counterfactual recordings exist for629,753,1285,1395,1481, totaling2880frames. Server dataset:

```
gqft_mask_review/motion_fixes_20261112/height_corrected_v1/
  poses/<original_stem>.npz
  frames/<original_stem>/00000.png ...
  <original_stem>_render.json
```

These are **mesh-reconstructed vertical trajectories**, not recovery of the lost original world-Y logs. A 1.2m mount is enforced relative to estimated support. For the unresolved episodes, recover the original3-D agent path or inspect/verify native/semantic floor support before rerendering. Do not interpolate across uncertain stair floors automatically.

## Images, cache provenance and experiment separation

**[Open the experiment dashboard](comparison.html).** Experiment A is the default: original RGB, original versus central-floor rule, with its own ten-recording table. **[Experiment B: camera-height reconstruction](comparison.html#height)** is a separate selectable experiment: original RGB with central floor versus reconstructed-height RGB with central floor, with its own five-recording table. Model and sensor mount height remain 1.2m; reconstructed agent elevation is the changed variable. The height experiment does not replace the original-data benchmark. Click an overlay to open its full-size PNG.

Visual outputs are kept separate:

- [Original RGB / central floor gallery](original_rgb_center/index.html):10 episodes,133 legs,143 views,725 trajectory PNGs. Same checkpoints, explicit central-floor runtime control. These show the algorithm intervention without changing images.
- [Corrected-height gallery](height_corrected_center/index.html):5 episodes,70 legs,75 views,380 trajectory PNGs. Same checkpoints and central-floor rule. These show the additional input-height intervention.
- The prior unmodified gallery remains at `../trained_episode_overlays/20261111T220751Z_gpu4/all_episodes_20261111T223221Z/index.html`.

The overlay helper supports `--solver-control unchanged|center|split` and `--context-mode chunked|sliding`. Learned controls are strictly loaded before any override. Predictions integrate their own estimated yaw; recorded poses are used only for the reference and error calculation. There is no fitted heading, scale or alignment.

Flow caches now include the input dataset root, pose-file hash and frozen SEA-RAFT weight hash in their identity. Hash-matched old caches can be hardlinked for the **original RGB only**, recorded in `original_cache_reuse.json`. Corrected RGB gets newly computed flow, confidence and validity in a separate cache identity. Reusing old flow for rerendered frames would invalidate the experiment.

All-episode recordings, including the existing locked-test recording837, are visualization only after constants are frozen. They are not another model-selection benchmark. The current104-window validation and26-sequence selection experiments do not access locked-test data.

### What the new recorded-episode images establish

Central floor does not improve every recording. For the learned-weight checkpoint, full episode629 worsens from17.88 to33.01cm mean ground error on unchanged RGB;1395 is nearly unchanged (4.12→4.18cm), while1285 improves422.62→120.22cm. These are diagnostics under a different, longer recorded-motion regime, not replacements for the validation benchmark. [All original-versus-center values](original_center_full_episode_comparison.json) include the regressions.

With central floor held fixed, the additional height intervention gives:

| Episode | Solver + correction: original → corrected RGB, cm | Solver + learned weights: original → corrected RGB, cm |
| --- | ---: | ---: |
|629|23.26 → 7.71|33.01 → 31.48|
|753|48.55 → 18.58|38.24 → 38.24|
|1285|130.72 → 107.24|120.22 → 103.07|
|1395|8.15 → 5.26|4.18 → 9.48|
|1481|28.72 → 25.78|36.09 → 40.72|

The correction hybrid improves on5/5 complete counterfactual recordings. The learned-weight model improves on2/5, is nearly unchanged on753 and worsens on1395/1481. The independent neural reference worsens on4/5. Height correction changes rendered optical flow and can change accumulated yaw as well as scale; a frozen learned model is not guaranteed to improve. Do not choose a different checkpoint for each episode or claim universal error removal. [Full three-model paired results](height_intervention_full_episode_comparison.json).

The expected original `HSGM_public/integration/runs/b10_A_drivefix_idx{0,4,9,2,6}_20260829_114756/episode_results.json` paths are absent on this server. The saved pose files alone cannot recover a true per-frame elevation trace for the deferred episodes.

## Verification and reproducibility

[CPU checks](cpu_verification.json):18/18 pass. They cover synthetic motion/yaw recovery, absence of false pure-yaw translation, empty support, central wedge selection, bounded rolling histories, exactly-once integration, retained vertical motion, quality fallback, height-versus-world-coordinate distinctions, fixed asset transforms, height-plan preservation/refusal and exact checkpoint parameter preservation after an override. Real-data validation results above are necessary in addition to these checks.

[Height dataset verification](height_dataset_verification.json) checks all2880 rendered frame names/counts, identical original X/Z/yaw/leg boundaries/intrinsics, finite support, exact audit/pose hashes and1.2m clearance relative to reconstructed support. Both galleries pass saved-path metric recomputation, PNG decoding and desktop/mobile browser checks across all218 trajectory views. The [comparison check](comparison_verification.json) exercises60 experiment/episode/model selections with real PNG loading, explicit uncertain-height states and no JavaScript errors. The first restricted browser attempt could not start; checks succeeded in an isolated permitted browser.

`source_initial/` preserves all18 original diagnostic source hashes from `SOURCE_MANIFEST.json`. `source/` and `VISUAL_SOURCE_MANIFEST.json` preserve the later inference source, whose only motion-control addition is the strict runtime-override helper. [Version verification](source_version_verification.json) records exact reconstruction of the earlier snapshot. Historical manifests are not overwritten.

To repeat the H24 frozen intervention on the server into a **new** results file:

```bash
cd /data/robotics/toshith/vivekananda/gqft_algorithm_sharing_vivekananda
CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES=4 \
PYTHONDONTWRITEBYTECODE=1 /data/robotics/toshith/envs/agentvln/bin/python -B \
  gqft_mask_review/motion_fixes_20261112/evaluate_trained_center_control.py \
  --project "$PWD" \
  --source "$PWD/gqft_mask_review/motion_fixes_20261112/source" \
  --pilot "$PWD/gqft_mask_review/ground_pilots/20261111T220751Z_gpu4" \
  --device cuda \
  --out "$PWD/gqft_mask_review/motion_fixes_20261112/trained_center_h24_repeat.json"
```

This is inference, not training. Check GPU authorization/availability before a later run. `run_height_renders.py` uses fresh-output refusal and is not intended to overwrite its completed dataset. CPU-only checks can be repeated from the local lab with the existing torch environment using `python -B verify_motion_controls.py`.

## Next decisions

1. Review central-floor predictions across the ground-floor cohort together; retain validation as the selection evidence. Freeze the rule before any independent cross-scene evaluation.
2. Compare original and corrected-height RGB using newly computed flow and identical frozen models. Do not infer improvement merely from the configured1.2m mount.
3. Resolve the incomplete floor audits from the original3-D logs or verified floor geometry; keep their existing results in a separate height-uncertain group.
4. Diagnose the history signature independently. Current trajectory gains do not satisfy that requirement.
5. Only after these checks consider matched multi-seed training with the validated central-floor control. Far-ray yaw, sliding and residual fusion have not earned default status.
