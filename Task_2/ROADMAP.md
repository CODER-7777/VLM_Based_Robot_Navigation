# Task 2 — Roadmap & Tracker

> **Goal**: Beat the GQFT baseline test ADE of **9.63 px** → then explore further improvements.
> **ICRA internal cutoff**: 10 Sep 2026 | **Fallback**: RA-L (31 Dec 2026)

---

## Phase 1: Train Augmented Model on ISL Server ⬅️ START HERE

### Step 1.1 — SSH into the ISL server

- [ ] Open a terminal and SSH in:
  ```bash
  ssh isl-server
  ```
  *(If `isl-server` doesn't resolve, use the full hostname/IP your professor gave you.)*

### Step 1.2 — Navigate and set up environment

- [ ] Go to the project directory and set PYTHONPATH:
  ```bash
  cd /data/robotics/toshith/gqft_algorithm_sharing_vivekananda
  export PYTHONPATH=$PWD
  ```

### Step 1.3 — Sync your augmented dataset.py to the server

Your augmentation code is in your local `step2/dataset.py`. You need it on the server too.

- [ ] **Option A** — If you pushed to git:
  ```bash
  git pull origin main
  ```

- [ ] **Option B** — If NOT pushed yet, copy from your local machine (run this **on YOUR machine**, not the server):
  ```bash
  scp ~/UGP_1_VLM/VLM_Based_Robot_Navigation/Task_2/gqft_algorithm_sharing_vivekananda/step2/dataset.py \
    isl-server:/data/robotics/toshith/gqft_algorithm_sharing_vivekananda/step2/dataset.py
  ```

### Step 1.4 — Verify environment still works

- [ ] Run the verification script:
  ```bash
  PY=/tmp/hsgm_env/hsgm/bin/python
  $PY verify_setup.py
  ```
  You should see `"status": "ok"` and the GPU name `NVIDIA A40`.

### Step 1.5 — Check which GPUs are free

- [ ] Check GPU usage:
  ```bash
  nvidia-smi
  ```
  Look for GPUs with 0 MB memory used. Note their IDs (0-7).

### Step 1.6 — Start a tmux session (so training survives SSH disconnect)

- [ ] Create a tmux session:
  ```bash
  tmux new -s gqft_train
  ```
  *(To detach later: `Ctrl+B` then `D`. To reattach: `tmux attach -t gqft_train`)*

### Step 1.7 — Start training 🚀

- [ ] Set up env inside tmux:
  ```bash
  cd /data/robotics/toshith/gqft_algorithm_sharing_vivekananda
  export PYTHONPATH=$PWD
  PY=/tmp/hsgm_env/hsgm/bin/python
  ```

- [ ] **If 3 GPUs are free** (e.g., GPUs 5,6,7):
  ```bash
  CUDA_VISIBLE_DEVICES=5,6,7 $PY -m torch.distributed.run \
    --nproc_per_node=3 step2/train_gqft.py \
    --manifest results/hsgm_manifest_v1.json --out runs/gqft_aug_v1 \
    --steps 10000 --batch-size 6 --workers 4 --queries 1 \
    --max-history 30 --virtual-extension-px 270 --warmup 500 \
    --log-every 20 --val-every 500 --val-batches 100 \
    --checkpoint-every 1000 --min-stable-step 1000
  ```

- [ ] **If only 1 GPU is free** (e.g., GPU 2):
  ```bash
  CUDA_VISIBLE_DEVICES=2 $PY step2/train_gqft.py \
    --manifest results/hsgm_manifest_v1.json --out runs/gqft_aug_v1 \
    --steps 10000 --batch-size 18 --workers 4 --queries 1 \
    --max-history 30 --virtual-extension-px 270 --warmup 500 \
    --log-every 20 --val-every 500 --val-batches 100 \
    --checkpoint-every 1000 --min-stable-step 1000
  ```

> **⏱ Expected time**: ~1-2 hours depending on GPU count.

### Step 1.8 — Monitor training

- [ ] Watch the log (in another terminal or after detaching tmux):
  ```bash
  tail -f runs/gqft_aug_v1/metrics.jsonl
  ```
  Look for `"kind": "val"` lines. If `ade_px` is dropping → good sign.

---

## Phase 2: Evaluate the Augmented Model

### Step 2.1 — Validation history selection

- [ ] Run validation sweep:
  ```bash
  $PY -m step2.evaluate_gqft \
    --checkpoint runs/gqft_aug_v1/best.pt \
    --manifest results/hsgm_manifest_v1.json --split val \
    --histories 4,8,12,16,20,24,30 --queries 1 \
    --out results/gqft_aug_v1_val_history.json
  ```

- [ ] Find the **shortest history where signature ambiguity = 0**:
  ```bash
  cat results/gqft_aug_v1_val_history.json | python3 -m json.tool
  ```
  Write down the selected history: `______`

### Step 2.2 — Locked test evaluation (⚠️ ONE SHOT ONLY)

- [ ] Run test with your selected history (replace `<H>` with the number):
  ```bash
  $PY -m step2.evaluate_gqft \
    --checkpoint runs/gqft_aug_v1/best.pt \
    --manifest results/hsgm_manifest_v1.json --split test \
    --history <H> --queries 1 \
    --out results/gqft_aug_v1_test.json
  ```

- [ ] Record the results:

  | Metric | Baseline | Augmented (yours) |
  |--------|----------|-------------------|
  | ADE    | 9.63 px  |                   |
  | FDE    | 15.85 px |                   |

> ⚠️ **DO NOT** run this more than once. That would be test-set leakage.

### Step 2.3 — Copy results back to your machine

- [ ] From your LOCAL machine:
  ```bash
  scp isl-server:/data/robotics/toshith/gqft_algorithm_sharing_vivekananda/results/gqft_aug_v1_*.json \
    ~/UGP_1_VLM/VLM_Based_Robot_Navigation/Task_2/gqft_algorithm_sharing_vivekananda/results/
  ```

---

## Phase 3: Document Results

- [ ] Update `Task_2_Deliverable.md` with:
  - Training config used
  - Validation history selection table
  - Test ADE/FDE comparison vs baseline
  - Whether the hypothesis succeeded or failed
- [ ] Git commit and push:
  ```bash
  cd ~/UGP_1_VLM/VLM_Based_Robot_Navigation
  git add .
  git commit -m "Task 2: augmented training results — ADE X.XX px vs baseline 9.63 px"
  git push origin main
  ```

---

## Phase 4: Further Model Improvements (Post-Augmentation)

Once Phase 1-3 are done, pick **one** hypothesis at a time:

| # | Hypothesis | What to change | Difficulty |
|---|-----------|----------------|------------|
| 1 | **Multi-scale spatial flow tokens** | Modify `FlowFrameEncoder` in `step2/models/gqft.py` | Medium |
| 2 | **Adaptive history stopping** | Add a learned stop head to the Transformer | Medium |
| 3 | **Texture/lighting augmentation** | Add noise/jitter to flow inputs in `step2/dataset.py` | Easy |
| 4 | **More training scenes** | Capture new scenes with `step2/capture_hsgm_habitat.py` | Easy but slow |
| 5 | **Calibrated uncertainty** | Calibrate the existing `logvar_head` output | Hard |
| 6 | **Long-rollout re-anchoring** | Re-anchor queries during long trajectories | Medium |

For each attempt:
- [ ] Train with unchanged data split and camera config
- [ ] Validate on `D7G3Y4RVNrH` only
- [ ] Compare ADE/FDE, latency, param count vs baseline
- [ ] If improved → one locked test run
- [ ] If not → try next hypothesis

---

## Quick Reference

| What | Path |
|------|------|
| ISL project dir | `/data/robotics/toshith/gqft_algorithm_sharing_vivekananda` |
| Python executable | `/tmp/hsgm_env/hsgm/bin/python` |
| Baseline checkpoint | `checkpoints/gqft_hsgm_best.pt` |
| Dataset manifest | `results/hsgm_manifest_v1.json` |
| Flow data (16 GB) | `/data/robotics/toshith/rgbd_vo_dataset/hsgm_sequences` |
| Augmentation code | `step2/dataset.py` lines 152-158 |
| Training script | `step2/train_gqft.py` |
| Evaluation script | `step2/evaluate_gqft.py` |
| Train scenes | `17DRP5sb8fy`, `5q7pvUzZiYa`, `VLzqgDo317F`, `mJXqzFtmKg4` |
| Val scene | `D7G3Y4RVNrH` |
| Test scene (LOCKED) | `TbHJrupSAjP` |
