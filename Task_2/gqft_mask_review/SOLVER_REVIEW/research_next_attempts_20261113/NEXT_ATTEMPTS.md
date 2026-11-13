# Next attempts after reviewing the papers and our evidence

Prepared13 November2026. Start with the [masked-attention image gallery](../masked_attention/index.html) and the [main solver review](../START_HERE.html).

The next work should diagnose the history failure and test geometric support/consensus before another broad attention change. Central-floor selection is our strongest current validation intervention; it is not yet an accepted generalization result. Camera-height reconstruction remains a separate experiment.

## Reading scope and evidence

All14 primary PDFs in our catalogue were retrieved and text-extracted for this review. Their method sections and relevant assumptions were checked against the existing source/implementation audit. This is a method-focused review across all14 papers, **not a claim that all231 pages, references and appendices were read line by line**, and not a reproduction of any external system. The temporary PDFs/text are reading copies, not republished in this package. [Access/hash/page-count receipts](paper_reading_sources.json). The reading map below identifies the inspected method sections.

The paper-to-GQFT adaptations below are proposals. A paper's reported results do not establish their effect on our model. Repository status refers to the pinned4 November audit unless explicitly stated; it is not a new claim that every current upstream version was checked.

## What is already established locally

| Observation | Evidence | Consequence |
| --- | --- | --- |
| Late hard masking can remove useful evidence | Frozen pooling isolation and neighbouring receptive-field support | Do not repeat joint attention/max rejection as the default |
| Frozen soft weighting has only a tiny uncertain effect | Ground mean4.4917→4.4830cm; sequence-bootstrap interval includes zero | This does not justify claiming a practically useful mask improvement |
| Trained soft masking did not improve the matched pilot | Reference12.4626→mask-only12.8267px; yaw-local11.3485→mask+yaw11.8091px | A new neural-mask experiment needs a different mechanism and matched controls |
| Central floor helps validation motion | Learned hybrid ADE15.4479→4.6543px, same104 windows,float32; pure solver13.5467→6.4067cm on26 full sequences | Retain as the primary inference candidate; do not claim new trained weights |
| Long recorded paths remain mixed | Learned full episode62917.88→33.01cm with central floor | Include regressions; do not judge by selected attractive legs |
| The original history gate still fails | Central learned weights ambiguity0.71579 atH24 and0.74227 atH30; no sufficient history | Better trajectories are not proof that temporal signatures encode path identity |
| Three other controls did not establish an overall gain | Far-ray split worse; sliding neutral; residual-only fusion worse overall | Keep these experimental, not defaults |
| Height reconstruction is incomplete | Five complete mesh-support counterfactual recordings; uncertain episodes deferred | Keep1.2m calibration fixed and original-data scores separate |

These protocols differ. October frozen-mask pointwise metrics exclude the origin; the matched trained H24 evaluation includes it. Full48-pair sequence metrics are a third protocol. Do not merge their absolute pixel errors.

## The next attempts, in order

### 1. Freeze the original-data comparison and acceptance rules

Use the exact104 validation windows,26 sequences, H24/reference30, anchor(480,809),960×810 canvas, no flips, strict checkpoint hashes and one declared precision. Keep the seven-history rule and all original metrics. Record the separate48-pair diagnostic separately. Preserve the default original-RGB dashboard; height reconstruction remains Experiment B.

**Deliverable:** an experiment manifest defining checkpoints, windows, constants, precision, query/camera/label conventions and all acceptance metrics before running a new variant. Frozen SEA-RAFT and the analytic projector stay in place. Episode837 is locked-test-scene visualization only; it cannot select parameters. No fitted scale/heading or per-episode choice of the best model is allowed.

### 2. Diagnose the history failure before adding a contrastive loss

**Papers:** P08–P10. Extract full temporal states from the existing yaw-local, original hybrid and central-floor hybrid checkpoints; save all states, predictions, IDs and targets once. Begin withH24 andH30. If those embeddings were not saved, extraction requires a model pass even though it requires no training.

Compare predeclared terminal, temporal-mean and middle+terminal signatures. Report original raw-terminal results unchanged, plus separately labelled centered/PCA diagnostics. Measure raw/centered singular spectra, effective rank, common-mean energy, cross-sequence cosine distribution, nearest-neighbour identities, observed-prefix curve gap and full-reference curve gap. Print all flagged pairs with final local motion and earlier trajectory differences.

AtH24, the reference has six unobserved future pairs; atH30 it does not. BecauseH30 also fails, unseen future motion cannot be the entire explanation. Report eligible queries, cosine-near query count and ambiguous count separately:68/95 near queries is not68/104. Zero near queries is not a successful retrieval result.

**Decision:** temporal pooling improving observed-path retrieval supports a signature mismatch; centering improving neighbour quality supports a common-mode effect. Neither automatically proves collapse or repairs deployment. With104 vectors, raw matrix rank is at most104, not256; centering reduces the maximum further. Do not adopt a30% rank-drop threshold as proof. Fit any deployable centering/PCA transform on training/reference embeddings, not the scored validation set. Keep the original acceptance rule unless its intended task is explicitly revised and revalidated.

### 3. Audit floor/label consistency and solver support on train and validation

**Papers:** P07,P05,P13. Check the actual training frequency of sequence-floor versus fixed-rig label conflicts, camera clearances and variable-height sequences. The previous3/104 conflicting validation windows all belong to one sequence and do not establish training contamination. Measure losses and shared-parameter gradient contributions; a scalar motion weight4 does not prove motion supervision dominates.

For solver failures, record flow validity/confidence, support area and image distribution, residual quantiles, effective support, scaled normal-matrix singular values/conditioning, estimated yaw/translation and errors by motion family. A low residual can still correspond to a well-fitted wrong wall plane, so support and residual must not be treated as semantic floor truth.

**Decision:** resolve a demonstrable coordinate/label inconsistency first, with preserved originals and separately declared scoring. For stairs/upstairs, recover the original3-D pose trace or verify floor support; the2-D X/Z/yaw NPZ cannot recover missing elevation. Do not alter camera height to fit prediction errors. A label-consistency training experiment is separate from an architecture experiment.

### 4. First new algorithm attempt: spatial consensus and conditioning-aware floor fitting

**Papers:** P13, informed by P11/P06. Keep the successful central-floor rule as the control. Partition usable support into fixed spatial patches, estimate local planar motions where sufficiently observable, and combine them using motion agreement, support distribution and conditioning. Compare against our existing joint robust solver. Use training data/synthetic cases to fix thresholds before validation.

Our solver already has confidence/validity weights and residual-based IRLS. Adding an ordinary robust loss is not new. The new variable is **agreement among independently supported spatial regions**, rather than a single all-pixel fit or a manually distant yaw region. Normalize parameter units before interpreting a condition number. Report how much support is discarded and how often a hypothesis cannot be formed. Texture/ground-normal cues in P13's direct RGB method are not automatically available from our flow-only inputs; a flow-based patch consensus is our adaptation, not its reproduction.

**Pass/fail:** paired improvements in ground/yaw error over the whole declared validation cohort, no hidden empty/negative-depth failures, acceptable latency, and improvements on supported planar sequences rather than one629 window. Use sequence-level uncertainty. Include all failures. This is a zero-training prototype first; it is not a guaranteed fix for stairs.

### 5. Then test central-floor-aware training with matched seeds

The strong central-floor result was an inference intervention on weights trained with the original rule. Prepare a matched two-arm pilot: original learned-weight solver versus the same model with central-floor support during training. Use identical initialization, data order, labels, budget, schedule and seeds42/43/44. Retain the frozen runtime-intervention and yaw-local reference as evaluation controls. Do not simultaneously change masks, yaw semantics, labels and losses.

**Pass/fail:** consistent ADE/metric-error improvement across seeds without a new failure in the original history acceptance rule or numerical stability. State clearly if trajectory accuracy improves but acceptance still fails. Budget and GPU must be agreed for the actual training launch; this review starts no training.

The current validation evidence repeatedly uses one house. For cross-scene evidence, acquire an independent non-test development scene or perform a declared leave-one-training-house-out study. A checkpoint already trained on that held-out house cannot initialize a supposedly unseen-house evaluation. Do not use locked-test837 to choose the architecture or training length.

### 6. If reliability remains the bottleneck, test one new learned mechanism

**Geometry route, P11/P06/P12:** compare existing input-only learned pixel weights against residual-conditioned iterative weights. The current weight network consumes flow,confidence,validity and calibrated rays once; robust residual reweighting is analytic inside the iterations. A new learner could condition on current fit residuals and global/patch context before another solve. Hold the number of solves and parameter budget under control, constrain finite positive weights and report spatial concentration. This requires matched training and numerical-gradient checks; it is not already implemented by the existing learned-weight arm.

**Neural-mask route, P01/P02/P03:** separately compare the current attention+max encoder with one confidence-propagating or partial-convolution operator. Propagate support through the encoder and explicitly account for normalization statistics. A first-layer replacement alone does not fix later GroupNorm dependence; changing only the final6×10 mask is not partial convolution. Retraining is necessary. NConv's nonnegative applicability assumptions also need examination for signed flow/features.

For a cheaper gate/entropy/dropout control, keep the original max branch intact and change only the attention branch, one variable per arm. Any dropout mask must preserve temporal comparability; choose its rule and regularization coefficient on training/development data. P03/DPVO do not establish a universal20% dropout rate,1.5-nat entropy target or guaranteed gain for GQFT. Do not combine the geometry and neural-mask routes in the first test.

### 7. Only after evidence of task interference, try context-guided motion branches

**Paper:** P04. Compare a parameter-matched shared representation with separate translation/yaw feature selection conditioned causally on predicted prior state. Preserve the frozen flow frontend and camera/projector contracts. Measure yaw and translation separately and verify that branch conditioning uses no ground-truth motion at inference.

This is different from our already-tested “far rays for yaw” heuristic, which regressed. The paper motivates learned context-specific selection; it does not say that every high-image ray observes a distant surface. P07 also reports a setting where shared pose features were better than splitting, so dual branches are a hypothesis, not a universal rule.

### 8. For long-trajectory drift, consider independent multi-frame constraints later

**Papers:** P06/P12. A short pose/patch optimization can use correspondences spanning several frames and explicit geometry. Reoptimizing only the same adjacent-frame increments, or sliding the Transformer over the same last24 pairs, adds no independent measurement that guarantees drift removal. New cross-frame tracks/flow would be a separately measured experiment, with visibility, metric gauge and latency explicit.

Full DPVO/DROID-SLAM replacement changes the architecture, frontend/runtime and evaluation scope; it is not an immediate GQFT patch. Keep it behind the simpler consensus and representation checks.

## Paper-by-paper reading map and implementation implication

Each numbered paragraph is a concise, method-focused interpretation. Primary links allow checking the original assumptions. None of the transfer proposals below is a reproduced result for our dataset.

1. **P01 — Propagating Confidences through CNNs for Sparse Data Regression.** Inspected§3.1–3.3, PDFpp4–5: normalized convolution uses nonnegative applicability, confidence-weighted normalization and propagated confidence. Applicable to an early encoder-operator experiment, not merely a final attention bias. The sparse-depth task differs from signed flow features, and normalization can still mix locations. Author source `NConv2d.forward` was inspected; its legacy weight enforcement/private PyTorch APIs are not a drop-in dependency. [Paper](https://arxiv.org/abs/1805.11913), [author code](https://github.com/abdo-eldesokey/nconv).

2. **P02 — Image Inpainting for Irregular Holes Using Partial Convolutions.** Inspected§3.1–3.2, PDFpp5–6: valid-only convolution is rescaled and the support mask expands when any valid input exists. This justifies testing an actual mask-aware encoder, while warning that binary support can quickly become nearly all-valid. Four support-pooling stages describe convolution paths, not all GroupNorm dependence or semantic reliability. NVIDIA's `PartialConv2d.forward` provides mask-ratio and bias-correction details. [Paper](https://arxiv.org/abs/1804.07723), [author code](https://github.com/NVIDIA/partialconv).

3. **P03 — Free-Form Image Inpainting with Gated Convolution.** Inspected§3.1, PDFpp3–4: separate learned feature/gate filters produce channel/location-dependent selection. A lightweight attention-side sigmoid gate is a plausible GQFT adaptation, but differs from the multi-layer inpainting network and its GAN objective. It does not prove our observed attention concentration causes overfitting. The pinned `gen_conv` source is legacy TensorFlow, not a PyTorch module to install. [Paper](https://arxiv.org/abs/1806.03589), [author code](https://github.com/JiahuiYu/generative_inpainting).

4. **P04 — Guided Feature Selection for Deep Visual Odometry.** Inspected§3.1–3.3, PDFpp5–8: spatial feature maps feed separate motion branches; previous recurrent outputs guide channel or spatial feature selection. This motivates causal task-specific gates after diagnosis. It is not fixed geometric far/near splitting, and an exact official implementation was not verified in the pinned audit. [Paper](https://arxiv.org/abs/1811.09935).

5. **P05 — TartanVO.** Inspected§3.3–3.4, PDFpp3–5: up-to-scale translation supervision and intrinsic-ray channels address data/camera generalization. GQFT needs metric scale and keeps its calibrated1.2m contract; changing to an up-to-scale objective is not an interchangeable evaluation. Calibrated rays are already input to our solver's learned-weight network. With one fixed calibration, replacing generic coordinates by rays adds no new per-sample calibration information. [Paper](https://arxiv.org/abs/2011.00359), [author code](https://github.com/castacks/tartanvo).

6. **P06 — Deep Patch Visual Odometry.** Inspected§3, PDFpp3–6: sampled patches, recurrent correspondence corrections and confidence-weighted differentiable bundle adjustment cooperate. This motivates spatial coverage and geometric consistency; it does not isolate entropy regularization as the cause of transfer. Its monocular pose training uses scale alignment; our metric validation does not. The full pipeline is not a replacement for a pooling layer. [Paper](https://arxiv.org/abs/2208.04726), [author code](https://github.com/princeton-vl/DPVO).

7. **P07 — Geometric Loss Functions for Camera Pose Regression.** Inspected§3.3.2–3.3.4, PDFpp4–5: task-level uncertainty balances pose losses and geometric reprojection couples their effects. Use it to motivate checking consistent supervision and actual gradient scales. GQFT's per-sample motion log-variance is different from learned task-level constants. No paper removes contradictory label geometry automatically. The audited legacy PoseNet repository is not a verified exact implementation of all2017 variants. [Paper](https://arxiv.org/abs/1704.00390).

8. **P08 — How Contextual are Contextualized Word Representations?** Inspected§3–4, PDFpp3–4: cosine/contextuality statistics are interpreted relative to anisotropy baselines. Transfer the measurement procedure to our states; do not transfer language-model cosine values as a universal motion-model fact. LayerNorm does not by itself force a positive cone. Inspect the author analysis code rather than running an irrelevant NLP model. [Paper](https://arxiv.org/abs/1909.00512), [author code](https://github.com/kawine/contextual).

9. **P09 — All-but-the-Top.** Inspected§2.1/Algorithm1, PDFp4: remove a common mean and selected leading PCA directions. Use only as a separately labelled representation diagnostic until a transform is fitted on training/reference data. Reduced cosine-near coverage alone does not mean improved retrieval. The supplied Half-Size repository belongs to a different paper and is not a verified ABTT implementation. The linked final ICLR PDF lists Mu/Viswanath, while earlier catalogue metadata included Bhat; retain version-aware attribution. [Paper](https://arxiv.org/abs/1702.01417).

10. **P10 — RankMe.** Inspected§3.1, PDFpp3–4: effective rank is the exponential entropy of normalized singular values. The paper explicitly cautions that rank is not the only performance factor and compares runs of a given method. Use it alongside retrieval/motion measurements, not as a universal model-selection score across architectures or proof of collapse. The supplied repository was404 in the historical audit; implement and verify the statistic from the formula. [Paper](https://proceedings.mlr.press/v202/garrido23a.html).

11. **P11 — Deep Fundamental Matrix Estimation.** Inspected§4 and Algorithm1, PDFpp5–8: learn weights from correspondences,side information and current residuals, alternating with differentiable weighted fitting. Our current neural weights are input-only; their residual-conditioned extension is a concrete distinct experiment. The paper's homogeneous SVD estimator is not our nonlinear planar Gauss-Newton solver, so it is a design reference rather than copied mathematics. [Paper](https://vladlen.info/papers/deep-fundamental.pdf), [author implementation](https://github.com/isl-org/DFE).

12. **P12 — DROID-SLAM.** Inspected§3.1–3.2, PDFpp3–5: a frame graph, recurrent flow revisions and confidence/damping guide joint pose/depth optimization. Useful lesson: use feedback and independent multi-view constraints. Our residual-only neural fallback and rolling context are not equivalent to this system. Full dense bundle adjustment needs additional geometry/state/runtime; preserve it as a later separate project scope. [Paper](https://arxiv.org/abs/2108.10869), [author code](https://github.com/princeton-vl/DROID-SLAM).

13. **P13 — Virtual downward-looking camera / ground-layer detection.** Inspected§2–4.1, PDFpp2–5: fixed calibrated virtual geometry improves local planar-motion conditioning; local patch estimates and geometry/intensity weighting reject non-ground contributions. This directly motivates the next spatial-consensus diagnostic. Its direct RGB residuals and refined plane normals are not already present in our flow-only solver. Virtual coordinate conditioning is not physical camera-height adjustment, and metric scale still needs a valid known height. [Paper](https://publications.ri.cmu.edu/storage/publications/pub_files/pub4/ke_qifa_2003_1/ke_qifa_2003_1.pdf).

14. **P14 — On-road VO with1-point RANSAC.** Inspected§III–IV, PDFpp2–4: an Ackermann/circular-motion model reduces the essential-matrix problem and enables efficient consensus. The model assumes a specific relation between translation and yaw and appropriate camera placement. GQFT includes turn-in-place and reconstructed/nonplanar recordings, so imposing that one-point vehicle model blindly is inappropriate. Transfer the consensus-testing idea, not the unverified kinematic restriction. [Paper](https://rpg.ifi.uzh.ch/docs/ICRA09_scaramuzza.pdf).

## What we should not repeat next

- Hard-reject both late CNN pooling branches and expect the masked model to adapt without training.
- Treat far ray-ground intersection as measured distant-object depth.
- Add calibrated rays or a robust residual loss as though our solver lacks them.
- Tune camera height, floor masks or checkpoint choice on episode629 or locked-test837.
- Claim that a lower conditional ambiguity fraction proves improvement if near-query coverage collapses.
- Add contrastive loss merely to cross0.995 without checking whether its signature/target pair measures the intended observed trajectory.
- Start long multi-change training or replace the full frontend with a paper's VO/SLAM package before a controlled local comparison.

**Immediate recommendation:** run attempts1–3, then a zero-training spatial-consensus prototype. Use the resulting evidence to choose the first matched training comparison. The mask image collection is historical evidence, not a claim that masking currently beats the solver.
