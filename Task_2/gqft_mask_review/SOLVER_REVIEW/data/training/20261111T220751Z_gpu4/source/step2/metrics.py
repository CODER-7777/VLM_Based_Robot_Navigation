"""Common pixel-space evaluation for query-conditioned path models."""

from __future__ import annotations

import math

import torch

from .geometry import CameraModel


class PathMetricAccumulator:
    def __init__(self, camera: CameraModel = CameraModel()):
        self.camera = camera
        self.sums = {"ade_px": 0.0, "fde_px": 0.0, "length_mae": 0.0,
                     "endpoint_5px": 0.0, "endpoint_10px": 0.0}
        self.counts = {"ade_px": 0, "queries": 0}

    @torch.no_grad()
    def update(self, output, batch):
        pred = output["uv_norm"].float()
        target = batch["target_uv"][:, :, :pred.shape[2]].float()
        pose_mask = output["pose_mask"]
        valid = batch["target_valid"][:, :, :pred.shape[2]] & pose_mask[:, None]
        scale = pred.new_tensor([self.camera.width - 1, self.camera.height - 1])
        error = torch.linalg.vector_norm((pred - target) * scale, dim=-1)
        self.sums["ade_px"] += float(error[valid].sum().cpu())
        self.counts["ade_px"] += int(valid.sum().cpu())

        true_length = valid.long().sum(dim=2).clamp_min(1)
        last = true_length.sub(1)
        fde = error.gather(2, last[..., None]).squeeze(2)
        query_count = fde.numel()
        self.sums["fde_px"] += float(fde.sum().cpu())
        self.sums["endpoint_5px"] += float((fde <= 5.0).sum().cpu())
        self.sums["endpoint_10px"] += float((fde <= 10.0).sum().cpu())

        predicted_valid = ((output["valid_logits"] >= 0) & output["analytic_valid"] &
                           pose_mask[:, None])
        # A path terminates permanently at the first stop decision.
        predicted_prefix = torch.cumprod(predicted_valid.long(), dim=2)
        predicted_length = predicted_prefix.sum(dim=2)
        self.sums["length_mae"] += float((predicted_length - true_length).abs().sum().cpu())
        self.counts["queries"] += query_count

    def compute(self):
        points = max(self.counts["ade_px"], 1)
        queries = max(self.counts["queries"], 1)
        result = {"ade_px": self.sums["ade_px"] / points}
        for key in ("fde_px", "length_mae", "endpoint_5px", "endpoint_10px"):
            result[key] = self.sums[key] / queries
        result["visible_points"] = self.counts["ade_px"]
        result["queries"] = self.counts["queries"]
        if not all(math.isfinite(v) for k, v in result.items()
                   if k not in {"visible_points", "queries"}):
            raise FloatingPointError(f"non-finite validation metrics: {result}")
        return result


@torch.inference_mode()
def evaluate_loader(model, loader, device, *, max_batches=None, amp=True):
    was_training = model.training
    model.eval()
    camera = getattr(model, "camera", None)
    if camera is None:
        config = getattr(model, "config", None)
        camera = CameraModel(width=int(getattr(config, "image_width", 640)),
                             height=int(getattr(config, "image_height", 360)))
    metrics = PathMetricAccumulator(camera)
    for batch_index, batch in enumerate(loader):
        if max_batches is not None and batch_index >= max_batches:
            break
        batch = {k: v.to(device, non_blocking=True) if torch.is_tensor(v) else v
                 for k, v in batch.items()}
        with torch.autocast(device_type=device.type, dtype=torch.bfloat16,
                            enabled=amp and device.type == "cuda"):
            output = model(batch["flow"], batch["history_mask"], batch["query_uv"],
                           batch["query_norm"])
        metrics.update(output, batch)
    if was_training:
        model.train()
    return metrics.compute()
