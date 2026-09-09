# UGP Task 2: Baseline Reproduction and Improvement

## 1. Goal
The primary objective of this task was to analyze the `gqft_algorithm_sharing_vivekananda` handoff repository, successfully reproduce the inference pipeline locally, and design an algorithmic improvement to beat the locked test set ADE of **9.63 px**.

## 2. Selected Hypothesis: Data Augmentation
The GQFT model was trained on a highly restricted dataset (only 4 Matterport3D scenes) with zero data augmentation. Our hypothesis is that implementing **Horizontal Flip Augmentation** will prevent the model from overfitting to the specific right-or-left turn biases present in the limited dataset.

By doubling the effective distribution of turn geometries, the spatial CNN and temporal Transformer will learn more robust, symmetric ego-motion representations.

## 3. Implementation
The augmentation was implemented directly in the PyTorch `Dataset` (`step2/dataset.py`), acting dynamically during training.

With a 50% probability during the `"train"` split:
1. The 4-channel input feature block (optical flow, confidence, mask) is flipped along the width axis.
2. The X-component of the optical flow (`du`) is inverted (`*-1`).
3. The query anchor coordinates are mirrored across the canvas width.
4. The target 3D X-displacement (camera frame lateral motion) is inverted.
5. The 2D projected trajectory coordinates are mirrored across the canvas width.

## 4. Next Steps & Server Execution
Due to hardware constraints (4GB VRAM), this modification was developed locally. It must now be trained on the ISL Server's A40 GPUs using the 16GB optical flow cache.

**Command to train:**
```bash
/tmp/hsgm_env/hsgm/bin/torchrun --nproc_per_node=3 step2/train_gqft.py --run-dir runs/gqft_aug_v1
```

**Command to evaluate:**
```bash
/tmp/hsgm_env/hsgm/bin/python step2/evaluate_gqft.py --run-dir runs/gqft_aug_v1 --split test --history 24
```
