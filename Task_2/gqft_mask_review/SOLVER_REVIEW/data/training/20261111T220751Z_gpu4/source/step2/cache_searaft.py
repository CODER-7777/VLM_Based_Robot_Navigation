"""Cache SEA-RAFT flow/uncertainty from the actual RGB sequences.

Run where SEA-RAFT and its weights are available. Flow is cached at 160x90 as normalized image
displacement, with uncertainty and forward/backward consistency converted into confidence/validity.
"""

from __future__ import annotations

import argparse
import fnmatch
import glob
import json
import os
import sys

import cv2
import numpy as np
import torch
import torch.nn.functional as F


def load_model(searaft_root, cfg, checkpoint, hub_model, device):
    sys.path.insert(0, os.path.join(searaft_root, "core"))
    sys.path.insert(0, searaft_root)
    from config.parser import json_to_args
    from raft import RAFT
    from utils.utils import load_ckpt
    args = json_to_args(cfg)
    if checkpoint:
        model = RAFT(args)
        if checkpoint.endswith(".safetensors"):
            from safetensors.torch import load_file
            state = load_file(checkpoint, device="cpu")
            model.load_state_dict(state, strict=False)
        else:
            load_ckpt(model, checkpoint)
    else:
        model = RAFT.from_pretrained(hub_model, args=args)
    return model.to(device).eval(), args


def mixture_scale(info, args):
    weight = info[:, :2].softmax(dim=1)
    raw = info[:, 2:]
    log_b = torch.stack([raw[:, 0].clamp(0, args.var_max),
                         raw[:, 1].clamp(args.var_min, 0)], dim=1)
    return (weight * log_b.exp()).sum(dim=1)


def warp(tensor, flow):
    b, _, h, w = tensor.shape
    yy, xx = torch.meshgrid(torch.arange(h, device=tensor.device),
                            torch.arange(w, device=tensor.device), indexing="ij")
    x = xx[None] + flow[:, 0]
    y = yy[None] + flow[:, 1]
    grid = torch.stack([2 * x / max(w - 1, 1) - 1, 2 * y / max(h - 1, 1) - 1], dim=-1)
    return F.grid_sample(tensor, grid, mode="bilinear", padding_mode="zeros", align_corners=True), x, y


@torch.inference_mode()
def infer_batch(model, model_args, image0, image1, out_hw):
    out_f = model(image0, image1, iters=model_args.iters, test_mode=True)
    out_b = model(image1, image0, iters=model_args.iters, test_mode=True)
    forward, backward = out_f["flow"][-1], out_b["flow"][-1]
    bwd_at_fwd, x1, y1 = warp(backward, forward)
    cycle = torch.linalg.vector_norm(forward + bwd_at_fwd, dim=1)
    magnitude = torch.linalg.vector_norm(forward, dim=1)
    endpoint_valid = ((x1 >= 0) & (x1 < forward.shape[-1]) &
                      (y1 >= 0) & (y1 < forward.shape[-2]))
    cycle_valid = cycle <= (0.5 + 0.05 * magnitude)
    scale_f = mixture_scale(out_f["info"][-1], model_args)
    scale_b = mixture_scale(out_b["info"][-1], model_args)[:, None]
    scale_b_at_fwd, _, _ = warp(scale_b, forward)
    confidence = 1.0 / (1.0 + scale_f + scale_b_at_fwd[:, 0])
    valid = endpoint_valid & cycle_valid & torch.isfinite(confidence)

    h, w = forward.shape[-2:]
    normalized = forward.clone()
    normalized[:, 0] /= w
    normalized[:, 1] /= h
    normalized = F.interpolate(normalized, out_hw, mode="area")
    confidence = F.interpolate(confidence[:, None], out_hw, mode="area")[:, 0]
    valid_fraction = F.interpolate(valid[:, None].float(), out_hw, mode="area")[:, 0]
    valid_small = valid_fraction >= 0.75
    normalized = normalized * valid_small[:, None]
    confidence = confidence * valid_small
    return normalized, confidence, valid_small, cycle, valid


def read_rgb(path):
    image = cv2.imread(path, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"could not read {path}")
    return torch.from_numpy(cv2.cvtColor(image, cv2.COLOR_BGR2RGB)).permute(2, 0, 1).float()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sequences", required=True)
    ap.add_argument("--searaft-root", required=True)
    ap.add_argument("--cfg", default=None)
    ap.add_argument("--checkpoint", default=None)
    ap.add_argument("--hub-model", default="MemorySlices/Tartan-C-T-TSKH-spring540x960-M")
    ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--out-name", default="flow_searaft_160x90.npz")
    ap.add_argument("--height", type=int, default=90)
    ap.add_argument("--width", type=int, default=160)
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--include", default="*", help="sequence basename glob")
    args = ap.parse_args()
    cfg = args.cfg or os.path.join(args.searaft_root, "config/eval/spring-M.json")
    device = torch.device(args.device)
    model, model_args = load_model(args.searaft_root, cfg, args.checkpoint,
                                   args.hub_model, device)

    sequence_dirs = sorted(os.path.dirname(p) for p in
                           glob.glob(os.path.join(args.sequences, "*", "meta.json")))
    sequence_dirs = [p for p in sequence_dirs
                     if fnmatch.fnmatch(os.path.basename(p), args.include)]
    for seq in sequence_dirs:
        out_path = os.path.join(seq, args.out_name)
        if os.path.isfile(out_path) and not args.overwrite:
            print(f"FLOW_SKIP {os.path.basename(seq)}", flush=True)
            continue
        images = sorted(glob.glob(os.path.join(seq, "rgb", "*.png")))
        if len(images) < 2:
            continue
        all_flow, all_conf, all_valid = [], [], []
        full_valid, cycle_means = [], []
        for begin in range(0, len(images) - 1, args.batch_size):
            pairs = [(images[i], images[i + 1])
                     for i in range(begin, min(begin + args.batch_size, len(images) - 1))]
            image0 = torch.stack([read_rgb(a) for a, _ in pairs]).to(device)
            image1 = torch.stack([read_rgb(b) for _, b in pairs]).to(device)
            flow, confidence, valid, cycle, valid_full = infer_batch(
                model, model_args, image0, image1, (args.height, args.width))
            all_flow.append(flow.permute(0, 2, 3, 1).cpu().half().numpy())
            all_conf.append(confidence.cpu().half().numpy())
            all_valid.append(valid.cpu().numpy().astype(np.uint8))
            full_valid.append(float(valid_full.float().mean().cpu()))
            cycle_means.append(float(cycle[valid_full].mean().cpu()) if valid_full.any() else float("nan"))
        flow = np.concatenate(all_flow)
        confidence = np.concatenate(all_conf)
        valid = np.concatenate(all_valid)
        if len(flow) != len(images) - 1 or not np.isfinite(flow).all():
            raise RuntimeError(f"{seq}: corrupt flow cache")
        tmp_out = out_path + ".tmp.npz"
        np.savez_compressed(tmp_out, flow=flow, confidence=confidence, valid=valid)
        os.replace(tmp_out, out_path)
        stats = {"sequence": os.path.basename(seq), "pairs": len(flow),
                 "cache_hw": [args.height, args.width], "flow_units": "du/W,dv/H",
                 "valid_fraction_full": float(np.mean(full_valid)),
                 "valid_fraction_cache": float(valid.mean()),
                 "cycle_error_px_valid_mean": float(np.nanmean(cycle_means)),
                 "confidence_mean_valid": float(confidence[valid.astype(bool)].mean())
                                          if valid.any() else None,
                 "model": args.hub_model, "cfg": os.path.basename(cfg)}
        meta_path = os.path.join(seq, "flow_searaft_meta.json")
        with open(meta_path + ".tmp", "w") as f:
            json.dump(stats, f, indent=2)
        os.replace(meta_path + ".tmp", meta_path)
        print("FLOW_OK " + json.dumps(stats), flush=True)


if __name__ == "__main__":
    main()
