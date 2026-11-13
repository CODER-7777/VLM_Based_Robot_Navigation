# GQFT: approaches, evidence, research and next experiments

Updated 12 November 2026. This is the consolidated working document for the GQFT lab. It records completed experiments, implemented but untrained changes, and proposed approaches separately. Historical evidence is linked rather than rewritten. The ten papers supplied in the discussion are reviewed in Section 8, with implementation status and corrections.

## 1. Current position

> **12 November update:** the GPU-4 pilot has since completed on 10 recorded episodes. The largest error source is upper-floor recordings whose camera is not 1.2 m above the floor. On correctly recorded episodes the solver models beat the reference. See A15 and the [root-cause report](root_cause_20261112/ROOT_CAUSE.md). The paragraphs below predate that run.

We have completed the frozen-mask experiments, a matched four-arm training pilot, numerical validation, episode-629 overlays and an offline comparison dashboard. Hard masking regressed. Frozen soft weighting produced only a tiny uncertain benefit. In the pilot, yaw-local integration improved validation trajectory error but failed the existing history-selection gate. A newer geometric floor-flow solver improves three of four inspected episode windows, but its range cutoff was selected on those same windows. The optional solver/GQFT hybrid is implemented and has recorded CPU checks; it has not been trained.

The immediate next experiment is a protocol-correct solver validation, accompanied by the pending representation and label audits. Another long training run is premature. GPU 4 is the user's latest device choice, supplied on 12 November; this document was prepared without allocating it or starting training. Training is intended for the guest-isl server. Current server availability and deployment of the newer local solver code have not been verified after the earlier SSH timeouts.

ADE means average displacement error along a trajectory; FDE means final displacement error. Pixels measure the projected image path. Metres measure the estimated physical displacement. A pixel improvement can coexist with worse metric motion. A history-gate pass is a separate acceptance criterion from ADE.

## 2. What GQFT does

GQFT means Geometry-Constrained Query Flow Transformer. Given a short sequence of camera observations, it estimates camera movement from optical flow, accumulates that movement into a 3-D path, and analytically projects the path relative to a selected ground anchor into the initial image.

```text
Consecutive RGB frames
  -> frozen SEA-RAFT optical flow
  -> [du, dv, confidence, validity] at 90 x 160 per pair
  -> append two coordinate channels
  -> four convolution / GroupNorm / GELU blocks
  -> 256-channel feature map, 6 x 10 spatial cells
  -> mean + max OR learned spatial attention + max
  -> concatenate summaries and project 512 -> 256
  -> learned time embeddings and causal Transformer
  -> per-step displacement, optional yaw, uncertainty
  -> accumulate movement in a declared coordinate frame
  -> calibrated analytic projection -> image trajectory

Selected pixel query -> geometric anchor and validity branch
```

The four 3 x 3 convolutions use stride 2 and padding 1. Channels are 6, 32, 64, 128, 256; spatial sizes are 90 x 160, 45 x 80, 23 x 40, 12 x 20, 6 x 10. The temporal model has four layers, eight heads, width 256 and feed-forward width 1024. Invalid input flow is already zeroed, while confidence and validity remain explicit channels. The displacement head predicts three bounded increments; the optional yaw head predicts one increment. A separate uncertainty head estimates motion uncertainty.

The selected pixel does not condition the current temporal motion states. It changes the geometric projection and the query-conditioned validity branch. Query-conditioned spatial cross-attention is a proposal, not the architecture presently evaluated.

### Coordinate frames: why the old cumulative sum was valid

The original displacement head is supervised in the initial camera frame. Summing those increments directly is consistent with that target convention. It was not a mathematical integration bug.

Yaw-local is an alternative factorization. It predicts increments in the current local camera/body convention, rotates each increment by the accumulated yaw from preceding steps about the calibrated camera-frame world-up axis, and then sums. Its target conversion changes with the head convention. Existing keyframe-trained heads cannot simply be reinterpreted as local heads; the implementation requires explicit head resets and matching targets.

For example, a robot drives forward, turns left, and drives forward again. The original model must express both forward steps in the initial frame. Yaw-local predicts forward in each local frame and uses the accumulated heading to rotate the second step into the initial frame. Both can express the same path; the experiment tests which is easier to learn.

Sources: [model](../gqft_algorithm_sharing_vivekananda/step2/models/gqft.py), [geometry](../gqft_algorithm_sharing_vivekananda/step2/geometry.py), [dataset](../gqft_algorithm_sharing_vivekananda/step2/dataset.py), [history study](../gqft_algorithm_sharing_vivekananda/step2/history_study.py).

## 3. Comparison contracts and limits

The benchmark has four training scenes, one validation scene (D7G3Y4RVNrH), and one locked-test scene (TbHJrupSAjP). The recorded camera contract is 960 x 540, 135-degree horizontal field of view, height 1.2 m, pitch 30 degrees downward and 5 Hz. A 270-pixel virtual extension makes the comparison canvas 960 x 810 and the extended anchor (480, 809).

Keep these protocols separate:

| Protocol | Scope and scoring | Appropriate use |
| --- | --- | --- |
| Historical released/attention benchmark | Historical fixed-H24 validation/test reports; checkpoint, precision and history-selection caveats retained | Establish historical reference results |
| Frozen masking validation | 104 overlapping windows from 26 sequences; reference history 30, observed history 24; fixed anchor; float32; post-origin errors | Compare frozen pooling interventions |
| October training pilot | Same fixed validation windows; CUDA bfloat16; ADE includes the origin; one reset-head seed and 500 steps per arm | Compare the four matched trained arms |
| Episode 629 | Legs 0, 2, 3, 4; first 24 pairs each; recorded poses; post-origin errors; no fitted scale or rotation | Qualitative/metric diagnosis, not benchmark selection |
| November solver exploration | Same four episode windows, but cutoff selected on those windows | Generate a hypothesis requiring independent validation |

The 104 validation windows overlap. They are not 104 independent scenes. One seed does not establish seed robustness. Historical training-time mixed-query validation is not the fixed-anchor comparison. CPU float32 scores and CUDA bfloat16 scores must be labeled separately.

The locked test has already been reported historically. Do not use its results or episode 837 (from the locked-test scene) to select architecture, cutoffs, labels or training settings. Keep all future decisions on training data and declared validation protocols.

## 4. All approaches and their status

| ID | Approach | Status | What the evidence says |
| --- | --- | --- | --- |
| A01 | Released mean + max pooling | Evaluated reference | Historical locked-test ADE/FDE 9.630945 / 15.847433 px |
| A02 | Horizontal-flip augmentation | Historical, discontinued | Mixed training-time validation improved in old notes; no controlled locked-test gain established; current policy forbids flips |
| A03 | Learned spatial attention + max | Trained/evaluated | Validation improved; historical locked-test ADE worsened to 10.090982 px and history selection failed |
| A04 | Attention + auxiliary yaw | Trained/evaluated | Historical locked-test ADE/FDE 8.783099 / 13.322794 px; one scene/seed and history-selection caveats |
| A05 | Frozen hard validity masking | Evaluated | Episode mean ground error 7.203 -> 12.570 cm; harmful for this intervention |
| A06 | Six-policy branch/support isolation | Completed | Max masking caused the larger individual regression; support restoration recovered much, not all, of the loss |
| A07 | Frozen soft coverage weighting | Completed | Primary ground gain 0.087 mm on validation; sequence-bootstrap interval includes zero |
| A08 | Four-arm soft-mask/yaw-local pilot | Trained/evaluated | Yaw-local improved ADE; masking hurt within both integration modes; yaw-local arms failed the history gate |
| A09 | Attention entropy/support/gate-count audit | Saved-array audit completed | Attention is concentrated; this does not by itself prove overfitting or collapse |
| A10 | Pixel-label geometry oracle | Validation audit completed | Three overlapping windows in one sequence disagree with the fixed-rig projector by up to 65.5247 px |
| A11 | Ten-paper and repository review | Consolidated here | Primary sources checked; source snapshots inspected; incorrect official-code links corrected |
| A12 | Geometric floor-flow solver | Implemented/exploratory evaluation | Improves three of four episode windows; no matched held-out validation result yet |
| A13 | GQFT + solver residual hybrid | Implemented, untrained | Fifteen recorded CPU checks pass; no trained hybrid checkpoint found |
| A14 | Motion-family/full-leg error diagnosis | Script implemented; partial notes | Motion-coverage and chunk-stitching hypotheses remain; complete multi-episode result not found locally |

### A01-A04: baseline, augmentation and learned attention

The released model is the preserved working reference. Spatial attention replaces average pooling with a learned softmax over 60 cells, while retaining max pooling. Repaired fixed-H24 CPU validation reports approximately 11.2625 -> 10.2826 px for baseline -> spatial attention. Older notes quote approximately 11.32 -> 10.38 under their historical protocol; these are not extra independent replications. Historical test FDE also regressed from 15.847433 to 16.591120 px for spatial attention.

Attention plus auxiliary yaw produced the best historical locked-test number listed here. This yaw supervision did not rotate displacement increments in the original keyframe mode. It is distinct from the later yaw-local integration pilot. The test advantage is a reported result, not evidence that every added attention or yaw mechanism will generalize.

The adapter/checkpoint audit also corrected contract problems: single flow normalization, mounting-pitch sign conversion, the trained anchor and strict variant loading. It identified old augmented-model overlays mislabeled as baseline. These repairs establish comparable inputs and provenance; their effect must not be attributed to masking.

Flip augmentation is retained only as historical work. A correct geometric flip requires consistent transformations of images, flow, poses, queries and camera conventions; the project now excludes it. Its old mixed-validation improvement cannot be combined with the no-flip comparisons.

Evidence: [improvements tracker](../IMPROVEMENTS_TRACKER.md), [historical project guide](../REPOSITORY_PROGRESS_README.md), preserved baseline/results in the active code folder.

### A05-A06: what was masked, and what the isolation established

The original frozen hard-mask probe used input validity to reject low-coverage cells in the final 6 x 10 CNN map, then changed both attention and max pooling. It did not segment furniture, detect semantic objects, or remove entire episodes. A cell above an invalid input patch is not necessarily an invalid feature.

Four strided convolutions give each cell a 31 x 31 direct-convolution receptive field. It can contain nearby valid flow even when its coarse average validity is low. GroupNorm also makes features depend on spatial statistics beyond that footprint. Removing a cell changes the distribution of summaries expected by a frozen trained head.

For example, a rejected border cell may have only 60% valid pixels in a coarse bin, yet its receptive field includes a strong valid edge immediately beside that bin. The CNN has already encoded the edge in the feature. Rejecting the feature discards that response as well. A support map shows that information can reach a cell; it does not certify that its features are correct.

| Frozen validation policy | Mean ground error, cm |
| --- | ---: |
| Original pooling | 4.491709 |
| Hard attention only | 6.496007 |
| Hard max only | 11.156014 |
| Hard attention and max | 25.112899 |
| Restore rejected cells with valid convolution support | 4.757932 |
| Replace coarse rule with convolution-support rule | 4.798161 |

The intervention was isolated at branch and feature-support level. Direct perturbation controls, with GroupNorm statistics frozen, showed local valid-neighbour influence and no direct influence outside the 31 x 31 convolution footprint. Ordinary GroupNorm restores global dependence. This supports useful-cue removal and frozen-pooling mismatch. It does not assign every recovered error to one cause. The jointly masked policy also generated nonpositive-depth failures; huge clamped pixel errors are failure diagnostics rather than ordinary accuracy comparisons.

Evidence: [isolation report](ISOLATION_RESULTS.md), [isolation artifacts](isolations/20261015_gpu2_pooling_v2/verification.json), [episode review](README.md).

### A07: frozen soft weighting

The predeclared primary used reliability = 0.25 + 0.75 x validity coverage over the convolution footprint. It multiplied attention weights by reliability and renormalized, while keeping the original max vector. The coarse-grid version was a control. This frozen trial did not use a new confidence threshold or semantic ground segmentation.

Primary validation ground mean was 4.491709 -> 4.483005 cm, a reduction of 0.194%, or 0.087 mm. The sequence-bootstrap 95% interval for the change was [-0.214, +0.043] mm. The coarse control reached 4.460674 cm, but its interval also included zero. These tiny effects do not establish dependable improvement. Passing a numerical screen without a minimum effect size is not proof of practical value.

Evidence: [soft trial report](SOFT_ATTENTION_RESULTS.md).

### A08: trained soft attention and yaw-local integration

The trainable implementation adds confidence/validity weighting and an optional geometric ray-support prior to attention logits. The soft configuration has a nonzero reliability floor and retains the original max summary. Geometric ray support estimates where a ray could meet the assumed plane; it does not establish that the visible surface is floor. A hard coverage gate is optional but was not the main soft pilot policy.

Four arms used the same pretrained yaw backbone, freshly reset displacement/uncertainty heads, initialization recipe, labels, optimizer and 500-step budget. All predict yaw. The original pretrained yaw model is an operational reference with older trained heads, not a matched fifth training arm.

| Model | H24 ADE px | H24 FDE px | H24 ambiguous / close queries | Selected history |
| --- | ---: | ---: | ---: | ---: |
| Trained reference | 12.4626 | 17.4344 | 0 / 17 | 16 |
| Soft mask only | 12.8267 | 18.8231 | 0 / 18 | 20 |
| Yaw-local only | 11.3485 | 13.3930 | 4 / 24 | None |
| Soft mask + yaw-local | 11.8091 | 14.1293 | 5 / 25 | None |
| Original pretrained yaw | 11.6926 | 15.3060 | 0 / 8 | 16 |

Masking worsens fixed-window ADE within both integration modes. Yaw-local improves ADE relative to the matched reference but does not satisfy the existing history rule. Histories tested were 4, 8, 12, 16, 20, 24 and 30. A longer run must not be justified by changing the ambiguity denominator or ignoring the gate.

Evidence: [implementation record](implementation_20261016/README.md), [matched pilot report](pilot_results/20261019T101035Z_431613/validation_20261019T104120Z/REPORT.md).

### A09: entropy, support and ambiguity

The saved-array audit covers 96 flow pairs from four episode-629 windows. Mean effective attention-cell counts are approximately 2.96 reference, 2.99 mask, 2.27 yaw-local, 2.43 combined and 3.17 original pretrained yaw, out of 60 cells. Uniform entropy would be log(60) = 4.094 nats. Concentrated attention is measured here; scene shortcuts and representation collapse are hypotheses.

For leg00, coarse coverage retains about 80.49% of cells whereas any-valid convolution-path support covers about 99.72%. About 19.24% of cells are rejected by the coarse rule despite having some valid convolution support. This is not a justification for trusting all admitted cells.

The official ambiguity denominator is cosine-near retrieved queries, so yaw-local is 4/24 = 0.1667, not 4/104. Query counts need not be unique unordered pairs. Small, dependent counts limit precision, but overlapping confidence intervals do not prove equivalence or invalidate the operational gate. Full validation embeddings, centered/pooled retrieval and effective-rank comparisons have not yet been extracted.

Evidence: [saved-array findings](diagnosis_20261104/findings.json).

### A10: label geometry

All three known conflicting validation windows belong to hsgm_D7G3Y4RVNrH_val_v023, at overlapping starts 5, 10 and 15. Sequence-relative heights are approximately 1.365, 1.566 and 1.794 m rather than the fixed 1.2 m. Exact-motion projection disagrees by up to 65.5247 px under the mismatched convention; matching the annotation height reduces the maximum to about 0.000126 px.

This establishes a target/projector mismatch on those windows. It does not establish its prevalence in training or its contribution to training gradients. We must verify the physical plane/height contract, audit training metadata, and report sequence-floor and fixed-rig pixel protocols separately. A motion-loss scalar of 4 does not prove gradient dominance. A short run failing to improve would not make inconsistent labels correct.

Evidence: [geometry oracle](../gqft_algorithm_sharing_vivekananda/analysis/label_geometry_20261009/oracle_geometry.json).

### A12-A13: floor-flow geometry and the optional residual hybrid

The solver uses known camera calibration, height and pitch to predict flow from three planar motion variables: forward, left and yaw. It weights observed flow by confidence, validity, a smooth near-ground ray prior and robust residual weighting, then performs six damped Gauss-Newton iterations. Known height supplies metric scale when the plane and observed correspondences satisfy the model. Walls, furniture, hidden floor and changing elevation violate those assumptions.

| Episode 629 leg | Original Attention+Yaw mean / endpoint m | Torch solver mean / endpoint m |
| --- | ---: | ---: |
| 00 | 0.102485 / 0.279731 | 0.016462 / 0.037997 |
| 02 | 0.070768 / 0.233033 | 0.017595 / 0.030329 |
| 03 | 0.030211 / 0.043172 | 0.033949 / 0.037772 |
| 04 | 0.084658 / 0.191099 | 0.016866 / 0.028757 |

These are the implemented torch solver's recorded results. Earlier scipy prototype values are different and must not be substituted. The 1.5 m cutoff was chosen on these same four windows; the solver is not yet a validation winner. Near-floor support is a geometric prior, not an object/floor segmentation result. Low-support zero/finite output is a failure/fallback condition that must be counted, not evidence that the robot was stationary.

The optional hybrid mode adds solver motion and diagnostics to the temporal token, then predicts bounded corrections: default translation residual 0.03 m per coordinate and yaw residual 0.05 rad per step. Residual heads are zero-initialized to start at solver motion. The optional pixel-weight network is 6 -> 16 -> 16 -> 1 with 2 x sigmoid output initialized to one. It changes solver weights, not final CNN feature masks. Default optimization can update the existing CNN/Transformer as well as new modules; this is not a frozen-backbone-only training scheme.

Fifteen recorded CPU checks cover synthetic motion recovery, no-floor finite behavior, gradients, strict checkpoint round trips, warm-start head-reset rules and legacy bit-identical outputs. These checks verify implementation properties, not real-data accuracy. No trained hybrid checkpoint or matched solver validation result was found in the inspected local artifacts.

Evidence: [solver source](../gqft_algorithm_sharing_vivekananda/step2/ground_solver.py), [recorded checks and episode scores](ground_geometry_20261109/verification.json).

### A14: motion coverage and full-leg diagnosis

The episode-diagnosis script and partial notes suggest errors during turn-in-place, variable speed and chunk restarts. Reported episode-629 step-error summaries were 0.45 / 2.37 / 0.85 cm for GQFT on turn-in-place / fast / normal steps, versus 0.07 / 0.66 / 0.22 cm for the solver. A complete structured multi-episode result was not found locally, so these remain note-level observations rather than a reproduced multi-episode benchmark.

Training-motion coverage mismatch is plausible but has not been isolated as the main cause. Solver success on some windows does not rule out flow errors, Transformer limitations or optimization effects. Chunk restarts can shorten available history and propagate heading errors; compare chunked and sliding-history inference under the same scoring before attributing drift to stitching.

The script's current defaults include episode 837 from the locked-test scene. Exclude it from analysis that changes the method. Source: [episode diagnosis](../gqft_algorithm_sharing_vivekananda/tools/episode_diagnosis.py).

### A15: GPU-4 pilot on all recorded episodes and root-cause analysis (12 November)

The GPU-4 pilot (`20261111T220751Z_gpu4`) trained three models for 500 steps: yaw-local reference, solver + correction and solver + learned weights. It scored them on 10 recorded episodes (133 legs, 5,658 steps) with no fitted alignment. Per-leg breakdown: [root-cause report](root_cause_20261112/ROOT_CAUSE.md).

- **Upper-floor recordings break the 1.2 m camera-height contract.** Episodes with `floor_y` > 1 m (837, 1031, 1781) are the only distance-scale outliers. All three models undershoot by about the same factor (median predicted/true length 0.64 on 837, 0.75 on 1031). In the same house, ground-floor episode 1395 scores 0.99. Every pose file records `mesh_floor_offset_applied: False`. These 37 legs hold about 68% of the solver's summed leg error. Measured association; confirm the actual camera height on the server (check C1 in the report).
- **Ground-floor episodes (96 legs):** mean/median ground error 0.094/0.059 m for the reference, 0.067/0.011 m for solver + correction, 0.064/0.014 m for solver + learned weights. One seed and one 500-step budget, so seed variance is unknown.
- **Turn on the spot** is 22% of steps. The reference adds 7.5 m of phantom distance and 0.68° yaw error per step there; the solver 1.2 m and 0.02° per step.
- **Remaining solver failure:** heading drift of 1–2° per step on nearly straight stretches in corridors, bathrooms and stairways (13 legs with end-heading error > 20°). Wall contamination of the near-floor window is a hypothesis to test.
- Episode 837 is in the locked-test scene. It is reported only as a frozen diagnostic; nothing was tuned on it.

## 5. Proposed approaches that have not been trained/evaluated

| Proposal | Intended mechanism | Current status / prerequisite |
| --- | --- | --- |
| Temporal key-quality attention bias | Add beta x log(frame reliability + epsilon) to causal attention key logits | Proposed; separate from spatial masking; handle padding and degenerate reliability explicitly |
| Confidence-normalized or partial-convolution encoder | Propagate support/confidence during convolution instead of masking mixed final cells | Paper/source reviewed; not integrated; retraining and normalization controls required |
| Feature/channel sigmoid gates | Learn reliability-dependent feature selection without spatial softmax competition | Final-feature gate not implemented; solver pixel-weight gate is a different mechanism |
| Separate translation/rotation pooling | Allow the two tasks to select different cues | Proposed; first measure shared-feature conflicts/errors |
| Analytical rotation-flow subtraction | Estimate yaw-induced flow and remove it before translation prediction | Proposed; calibration, rotation convention and yaw-error coupling require controls |
| Trajectory contrastive/anti-ambiguity loss | Penalize similar signatures for different trajectories | Proposed; diagnose the signature and future-tail confounds first; no guarantee of a gate pass |
| Query-conditioned spatial cross-attention | Use the selected query to pool spatial features | Proposed; changes the query-independent motion-state contract and multi-query cost |
| Entropy/temperature regularization or spatial dropout | Reduce excessive concentration in spatial attention | Proposed; interventions must be tested separately, with max unchanged |
| Calibrated rays as encoder coordinates | Replace generic coordinates with ray tangents | Solver weight network uses calibrated inputs; full-encoder comparison not done; fixed-camera rays add no new sample-specific information |
| Learned task-level uncertainty weights | Balance translation, yaw and projection objectives | Proposed; distinct from the existing per-sample uncertainty head |
| Paired sequence-floor/fixed-rig training | Isolate label/projector consistency | Not run; audit labels and physical plane convention first |
| Multi-seed replication / changed motion coverage | Test seed stability and episode-motion distribution hypotheses | Not run; define matched training-only interventions first |

## 6. What is still undiagnosed

Problem A: validation gain but locked-test regression. Measured on one test scene; scene-specific shortcuts, concentration, limited training diversity and optimization variance are alternatives. Attention concentration alone does not distinguish them.

Problems B/C: late masking regression. Branch interventions and neighbour controls support useful-feature removal and pooling-distribution mismatch. Confidence propagation and normalization-aware operators are still untested remedies.

Problem D: history ambiguity. Possible causes include signature mismatch, common-mean anisotropy, genuine information loss and comparison with unseen future motion. Neither head convention forces a terminal token to uniquely encode the full path, and LayerNorm does not mathematically impose a positive cosine cone.

The H24 gate compares signatures with a 31-point, 30-pair reference curve: six reference pairs are unobserved. Diagnose observed-prefix and future-tail gaps separately. With 26 sequences and four windows each, there are 5,200 unique cross-sequence unordered pairs, not all 5,356 pairs of 104 windows. Retrieval query counts are a different quantity again.

Problem E: label consistency. Three conflicting validation windows are established; training frequency, physical ground-plane definition and gradient effects are pending. Do not use a loss-weight change to hide a contract mismatch.

## 7. Next steps and decision rules

1. Correct the solver evaluator's comparison contract locally. It currently defaults to eight queries, omits the 270-pixel virtual extension and does not pass an 810-pixel canvas to SolverOnly. Setting queries to one alone still samples the wrong query. Match the original anchor, canvas, history, seed, window list, precision and metric domain before comparing ADE.
2. Audit train/validation labels and finish the saved-checkpoint representation diagnostic. Extract states once with checkpoint hashes and identifiers. Compare terminal, temporal-mean and middle-plus-terminal signatures; report raw and centered spectra, effective rank, cosine distributions, nearest-query coverage and every flagged pair. Keep the official gate unchanged. Validation-fit centering is exploratory; a deployed transform must be fitted on training/reference data. A 30% rank drop is not a validated collapse threshold.
3. Stage matching source on guest-isl and verify it against local hashes. The successful 4 November restore predates the 9 November solver additions. Do not assume the newer files are deployed. Shared environments and datasets stay unchanged.
4. Choose the solver cutoff on a fixed training subset only, then freeze it. Evaluate the declared 104 validation windows against the same checkpoints. Report direct 3-D/ground error, yaw error, pixel ADE/FDE, support/failure counts and sequence-level breakdowns. Score both plane conventions as separately declared protocols; do not choose the primary after seeing which scores better.
5. Add solver overlays to the dashboard with explicit provenance and matching windows. Compare full paths and turn-in-place/variable-speed failures on non-test diagnostic data. The current dashboard covers the October five-checkpoint comparison only.
6. If the frozen solver has a defensible validation result, prepare a matched yaw-local reference, solver-plus-residual arm and solver-plus-learned-weights arm. Fix labels, initialization, data order, schedule, budget and multiple seeds. Training belongs on guest-isl; GPU 4 is the latest user-selected device and must be checked for availability before launch. No training was launched for this document.

D1 representation diagnosis, D2 supervision consistency and D3 attention/support diagnosis remain distinct workstreams. CPU or GPU forward passes are inference, not training. New training is justified by a concrete unresolved question and matched controls; the literature does not guarantee a locked-test target, gate pass or fixed speedup.

## 8. Papers supplied by the user: checked relevance and implementation status

The catalogue below checks the ten supplied papers against primary sources and the saved static repository audit. Source inspection is not a reproduction. External implementations were not installed, imported or trained. Exact revisions and file hashes are in the [implementation ledger](research_20261104/REPOSITORY_IMPLEMENTATIONS.md). Four additional geometry references from the newer notes follow the original ten.

### P01. Propagating Confidences through CNNs for Sparse Data Regression

Abdelrahman Eldesokey, Michael Felsberg, Fahad Shahbaz Khan. BMVC 2018. [Primary paper](https://arxiv.org/abs/1805.11913), [author repository](https://github.com/abdo-eldesokey/nconv).

The method couples confidence-aware normalized convolution with propagated confidence, evaluated for sparse depth regression. It motivates testing reliability inside the encoder rather than rejecting already mixed features at its output.

Read `modules/nconv.py`, especially `NConv2d.forward` and `EnforcePos`. The denominator uses confidence and nonnegative applicability weights; confidence is propagated to the next layer. Source is legacy PyTorch, including private `_ConvNd` usage and `.data` weight updates. A modern adaptation requires explicit numerical and gradient checks.

GQFT proposal: a separately configured confidence-aware encoder experiment. Replacing its first convolution does not automatically exclude invalid regions from later GroupNorm statistics. The claimed 15% overhead is unverified for GQFT; measure it. The repository covers this paper and a later guided-depth extension, so distinguish their architectures.

### P02. Image Inpainting for Irregular Holes Using Partial Convolutions

Guilin Liu, Fitsum A. Reda, Kevin J. Shih, Ting-Chun Wang, Andrew Tao, Bryan Catanzaro. ECCV 2018. [Primary paper](https://arxiv.org/abs/1804.07723), [NVIDIA implementation](https://github.com/NVIDIA/partialconv).

Partial convolution normalizes masked convolution responses and updates the support mask. Inspect `models/partialconv2d.py`: its forward method computes mask support, renormalization and bias correction, and can return the updated mask.

GQFT diagnostic: four 3x3/stride2 max-pool support updates identify whether any valid flow lies on a convolution path. This is not the exact functional validity map of our GroupNorm encoder, nor a confidence measure. In leg00 it admits almost every cell, so it may barely suppress anything.

A true partial-convolution encoder changes the feature operator and needs a separately trained checkpoint. Changing only the mask rule is a frozen diagnostic, not a reproduction of the paper.

### P03. Free-Form Image Inpainting with Gated Convolution

Jiahui Yu, Zhe Lin, Jimei Yang, Xiaohui Shen, Xin Lu, Thomas S. Huang. ICCV 2019. [Primary paper](https://arxiv.org/abs/1806.03589), [author implementation](https://github.com/JiahuiYu/generative_inpainting).

Gated convolution learns a feature-selection gate per channel/location in an inpainting network. `inpaint_ops.py:gen_conv` splits convolution outputs into a feature branch and a sigmoid gate, then multiplies them.

The source uses TensorFlow1-era APIs and neuralgym. It is a conceptual reference, not a package to install into our PyTorch environment. A new 1x1 gate on final GQFT features would be our lightweight adaptation, not the original multi-layer inpainting architecture.

The paper does not establish that GQFT's spatial softmax overfits or that gating solves its history gate. Preserve an unmodified max branch when isolating an attention-side gate; gating features before both pooling branches changes both summaries and needs a different control.

### P04. Guided Feature Selection for Deep Visual Odometry

Fei Xue, Qiuyuan Wang, Xin Wang, Wei Dong, Junqiu Wang, Hongbin Zha. ACCV 2018 acceptance; proceedings are also listed as2019. [Primary paper](https://arxiv.org/abs/1811.09935), [author publication page](https://feixue94.github.io/).

The paper uses separate recurrent translation/rotation branches with context-guided feature selection. It motivates investigating whether one shared spatial summary is suitable for both tasks.

The author-page Code link currently resolves back to the same page; a usable author implementation was not verified. Do not relabel an unrelated dual-branch repository as official or assert that no implementation exists anywhere.

GQFT proposal: inspect translation/yaw error relationships and shared-feature gradients first. Splitting pooling or temporal branches is a later architecture experiment. The paper does not prove our ground prior is suppressing yaw cues or that task gradients currently conflict.

### P05. TartanVO: A Generalizable Learning-based VO

Wenshan Wang, Yaoyu Hu, Sebastian Scherer. CoRL 2020. [Primary paper](https://arxiv.org/abs/2011.00359), [author implementation](https://github.com/castacks/tartanvo).

TartanVO combines flow-based pose estimation, intrinsic conditioning and an up-to-scale objective, reporting transfer from synthetic to real datasets. Inspect `Datasets/utils.py:make_intrinsics_layer`, `TartanVO.py` and `Network/VOFlowNet.py`.

The audited default branch includes legacy Python2 idioms and explicit CUDA calls; the README points to a Python3 branch. The full model would change our front end and training recipe, so it is not a drop-in GQFT replacement.

Calibrated rays are an interesting GQFT input representation. With one fixed camera, however, ray tangents are an affine reparameterization of coordinates already supplied; they do not add previously missing per-sample calibration information. Metric scale still depends on our supervision and assumptions.

### P06. Deep Patch Visual Odometry

Zachary Teed, Lahav Lipson, Jia Deng. NeurIPS 2023. [Primary paper](https://arxiv.org/abs/2208.04726), [author implementation](https://github.com/princeton-vl/DPVO).

DPVO tracks sparse patches using recurrent updates and differentiable bundle adjustment. Inspect `dpvo/net.py`, `dpvo/patchgraph.py` and `dpvo/ba.py`: patch sampling and correspondence weights operate within a geometric optimization system.

The current repository also includes later SLAM work. Its full runtime has CUDA extensions and additional dependencies, beyond our frozen-SEA-RAFT architecture. No model/data downloads or installation were performed.

Patch sampling suggests a possible GQFT spatial-dropout control, but this is our transfer hypothesis. DPVO is not direct evidence that our attention entropy penalty will improve unseen scenes or pass the ambiguity gate. Sparse patch geometry and entropy-regularized global pooling are different mechanisms.

### P07. Geometric Loss Functions for Camera Pose Regression with Deep Learning

Alex Kendall, Roberto Cipolla. CVPR 2017. [Primary paper](https://arxiv.org/abs/1704.00390), [CVF full text](https://openaccess.thecvf.com/content_cvpr_2017/papers/Kendall_Geometric_Loss_Functions_CVPR_2017_paper.pdf), [author explanation](https://alexgkendall.com/blog/have-we-forgotten-about-geometry-in-computer-vision.html).

The paper studies pose losses, reprojection geometry and learned weighting of position/orientation objectives. It motivates checking our supervision contract before compensating with architecture or loss weights.

The author repository `alexgkendall/caffe-posenet` is a legacy PoseNet implementation. Its connection to the exact 2017 geometric-loss variants was not verified; distinguish it from a faithful reproduction of this paper.

GQFT's existing per-sample movement uncertainty head is different from learned task-level homoscedastic loss weights. A scalar motion weight of4 does not establish gradient dominance. No paper or our three validation conflicts establishes analogous training conflicts without a training-split audit.

### P08. How Contextual are Contextualized Word Representations? Comparing the Geometry of BERT, ELMo, and GPT-2 Embeddings

Kawin Ethayarajh. EMNLP-IJCNLP 2019. [Primary paper](https://arxiv.org/abs/1909.00512), [author implementation](https://github.com/kawine/contextual).

The study measures anisotropy and contextual embedding geometry in language models. Inspect `analyze.py`, which computes cosine and variance statistics, and `preprocess.py` for the original extraction workflow.

For GQFT, adopt the measurement idea on saved states: cross-sequence cosine distributions, common mean energy and principal-component spectrum. The language-model findings do not prove that our motion states occupy the same cone. LayerNorm alone does not impose a positive cone or a universal 0.995 similarity level.

The repository's NLP extraction would require irrelevant models/data. Reimplement only the diagnostic statistics around GQFT states; do not run its language-model pipeline. Extraction cost is not zero if GQFT embeddings were never saved.

### P09. All-but-the-Top: Simple and Effective Postprocessing for Word Representations

Jiaqi Mu, Suma Bhat, Pramod Viswanath in the linked arXiv metadata; the work is commonly cited as ICLR 2018. [Primary paper](https://arxiv.org/abs/1702.01417).

The method removes a common mean and selected dominant directions from word vectors. It motivates centered/PCA diagnostic views of GQFT embeddings, not a guaranteed motion-representation repair.

`vyraun/Half-Size` explicitly accompanies Effective Dimensionality Reduction for Word Embeddings, a different paper. Its `algo.py` contains centering/PCA-related operations but hardcoded dimensions and global-mean operations; do not copy it as a faithful 256-D GQFT ABTT implementation. A verified official implementation for P09 was not identified in this audit.

Centering on the same validation samples is a transductive exploratory diagnostic. A deployed transform must be fitted on training/reference data. Report original gate metrics unchanged; centering may reduce the count of cosine-near queries without improving retrieval.

### P10. RankMe: Assessing the Downstream Performance of Pretrained Self-Supervised Representations by Their Rank

Quentin Garrido, Randall Balestriero, Laurent Najman, Yann LeCun. ICML 2023. [Primary paper](https://proceedings.mlr.press/v202/garrido23a.html), [full text](https://proceedings.mlr.press/v202/garrido23a/garrido23a.pdf), [arXiv](https://arxiv.org/abs/2210.02885).

RankMe uses the entropy of normalized singular values to assess representation rank in self-supervised learning. For GQFT, record raw and centered effective rank with singular spectra and actual retrieval/trajectory performance.

The supplied `facebookresearch/RankMe` repository returns404. No official source from that link was inspected; the method can be implemented directly from the paper rather than trusting an unrelated package with the same name.

A 30% relative rank decrease is not a validated collapse criterion for GQFT. Rank alone is insufficient to establish task failure. With 104 samples in256 dimensions, raw algebraic rank cannot exceed 104, and centered rank cannot exceed 103. Compare identical samples, dimensions and preprocessing.

### P11. Deep Fundamental Matrix Estimation — additional geometry reference

René Ranftl and Vladlen Koltun. ECCV 2018. [Author publication page](https://vladlen.info/publications/deep-fundamental-matrix-estimation/), [linked source repository](https://github.com/isl-org/DFE).

The paper learns robust weights for a sequence of weighted homogeneous least-squares estimation problems. It motivates combining learned reliability with an explicit geometric estimator. Our three-variable floor-flow solver is a different objective and camera-motion parameterization; it is not an implementation of fundamental-matrix estimation. The linked repository is archived. Its publication/repository identity was checked; it is not among the eight pinned source snapshots in the November 4 audit and was not installed or executed.

### P12. DROID-SLAM: Deep Visual SLAM for Monocular, Stereo, and RGB-D Cameras — additional geometry reference

Zachary Teed and Jia Deng. NeurIPS 2021. [Primary paper](https://arxiv.org/abs/2108.10869), [author repository](https://github.com/princeton-vl/DROID-SLAM).

DROID-SLAM combines recurrent updates with differentiable dense bundle adjustment for pose/depth estimation. It informs the idea of neural predictions coupled to geometric optimization. Our solver has three planar motion variables and no depth optimization or SLAM graph. Full DROID-SLAM integration would exceed the current frozen-front-end experiment. The paper-linked repository was checked as a reference; it was not installed, executed or included in the pinned source-code audit.

### P13. Transforming Camera Geometry to a Virtual Downward-Looking Camera: Robust Ego-Motion Estimation and Ground-Layer Detection — additional geometry reference

Qifa Ke and Takeo Kanade. CVPR 2003. [CMU primary publication record](https://publications.ri.cmu.edu/transforming-camera-geometry-to-a-virtual-downward-looking-camera-robust-ego-motion-estimation-and-ground-layer-detection), [author-hosted paper](https://www.cs.cmu.edu/~ke/publications/ke_cvpr03.pdf).

The work exploits planar motion and a virtual camera transformation, combining local motion estimates with robust ground/photometric weighting. It supports investigating calibrated ground geometry and checking conditioning. It does not remove our requirement to distinguish floor from walls or verify a fixed height. No official implementation was verified in this review. Our confidence-weighted flow solver is an adaptation, not a reproduction of its image-based algorithm.

### P14. Real-Time Monocular Visual Odometry for On-Road Vehicles with 1-Point RANSAC — additional geometry reference

Davide Scaramuzza, Friedrich Fraundorfer and Roland Siegwart. ICRA 2009. [Author-hosted primary paper](https://rpg.ifi.uzh.ch/docs/ICRA09_scaramuzza.pdf).

The method uses restrictive nonholonomic wheeled-vehicle motion assumptions for efficient outlier rejection, demonstrated with an omnidirectional camera. It motivates making motion constraints explicit, but its one-point model and camera differ from our indoor fixed-rig floor-flow solver. It is not evidence that our solver is unbiased on turns-in-place, side motion or nonplanar floors. No official implementation was verified here.


## 9. Corrections to the supplied research claims

| Claim in the supplied text | Correct interpretation for our project |
| --- | --- |
| Different past paths must produce different terminal states | Neither architecture supervises the last token as a unique full-path identity. Both accumulate increments externally. Different head outputs also do not imply a prescribed cosine separation. |
| Matching local end motion forces identical terminal features | Plausible task-pressure hypothesis; a causal Transformer can retain earlier context. Measure it rather than assume it. |
| LayerNorm causes a narrow positive cone | Not a general property of LayerNorm. Inspect actual cross-sample means and spectra. |
| Rank down 30% proves genuine collapse | Arbitrary threshold; combine spectra, retrieval and motion information tests. |
| Four max-pool stages give exact feature validity | Exact any-valid support along convolution paths, excluding GroupNorm's global dependence. |
| First-layer NConv fixes all later normalization | Not established. Ordinary GroupNorm still uses spatial statistics. |
| Peaked attention proves scene shortcuts | Concentration is measured; dependence on scene-specific nuisance cues needs separate evidence. |
| Centering makes a model pass, therefore fixes it | Coverage of near pairs and nearest-curve quality can change; preserve the original gate and treat alternate signatures as diagnostics. |
| 104 windows give C(104,2) cross-sequence pairs | Same-sequence pairs are excluded. With 26 sequences and 4 windows each, there are 5,200 unique cross-sequence pairs; windows also overlap. |
| H24 terminal features are compared only to the observed trajectory | The current gate uses a 31-point,30-pair full reference, including 6 flow pairs not observed atH24. Report observed-prefix and unobserved-tail contributions. |
| Three validation conflicts establish training gradient corruption | Training frequency and gradients have not been audited. All three known windows belong to one sequence. |
| Failure to improve means freeze inconsistent labels permanently | Correctness of the target/projector contract is separate from short-run accuracy. Validate the physical plane/height convention and compare both scoring protocols. |
| Intrinsic rays add missing calibration for the fixed camera | They reparameterize existing coordinates for a single fixed calibration; varying-camera generalization is a different test. |
| A paper establishes our computational overhead or improvement | GQFT timing, accuracy and gate effects must be measured locally. |

## 10. Visual artifacts, source and handoff

Open [dashboard.html](dashboard.html) to compare the five October checkpoints on episode 629, legs 0/2/3/4, first 24 pairs each. It is self-contained offline HTML with trajectory, ground/pixel error, attention and validation comparisons. There are 41 saved PNGs in the [trained image gallery](trained_episode_overlays/20261019T101035Z_431613/20261019T123632Z/gallery.html). Twenty-nine browser checks were recorded. These are short windows, not complete legs. Solver/hybrid results are not yet included in that dashboard.

The newer gallery identifies its own colors: ground truth magenta, reference cyan, mask green, yaw-local purple, combined orange and original yaw steel. Historical cyan/steel DPVO figures belong to older visualizations and must not be presented as new masked/hybrid outputs.

| Location | Purpose |
| --- | --- |
| Task_2/gqft_algorithm_sharing_vivekananda | Active local model, dataset, solver and tools |
| Task_2/gqft_mask_review | Canonical lab artifacts and this consolidated document |
| research_20261104 | Historical literature review, pinned static sources, citations and exporter |
| pilot_results | October four-arm checkpoints/configuration hashes and validation reports |
| trained_episode_overlays, dashboard | Saved October figures and offline comparison |
| ground_geometry_20261109 | Solver/hybrid recorded CPU checks and exploratory episode scores |
| transfers/20261104_gqft_restore/local_backup | Verified historical server snapshot; not active local source |

The server restoration copied 636 original files (about 1.251 GiB) through local storage to guest-isl@172.26.186.222:/data/robotics/toshith/vivekananda/gqft_algorithm_sharing_vivekananda. Hash/size/mode/time receipts are preserved. The source backup was retained. This receipt establishes the 4 November transfer, not present connectivity or deployment of later changes.

Historical shared server paths: /data/robotics/toshith/rgbd_vo_dataset/hsgm_sequences for HSGM sequences and /data/robotics/toshith/envs/agentvln/bin/python for the working interpreter. Verify current availability before a run. All writes on that server must remain inside the authorized project directory. SEA-RAFT stays frozen; strict loading, fixed camera contract, analytic projection and no-flip policy remain. Preserve released artifacts and shared environments.

This document and its Word/PDF copies are a documentation handoff. They introduce no new model result, code deployment, inference or training. The supporting citation files and source ledger can be updated without altering old experiment evidence.


## Update: 12 November 2026 — motion failure controls

The [motion-fix report](motion_fixes_20261112/README.md) adds five controlled directions to this ledger: per-frame height reconstruction/rerendering, central-floor fitting, far-ray yaw separation, sliding history, and residual/support neural fusion. Central-floor fitting is the only new algorithm control with a clear validation trajectory gain: solver-only13.55→6.41cm over26 sequences, and trained learned weights15.45→4.65px ADE over104 H24 windows (float32). The original history gate still fails. Split yaw and quality fusion regress; sliding has no clear gain. These are frozen experiments, not newly trained models.

The original renderer retains only one agent elevation, so a configured1.2m sensor mount can disagree with actual local floor clearance. Five unambiguous recordings have separate mesh-reconstructed1.2m RGB counterfactuals. Uncertain support in837/1031/1781 and the stair recordings is not guessed. The exact methods, limitations, raw JSON, source, render receipts and visual outputs are linked from the report. P04 motivates task-dependent cue selection; the new solver control is not a reproduction of that paper. This update has not yet been included in the older DOCX/PDF exports.


## Update:13 November2026 — next attempts and mask-image collection

The [14-paper method review and ordered next-attempt plan](SOLVER_REVIEW/research_next_attempts_20261113/index.html) updates the research priorities after the solver experiments. Start with unchanged-protocol/history diagnostics, train/validation label-support auditing and a zero-training spatial-consensus control. Only then consider matched central-floor training, residual-conditioned reliability or a separate confidence-propagating encoder. Existing ray inputs and analytic robust weighting are already implemented. Full physical-height reconstruction remains a separate experiment. The [masked-attention gallery](SOLVER_REVIEW/masked_attention/index.html) collects62 existing October PNGs with source hashes; it is not a new masked-solver result. New plan Word/PDF exports are in that plan folder; older consolidated Word/PDF exports remain historical.
