# GQFT research review and implementation plan

Prepared 4 November 2026. Scope: the ten papers supplied in this discussion, their implementation sources, our measured GQFT failures, and the next controlled diagnostics. This document is the reference to read before starting another experiment.

**12 November handoff:** This is the historical4 November literature review. Its checked paper catalogue is now incorporated into the [consolidated approaches/research document](../GQFT_APPROACHES_AND_RESEARCH.md), with [Word](../GQFT_APPROACHES_AND_RESEARCH.docx), [PDF](../GQFT_APPROACHES_AND_RESEARCH.pdf), [citation JSON](papers.json), [BibTeX](papers.bib), [source ledger](REPOSITORY_IMPLEMENTATIONS.md) and [verification](verification.json). These exports were completed12 November. Read the consolidated document for the newer9 November solver/hybrid status and protocol blockers; the earlier ordering below is preserved as history.

## 1. Decision and reading order

Start with the representation diagnostic papers P08–P10, then supervision consistency P07, then reliability propagation P01–P03. P04–P06 inform later architecture proposals. A cited paper motivates a test; it does not establish the cause of our GQFT results.

The next work is saved-checkpoint analysis, followed by a train/validation label audit. Architecture changes and training come after those results. No new model diagnostics or training were launched while compiling this document. The earlier saved-result audit remains preserved separately.

Two implementation corrections were verified: `facebookresearch/RankMe` returns HTTP 404, and `vyraun/Half-Size` is code for a different paper, not the official All-but-the-Top release. Guided Feature Selection's author-page Code link returns to the same page rather than a verified implementation.

## 2. Our GQFT architecture

GQFT means Geometry-Constrained Query Flow Transformer. It estimates a camera trajectory from observed optical flow and projects the estimate into the initial image.

```text
RGB frame pairs
  -> frozen SEA-RAFT
  -> horizontal/vertical flow, confidence, validity [T,4,90,160]
  -> append x/y coordinates [T,6,90,160]
  -> four Conv3x3(stride2)-GroupNorm-GELU blocks
     channels 6 -> 32 -> 64 -> 128 -> 256
     grid 90x160 -> 45x80 -> 23x40 -> 12x20 -> 6x10
  -> spatial pooling: average+max OR learned-attention+max
  -> concatenate pooled vectors; Linear 512 -> 256
  -> learned time embeddings
  -> causal Transformer: 4 layers, 8 heads, width256, FFN1024
  -> displacement head 256 -> 256 -> 3
  -> optional yaw head 256 -> 128 -> 1
  -> uncertainty head 256 -> 128 -> 3
  -> integrate movement increments
  -> calibrated ground-anchor projection -> image path

Pixel query -> geometric anchor and separate query-conditioned validity branch
```

The pixel query does not condition the temporal motion states in this implementation. Original increments are already supervised in the initial camera frame, making direct cumulative summation consistent. The optional yaw-local mode changes the head's coordinate convention and rotates local increments by previous predicted cumulative yaw before accumulation. Both modes integrate increments outside the Transformer.

Reference source: [model and heads](../../gqft_algorithm_sharing_vivekananda/step2/models/gqft.py), [projection](../../gqft_algorithm_sharing_vivekananda/step2/geometry.py), [history retrieval](../../gqft_algorithm_sharing_vivekananda/step2/history_study.py).

## 3. Evidence we already have

### 3.1 Completed training pilot

Four matched arms trained for 500 steps with identical reset motion/uncertainty heads, seed, labels, optimizer and data recipe. All arms predict yaw. The original pretrained yaw model retains its trained heads and a different budget; it is an operational reference, not a matched training arm.

Fixed validation: 104 overlapping windows, 26 sequences, one validation scene D7G3Y4RVNrH, one extended anchor, reference horizon30, input history24, sequence-floor labels, CUDA bfloat16 autocast. Pixel ADE includes the origin. These results are not the separate episode629 diagnostic windows.

| Model | H24 ADE px | H24 FDE px | Ambiguous / close queries | Selected history |
| --- | ---: | ---: | ---: | ---: |
| Trained reference | 12.4626 | 17.4344 | 0 / 17 | 16 |
| Soft mask only | 12.8267 | 18.8231 | 0 / 18 | 20 |
| Yaw-local only | 11.3485 | 13.3930 | 4 / 24 | None |
| Soft mask + yaw-local | 11.8091 | 14.1293 | 5 / 25 | None |
| Original pretrained yaw | 11.6926 | 15.3060 | 0 / 8 | 16 |

The official gate's ambiguity is conditional on cosine-near retrieved queries: yaw-local is 4/24 = 0.1667. Four flagged queries out of all104 is 0.0385, but that different denominator does not make the model pass the official gate. Queries are not necessarily unique unordered pairs. Selected histories were tested among 4,8,12,16,20,24,30.

### 3.2 Masking and attention diagnosis

Earlier frozen-weight isolation demonstrated that masking max pooling causes a larger individual regression than masking attention, and that reinstating rejected cells with valid convolution support recovers much of the hard-mask regression. Those findings support cue removal and pooling-distribution mismatch; they do not prove every removed feature was useful only because of neighbouring pixels.

The new saved-array audit on episode629 leg00 finds coarse coverage retains 80.49% of feature cells, while any-valid convolution-path support covers 99.72%. About19.24% of all feature cells are rejected by the coarse rule despite having some valid input along a convolution path. Any-valid support says information can reach a cell, not that the feature is reliable. GroupNorm adds spatial dependence beyond the 31x31 direct-convolution footprint.

Attention entropy measured on 96 flow pairs from four episode629 windows:

| Model | Mean entropy nats | Mean effective attention cells | Mean largest-cell mass |
| --- | ---: | ---: | ---: |
| Trained reference | 0.9458 | 2.964 | 0.705 |
| Soft mask only | 0.9813 | 2.992 | 0.699 |
| Yaw-local only | 0.7463 | 2.267 | 0.758 |
| Soft mask + yaw-local | 0.7680 | 2.426 | 0.761 |
| Original pretrained yaw | 1.0176 | 3.168 | 0.696 |

Uniform attention over60 cells has entropy log(60)=4.094. Attention is concentrated here, but concentration alone does not demonstrate scene overfitting or representation collapse. These are one episode's diagnostic windows, not independent environments or a validation entropy benchmark.

### 3.3 Geometry and audit status

The exact-motion projection oracle found three inconsistent validation windows, all overlapping windows of sequence `hsgm_D7G3Y4RVNrH_val_v023`, with a maximum65.5247px discrepancy. Matching the annotation height reduces the maximum to approximately0.000126px. This establishes a target/projector contract mismatch. The frequency and gradient effect in the training split have not yet been measured.

The project backup has been restored and all636 original files passed SHA-256 verification. Shared validation inputs are available. Full validation-state embeddings have not yet been extracted for the proposed rank/centering/pooling audit; no result about GQFT representation collapse can be claimed yet.

Internal evidence: [pilot report](../pilot_results/20261019T101035Z_431613/validation_20261019T104120Z/REPORT.md), [saved-array findings](../diagnosis_20261104/findings.json), [mask isolation](../ISOLATION_RESULTS.md), [geometry oracle](../../gqft_algorithm_sharing_vivekananda/analysis/label_geometry_20261009/oracle_geometry.json), [restoration receipt](../transfers/20261104_gqft_restore/destination_verification.json).

## 4. Paper catalogue and GQFT relevance

### P01. Propagating Confidences through CNNs for Sparse Data Regression

Abdelrahman Eldesokey, Michael Felsberg, Fahad Shahbaz Khan. BMVC2018. [Primary paper](https://arxiv.org/abs/1805.11913), [author repository](https://github.com/abdo-eldesokey/nconv).

The method couples confidence-aware normalized convolution with propagated confidence, evaluated for sparse depth regression. It motivates testing reliability inside the encoder rather than rejecting already mixed features at its output.

Read `modules/nconv.py`, especially `NConv2d.forward` and `EnforcePos`. The denominator uses confidence and nonnegative applicability weights; confidence is propagated to the next layer. Source is legacy PyTorch, including private `_ConvNd` usage and `.data` weight updates. A modern adaptation requires explicit numerical and gradient checks.

GQFT proposal: a separately configured confidence-aware encoder experiment. Replacing its first convolution does not automatically exclude invalid regions from later GroupNorm statistics. The claimed15% overhead is unverified for GQFT; measure it. The repository covers this paper and a later guided-depth extension, so distinguish their architectures.

### P02. Image Inpainting for Irregular Holes Using Partial Convolutions

Guilin Liu, Fitsum A. Reda, Kevin J. Shih, Ting-Chun Wang, Andrew Tao, Bryan Catanzaro. ECCV2018. [Primary paper](https://arxiv.org/abs/1804.07723), [NVIDIA implementation](https://github.com/NVIDIA/partialconv).

Partial convolution normalizes masked convolution responses and updates the support mask. Inspect `models/partialconv2d.py`: its forward method computes mask support, renormalization and bias correction, and can return the updated mask.

GQFT diagnostic: four 3x3/stride2 max-pool support updates identify whether any valid flow lies on a convolution path. This is not the exact functional validity map of our GroupNorm encoder, nor a confidence measure. In leg00 it admits almost every cell, so it may barely suppress anything.

A true partial-convolution encoder changes the feature operator and needs a separately trained checkpoint. Changing only the mask rule is a frozen diagnostic, not a reproduction of the paper.

### P03. Free-Form Image Inpainting with Gated Convolution

Jiahui Yu, Zhe Lin, Jimei Yang, Xiaohui Shen, Xin Lu, Thomas S. Huang. ICCV2019. [Primary paper](https://arxiv.org/abs/1806.03589), [author implementation](https://github.com/JiahuiYu/generative_inpainting).

Gated convolution learns a feature-selection gate per channel/location in an inpainting network. `inpaint_ops.py:gen_conv` splits convolution outputs into a feature branch and a sigmoid gate, then multiplies them.

The source uses TensorFlow1-era APIs and neuralgym. It is a conceptual reference, not a package to install into our PyTorch environment. A new 1x1 gate on final GQFT features would be our lightweight adaptation, not the original multi-layer inpainting architecture.

The paper does not establish that GQFT's spatial softmax overfits or that gating solves its history gate. Preserve an unmodified max branch when isolating an attention-side gate; gating features before both pooling branches changes both summaries and needs a different control.

### P04. Guided Feature Selection for Deep Visual Odometry

Fei Xue, Qiuyuan Wang, Xin Wang, Wei Dong, Junqiu Wang, Hongbin Zha. ACCV2018 acceptance; proceedings are also listed as2019. [Primary paper](https://arxiv.org/abs/1811.09935), [author publication page](https://feixue94.github.io/).

The paper uses separate recurrent translation/rotation branches with context-guided feature selection. It motivates investigating whether one shared spatial summary is suitable for both tasks.

The author-page Code link currently resolves back to the same page; a usable author implementation was not verified. Do not relabel an unrelated dual-branch repository as official or assert that no implementation exists anywhere.

GQFT proposal: inspect translation/yaw error relationships and shared-feature gradients first. Splitting pooling or temporal branches is a later architecture experiment. The paper does not prove our ground prior is suppressing yaw cues or that task gradients currently conflict.

### P05. TartanVO: A Generalizable Learning-based VO

Wenshan Wang, Yaoyu Hu, Sebastian Scherer. CoRL2020. [Primary paper](https://arxiv.org/abs/2011.00359), [author implementation](https://github.com/castacks/tartanvo).

TartanVO combines flow-based pose estimation, intrinsic conditioning and an up-to-scale objective, reporting transfer from synthetic to real datasets. Inspect `Datasets/utils.py:make_intrinsics_layer`, `TartanVO.py` and `Network/VOFlowNet.py`.

The audited default branch includes legacy Python2 idioms and explicit CUDA calls; the README points to a Python3 branch. The full model would change our front end and training recipe, so it is not a drop-in GQFT replacement.

Calibrated rays are an interesting GQFT input representation. With one fixed camera, however, ray tangents are an affine reparameterization of coordinates already supplied; they do not add previously missing per-sample calibration information. Metric scale still depends on our supervision and assumptions.

### P06. Deep Patch Visual Odometry

Zachary Teed, Lahav Lipson, Jia Deng. NeurIPS2023. [Primary paper](https://arxiv.org/abs/2208.04726), [author implementation](https://github.com/princeton-vl/DPVO).

DPVO tracks sparse patches using recurrent updates and differentiable bundle adjustment. Inspect `dpvo/net.py`, `dpvo/patchgraph.py` and `dpvo/ba.py`: patch sampling and correspondence weights operate within a geometric optimization system.

The current repository also includes later SLAM work. Its full runtime has CUDA extensions and additional dependencies, beyond our frozen-SEA-RAFT architecture. No model/data downloads or installation were performed.

Patch sampling suggests a possible GQFT spatial-dropout control, but this is our transfer hypothesis. DPVO is not direct evidence that our attention entropy penalty will improve unseen scenes or pass the ambiguity gate. Sparse patch geometry and entropy-regularized global pooling are different mechanisms.

### P07. Geometric Loss Functions for Camera Pose Regression with Deep Learning

Alex Kendall, Roberto Cipolla. CVPR2017. [Primary paper](https://arxiv.org/abs/1704.00390), [CVF full text](https://openaccess.thecvf.com/content_cvpr_2017/papers/Kendall_Geometric_Loss_Functions_CVPR_2017_paper.pdf), [author explanation](https://alexgkendall.com/blog/have-we-forgotten-about-geometry-in-computer-vision.html).

The paper studies pose losses, reprojection geometry and learned weighting of position/orientation objectives. It motivates checking our supervision contract before compensating with architecture or loss weights.

The author repository `alexgkendall/caffe-posenet` is a legacy PoseNet implementation. Its connection to the exact2017 geometric-loss variants was not verified; distinguish it from a faithful reproduction of this paper.

GQFT's existing per-sample movement uncertainty head is different from learned task-level homoscedastic loss weights. A scalar motion weight of4 does not establish gradient dominance. No paper or our three validation conflicts establishes analogous training conflicts without a training-split audit.

### P08. How Contextual are Contextualized Word Representations? Comparing the Geometry of BERT, ELMo, and GPT-2 Embeddings

Kawin Ethayarajh. EMNLP-IJCNLP2019. [Primary paper](https://arxiv.org/abs/1909.00512), [author implementation](https://github.com/kawine/contextual).

The study measures anisotropy and contextual embedding geometry in language models. Inspect `analyze.py`, which computes cosine and variance statistics, and `preprocess.py` for the original extraction workflow.

For GQFT, adopt the measurement idea on saved states: cross-sequence cosine distributions, common mean energy and principal-component spectrum. The language-model findings do not prove that our motion states occupy the same cone. LayerNorm alone does not impose a positive cone or a universal0.995 similarity level.

The repository's NLP extraction would require irrelevant models/data. Reimplement only the diagnostic statistics around GQFT states; do not run its language-model pipeline. Extraction cost is not zero if GQFT embeddings were never saved.

### P09. All-but-the-Top: Simple and Effective Postprocessing for Word Representations

Jiaqi Mu, Suma Bhat, Pramod Viswanath in the linked arXiv metadata; the work is commonly cited as ICLR2018. [Primary paper](https://arxiv.org/abs/1702.01417).

The method removes a common mean and selected dominant directions from word vectors. It motivates centered/PCA diagnostic views of GQFT embeddings, not a guaranteed motion-representation repair.

`vyraun/Half-Size` explicitly accompanies Effective Dimensionality Reduction for Word Embeddings, a different paper. Its `algo.py` contains centering/PCA-related operations but hardcoded dimensions and global-mean operations; do not copy it as a faithful256-D GQFT ABTT implementation. A verified official implementation for P09 was not identified in this audit.

Centering on the same validation samples is a transductive exploratory diagnostic. A deployed transform must be fitted on training/reference data. Report original gate metrics unchanged; centering may reduce the count of cosine-near queries without improving retrieval.

### P10. RankMe: Assessing the Downstream Performance of Pretrained Self-Supervised Representations by Their Rank

Quentin Garrido, Randall Balestriero, Laurent Najman, Yann LeCun. ICML2023. [Primary paper](https://proceedings.mlr.press/v202/garrido23a.html), [full text](https://proceedings.mlr.press/v202/garrido23a/garrido23a.pdf), [arXiv](https://arxiv.org/abs/2210.02885).

RankMe uses the entropy of normalized singular values to assess representation rank in self-supervised learning. For GQFT, record raw and centered effective rank with singular spectra and actual retrieval/trajectory performance.

The supplied `facebookresearch/RankMe` repository returns404. No official source from that link was inspected; the method can be implemented directly from the paper rather than trusting an unrelated package with the same name.

A30% relative rank decrease is not a validated collapse criterion for GQFT. Rank alone is insufficient to establish task failure. With104 samples in256 dimensions, raw algebraic rank cannot exceed104, and centered rank cannot exceed103. Compare identical samples, dimensions and preprocessing.

## 5. Repository inspection ledger

Nine repositories were checked through the public GitHub API. Eight were reachable and small selected files were saved for static reading at pinned revisions. One returned404. No external source was installed, imported, executed or merged into active GQFT.

| Reference | Repository / source | Status | GQFT reuse assessment |
| --- | --- | --- | --- |
| P01 | abdo-eldesokey/nconv | Author code; layer inspected | Port formula/operator carefully; legacy internals |
| P02 | NVIDIA/partialconv | Author/company code; layer inspected | Clear mask update and normalization reference |
| P03 | JiahuiYu/generative_inpainting | Author code; gen_conv inspected | Concept only; TensorFlow1 implementation |
| P04 | Fei Xue publication-page Code link | Self-link; implementation unverified | Paper-driven design only until code is located |
| P05 | castacks/tartanvo | Author code; intrinsics/VO files inspected | Representation reference; full runtime changes scope |
| P06 | princeton-vl/DPVO | Author code; net/patchgraph/BA inspected | Geometric reference; not a lightweight pooling replacement |
| P07 | alexgkendall/caffe-posenet | Author legacy PoseNet code | Exact2017 loss reproduction unverified |
| P08 | kawine/contextual | Author code; analyze.py inspected | Reuse statistical ideas on our saved states |
| P09 | vyraun/Half-Size | Related different paper; algo.py inspected | Not official ABTT; no direct copy |
| P10 | facebookresearch/RankMe | HTTP404 | Derive a tested statistic from the paper |

Exact commit hashes, source URLs, file hashes and license records are in [repository_audit.json](repository_audit.json). Original license files are preserved with the small source snapshots where present. Unidentified licenses and API NOASSERTION records are left explicit rather than guessed.

## 6. Corrections to the supplied diagnosis

| Claim in the supplied text | Correct interpretation for our project |
| --- | --- |
| Different past paths must produce different terminal states | Neither architecture supervises the last token as a unique full-path identity. Both accumulate increments externally. Different head outputs also do not imply a prescribed cosine separation. |
| Matching local end motion forces identical terminal features | Plausible task-pressure hypothesis; a causal Transformer can retain earlier context. Measure it rather than assume it. |
| LayerNorm causes a narrow positive cone | Not a general property of LayerNorm. Inspect actual cross-sample means and spectra. |
| Rank down30% proves genuine collapse | Arbitrary threshold; combine spectra, retrieval and motion information tests. |
| Four max-pool stages give exact feature validity | Exact any-valid support along convolution paths, excluding GroupNorm's global dependence. |
| First-layer NConv fixes all later normalization | Not established. Ordinary GroupNorm still uses spatial statistics. |
| Peaked attention proves scene shortcuts | Concentration is measured; dependence on scene-specific nuisance cues needs separate evidence. |
| Centering makes a model pass, therefore fixes it | Coverage of near pairs and nearest-curve quality can change; preserve the original gate and treat alternate signatures as diagnostics. |
| 104 windows give C(104,2) cross-sequence pairs | Same-sequence pairs are excluded. With26 sequences and4 windows each, there are5,200 unique cross-sequence pairs; windows also overlap. |
| H24 terminal features are compared only to the observed trajectory | The current gate uses a31-point,30-pair full reference, including6 flow pairs not observed atH24. Report observed-prefix and unobserved-tail contributions. |
| Three validation conflicts establish training gradient corruption | Training frequency and gradients have not been audited. All three known windows belong to one sequence. |
| Failure to improve means freeze inconsistent labels permanently | Correctness of the target/projector contract is separate from short-run accuracy. Validate the physical plane/height convention and compare both scoring protocols. |
| Intrinsic rays add missing calibration for the fixed camera | They reparameterize existing coordinates for a single fixed calibration; varying-camera generalization is a different test. |
| A paper establishes our computational overhead or improvement | GQFT timing, accuracy and gate effects must be measured locally. |

## 7. Ordered work plan

### D1. Embedding and ambiguity audit — first, no training

Question: is the yaw-local gate failure caused by the last-token signature, a common mean/anisotropy effect, lost motion information, unobserved future divergence, or a combination?

Use the exact four pilot best checkpoints, original pretrained yaw, released baseline and historical no-flip attention where available. Strictly match architectures and checkpoint hashes. Use the same104 validation windows, queries and reference horizon30. CPU float32 analysis is separate from historical CUDA bfloat16 scores; reproduce and report precision differences explicitly.

Save full per-window temporal states, predictions, identifiers, target curves and yaw. Begin at input history24; extend to the existing seven-history protocol if needed. Preserve all raw outputs so future statistical analysis does not require another model pass.

Compare predeclared signatures: terminal state; temporal mean; middle+terminal concatenation. For each, report raw cosine retrieval and a separately labeled centered diagnostic. If dominant-PC removal is later added, fit it on training/reference embeddings and disclose the number removed. Do not select a new signature only because it reduces the original ambiguity count.

Measure raw and centered singular spectra/effective rank, mean-vector energy, cross-sequence cosine distribution, nearest-neighbour identities, close-query coverage, full-reference curve gaps, observed-prefix gaps and future-tail gaps. Print all flagged pairs and compare their final local translation/yaw against their earlier motion. Preserve original raw-terminal gate metrics.

Interpretation: temporal pooling improving observed-path retrieval supports a signature mismatch; centering improving neighbour quality supports a common-mean effect. Neither proves a training cause. Rank reduction alone is insufficient; examine retained motion information and direct predictions. Zero close queries is not evidence of successful discrimination.

Deliverables: extraction manifest; states/predictions NPZ; per-pair table; spectra/cosine plots; original-versus-diagnostic metrics; a written conclusion that identifies remaining uncertainty.

### D2. Geometry and supervision audit — before label training

Audit train and validation metadata with exact ground-truth displacement and both plane conventions. Separate conflicting windows and all remaining windows. Verify what the plane/height contract means physically, particularly where camera elevation changes. Do not infer training conflicts from validation alone.

If a paired training experiment is justified, fix one no-flip architecture and vary only sequence-floor versus fixed-rig labels. Use identical initialization, budget, schedule, data order and at least three matched seeds. Keep yaw and mask changes separate. Evaluate direct3-D error, both pixel-label conventions, conflicting/non-conflicting subsets and the unchanged history gate.

A candidate budget can be prepared in advance, but training starts only after the user chooses an available GPU. If training fails to improve, investigate the measured result; it does not make an inconsistent supervision contract correct. Scalar loss weights are not a substitute for gradient measurements.

### D3. Attention and support audit — then a single controlled intervention

Extend the saved episode entropy calculation to training/reference and validation windows. Report entropy, top-cell mass, effective attended-cell count, spatial location, motion family and error. Account for overlapping windows and single-scene validation; use sequence-level summaries rather than treating every frame as independent.

Keep max pooling unchanged. Compare coarse coverage and convolution-path support as diagnostics first. A confidence-propagating encoder, entropy regularization, temperature change and spatial dropout are distinct interventions, not one combined arm.

If training is warranted, compare mean+max, attention+max and one predeclared regularized-attention arm, with the same seeds, labels and budget. Define the sign/form of the entropy term or the precise dropout/renormalization rule before running it. Do not tune on the locked test or choose a method based on episode629 alone.

Decision criterion: assess trajectory error, representation retrieval, numerical failures and compute together, with uncertainty across matched seeds. No universal entropy1.5, rank-drop30%, or dropout20% threshold is established by our evidence. Failure of one pilot setting is not proof that all learned attention should be removed permanently.

## 8. Constraints and current status

SEA-RAFT stays frozen; fixed camera conventions, analytic projection, strict loading and no-flip data policy remain. Shared datasets/environments and released baseline artifacts are preserved. New lab artifacts stay under Task_2/gqft_mask_review, with server output inside the restored GQFT project.

Completed before this document: model/adapter repairs; frozen mask isolation; soft-weighting sensitivity; optional soft/yaw-local source; four-arm500-step pilot; matched validation; episode overlays/dashboard; backup restoration; saved-result entropy/support/gate-count audit.

Completed for this document: all ten paper identities checked against primary pages; nine repository links checked; eight small pinned source snapshots inspected; incorrect official-code claims marked; Markdown draft and repository-audit JSON prepared. The Word/PDF export and separate citation/implementation packaging were subsequently completed on12 November; use the consolidated-document links above.

Next after this document: D1 CPU saved-checkpoint extraction and statistics. Not yet completed: full validation embedding audit, training-split geometry audit, paired-label training, multi-seed architecture comparisons or any new locked-test result. No training or GPU allocation is authorized by the literature review itself.

## 9. Folder guide

The current package layout is:

```text
gqft_mask_review/
  GQFT_APPROACHES_AND_RESEARCH.md     canonical current document
  GQFT_APPROACHES_AND_RESEARCH.docx   generated Word copy
  GQFT_APPROACHES_AND_RESEARCH.pdf    rendered PDF copy
  research_20261104/
    GQFT_RESEARCH_REVIEW.md          historical literature review
    export_document.py              standard-library DOCX exporter
    papers.json, papers.bib          10 original + 4 additional citations
    REPOSITORY_IMPLEMENTATIONS.md    pinned source files and status
    repository_audit.json            historical repository metadata/hashes
    inspect_repositories.py         bounded static-source audit script
    repositories/                   pinned source snapshots and licenses
    historical/                     preserved9 November approach narrative
    verification.json               package checks and hashes
```

Read this document first, then the implementation ledger. Update conclusions with links to immutable experiment results rather than overwriting earlier evidence.
