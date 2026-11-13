"""Geometry-Constrained Query Flow Transformer (first/main Step-2 architecture)."""

from __future__ import annotations

import math
from dataclasses import dataclass

import torch
import torch.nn as nn
import torch.nn.functional as F

from step2.geometry import (CameraModel, project_displacements_torch, canonical_ground_normal_camera,
                            rotate_about_axis_torch, local_increment_targets_torch, ground_ray_support_torch)
from step2.ground_solver import GroundPlaneSolver, planar_to_camera_increment


@dataclass(frozen=True)
class GQFTConfig:
    d_model: int = 256
    temporal_layers: int = 4
    temporal_heads: int = 8
    dropout: float = 0.1
    max_history: int = 64
    max_step_m: float = 0.12
    max_step_yaw_rad: float = 0.15
    canvas_height: int = 360
    spatial_pooling: str = "attention_max"
    predict_yaw: bool = False
    spatial_mask: str = "none"
    mask_confidence_threshold: float = 0.0
    mask_min_coverage: float = 0.75
    mask_coverage_rule: str = "adaptive"
    mask_soft_floor: float = 0.25
    mask_logit_strength: float = 1.0
    mask_hard_min_coverage: float = 0.0
    mask_ground_near_m: float = 0.5
    mask_ground_far_m: float = 8.0
    motion_integration: str = "keyframe"
    # Optional geometric motion prior (off by default; legacy outputs unchanged).
    motion_prior: str = "none"
    ground_max_floor_m: float = 1.5
    ground_iterations: int = 6
    ground_learned_weights: bool = False
    ground_residual_m: float = 0.03
    ground_residual_yaw_rad: float = 0.05

    def __post_init__(self):
        if self.motion_prior not in {"none", "ground_solver"}:
            raise ValueError("motion_prior must be none or ground_solver")
        if self.motion_prior == "ground_solver":
            if self.motion_integration != "yaw_local":
                raise ValueError("ground_solver predicts local planar steps; requires yaw_local integration")
            if not (0 < self.ground_max_floor_m < 50 and self.ground_iterations >= 1
                    and self.ground_residual_m >= 0 and self.ground_residual_yaw_rad >= 0):
                raise ValueError("Invalid ground solver settings")
        if self.spatial_mask not in {"none", "validity", "confidence", "soft_validity",
                                     "soft_confidence", "soft_confidence_ground"}:
            raise ValueError("Unknown spatial_mask")
        if self.spatial_mask != "none" and self.spatial_pooling != "attention_max":
            raise ValueError("Spatial masking requires attention_max pooling")
        if not 0.0 <= self.mask_confidence_threshold <= 1.0:
            raise ValueError("mask_confidence_threshold must be in [0,1]")
        if self.spatial_mask == "confidence" and self.mask_confidence_threshold <= 0:
            raise ValueError("Confidence masking requires an explicit positive threshold")
        if not 0.0 < self.mask_min_coverage <= 1.0:
            raise ValueError("mask_min_coverage must be in (0,1]")
        if self.mask_coverage_rule not in {"adaptive", "receptive_field"}:
            raise ValueError("mask_coverage_rule must be adaptive or receptive_field")
        if not 0 < self.mask_soft_floor <= 1 or not math.isfinite(self.mask_logit_strength) or self.mask_logit_strength < 0:
            raise ValueError("Require soft floor in (0,1] and finite nonnegative logit strength")
        if not 0 <= self.mask_hard_min_coverage <= 1:
            raise ValueError("mask_hard_min_coverage must be in [0,1]")
        if not (0 < self.mask_ground_near_m < self.mask_ground_far_m < float('inf')):
            raise ValueError("Require finite 0 < near depth < far depth")
        if self.motion_integration not in {"keyframe", "yaw_local"}:
            raise ValueError("motion_integration must be keyframe or yaw_local")
        if self.motion_integration == "yaw_local" and not self.predict_yaw:
            raise ValueError("yaw_local integration requires predict_yaw")


class ConvBlock(nn.Sequential):
    def __init__(self, cin, cout, stride=2):
        super().__init__(nn.Conv2d(cin, cout, 3, stride=stride, padding=1, bias=False),
                         nn.GroupNorm(min(8, cout), cout), nn.GELU())


class FlowFrameEncoder(nn.Module):
    """Encode one dense confidence-masked flow field into a global ego-motion token."""

    def __init__(self, d_model, spatial_pooling="attention_max", *, spatial_mask="none",
                 mask_confidence_threshold=0.0, mask_min_coverage=0.75,
                 mask_coverage_rule="adaptive", mask_soft_floor=.25, mask_logit_strength=1.,
                 mask_hard_min_coverage=0., mask_ground_near_m=.5, mask_ground_far_m=8., camera=None):
        super().__init__()
        GQFTConfig(spatial_pooling=spatial_pooling, spatial_mask=spatial_mask,
                   mask_confidence_threshold=mask_confidence_threshold,
                   mask_min_coverage=mask_min_coverage, mask_coverage_rule=mask_coverage_rule,
                   mask_soft_floor=mask_soft_floor, mask_logit_strength=mask_logit_strength,
                   mask_hard_min_coverage=mask_hard_min_coverage,
                   mask_ground_near_m=mask_ground_near_m, mask_ground_far_m=mask_ground_far_m)
        self.spatial_mask = spatial_mask
        self.mask_confidence_threshold = mask_confidence_threshold
        self.mask_min_coverage = mask_min_coverage
        self.mask_coverage_rule = mask_coverage_rule
        self.mask_soft_floor = mask_soft_floor
        self.mask_logit_strength = mask_logit_strength
        self.mask_hard_min_coverage = mask_hard_min_coverage
        self.mask_ground_near_m, self.mask_ground_far_m = mask_ground_near_m, mask_ground_far_m
        self.camera = camera or CameraModel()
        self.soft_mask = spatial_mask.startswith("soft_")
        self.net = nn.Sequential(ConvBlock(6, 32), ConvBlock(32, 64), ConvBlock(64, 128),
                                 ConvBlock(128, d_model))
        if spatial_pooling not in {"mean_max", "attention_max"}:
            raise ValueError(f"Unknown spatial pooling: {spatial_pooling}")
        self.spatial_pooling = spatial_pooling
        if spatial_pooling == "attention_max":
            self.attention = nn.Sequential(
                nn.Conv2d(d_model, d_model // 2, kernel_size=1),
                nn.GELU(),
                nn.Conv2d(d_model // 2, 1, kernel_size=1),
            )
        self.pool = nn.Linear(2 * d_model, d_model)

    def pixel_eligibility(self, flow):
        """Reliability only: no semantic categories, route labels, or image overlays."""
        eligible = (flow[:, 3:4] > 0.5) & torch.isfinite(flow).all(dim=1, keepdim=True)
        if self.spatial_mask == "confidence":
            eligible = eligible & (flow[:, 2:3] >= self.mask_confidence_threshold)
        return eligible

    def coverage(self, values, shape):
        if self.mask_coverage_rule == "adaptive":
            return F.adaptive_avg_pool2d(values.float(), shape)
        pooled = F.avg_pool2d(values.float(), 31, 16, 15, count_include_pad=False)
        if pooled.shape[-2:] != shape:
            raise ValueError("Convolution support shape differs from CNN features")
        return pooled

    def soft_weights(self, logits, flow, pixel_mask):
        shape = logits.shape[-2:]
        coverage = self.coverage(pixel_mask, shape)
        evidence = pixel_mask.float()
        if self.spatial_mask != "soft_validity":
            confidence = torch.nan_to_num(flow[:, 2:3].float(), nan=0., posinf=0., neginf=0.).clamp(0, 1)
            evidence = evidence * confidence
        reliability = self.coverage(evidence, shape)
        geo_coverage = torch.ones_like(reliability)
        if self.spatial_mask == "soft_confidence_ground":
            support = ground_ray_support_torch(self.camera, *flow.shape[-2:],
                         near_m=self.mask_ground_near_m, far_m=self.mask_ground_far_m, device=flow.device)
            geo_coverage = self.coverage(support, shape).expand_as(reliability)
            reliability = reliability * geo_coverage
        # Floor preserves weak evidence; exact VC average avoids counting validity twice.
        reliability = self.mask_soft_floor + (1-self.mask_soft_floor) * reliability
        original = logits.flatten(1).softmax(-1).view_as(logits)
        biased_logits = logits.float() + self.mask_logit_strength * reliability.log()
        mask = coverage >= self.mask_hard_min_coverage
        observed = pixel_mask.flatten(1).any(1)
        any_cell = mask.flatten(1).any(1)
        flat = biased_logits.flatten(1).masked_fill(~mask.flatten(1), -torch.inf)
        flat = torch.where(any_cell[:, None], flat, torch.zeros_like(flat))
        weights = flat.softmax(-1).view_as(logits).masked_fill(~mask, 0)
        constant = reliability.flatten(1).amax(1) == reliability.flatten(1).amin(1)
        neutral = (constant | (self.mask_logit_strength == 0)) & mask.flatten(1).all(1)
        weights = torch.where(neutral[:, None, None, None], original, weights).to(logits.dtype)
        diagnostics = {"motion_observed": observed,
                       "spatial_input_coverage": pixel_mask.float().mean((1, 2, 3)),
                       "spatial_feature_coverage": mask.float().mean((1, 2, 3)),
                       "pixel_mask": pixel_mask, "feature_mask": mask,
                       "feature_reliability": reliability, "feature_valid_coverage": coverage,
                       "ground_prior_coverage": geo_coverage}
        return weights, diagnostics

    def forward(self, flow, *, return_diagnostics=False):
        # flow [N,4,H,W] = normalized du,dv,confidence,validity; coordinates are structural constants.
        n, _, h, w = flow.shape
        yy, xx = torch.meshgrid(torch.linspace(-1, 1, h, device=flow.device, dtype=flow.dtype),
                                torch.linspace(-1, 1, w, device=flow.device, dtype=flow.dtype),
                                indexing="ij")
        xy = torch.stack([xx, yy])[None].expand(n, -1, -1, -1)
        pixel_mask = None
        if self.spatial_mask != "none":
            pixel_mask = self.pixel_eligibility(flow)
            if self.soft_mask:
                # Preserve finite cached inputs/max features; sanitize only nonfinite pixels.
                flow = flow.masked_fill(~torch.isfinite(flow).all(1, keepdim=True), 0.)
            else:
                flow = flow.masked_fill(~pixel_mask, 0.0)
        feat = self.net(torch.cat([flow, xy], dim=1))
        diagnostics = {}
        if self.spatial_pooling == "attention_max":
            attn_logits=self.attention(feat)
            b,_,fh,fw=attn_logits.shape
            if self.soft_mask:
                attn_weights, diagnostics = self.soft_weights(attn_logits, flow, pixel_mask)
                max_pooled = feat.amax((-2, -1))
            elif pixel_mask is not None:
                # Coverage of adaptive grid cells, not a claim of pure receptive fields.
                coverage = self.coverage(pixel_mask, (fh, fw))
                feature_mask = coverage >= self.mask_min_coverage
                observed = feature_mask.flatten(1).any(dim=1)
                logits = attn_logits.float().flatten(1).masked_fill(~feature_mask.flatten(1), -torch.inf)
                # Softmax must never receive an all -inf row.
                logits = torch.where(observed[:, None], logits, torch.zeros_like(logits))
                attn_weights = torch.softmax(logits, dim=-1).view(b, 1, fh, fw)
                attn_weights = attn_weights.masked_fill(~feature_mask, 0).to(feat.dtype)
                max_pooled = feat.masked_fill(~feature_mask, -torch.inf).amax((-2, -1))
                max_pooled = torch.where(observed[:, None], max_pooled, torch.zeros_like(max_pooled))
                diagnostics = {"motion_observed": observed,
                               "spatial_input_coverage": pixel_mask.float().mean((1, 2, 3)),
                               "spatial_feature_coverage": feature_mask.float().mean((1, 2, 3))}
                if return_diagnostics:
                    diagnostics.update(pixel_mask=pixel_mask, feature_mask=feature_mask,
                                       feature_reliability=coverage)
            else:
                attn_weights=torch.softmax(attn_logits.view(b,-1),dim=-1).view(b,1,fh,fw)
                max_pooled = feat.amax((-2, -1))
            attn_pooled=(feat*attn_weights).sum(dim=(-2,-1))
            if return_diagnostics:
                diagnostics["attention_weights"] = attn_weights
        else:
            attn_pooled = feat.mean((-2, -1))
            max_pooled = feat.amax((-2, -1))
        pooled = torch.cat([attn_pooled,max_pooled], dim=-1)
        token = self.pool(pooled)
        if pixel_mask is not None and not self.soft_mask:
            # A missing observation is not a measured zero-motion increment. Keep its time
            # slot; the causal model may infer motion from history. Consumers get a flag.
            token = torch.where(observed[:, None], token, torch.zeros_like(token))
        return (token, diagnostics) if return_diagnostics else token


class GQFT(nn.Module):
    """Infer one 3-D camera-centre curve and analytically project it for arbitrary queries."""

    def __init__(self, config: GQFTConfig = GQFTConfig(), camera: CameraModel = CameraModel()):
        super().__init__()
        self.config = config
        self.camera = camera
        d = config.d_model
        self.flow_encoder = FlowFrameEncoder(
            d, config.spatial_pooling, spatial_mask=config.spatial_mask,
            mask_confidence_threshold=config.mask_confidence_threshold,
            mask_min_coverage=config.mask_min_coverage, mask_coverage_rule=config.mask_coverage_rule,
            mask_soft_floor=config.mask_soft_floor, mask_logit_strength=config.mask_logit_strength,
            mask_hard_min_coverage=config.mask_hard_min_coverage,
            mask_ground_near_m=config.mask_ground_near_m, mask_ground_far_m=config.mask_ground_far_m,
            camera=camera)
        self.time_embed = nn.Parameter(torch.randn(1, config.max_history, d) * 0.01)
        layer = nn.TransformerEncoderLayer(d, config.temporal_heads, 4 * d, config.dropout,
                                           activation="gelu", batch_first=True, norm_first=True)
        self.temporal = nn.TransformerEncoder(layer, config.temporal_layers, norm=nn.LayerNorm(d))
        self.delta_head = nn.Sequential(nn.Linear(d, d), nn.GELU(), nn.Linear(d, 3))
        if config.predict_yaw:
            self.yaw_head=nn.Sequential(nn.Linear(d,d//2),nn.GELU(),nn.Linear(d//2,1))
        self.logvar_head = nn.Sequential(nn.Linear(d, d // 2), nn.GELU(), nn.Linear(d // 2, 3))
        self.start_state = nn.Parameter(torch.zeros(1, 1, d))
        self.query_encoder = nn.Sequential(nn.Linear(2, d), nn.GELU(), nn.Linear(d, d))
        self.time_for_valid = nn.Linear(d, d)
        self.query_for_valid = nn.Linear(d, d)
        self.valid_head = nn.Linear(d, 1)
        if config.motion_prior == "ground_solver":
            self.ground_solver = GroundPlaneSolver(
                camera, max_floor_m=config.ground_max_floor_m, iterations=config.ground_iterations,
                learned_weights=config.ground_learned_weights)
            # Solver step + reliability summary -> token; zero init leaves tokens unchanged at start.
            self.solver_embed = nn.Linear(5, d)
            nn.init.zeros_(self.solver_embed.weight)
            nn.init.zeros_(self.solver_embed.bias)
            # Heads now predict bounded residuals; zero last layers so training starts at the solver.
            for head in (self.delta_head, self.yaw_head):
                nn.init.zeros_(head[-1].weight)
                nn.init.zeros_(head[-1].bias)

    def forward(self, flow, history_mask, query_uv, query_norm=None):
        b, t, c, h, w = flow.shape
        if t > self.config.max_history:
            raise ValueError(f"history {t} exceeds configured maximum {self.config.max_history}")
        if c != 4:
            raise ValueError(f"expected 4 flow channels, got {c}")
        reliability = {}
        if self.config.spatial_mask != "none":
            encoded, diagnostics = self.flow_encoder(flow.reshape(b * t, c, h, w), return_diagnostics=True)
            token = encoded.reshape(b, t, -1)
            for key in ("motion_observed", "spatial_input_coverage", "spatial_feature_coverage"):
                reliability[key] = diagnostics[key].reshape(b, t) * history_mask
        else:
            token = self.flow_encoder(flow.reshape(b * t, c, h, w)).reshape(b, t, -1)
        ground = self.config.motion_prior == "ground_solver"
        if ground:
            solver_motion, solver_info = self.ground_solver(flow.reshape(b * t, c, h, w))
            solver_motion = solver_motion.reshape(b, t, 3) * history_mask[..., None]
            summary = torch.cat([
                solver_motion[..., :2] / self.config.max_step_m,
                solver_motion[..., 2:] / self.config.max_step_yaw_rad,
                solver_info["weight_sum"].reshape(b, t, 1).clamp_min(1e-6).log() / 10,
                solver_info["residual_rms_px"].reshape(b, t, 1).clamp(max=20) / 10], -1)
            token = token + self.solver_embed(summary.to(token.dtype))
        token = token + self.time_embed[:, :t]
        causal = torch.triu(torch.ones(t, t, device=flow.device, dtype=torch.bool), diagonal=1)
        state = self.temporal(token, mask=causal, src_key_padding_mask=~history_mask)
        if ground:
            residual = torch.tanh(self.delta_head(state).float()) * self.config.ground_residual_m
            delta = planar_to_camera_increment(solver_motion, self.camera.pitch_down_deg) + residual
        else:
            delta = torch.tanh(self.delta_head(state)) * self.config.max_step_m
        delta = delta * history_mask[..., None]
        displacement = torch.cat([torch.zeros_like(delta[:, :1]), torch.cumsum(delta, dim=1)], dim=1)

        yaw_output = {}
        if self.config.predict_yaw:
            if ground:
                delta_yaw = (solver_motion[..., 2:] + torch.tanh(self.yaw_head(state).float())
                             * self.config.ground_residual_yaw_rad)
            else:
                delta_yaw=torch.tanh(self.yaw_head(state))*self.config.max_step_yaw_rad
            delta_yaw=delta_yaw*history_mask[...,None]
            yaw=torch.cat([torch.zeros_like(delta_yaw[:,:1]),torch.cumsum(delta_yaw,dim=1)],dim=1)
            yaw_output = {"delta_yaw": delta_yaw, "yaw": yaw}
        if self.config.motion_integration == "yaw_local":
            # New semantic mode only: previous yaw rotates local increments into camera0.
            delta_local = delta.float()
            delta_yaw = delta_yaw.float()
            yaw = torch.cat([torch.zeros_like(delta_yaw[:, :1]), delta_yaw.cumsum(1)], 1)
            axis = delta_local.new_tensor(canonical_ground_normal_camera(self.camera.pitch_down_deg))
            delta = rotate_about_axis_torch(delta_local, yaw[:, :-1, 0], axis)
            displacement = torch.cat([torch.zeros_like(delta[:, :1]), delta.cumsum(1)], 1)
            yaw_output.update(delta_yaw=delta_yaw, yaw=yaw, delta_local=delta_local, motion_up_axis=axis)
        logvar = self.logvar_head(state).clamp(-6.0, 3.0)

        uv_px, analytic_valid = project_displacements_torch(
            displacement, query_uv, self.camera,
            (self.camera.width, self.config.canvas_height))
        uv_norm = uv_px.clone()
        uv_norm[..., 0] /= self.camera.width - 1
        uv_norm[..., 1] /= self.camera.height - 1

        if query_norm is None:
            query_norm = query_uv.clone()
            query_norm[..., 0] /= self.camera.width - 1
            query_norm[..., 1] /= self.camera.height - 1
        qstate = self.query_encoder(query_norm)
        all_state = torch.cat([self.start_state.repeat(b, 1, 1), state], dim=1)
        joint = torch.tanh(self.time_for_valid(all_state)[:, None] +
                           self.query_for_valid(qstate)[:, :, None])
        valid_logits = self.valid_head(joint).squeeze(-1)
        pose_mask = torch.cat([torch.ones_like(history_mask[:, :1]), history_mask], dim=1)
        if ground:
            reliability.update(solver_motion=solver_motion,
                               solver_weight_sum=solver_info["weight_sum"].reshape(b, t),
                               solver_residual_rms_px=solver_info["residual_rms_px"].reshape(b, t))
        return {"delta": delta, "displacement": displacement, "motion_logvar": logvar,
                **yaw_output, **reliability,
                "uv_px": uv_px, "uv_norm": uv_norm, "analytic_valid": analytic_valid,
                "valid_logits": valid_logits, "pose_mask": pose_mask, "state": state}


def _masked_mean(value, mask):
    mask = mask.to(value.dtype)
    while mask.ndim < value.ndim:
        mask = mask.unsqueeze(-1)
    return (value * mask).sum() / mask.expand_as(value).sum().clamp_min(1.0)


def gqft_loss(output, batch, *, motion_weight=4.0, path_weight=1.0,
              endpoint_weight=1.0, valid_weight=0.25, uncertainty_weight=0.05,yaw_weight=2.0):
    pose_mask = output["pose_mask"]
    target_disp = batch["displacement"][:, :output["displacement"].shape[1]]
    disp_error = F.smooth_l1_loss(output["displacement"], target_disp, reduction="none", beta=0.01)
    motion = _masked_mean(disp_error, pose_mask)
    target_delta = target_disp[:, 1:] - target_disp[:, :-1]
    predicted_delta = output["delta"]
    if "delta_local" in output:
        if "target_yaw" not in batch:
            raise ValueError("Local-frame integration training requires ground-truth yaw")
        target_delta = local_increment_targets_torch(target_disp, batch["target_yaw"][:, :target_disp.shape[1]],
                                                      output["motion_up_axis"])
        predicted_delta = output["delta_local"]
    delta_sq = (predicted_delta - target_delta).square()
    motion_nll = _masked_mean(0.5 * (delta_sq * (-output["motion_logvar"]).exp() +
                              output["motion_logvar"]),
                              pose_mask[:, 1:])

    target_uv = batch["target_uv"][:, :, :output["uv_norm"].shape[2]]
    target_valid = batch["target_valid"][:, :, :output["uv_norm"].shape[2]]
    supervised = target_valid & pose_mask[:, None]
    path_error = F.smooth_l1_loss(output["uv_norm"], target_uv, reduction="none", beta=0.005)
    path = _masked_mean(path_error, supervised)

    # Endpoint for each query is its last target-valid point, not the padded batch endpoint.
    last = supervised.long().sum(dim=2).sub(1).clamp_min(0)
    gather = last[..., None, None].expand(-1, -1, 1, 2)
    pred_end = output["uv_norm"].gather(2, gather).squeeze(2)
    true_end = target_uv.gather(2, gather).squeeze(2)
    endpoint = F.smooth_l1_loss(pred_end, true_end, beta=0.005)

    valid_domain = pose_mask[:, None].expand_as(target_valid)
    visibility = F.binary_cross_entropy_with_logits(output["valid_logits"][valid_domain],
                                                     target_valid[valid_domain].float())

    if "target_yaw" in batch and "yaw" in output:
        target_yaw=batch["target_yaw"][:,:output["yaw"].shape[1]]
        if "delta_local" in output:
            residual = output["yaw"] - target_yaw
            wrapped = torch.atan2(torch.sin(residual), torch.cos(residual))
            yaw_err = F.smooth_l1_loss(wrapped, torch.zeros_like(wrapped), reduction="none", beta=.01)
        else:
            yaw_err=F.smooth_l1_loss(output["yaw"],target_yaw,reduction="none",beta=0.01)
        yaw_loss=_masked_mean(yaw_err,pose_mask)
    else:
        yaw_loss=torch.tensor(0.0,device=output["displacement"].device)

    total = (motion_weight * motion + path_weight * path + endpoint_weight * endpoint +
             valid_weight * visibility + uncertainty_weight * motion_nll+ yaw_weight*yaw_loss)

    return {"loss": total, "motion": motion.detach(), "path": path.detach(),
            "endpoint": endpoint.detach(), "visibility": visibility.detach(),
            "motion_nll": motion_nll.detach(),"yaw":yaw_loss.detach()}
