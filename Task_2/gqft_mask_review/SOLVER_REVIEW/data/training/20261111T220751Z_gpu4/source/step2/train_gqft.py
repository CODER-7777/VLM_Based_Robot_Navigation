"""Train GQFT with strict unseen-environment validation and stability gates."""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np
import torch
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel
from torch.utils.data import DataLoader
from torch.utils.data.distributed import DistributedSampler

from step2.dataset import FlowPathDataset, collate_windows
from step2.metrics import evaluate_loader
from step2.models.gqft import GQFT, GQFTConfig, gqft_loss
from step2.checkpoint import config_from_checkpoint, initialize_gqft


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--sequences-root", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--steps", type=int, default=40000)
    ap.add_argument("--batch-size", type=int, default=6, help="per GPU")
    ap.add_argument("--workers", type=int, default=4, help="per process")
    ap.add_argument("--queries", type=int, default=8)
    ap.add_argument("--max-history", type=int, default=30)
    ap.add_argument("--virtual-extension-px", type=int, default=0)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--weight-decay", type=float, default=1e-2)
    ap.add_argument("--warmup", type=int, default=500)
    ap.add_argument("--log-every", type=int, default=20)
    ap.add_argument("--val-every", type=int, default=500)
    ap.add_argument("--val-batches", type=int, default=100)
    ap.add_argument("--checkpoint-every", type=int, default=1000)
    ap.add_argument("--min-stable-step", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=20260820)
    ap.add_argument("--resume", default=None)
    ap.add_argument("--init-checkpoint", default=None)
    ap.add_argument("--no-amp", action="store_true")
    ap.add_argument("--spatial-pooling", choices=("mean_max", "attention_max"), default="attention_max")
    ap.add_argument("--predict-yaw", action="store_true")
    ap.add_argument("--spatial-mask", choices=("none", "validity", "confidence", "soft_validity",
                                               "soft_confidence", "soft_confidence_ground"), default="none")
    ap.add_argument("--mask-confidence-threshold", type=float, default=0.0)
    ap.add_argument("--mask-min-coverage", type=float, default=0.75)
    ap.add_argument("--mask-coverage-rule", choices=("adaptive", "receptive_field"), default="adaptive")
    ap.add_argument("--mask-soft-floor", type=float, default=.25)
    ap.add_argument("--mask-logit-strength", type=float, default=1.)
    ap.add_argument("--mask-hard-min-coverage", type=float, default=0.)
    ap.add_argument("--mask-ground-near-m", type=float, default=.5)
    ap.add_argument("--mask-ground-far-m", type=float, default=8.)
    ap.add_argument("--motion-integration", choices=("keyframe", "yaw_local"), default="keyframe")
    ap.add_argument("--motion-prior", choices=("none", "ground_solver"), default="none",
                    help="ground_solver: differentiable floor-flow ego-motion + learned residual")
    ap.add_argument("--ground-max-floor-m", type=float, default=1.5,
                    help="Select on TRAINING scenes (tools/evaluate_ground_solver.py), never on test")
    ap.add_argument("--ground-iterations", type=int, default=6)
    ap.add_argument("--ground-learned-weights", action="store_true")
    ap.add_argument("--ground-residual-m", type=float, default=0.03)
    ap.add_argument("--ground-residual-yaw-rad", type=float, default=0.05)
    ap.add_argument("--reinitialize-motion-heads", action="store_true",
                    help="Keep fresh seeded delta/logvar heads; required when warm-starting a new increment frame")
    ap.add_argument("--target-ground-plane", choices=("sequence_floor", "fixed_rig"),
                    default="sequence_floor", help="Explicit annotation protocol; legacy is the default")
    ap.add_argument("--allow-gpu", action="store_true",
                    help="Pass only after obtaining the user's permission to use server GPUs")
    return ap.parse_args()


def distributed_setup():
    world = int(os.environ.get("WORLD_SIZE", "1"))
    rank = int(os.environ.get("RANK", "0"))
    local_rank = int(os.environ.get("LOCAL_RANK", "0"))
    if world > 1:
        torch.cuda.set_device(local_rank)
        dist.init_process_group("nccl")
    device = torch.device(f"cuda:{local_rank}" if torch.cuda.is_available() else "cpu")
    return rank, world, local_rank, device


def validate_unseen_manifest(path):
    with open(path) as f:
        manifest = json.load(f)
    scenarios = manifest.get("split_scenarios", {})
    train, val = set(scenarios.get("train", [])), set(scenarios.get("val", []))
    if not train or not val or train & val:
        raise ValueError("manifest must declare non-empty, disjoint train/val scenarios")
    ready = {"train": 0, "val": 0}
    for entry in manifest.get("entries", []):
        split = entry.get("split")
        if split in ready and entry.get("flow_ready"):
            ready[split] += 1
            if entry.get("scenario") not in (train if split == "train" else val):
                raise ValueError(f"{split} entry disagrees with declared scenarios")
    if min(ready.values()) == 0:
        raise ValueError(f"flow-ready train and unseen-val data required, got {ready}")


def atomic_json(path, payload):
    tmp = str(path) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(payload, f, indent=2)
    os.replace(tmp, path)


def save_checkpoint(path, model, optimizer, scheduler, step, best_val, initial_val, args,
                    model_config, camera):
    tmp = str(path) + ".tmp"
    torch.save({"architecture": "GQFT", "model": model.state_dict(), "optimizer": optimizer.state_dict(),
                "scheduler": scheduler.state_dict(), "step": step, "best_val": best_val,
                "initial_val": initial_val, "args": vars(args),
                "model_config": asdict(model_config), "camera_model": asdict(camera)}, tmp)
    os.replace(tmp, path)


def move_batch(batch, device):
    return {k: v.to(device, non_blocking=True) if torch.is_tensor(v) else v
            for k, v in batch.items()}


def main():
    args = parse_args()
    if not args.allow_gpu:
        raise SystemExit("GPU training requires user permission. Pass --allow-gpu only after approval.")
    rank, world, local_rank, device = distributed_setup()
    if device.type != "cuda":
        raise SystemExit("GQFT training requires CUDA")
    if args.max_history < 2 or args.steps < 1 or args.batch_size < 1 or min(
            args.log_every, args.val_every, args.checkpoint_every) < 1:
        raise SystemExit("history >= 2 and positive steps, batch size, and intervals are required")
    if args.virtual_extension_px < 0 or (args.resume and args.init_checkpoint):
        raise SystemExit("extension must be non-negative; resume and init-checkpoint are exclusive")
    if args.reinitialize_motion_heads and (args.resume or not args.init_checkpoint):
        raise ValueError("Motion-head reinitialization requires init-checkpoint and cannot resume")
    validate_unseen_manifest(args.manifest)
    seed = args.seed + rank
    random.seed(seed)
    np.random.seed(seed % (2 ** 32))
    torch.manual_seed(seed)
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.set_float32_matmul_precision("high")

    out_dir = Path(args.out)
    if rank == 0:
        out_dir.mkdir(parents=True, exist_ok=True)
        atomic_json(out_dir / "run_config.json", {**vars(args), "world_size": world,
                                                   "device": torch.cuda.get_device_name(device)})

    train_set = FlowPathDataset(args.manifest, "train", sequences_root=args.sequences_root,
                                max_history=args.max_history, queries=args.queries, seed=args.seed,
                                virtual_extension_px=args.virtual_extension_px,
                                target_ground_plane=args.target_ground_plane)
    val_set = FlowPathDataset(args.manifest, "val", sequences_root=args.sequences_root,
                              max_history=args.max_history, queries=args.queries, seed=args.seed,
                              virtual_extension_px=args.virtual_extension_px,
                              target_ground_plane=args.target_ground_plane)
    sampler = DistributedSampler(train_set, num_replicas=world, rank=rank, shuffle=True,
                                 seed=args.seed, drop_last=True) if world > 1 else None
    generator = torch.Generator().manual_seed(seed)
    train_loader = DataLoader(train_set, batch_size=args.batch_size, shuffle=sampler is None,
                              sampler=sampler, num_workers=args.workers, pin_memory=True,
                              persistent_workers=args.workers > 0, drop_last=True,
                              collate_fn=collate_windows, generator=generator)
    if len(train_loader) == 0:
        raise ValueError("training loader is empty; reduce batch size or add train windows")
    val_loader = None
    if rank == 0:
        val_loader = DataLoader(val_set, batch_size=args.batch_size, shuffle=False,
                                num_workers=min(args.workers, 2), pin_memory=True,
                                persistent_workers=args.workers > 0,
                                collate_fn=collate_windows)

    camera = train_set.camera
    if camera != val_set.camera:
        raise ValueError("train and validation camera contracts differ")
    model_config = GQFTConfig(max_history=args.max_history,
                              canvas_height=camera.height + args.virtual_extension_px,
                              spatial_pooling=args.spatial_pooling, predict_yaw=args.predict_yaw,
                              spatial_mask=args.spatial_mask,
                              mask_confidence_threshold=args.mask_confidence_threshold,
                              mask_min_coverage=args.mask_min_coverage,
                              mask_coverage_rule=args.mask_coverage_rule,
                              mask_soft_floor=args.mask_soft_floor,
                              mask_logit_strength=args.mask_logit_strength,
                              mask_hard_min_coverage=args.mask_hard_min_coverage,
                              mask_ground_near_m=args.mask_ground_near_m,
                              mask_ground_far_m=args.mask_ground_far_m,
                              motion_integration=args.motion_integration,
                              motion_prior=args.motion_prior,
                              ground_max_floor_m=args.ground_max_floor_m,
                              ground_iterations=args.ground_iterations,
                              ground_learned_weights=args.ground_learned_weights,
                              ground_residual_m=args.ground_residual_m,
                              ground_residual_yaw_rad=args.ground_residual_yaw_rad)
    base_model = GQFT(model_config, camera=camera).to(device)
    optimizer = torch.optim.AdamW(base_model.parameters(), lr=args.lr,
                                  weight_decay=args.weight_decay)
    def lr_scale(step):
        if step < args.warmup:
            return max(step, 1) / max(args.warmup, 1)
        progress = (step - args.warmup) / max(args.steps - args.warmup, 1)
        return 0.05 + 0.95 * 0.5 * (1.0 + math.cos(math.pi * min(progress, 1.0)))
    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_scale)
    start_step, best_val, initial_val = 0, float("inf"), None
    if args.init_checkpoint:
        state = torch.load(args.init_checkpoint, map_location="cpu")
        initialize_gqft(base_model, state, reinitialize_motion_heads=args.reinitialize_motion_heads)
    if args.resume:
        state = torch.load(args.resume, map_location="cpu")
        if state.get("architecture", "GQFT") != "GQFT":
            raise ValueError("resume checkpoint is not a GQFT checkpoint")
        if config_from_checkpoint(state) != model_config:
            raise ValueError("Resume model/mask configuration differs; use init-checkpoint for a new experiment")
        base_model.load_state_dict(state["model"])
        optimizer.load_state_dict(state["optimizer"])
        scheduler.load_state_dict(state["scheduler"])
        start_step = int(state["step"])
        best_val = float(state.get("best_val", best_val))
        initial_val = state.get("initial_val")
    model = (DistributedDataParallel(base_model, device_ids=[local_rank],
                                     broadcast_buffers=False) if world > 1 else base_model)

    if rank == 0 and initial_val is None:
        baseline = evaluate_loader(base_model, val_loader, device,
                                   max_batches=args.val_batches, amp=not args.no_amp)
        initial_val = baseline["ade_px"]
        print("VAL " + json.dumps({"step": start_step, **baseline}), flush=True)
    if world > 1:
        holder = [initial_val]
        dist.broadcast_object_list(holder, src=0)
        initial_val = holder[0]
        dist.barrier()

    model.train()
    step, epoch, finite_streak, validation_count = start_step, 0, 0, 0
    running = {k: 0.0 for k in ("loss", "motion", "path", "endpoint", "visibility",
                                     "motion_nll","yaw")}
    running_count = 0
    while step < args.steps:
        if sampler is not None:
            sampler.set_epoch(epoch)
        for batch in train_loader:
            if step >= args.steps:
                break
            batch = move_batch(batch, device)
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast("cuda", dtype=torch.bfloat16, enabled=not args.no_amp):
                output = model(batch["flow"], batch["history_mask"], batch["query_uv"],
                               batch["query_norm"])
                losses = gqft_loss(output, batch)
            loss = losses["loss"]
            finite_loss = torch.isfinite(loss).to(torch.int32)
            if world > 1:
                dist.all_reduce(finite_loss, op=dist.ReduceOp.MIN)
            if bool(finite_loss):
                loss.backward()
                grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                finite = bool(torch.isfinite(grad_norm))
            else:
                finite, grad_norm = False, torch.tensor(float("nan"), device=device)
            if finite:
                optimizer.step()
                scheduler.step()
                finite_streak += 1
            else:
                optimizer.zero_grad(set_to_none=True)
                finite_streak = 0
            step += 1

            values = torch.tensor([float(losses[k].detach()) for k in running], device=device)
            if world > 1:
                dist.all_reduce(values, op=dist.ReduceOp.SUM)
                values /= world
            for key, value in zip(running, values.tolist()):
                running[key] += value
            running_count += 1
            if step % args.log_every == 0:
                if rank == 0:
                    record = {"step": step, "epoch": epoch,
                              **{k: v / running_count for k, v in running.items()},
                              "grad_norm": float(grad_norm), "lr": scheduler.get_last_lr()[0],
                              "finite_streak": finite_streak, "time": time.time()}
                    print("TRAIN " + json.dumps(record), flush=True)
                    with open(out_dir / "metrics.jsonl", "a") as f:
                        f.write(json.dumps({"kind": "train", **record}) + "\n")
                running = {k: 0.0 for k in running}
                running_count = 0

            do_val = step % args.val_every == 0 or step == args.steps
            if do_val:
                if world > 1:
                    dist.barrier()
                if rank == 0:
                    metrics = evaluate_loader(base_model, val_loader, device,
                                              max_batches=args.val_batches,
                                              amp=not args.no_amp)
                    validation_count += 1
                    improved = metrics["ade_px"] < best_val
                    best_val = min(best_val, metrics["ade_px"])
                    record = {"step": step, **metrics, "best_ade_px": best_val,
                              "initial_ade_px": initial_val}
                    print("VAL " + json.dumps(record), flush=True)
                    with open(out_dir / "metrics.jsonl", "a") as f:
                        f.write(json.dumps({"kind": "val", **record}) + "\n")
                    if improved:
                        save_checkpoint(out_dir / "best.pt", base_model, optimizer, scheduler,
                        step, best_val, initial_val, args, model_config, camera)
                    stable = (step >= args.min_stable_step and finite_streak >= 250 and
                              validation_count >= 2 and best_val <= 0.98 * initial_val and
                              metrics["ade_px"] <= 1.25 * best_val)
                    if stable and not (out_dir / "STABLE.json").exists():
                        atomic_json(out_dir / "STABLE.json", record)
                        print("TRAINING_STABLE " + json.dumps(record), flush=True)
                if world > 1:
                    dist.barrier()
                model.train()

            if rank == 0 and (step % args.checkpoint_every == 0 or step == args.steps):
                save_checkpoint(out_dir / "last.pt", base_model, optimizer, scheduler,
                                step, best_val, initial_val, args, model_config, camera)
        epoch += 1

    if rank == 0:
        print("TRAINING_DONE " + json.dumps({"step": step, "best_ade_px": best_val}), flush=True)
    if world > 1:
        dist.destroy_process_group()


if __name__ == "__main__":
    main()
