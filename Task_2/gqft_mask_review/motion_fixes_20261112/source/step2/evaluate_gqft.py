"""Unseen-environment GQFT evaluation and shortest-history selection."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict

import torch
from torch.utils.data import DataLoader

from step2.dataset import FlowPathDataset, collate_windows
from step2.history_study import (FixedTaskHistoryView,
                                 SignatureRetrievalAccumulator,
                                 select_shortest_history)
from step2.metrics import PathMetricAccumulator
from step2.geometry import camera_model_from_mapping
from step2.models.gqft import GQFT, GQFTConfig
from step2.checkpoint import load_gqft_checkpoint


def parse_histories(text):
    values = sorted(set(int(x) for x in text.split(",")))
    if not values or values[0] < 2:
        raise ValueError("histories must be comma-separated integers >= 2")
    return values


@torch.inference_mode()
def evaluate_history(model, loader, device, max_batches, signature_samples,
                     signature_cosine=0.995):
    metrics = PathMetricAccumulator(model.camera)
    retrieval = SignatureRetrievalAccumulator(
        signature_samples, cosine_threshold=signature_cosine)
    mask_frames = empty_frames = 0
    input_coverage = feature_coverage = 0.0
    for batch_index, batch in enumerate(loader):
        if max_batches and batch_index >= max_batches:
            break
        batch = {k: v.to(device, non_blocking=True) if torch.is_tensor(v) else v
                 for k, v in batch.items()}
        with torch.autocast("cuda", dtype=torch.bfloat16, enabled=device.type == "cuda"):
            output = model(batch["flow"], batch["history_mask"], batch["query_uv"],
                           batch["query_norm"])
        metrics.update(output, batch)
        if "motion_observed" in output:
            real = batch["history_mask"]
            mask_frames += int(real.sum())
            empty_frames += int((~output["motion_observed"].bool() & real).sum())
            input_coverage += float(output["spatial_input_coverage"][real].sum())
            feature_coverage += float(output["spatial_feature_coverage"][real].sum())
        if signature_samples > 0:
            last = batch["history_mask"].long().sum(dim=1).sub(1)
            state = output["state"].gather(
                1, last[:, None, None].expand(-1, 1, output["state"].shape[-1])).squeeze(1)
            retrieval.update(state, batch["displacement"], batch["sequence"])
    result = metrics.compute()
    if mask_frames:
        result.update(mask_frames=mask_frames, empty_mask_frames=empty_frames,
                      empty_mask_fraction=empty_frames / mask_frames,
                      mean_input_coverage=input_coverage / mask_frames,
                      mean_feature_coverage=feature_coverage / mask_frames)
    if signature_samples > 0:
        result.update(retrieval.compute())
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--sequences-root", default=None)
    ap.add_argument("--split", choices=("val", "test"), default="val")
    ap.add_argument("--histories", default="2,3,4,6,8,12,18,24,30")
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--queries", type=int, default=8)
    ap.add_argument("--max-batches", type=int, default=0)
    ap.add_argument("--signature-samples", type=int, default=512)
    ap.add_argument("--signature-cosine", type=float, default=0.995)
    ap.add_argument("--retrieval-tolerance", type=float, default=0.02)
    ap.add_argument("--max-signature-ambiguity", type=float, default=0.05)
    ap.add_argument("--out", default=None)
    ap.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    ap.add_argument("--target-ground-plane", choices=("sequence_floor", "fixed_rig"), default="sequence_floor")
    args = ap.parse_args()
    if args.signature_samples < 0 or args.max_batches < 0 or args.batch_size < 1:
        raise SystemExit("signature-samples/max-batches must be non-negative and batch-size positive")
    if not (0.0 <= args.signature_cosine <= 1.0):
        raise SystemExit("--signature-cosine must be in [0,1]")
    if not (0.0 <= args.max_signature_ambiguity <= 1.0):
        raise SystemExit("--max-signature-ambiguity must be in [0,1]")
    if args.retrieval_tolerance < 0:
        raise SystemExit("--retrieval-tolerance must be non-negative")
    histories = parse_histories(args.histories)
    device = torch.device(args.device)
    model, checkpoint = load_gqft_checkpoint(args.checkpoint, device)
    trained_max_history = int(checkpoint.get("args", {}).get("max_history", 30))
    if max(histories) > trained_max_history:
        raise SystemExit(f"requested history exceeds trained maximum {trained_max_history}")
    reference_history = max(histories)
    extension = int(checkpoint.get("args", {}).get("virtual_extension_px", 0))
    reference_dataset = FlowPathDataset(
        args.manifest, args.split, sequences_root=args.sequences_root,
        min_history=2, max_history=reference_history,
        deterministic_history=reference_history,
        queries=args.queries, seed=20260820, virtual_extension_px=extension,
        target_ground_plane=args.target_ground_plane)
    reference_loader = DataLoader(
        reference_dataset, batch_size=args.batch_size, shuffle=False,
        num_workers=args.workers, pin_memory=device.type == "cuda",
        persistent_workers=args.workers > 0, collate_fn=collate_windows)

    results = []
    for history in histories:
        loader = FixedTaskHistoryView(reference_loader, history)
        metrics = evaluate_history(model, loader, device, args.max_batches,
                                   args.signature_samples, args.signature_cosine)
        metrics["prefix_ade_px"] = metrics["ade_px"]
        record = {"history": history, **metrics}
        results.append(record)
        print("HISTORY " + json.dumps(record), flush=True)

    payload = {"checkpoint": os.path.abspath(args.checkpoint), "split": args.split,
               "model_config": asdict(model.config),
               "target_ground_plane": args.target_ground_plane, "device": args.device,
               "reference_history": reference_history,
               "fixed_reference_tasks": True, "histories": results}
    if args.split == "val":
        selected = select_shortest_history(
            results, retrieval_tolerance=args.retrieval_tolerance,
            max_ambiguity=args.max_signature_ambiguity)
        payload["shortest_sufficient_history"] = selected
        payload["selection_rule"] = {
            "validation_only": True,
            "metric": "cross-sequence nearest-neighbour full 3-D curve mean gap",
            "retrieval_tolerance_from_best_equal_or_longer": args.retrieval_tolerance,
            "max_signature_ambiguity": args.max_signature_ambiguity,
            "signature_cosine": args.signature_cosine,
            "prefix_ade_used_for_selection": False,
        }
        print("HISTORY_SELECTION " + json.dumps({
            "shortest_sufficient_history": selected,
            "validation_only": True}), flush=True)
    else:
        payload["history_selection_performed"] = False
        payload["selection_note"] = "Test data is reporting-only; select history on validation."
    if args.out:
        tmp = args.out + ".tmp"
        with open(tmp, "w") as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp, args.out)


if __name__ == "__main__":
    main()
