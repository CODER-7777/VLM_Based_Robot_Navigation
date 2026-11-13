"""Score the zero-training ground-plane solver with the GQFT evaluation protocol (CPU).

Protocol (matches step2/evaluate_gqft.py): reference windows of `--reference-history`
pairs, model input truncated to `--history`, same queries/seed/labels and the same
PathMetricAccumulator. Adds direct 3-D displacement and yaw errors, plus per-window
records so sequence-level bootstrap intervals can be computed later.

Cutoff selection is leakage-safe: `--select-split train` sweeps `--floor-cutoffs` on
training scenes and picks the lowest train ADE; only that cutoff is reported as the
primary validation result. Other validation cutoffs are written as clearly labelled
sensitivity rows. Never pass --split test while choosing settings.

Example (ISL, CPU):
  python tools/evaluate_ground_solver.py --manifest results/hsgm_manifest_v1.json \
      --split val --history 24 --out results/ground_solver_val_h24.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import hashlib
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Subset

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from step2.dataset import FlowPathDataset, collate_windows  # noqa: E402
from step2.geometry import (canonical_ground_normal_camera, project_displacements_torch,  # noqa: E402
                            rotate_about_axis_torch)
from step2.ground_solver import GroundPlaneSolver, planar_to_camera_increment  # noqa: E402
from step2.history_study import FixedTaskHistoryView  # noqa: E402
from step2.metrics import PathMetricAccumulator  # noqa: E402
from step2.checkpoint import load_gqft_checkpoint  # noqa: E402


class SolverOnly(nn.Module):
    """Same output contract as GQFT, with motion taken purely from the floor solver."""

    def __init__(self, camera, max_floor_m, iterations=6, canvas_height=None):
        super().__init__()
        self.camera = camera
        self.canvas_height = canvas_height or camera.height
        self.solver = GroundPlaneSolver(camera, max_floor_m=max_floor_m, iterations=iterations)

    def forward(self, flow, history_mask, query_uv, query_norm=None):
        b, t, c, h, w = flow.shape
        motion, info = self.solver(flow.reshape(b * t, c, h, w))
        motion = motion.reshape(b, t, 3) * history_mask[..., None]
        local = planar_to_camera_increment(motion, self.camera.pitch_down_deg)
        yaw = torch.cat([motion.new_zeros(b, 1), motion[..., 2].cumsum(1)], 1)
        axis = local.new_tensor(canonical_ground_normal_camera(self.camera.pitch_down_deg))
        delta = rotate_about_axis_torch(local, yaw[:, :-1], axis)
        disp = torch.cat([delta.new_zeros(b, 1, 3), delta.cumsum(1)], 1)
        uv_px, analytic = project_displacements_torch(disp, query_uv, self.camera,
                                                      (self.camera.width, self.canvas_height))
        uv_norm = uv_px.clone()
        uv_norm[..., 0] /= self.camera.width - 1
        uv_norm[..., 1] /= self.camera.height - 1
        pose_mask = torch.cat([torch.ones_like(history_mask[:, :1]), history_mask], 1)
        return {"uv_norm": uv_norm, "analytic_valid": analytic, "pose_mask": pose_mask,
                "valid_logits": analytic.float() * 20 - 10, "displacement": disp,
                "yaw": yaw[..., None], "weight_sum": info["weight_sum"].reshape(b, t)}


@torch.inference_mode()
def score(model, loader, device="cpu"):
    metrics = PathMetricAccumulator(model.camera)
    windows = []
    for batch_index, batch in enumerate(loader):
        batch = {k: v.to(device) if torch.is_tensor(v) else v for k, v in batch.items()}
        out = model(batch["flow"], batch["history_mask"], batch["query_uv"], batch["query_norm"])
        metrics.update(out, batch)
        n = out["displacement"].shape[1]
        err = torch.linalg.vector_norm(out["displacement"] - batch["displacement"][:, :n], dim=-1)
        yaw_err = torch.atan2(torch.sin(out["yaw"] - batch["target_yaw"][:, :n]),
                              torch.cos(out["yaw"] - batch["target_yaw"][:, :n])).abs()[..., 0]
        normal = err.new_tensor(canonical_ground_normal_camera(model.camera.pitch_down_deg))
        diff = out["displacement"] - batch["displacement"][:, :n]
        ground_err = torch.linalg.vector_norm(diff - (diff * normal).sum(-1, keepdim=True) * normal, dim=-1)
        for i in range(err.shape[0]):
            row = {"sequence": batch["sequence"][i], "start": int(batch["start"][i]),
                            "query_uv": batch["query_uv"][i].tolist(),
                            "mean_3d_err_m": float(err[i, 1:].mean()),
                            "end_3d_err_m": float(err[i, -1]),
                            "mean_ground_err_m": float(ground_err[i, 1:].mean()),
                            "end_ground_err_m": float(ground_err[i, -1]),
                            "end_yaw_err_deg": float(torch.rad2deg(yaw_err[i, -1]))}
            if "weight_sum" in out:
                row["min_weight_sum"] = float(out["weight_sum"][i].min())
                row["low_support_frames"] = int((out["weight_sum"][i] < 1e-6).sum())
            windows.append(row)
        if batch_index % 10 == 0:
            print(f"SCORE windows={len(windows)}", flush=True)
    result = metrics.compute()
    for key in ("mean_3d_err_m", "end_3d_err_m", "mean_ground_err_m", "end_ground_err_m", "end_yaw_err_deg"):
        result[key] = sum(w[key] for w in windows) / max(len(windows), 1)
    if windows and "low_support_frames" in windows[0]:
        result["low_support_frames"] = sum(w["low_support_frames"] for w in windows)
    return result, windows


def build_loader(args, split, max_windows):
    ds = FlowPathDataset(args.manifest, split, sequences_root=args.sequences_root, min_history=2,
                         max_history=args.reference_history, deterministic_history=args.reference_history,
                         queries=args.queries, seed=20260820, target_ground_plane=args.target_ground_plane,
                         virtual_extension_px=args.virtual_extension_px)
    if max_windows and len(ds) > max_windows:
        step = len(ds) / max_windows  # evenly spaced, deterministic subset
        ds = Subset(ds, [int(i * step) for i in range(max_windows)])
    loader = DataLoader(ds, batch_size=args.batch_size, shuffle=False, num_workers=args.workers,
                        collate_fn=collate_windows)
    camera = (ds.dataset if isinstance(ds, Subset) else ds).camera
    return FixedTaskHistoryView(loader, args.history), camera


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--sequences-root", default=None)
    ap.add_argument("--split", choices=("val", "test"), default="val")
    ap.add_argument("--select-split", choices=("train", "none"), default="train")
    ap.add_argument("--floor-cutoffs", default="1.0,1.5,2.0,3.0,6.0")
    ap.add_argument("--fixed-cutoff", type=float, default=None,
                    help="Use a cutoff chosen earlier on training data (required with --split test)")
    ap.add_argument("--max-train-windows", type=int, default=300)
    ap.add_argument("--history", type=int, default=24)
    ap.add_argument("--reference-history", type=int, default=30)
    ap.add_argument("--queries", type=int, default=1)
    ap.add_argument("--virtual-extension-px", type=int, default=270)
    ap.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    ap.add_argument("--comparison-checkpoint", action="append", nargs=2, default=[], metavar=("LABEL", "PATH"))
    ap.add_argument("--validation-sensitivity", action="store_true",
                    help="Exploratory sensitivity only; omitted by default to keep validation single-pass")
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--target-ground-plane", choices=("sequence_floor", "fixed_rig"), default="sequence_floor")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    if args.history < 2 or args.history > args.reference_history or args.queries < 1 or args.batch_size < 1:
        raise SystemExit("Require 2 <= history <= reference-history and positive queries/batch size")
    if args.virtual_extension_px < 0 or args.max_train_windows < 1:
        raise SystemExit("Require nonnegative extension and positive training subset size")
    if args.device == "cuda" and not torch.cuda.is_available():
        raise SystemExit("CUDA requested but unavailable")
    if args.split == "test" and args.fixed_cutoff is None:
        raise SystemExit("Test reporting needs --fixed-cutoff selected on training data")
    cutoffs = [float(x) for x in args.floor_cutoffs.split(",")]
    torch.set_grad_enabled(False)

    selection = []
    if args.fixed_cutoff is not None:
        chosen = args.fixed_cutoff
    elif args.select_split == "train":
        loader, camera = build_loader(args, "train", args.max_train_windows)
        for cut in cutoffs:
            model = SolverOnly(camera, cut, canvas_height=camera.height + args.virtual_extension_px).to(args.device)
            res, _ = score(model, loader, args.device)
            selection.append({"cutoff_m": cut, **res})
            print("TRAIN " + json.dumps(selection[-1]), flush=True)
        chosen = min(selection, key=lambda r: r["ade_px"])["cutoff_m"]
    else:
        raise SystemExit("Choose --select-split train or pass --fixed-cutoff")

    loader, camera = build_loader(args, args.split, 0)
    model = SolverOnly(camera, chosen, canvas_height=camera.height + args.virtual_extension_px).to(args.device)
    primary, windows = score(model, loader, args.device)
    print(f"PRIMARY {args.split} cutoff={chosen} " + json.dumps(primary), flush=True)
    sensitivity = []
    if args.split == "val" and args.validation_sensitivity:
        for cut in cutoffs:
            if cut != chosen:
                other = SolverOnly(camera, cut, canvas_height=camera.height + args.virtual_extension_px).to(args.device)
                res, _ = score(other, loader, args.device)
                sensitivity.append({"cutoff_m": cut, **res})
                print("VAL_SENSITIVITY " + json.dumps(sensitivity[-1]), flush=True)

    comparisons = []
    for label, path in args.comparison_checkpoint:
        reference, checkpoint = load_gqft_checkpoint(path, args.device)
        if reference.camera != camera or reference.config.canvas_height != camera.height + args.virtual_extension_px:
            raise ValueError("Comparison checkpoint camera/canvas does not match the scoring protocol")
        res, records = score(reference, loader, args.device)
        comparisons.append({"label": label, "checkpoint": path,
                            "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                            "metrics": res, "windows": records})
        print("COMPARISON " + json.dumps({"label": label, **res}), flush=True)
        del reference
    payload = {"method": "zero-training ground-plane solver", "split": args.split,
               "history": args.history, "reference_history": args.reference_history,
               "protocol": {"queries": args.queries, "virtual_extension_px": args.virtual_extension_px,
                            "canvas": [camera.width, camera.height + args.virtual_extension_px],
                            "seed": 20260820, "stride": 5, "device": args.device,
                            "precision": "float32", "pixel_origin_included": True,
                            "direct_motion_origin_excluded": True,
                            "max_train_windows": args.max_train_windows},
               "target_ground_plane": args.target_ground_plane, "camera": vars(camera) if hasattr(camera, "__dict__") else str(camera),
               "chosen_cutoff_m": chosen, "cutoff_selected_on": "train" if selection else "fixed",
               "train_selection": selection, "primary": primary,
               "validation_sensitivity_not_for_selection": sensitivity, "windows": windows,
               "comparisons": comparisons}
    if args.out:
        tmp = args.out + ".tmp"
        with open(tmp, "w") as f:
            json.dump(payload, f, indent=2, default=str)
        os.replace(tmp, args.out)


if __name__ == "__main__":
    main()
