# Trainable spatial prior and yaw-local integration

**19 October result:** The GPU-7 pilot completed all four 500-step arms. [Complete training and matched-validation report](../pilot_results/20261019T101035Z_431613/validation_20261019T104120Z/REPORT.md). Yaw-local alone lowers H24 ADE 12.4626→11.3485 px relative to the matched pilot reference, but fails history selection. Masking worsens fixed-window ADE within both integration modes. The combined model is not selected for a long run. The dated preparation notes below describe what had been executed at those earlier dates.

Latest device selection, 19 October: the user selected **physical GPU 7**, superseding GPU 2 for the upcoming pilot. `run_attention_pilot.sh` now exports `CUDA_VISIBLE_DEVICES=7`, prints GPU 7 in dry runs and checks GPU 7 with nvidia-smi. The source archive and older prepared-plan examples retain their historical content; use the updated launcher for this run. This device change does not alter model/data/training settings. [GPU-7 launcher checks](launcher_checks_20261019_gpu7.json).

Implemented locally on 16 October 2026. No server files were replaced, no GPU was used for this implementation check, and no training was launched. The released baseline is unchanged. This adds two optional modes, not a measured model improvement.

Revalidated 17 October: all 15 trainable-mode checks, 10 hard-mask regression checks and legacy contract checks pass on CPU. Legacy baseline/Attention/Yaw outputs remain bit-identical. Dataset-dependent legacy checks remain skipped locally; trained-model accuracy and history-gate improvement remain unmeasured. [Fresh verification record](revalidation_20261017.json).

Why these changes follow the earlier diagnostics: soft attention preserves useful neighbouring evidence that hard cell rejection removed; max pooling stays unchanged because masking it had the larger individual validation regression. Confidence and ground-ray support add testable reliability/geometry priors, whose benefit remains a hypothesis. Local-yaw integration explicitly separates local translation prediction from rotation, but the old cumsum is already correct for its keyframe-frame labels. Input/camera/label contracts and frozen pooling effects were checked first to avoid attributing those defects to architecture. The prepared four-way pilot will isolate the two new interventions before considering temporal biases or embedding losses.

## Spatial attention

New `--spatial-mask` modes:

| Mode | Evidence before soft flooring |
| --- | --- |
| `soft_validity` | Mean supplied valid-pixel coverage; reproduces the preceding soft-validity probe |
| `soft_confidence` | Mean `validity * confidence` |
| `soft_confidence_ground` | Mean `validity * confidence`, multiplied by mean ground-ray support |

`--mask-coverage-rule receptive_field` averages over the 31×31 local convolution footprint (stride 16, padding 15, outside-image padding excluded). `adaptive` retains the old bin mapping. GroupNorm additionally mixes global spatial statistics; this is not a strictly local functional receptive field.

For evidence `e`, reliability is `r = floor + (1-floor)*e`; attention logits become `A + gamma*log(r)`. Defaults are floor 0.25, gamma 1. Confidence is clamped to [0,1]. The implementation averages `V*C` once, rather than separately pooling V and C and counting validity twice. Original max pooling is retained in every new soft mode, following the observed hard-max regression. Finite cached CNN inputs are preserved; nonfinite pixels are sanitized.

The calibrated prior uses the manifest/checkpoint camera and hypothetical ray-ground intersections on the resized RGB/flow grid. Default optical-axis ground depth is 0.5–8 m. This **does not segment actual floor pixels**: a ray hitting a wall can also intersect the hypothetical infinite ground plane. It is a proposed geometric bias, not proof that walls/ceilings caused the old test regression.

Optional `--mask-hard-min-coverage 0.1` hard-gates only attention at less than 10% valid support. Default is **0**, preserving a fully soft comparison. An all-gated frame produces zero attention contribution with finite original max/bias contribution; the time slot is retained. `motion_observed` marks actual input validity, independently of token magnitude. Old `validity`/`confidence` modes retain their previous joint attention+max hard masking.

Example flags, without launching training:

```text
--spatial-mask soft_confidence_ground
--mask-coverage-rule receptive_field
--mask-soft-floor 0.25 --mask-logit-strength 1
--mask-hard-min-coverage 0
--mask-ground-near-m 0.5 --mask-ground-far-m 8
```

## Yaw-coupled motion

`--motion-integration keyframe` remains default. Existing targets are already displacement in the initial camera frame, so their existing cumsum is valid and unchanged.

`--predict-yaw --motion-integration yaw_local` changes the head semantics explicitly:

```text
local_delta[t] = bounded head output in camera frame at interval start
yaw[t] = accumulated predicted yaw through interval t-1
delta_camera0[t] = Rodrigues(world_up_in_camera0, yaw[t]) @ local_delta[t]
displacement_camera0 = cumulative_sum(delta_camera0)
```

At 30° downward pitch the up axis is `[0, -cos(30°), -sin(30°)]`; rotating about camera Y would be wrong. Rotation uses previous yaw, not end-of-interval yaw. This is yaw-coupled 3-D integration with optional vertical motion, not a strictly planar SE(2) state.

Training loss derives **local increment targets using ground-truth previous yaw** and inverse rotation of the existing keyframe displacement differences. Local uncertainty/NLL is computed in that same local frame. Path/displacement supervision stays in camera0 with the same analytic projector. Yaw residuals are wrapped in the new mode. Pose padding remains zero-motion and the temporal encoder remains causal.

No dataset label files, camera calibration or SEA-RAFT weights are changed. Translation/path losses now have a gradient path into predicted yaw. The new mode requires yaw supervision, and it is not meaningful to reinterpret an old trained delta head as local without training.

## Checkpoints and warm starts

New config fields are saved by the existing checkpoint format. Strict loading restores both modes; old checkpoints default to mask-off/keyframe semantics and reproduce old outputs.

Changing the increment frame when using `--init-checkpoint` is rejected unless `--reinitialize-motion-heads` is explicit. That flag keeps the destination model's freshly seeded delta and uncertainty heads while strictly loading the backbone/yaw head. The four pilot arms all use this flag, same seed, and the same Attention+Yaw checkpoint, so they begin with identical motion heads. Resume still requires the exact saved config. Initial checkpoint camera must match the destination camera.

`infer_gqft.py` exports model config and, for the new mode, local and keyframe motion increments. Final displacement remains camera0 coordinates for consumers.

## Verification

[verification.json](verification.json) records CPU checks, PyTorch version and source hashes. They cover calibrated horizon/range, confidence-bias direction, unchanged max pooling, empty/nonfinite observations, known left-turn sign with pitched world-up, inverse local targets, gradients through yaw/translation/attention, local-frame NLL, wrapped yaw, causality/padding, bfloat16 backward, strict new checkpoint round trip, initialization safeguards and agreement with the preceding real-checkpoint soft-validity probe.

Existing `tools/verify_spatial_mask.py` and `tools/verify_cpu_contracts.py` also pass. Legacy baseline/Attention/Yaw outputs remain bit-identical. Dataset-dependent legacy checks are skipped locally because shared sequence caches are on the server. No training gain, test gain or history-gate result is claimed.

From the local repository root:

```bash
CUDA_VISIBLE_DEVICES='' PYTHONDONTWRITEBYTECODE=1 python3 -B \
  Task_2/gqft_mask_review/verify_trainable_attention.py

CUDA_VISIBLE_DEVICES='' PYTHONDONTWRITEBYTECODE=1 python3 -B \
  Task_2/gqft_mask_review/prepare_attention_pilot.py
```

## Pilot preparation record (now completed; see result above)

17 October: [run_attention_pilot.sh](run_attention_pilot.sh) is the sequential launcher. Upload it beside the source archive in the server's `gqft_mask_review/`, then run it inside tmux. It verifies the source archive, staged-source hashes and starting checkpoint; stages source only if absent; runs all four arms for 500 steps each on GPU 2; and records per-arm logs/checkpoints under a fresh UTC/PID run folder. A failure stops the sequence. `bash run_attention_pilot.sh --dry-run` prints commands without staging source or starting training. [Launcher checks](launcher_checks_20261017.json). No training was launched during preparation.

[pilot_plan.json](pilot_plan.json) and [PILOT_COMMANDS.txt](PILOT_COMMANDS.txt) define a four-arm factorial pilot:

| Arm | Spatial mode | Integration |
| --- | --- | --- |
| Reference | none | keyframe |
| Masked only | soft confidence + ground | keyframe |
| Yaw-local only | none | yaw_local |
| Both | soft confidence + ground | yaw_local |

All arms predict yaw, share the same backbone/yaw initialization and reset identical delta/logvar heads. Proposed pilot budget: 500 steps per arm, batch 6, seed 20260820, warmup 50, one extended anchor, max history 30, original `sequence_floor` labels, same optimizer/AMP/data recipe. This is a smoke pilot, not sufficient evidence of convergence or independent-seed generalization. Keep the separate ground-label experiment independent.

The training script's checkpoint validation retains its deterministic-per-index mixed-history protocol. It is **not** the fixed 104-window history-24 score. After the pilot, run matched validation/history selection before comparing with the earlier diagnostic scores; do not tune on locked test. Compare masking within each integration mode and integration within each mask setting, then inspect the interaction and motion families.

`source_20261016.tar.gz` is an isolated source bundle containing `step2/`, inference source and source hashes; no weights, datasets, environments or preserved-baseline files. It has not been deployed. To stage it without replacing active server code, from the local repository root:

```bash
scp Task_2/gqft_mask_review/implementation_20261016/source_20261016.tar.gz \
  guest-isl@172.26.186.222:/data/robotics/toshith/vivekananda/gqft_algorithm_sharing_vivekananda/gqft_mask_review/
```

Then on ISL:

```bash
cd /data/robotics/toshith/vivekananda/gqft_algorithm_sharing_vivekananda/gqft_mask_review
tar -xzf source_20261016.tar.gz
cd source_20261016
```

The prepared commands use that staged root, the existing `agentvln` environment and physical GPU 2, while all datasets/checkpoint inputs retain absolute read-only paths. They write only under the GQFT project's lab. The commands actually start training when manually run; preparation did not execute them. Use a fresh output run directory for subsequent pilots rather than overwriting an earlier one.

## Other pasted proposals

Temporal quality bias, flow decomposition, contrastive embedding loss and query-conditioned cross-attention are separate candidates and are not bundled into this implementation. The current history gate compares different sequences; the validation set is one scene. Neither a contrastive loss nor SE(2)-style integration guarantees a gate pass, and validation/test disagreement alone does not identify specific scene artifacts as its cause. Keep these as measured hypotheses.
