# GQFT: every approach tried, what happened, and what comes next

Last updated 9 November 2026. Read this first before starting another experiment. Each row links to its evidence, and numbers are copied from saved result files. Where a comparison is weak (one scene, one seed, few windows), the row says so.

## 1. Setup facts that limit every conclusion

| Fact | Value | Consequence |
|---|---|---|
| Training scenes | **4** Matterport3D scenes, 144 sequences × 49 frames, 8 synthetic motion shapes | Learned spatial selection can memorise room layout |
| Validation | 1 scene (D7G3Y4RVNrH), 26 sequences, 104 overlapping windows | Windows are not independent environments |
| Locked test | 1 scene (TbHJrupSAjP), 24 sequences | 9.63 vs 10.09 px is one scene; no significance can be claimed |
| Camera | 960×540, HFOV 135°, height 1.2 m, pitch 30° down, 5 Hz | Fixed rig: floor flow alone determines planar motion (Section 4) |
| Seeds | One per run | No seed variance is known for any result |

History-gate counts are small. Wilson 95% intervals for "ambiguous / close queries": reference 0/17 → 0–18%; yaw-local 4/24 → 7–36%; masked+yaw 5/25 → 9–39%; pretrained yaw 0/8 → 0–32%. The intervals overlap. **The gate cannot currently separate these models.** A pass/fail at 0.05 is not reliable at this sample size.

## 2. Approaches tried (chronological)

| # | Approach | Idea | Result (same protocol only) | Verdict | Evidence |
|---|---|---|---|---|---|
| 1 | Released baseline (mean+max pooling) | Supervisor's reference | Test ADE/FDE **9.631 / 15.847 px**, H24 | Reproduced reference | `gqft_algorithm_sharing_vivekananda/baseline/released_gqft` |
| 2 | Horizontal-flip augmentation (aug_v1, aug_20260909, aug_v2) | More training variety | Training-time val ADE 9.09 → 8.74 px; no locked-test result | **Discontinued**: flips break left/right geometry; project rule now forbids them | `archive/discontinued_flip`, `CURRENT_STATE_REVIEW.md` |
| 3 | Learned spatial attention + max | Let network pick informative cells | Val H24 11.32 → 10.38 px, but test **9.63 → 10.09 px (worse)**; history gate fails (0.143) | Does not generalise across scenes | `results/spatial_attn_val.json` |
| 4 | Attention + yaw head | Extra yaw supervision | Test **8.783 / 13.323 px** at H24; validation-selected history mismatch | Best test number, but one scene, one seed and protocol caveat | `IMPROVEMENTS_TRACKER.md` |
| 5 | Hard validity masking (frozen weights) | Drop unreliable cells from pooling | Episode 629: ground error 7.20 → 12.57 cm (+74.5%); val: 4.49 → 25.11 cm when attention and max are both masked | **Harmful.** Cells over invalid pixels still carry valid neighbour information (31×31 receptive field + GroupNorm) | `gqft_mask_review/ISOLATION_RESULTS.md` |
| 6 | Six-way masking isolation | Which branch is hurt? | Attention-only 6.50 cm, max-only 11.16 cm, both 25.11 cm, restore RF-valid cells 4.76 cm vs original 4.49 cm | Max branch is the most sensitive; no masking beats the original | same |
| 7 | Soft attention weighting (floor 0.25) | Down-weight instead of delete | 4.4917 → 4.4830 cm (−0.19%); bootstrap interval includes zero | No measurable benefit | `gqft_mask_review/SOFT_ATTENTION_RESULTS.md` |
| 8 | Trainable soft masks + yaw-local integration, 4-arm 500-step pilot | Train with reliability priors; rotate local steps by predicted yaw | H24 val ADE: reference 12.46, soft mask 12.83, **yaw-local 11.35**, both 11.81 px; yaw-local fails gate (4/24) | Yaw-local helps ADE; soft mask hurts; gate result not statistically meaningful (Section 1) | `gqft_mask_review/pilot_results/`, `diagnosis_20261104/findings.json` |
| 9 | Attention entropy audit | Is attention collapsing? | Mean 2.3–3.2 effective cells out of 60 | Very concentrated, consistent with layout memorisation (not proven) | `diagnosis_20261104/` |
| 10 | Label geometry audit | Do labels match the 1.2 m projector? | 3/104 val windows (one sequence) off by up to 65.5 px under sequence-floor labels | Real contract mismatch; training-split frequency not yet measured | `analysis/label_geometry_20261009/` |
| 11 | Literature review P01–P10 | Diagnose problems A–E | Ordered diagnostic plan D1–D3 | Done; papers mapped in Section 5 | `gqft_mask_review/research_20261104/GQFT_RESEARCH_REVIEW.md` |
| 12 | **Ground-plane solver (zero training)**, 9 Nov | Fit planar motion to near-floor flow with the known rig | Episode 629, 4 legs: mean ground error 1.6–3.4 cm vs Attention+Yaw 3.0–10.2 cm; wins 3/4 legs | **Most promising lead.** Cutoff (1.5 m) was picked on these same windows, so validation is required | `gqft_mask_review/ground_geometry_20261109/` |
| 13 | **GQFT + ground solver (hybrid mode)**, 9 Nov | Solver supplies each step; Transformer adds a bounded correction; optional learned pixel weights trained through the solver | Implemented, 15/15 CPU checks pass, legacy outputs bit-identical. **Not trained yet** | Ready for validation (Section 6) | `step2/ground_solver.py`, `step2/models/gqft.py` |

| 14 | **Episode error diagnosis**, 9 Nov | Why does GQFT fail on episodes 629/837/1285/1689? Split per-step error by motion type | Episode 629, 4 windows: GQFT step error per step: turn-in-place 0.45 cm (truth 0), fast ≥6 cm 2.37 cm, normal 0.85 cm. Solver: 0.07 / 0.66 / 0.22 cm. During leg00's 8 on-the-spot turn frames GQFT thinks it drove 5.6 cm forward | Main cause is **training-motion mismatch**: HSGM always drives at 0.10–0.36 m/s with smooth turns, while episodes turn on the spot and speed up/slow down. GQFT also undershoots path length (0.66 vs 0.76 m). Full-leg stitching still needs a server run | `tools/episode_diagnosis.py` |

### Why the episodes fail (approach 14)

| Episode motion | HSGM training motion | Effect on GQFT |
|---|---|---|
| Turns on the spot (leg 1 and leg 5 are pure rotation; leg 0 starts with 8 such frames) | Never, except brief pauses in the "stop-go" family | Rotation flow is read as forward motion (5.6 cm phantom drive in 8 frames) |
| Speed varies 0–7 cm per step inside a leg | Constant speed per sequence, 2.0–7.2 cm per step | Fast steps undershot by ~30% (regression to the training mean) |
| Legs of 20–120 frames, run in 24-pair chunks | Windows of up to 30 pairs | At each chunk restart, history drops to 1 pair (training minimum is 2); heading error from each chunk rotates all later chunks |

The flow itself is fine: the solver reaches 1.6–3.4 cm on the same flow. So SEA-RAFT is not the main problem, and nothing points to the Transformer as the bottleneck.

### What the failures have in common

Approaches 3 and 5–9 all tried to make a learned 6×10 pooling stage choose better evidence. Each change stayed within noise, or helped validation and hurt test. With 4 training rooms the network has little reason to learn rig geometry instead of room appearance. Approach 12 uses the geometry directly, and it worked best on the same windows where masking failed.

## 3. Episode 629 numbers (approach 12)

Solver: 6 damped Gauss–Newton steps with soft-L1 weights, floor within 1.5 m, no training. GQFT: frozen Attention+Yaw weights. Errors are ground positions in metres against recorded poses. Window is 24 flow pairs.

| Leg | Motion | Solver mean / end | GQFT mean / end |
|---|---|---|---|
| leg00 | left turn ~68° | **0.016 / 0.038** | 0.102 / 0.280 |
| leg02 | right turn ~84° | **0.018 / 0.030** | 0.071 / 0.233 |
| leg03 | straight | 0.034 / **0.038** | **0.030** / 0.043 |
| leg04 | straight | **0.017 / 0.029** | 0.085 / 0.191 |

Cutoff sensitivity (scipy prototype): 6 m → straight legs overshoot by 35–50% (furniture and walls are closer than the floor, so flow is larger than the floor model predicts); 3 m → 6.7–23 cm; 2 m → 4–10 cm; 1.5 m → 1.5–2.0 cm. **The cutoff must be re-selected on training scenes.** The evaluation tool does this automatically.

Limitations: single episode from separate recordings (not the HSGM benchmark); ground metres, not pixel ADE; heading drifts 10–14° on straight legs; the solver assumes a flat floor and a static scene, and fails when the floor is hidden (it then returns zero motion with weight_sum ≈ 0, which the hybrid exposes to the Transformer).

## 4. Why the geometry works

For a camera at known height h and pitch, a floor pixel's ray hits the floor at a known 3-D point. Planar motion (forward, left, yaw) moves that point predictably, which gives the expected flow. The solver finds the three numbers that best explain the observed SEA-RAFT flow on nearby floor pixels, weighted by SEA-RAFT confidence and validity and by a robust loss. This is the classic planar ego-motion idea (Ke & Kanade 2003; Scaramuzza et al. 2009). Those methods recover translation only up to scale or need extra cues. **Our known 1.2 m height gives metric scale directly.**

It also addresses the earlier problems:
- **A (generalisation):** the geometry is the same in every room.
- **B/C (masking):** reliability acts per flow pixel inside the solver, not on 6×10 CNN cells, so receptive fields and GroupNorm don't interfere.
- **D (yaw):** translation and rotation are separated explicitly.
- **E (labels):** the solver uses the fixed rig, so fixed-rig labels become the consistent choice.

## 5. Papers you supplied (P01–P10) and how they feed the new design

| Paper | What we take | What we do not claim |
|---|---|---|
| P01 Normalized convolution (Eldesokey et al., BMVC 2018) | Confidence should weight evidence *at the estimation step*, not after mixing. The solver's weighted normal equations do this with SEA-RAFT confidence | No NConv encoder was built |
| P02 Partial convolution (Liu et al., ECCV 2018) | Explains masking failure (approach 5): validity spreads through receptive fields | The solver uses pixel validity directly instead |
| P03 Gated convolution (Yu et al., ICCV 2019) | Optional learned per-pixel weight = sigmoid gate (`--ground-learned-weights`), initialised to exactly 1 | Gate is on solver weights, not CNN features |
| P04 Guided feature selection (Xue et al., ACCV 2018) | Separate translation and rotation: the solver estimates both explicitly | Code still unverified |
| P05 TartanVO (Wang et al., CoRL 2020) | Calibrated ray tangents as weight-net inputs (`make_intrinsics_layer` idea) | For one fixed camera this is a reparameterisation, not new information |
| P06 DPVO (Teed et al., NeurIPS 2023) | Main template: learned weights feeding a damped, differentiable Gauss–Newton solve. Our solve has 3 unknowns, so a dense 3×3 solve replaces bundle adjustment | No patch graph or bundle adjustment |
| P07 Kendall & Cipolla (CVPR 2017) | Geometry must match supervision, so pair the solver with fixed-rig labels | No learned task weights added |
| P08 Ethayarajh (EMNLP 2019) | Check anisotropy before trusting raw cosine 0.995 | Diagnostic only; still pending (D1) |
| P09 All-but-the-Top (Mu et al., ICLR 2018) | Centred embeddings as a separately labelled diagnostic | Not a fix |
| P10 RankMe (Garrido et al., ICML 2023) | Effective rank of terminal states as a diagnostic | Official repo 404s; implement from the paper |

New papers for the geometry direction (checked against primary sources on 9 Nov 2026):

| Paper | Link | Relevance |
|---|---|---|
| R. Ranftl, V. Koltun, *Deep Fundamental Matrix Estimation*, ECCV 2018 | [CVF](https://openaccess.thecvf.com/content_ECCV_2018/html/Rene_Ranftl_Deep_Fundamental_Matrix_ECCV_2018_paper.html), code [isl-org/DFE](https://github.com/isl-org/DFE) (archived) | Networks predict robust weights for iterated weighted least squares, trained end to end. Closest precedent for learned solver weights |
| Z. Teed, J. Deng, *DROID-SLAM*, NeurIPS 2021 | [arXiv 2108.10869](https://arxiv.org/abs/2108.10869), code [princeton-vl/DROID-SLAM](https://github.com/princeton-vl/DROID-SLAM) | Confidence-weighted flow residuals inside a differentiable dense bundle adjustment layer |
| Q. Ke, T. Kanade, *Transforming Camera Geometry to a Virtual Downward-Looking Camera: Robust Ego-Motion Estimation and Ground-Layer Detection*, CVPR 2003 | [CMU RI](https://www.ri.cmu.edu/?p=8664) | Planar-motion ego-motion from ground pixels with robust weights; translation only up to scale |
| D. Scaramuzza, F. Fraundorfer, R. Siegwart, *Real-time monocular VO for on-road vehicles with 1-point RANSAC*, ICRA 2009 | [PDF](https://rpg.ifi.uzh.ch/docs/ICRA09_scaramuzza.pdf) | Restricted planar motion model makes estimation cheap and robust |

Possible paper framing: *a fixed-rig, metric, differentiable floor-flow solver inside a learned temporal model, where learned weights replace hand-made masks*. The contribution claims still need validation numbers.

## 6. What to run next, in order

**E0. Episode diagnosis on full legs (CPU, server).** Runs the current deployment, sliding-window GQFT and the solver on all 4 episodes, splitting error by motion type.
```bash
python tools/episode_diagnosis.py --checkpoint runs/gqft_spatial_yaw_v1/best.pt
```
Make decisions on episodes 837/1285/1689 as well as 629. Never train on episode data.

**E1. Plain solver on validation (CPU only, no training, no GPU permission needed).** The cutoff is chosen on training scenes; validation is reported once.
```bash
cd /data/robotics/toshith/vivekananda/gqft_algorithm_sharing_vivekananda
python tools/evaluate_ground_solver.py --manifest results/hsgm_manifest_v1.json --split val \
  --history 24 --target-ground-plane sequence_floor --out results/ground_solver_val_h24_seqfloor.json
python tools/evaluate_ground_solver.py --manifest results/hsgm_manifest_v1.json --split val \
  --history 24 --target-ground-plane fixed_rig --out results/ground_solver_val_h24_fixedrig.json
```
Compare with reference 12.46 px, yaw-local 11.35 px and pretrained yaw 11.69 px at H24. The pilot numbers used sequence-floor labels, so compare like with like.
- **Hypothesis:** solver ADE ≤ 11.35 px.
- **Fails if:** solver ADE > 12.46 px. If so, inspect per-window `min_weight_sum` and errors by motion shape before building on it.

**E2. Hybrid training (needs GPU approval).** Same data, 500-step budget, init and seed as the pilot. Three arms: yaw-local (existing), hybrid, hybrid + learned weights. Three seeds each.
```bash
python step2/train_gqft.py --manifest results/hsgm_manifest_v1.json --out runs/ground_hybrid_s1 \
  --predict-yaw --motion-integration yaw_local --motion-prior ground_solver \
  --ground-max-floor-m <E1 cutoff> --init-checkpoint <pilot init> --reinitialize-motion-heads \
  --steps 500 --seed <s> --allow-gpu
```
- **Fails if:** the hybrid does not beat both the plain solver (E1) and yaw-local on validation ADE in at least 2 of 3 seeds.
- Also report 3-D error, yaw error, history gate with Wilson intervals, and errors per motion shape.

**E3. Fixed-rig vs sequence-floor labels** with the hybrid. Single variable, 3 seeds. The solver's geometry assumes the fixed rig.

**E4. More scenes (needed for publication).** Capture ≥20 training scenes and ≥5 each for validation and test with `step2/capture_hsgm_habitat.py`. Report per-scene results with sequence-bootstrap intervals. A single test scene will not convince reviewers.

**E5. Embedding diagnostics D1** (P08–P10) on saved states. Only needed if the history gate stays part of the paper.

Do not tune the cutoff, residual limits or iterations on the locked test scene. Test once, after the configuration is frozen on validation.

## 7. Files added on 9 November 2026

| File | Purpose |
|---|---|
| `gqft_algorithm_sharing_vivekananda/step2/ground_solver.py` | Differentiable 3-DOF floor-flow solver |
| `step2/models/gqft.py` (edited) | Optional `motion_prior="ground_solver"`; default behaviour bit-identical |
| `step2/checkpoint.py` (edited) | Warm start into the hybrid: only solver modules may be missing; motion heads must be reset |
| `step2/train_gqft.py` (edited) | `--motion-prior`, `--ground-*` options |
| `tools/evaluate_ground_solver.py` | E1 evaluation with train-only cutoff selection and per-window records |
| `gqft_mask_review/ground_geometry_20261109/` | Prototype, episode 629 results, 15 CPU checks (`verification.json`) |
