"""Differentiable ground-plane ego-motion solver for one flow pair.

The rig is fixed (known height, pitch, intrinsics), so flow on nearby floor pixels
determines planar camera motion (forward, left, yaw) in metres/radians with no
learning. We solve a weighted, robust 3-parameter least-squares problem with a few
damped Gauss-Newton steps (the DPVO recipe of learned weights + differentiable
solver, reduced to 3 unknowns). Gradients flow through the solve, so optional
learned per-pixel weights are trained by the trajectory loss.

Conventions (match geometry.py / episode_contract.py):
  body frame: x forward, y left, z up; positive yaw = left turn about world-up.
  camera frame: OpenCV (x right, y down, z forward), pitched down by `pitch_down_deg`.
  flow channels: [du/W, dv/H, confidence, validity] on a resized grid.

Assumptions: flat floor at the rig height and a static scene. Pixels whose floor
ray lands farther than `max_floor_m` are excluded, because nearby furniture/walls
violate the floor assumption more often at long range. Robust (soft-L1) weights
down-weight the remaining violations; they do not segment the floor.
"""

from __future__ import annotations

import math

import torch
import torch.nn as nn

from step2.geometry import CameraModel


def body_to_camera_matrix(pitch_down_deg: float) -> torch.Tensor:
    """Rows are camera axes in body (forward, left, up) coordinates."""
    p = math.radians(pitch_down_deg)
    s, c = math.sin(p), math.cos(p)
    return torch.tensor([[0., -1., 0.], [-s, 0., -c], [c, 0., -s]], dtype=torch.float64)


def planar_to_camera_increment(motion: torch.Tensor, pitch_down_deg: float) -> torch.Tensor:
    """[...,3] (forward, left, yaw) -> [...,3] camera-frame translation of that step."""
    p = math.radians(pitch_down_deg)
    forward = motion.new_tensor([0., -math.sin(p), math.cos(p)])
    left = motion.new_tensor([-1., 0., 0.])
    return motion[..., :1] * forward + motion[..., 1:2] * left


class GroundPlaneSolver(nn.Module):
    """Flow [N,4,H,W] -> planar motion [N,3] = (forward m, left m, yaw rad)."""

    def __init__(self, camera: CameraModel, *, max_floor_m: float = 1.5, iterations: int = 6,
                 robust_scale_px: float = 2.0, damping: float = 1e-4, floor_softness_m: float = .05,
                 learned_weights: bool = False):
        super().__init__()
        if not (0 < max_floor_m < 50) or iterations < 1 or robust_scale_px <= 0 or damping <= 0:
            raise ValueError("Require 0<max_floor_m<50, iterations>=1, positive robust scale/damping")
        self.camera = camera
        self.max_floor_m, self.iterations = float(max_floor_m), int(iterations)
        self.robust_scale_px, self.damping = float(robust_scale_px), float(damping)
        self.floor_softness_m = float(floor_softness_m)
        self.learned_weights = bool(learned_weights)
        if learned_weights:
            # Inputs: du, dv, confidence, validity and calibrated ray tangents (TartanVO-style).
            self.weight_net = nn.Sequential(
                nn.Conv2d(6, 16, 3, padding=1), nn.GELU(),
                nn.Conv2d(16, 16, 3, padding=1), nn.GELU(),
                nn.Conv2d(16, 1, 1))
            # Weight = 2*sigmoid(0) = 1 everywhere at init: training starts from the pure solver.
            nn.init.zeros_(self.weight_net[-1].weight)
            nn.init.zeros_(self.weight_net[-1].bias)
        self._grid_cache: dict = {}

    @torch.inference_mode(False)
    def grid(self, h: int, w: int, device):
        # Initial validation runs in inference_mode. Cached geometry must remain
        # ordinary tensors so a later learned-weight solve can save it for backward.
        key = (h, w, str(device))
        if key not in self._grid_cache:
            cam = self.camera
            v = (torch.arange(h, dtype=torch.float64) + .5) * cam.height / h - .5
            u = (torch.arange(w, dtype=torch.float64) + .5) * cam.width / w - .5
            vv, uu = torch.meshgrid(v, u, indexing="ij")
            rays = torch.stack([(uu - cam.cx) / cam.fx, (vv - cam.cy) / cam.fy, torch.ones_like(uu)], -1)
            R = body_to_camera_matrix(cam.pitch_down_deg)
            up_cam = R[:, 2]  # body up expressed in camera coordinates
            den = rays @ up_cam
            hits = den < -1e-6
            lam = torch.where(hits, -cam.camera_height_m / den.clamp(max=-1e-6), torch.zeros_like(den))
            body = (rays * lam[..., None]) @ R  # camera -> body (R orthonormal)
            dist = torch.linalg.vector_norm(body[..., :2], dim=-1)
            prior = torch.sigmoid((self.max_floor_m - dist) / self.floor_softness_m) * hits
            self._grid_cache[key] = {
                "body": body.reshape(-1, 3).float().to(device),
                "uv0": torch.stack([uu, vv], -1).reshape(-1, 2).float().to(device),
                "prior": prior.reshape(-1).float().to(device),
                "rays": rays[..., :2].permute(2, 0, 1).float().to(device),
                "R": R.float().to(device),
            }
        return self._grid_cache[key]

    def _project(self, x, body, R):
        """Planar motion x [N,3] and floor points body [M,3] -> pixels [N,M,2] and Jacobian [N,M,2,3]."""
        cam = self.camera
        dx, dy, psi = x[:, 0, None], x[:, 1, None], x[:, 2, None]
        qx, qy = body[None, :, 0] - dx, body[None, :, 1] - dy
        qz = body[None, :, 2].expand_as(qx)
        cz, sz = psi.cos(), psi.sin()
        p1 = torch.stack([cz * qx + sz * qy, -sz * qx + cz * qy, qz], -1)
        dp = torch.stack([
            torch.stack([-cz.expand_as(qx), sz.expand_as(qx), torch.zeros_like(qx)], -1),
            torch.stack([-sz.expand_as(qx), -cz.expand_as(qx), torch.zeros_like(qx)], -1),
            torch.stack([-sz * qx + cz * qy, -cz * qx - sz * qy, torch.zeros_like(qx)], -1)], -1)
        C = p1 @ R.T                       # [N,M,3]
        dC = torch.einsum("ij,nmjk->nmik", R, dp)  # [N,M,3,3]
        z = C[..., 2].clamp(min=1e-3)
        uv = torch.stack([cam.fx * C[..., 0] / z + cam.cx, cam.fy * C[..., 1] / z + cam.cy], -1)
        du_dC = torch.stack([cam.fx / z, torch.zeros_like(z), -cam.fx * C[..., 0] / z ** 2], -1)
        dv_dC = torch.stack([torch.zeros_like(z), cam.fy / z, -cam.fy * C[..., 1] / z ** 2], -1)
        J = torch.stack([(du_dC[..., :, None] * dC).sum(-2), (dv_dC[..., :, None] * dC).sum(-2)], -2)
        return uv, J

    def pixel_weights(self, flow):
        """Per-pixel solver weights [N,H*W]: validity x confidence x near-floor prior (x learned)."""
        n, _, h, w = flow.shape
        g = self.grid(h, w, flow.device)
        valid = (flow[:, 3] > .5).float()
        conf = flow[:, 2].clamp(min=0.).clamp(min=1e-3)
        weight = (valid * conf).reshape(n, -1) * g["prior"][None]
        if self.learned_weights:
            inp = torch.cat([flow, g["rays"][None].expand(n, -1, -1, -1)], 1)
            weight = weight * (2 * torch.sigmoid(self.weight_net(inp))).reshape(n, -1)
        return weight

    def forward(self, flow: torch.Tensor):
        if flow.ndim != 4 or flow.shape[1] != 4:
            raise ValueError("expected flow [N,4,H,W]")
        with torch.autocast(device_type=flow.device.type, enabled=False):
            flow = torch.nan_to_num(flow.float())
            n, _, h, w = flow.shape
            g = self.grid(h, w, flow.device)
            scale = flow.new_tensor([self.camera.width, self.camera.height])
            obs1 = g["uv0"][None] + flow[:, :2].reshape(n, 2, -1).transpose(1, 2) * scale
            base_w = self.pixel_weights(flow)
            # Only pixels with any weight enter the solve: keeps the [N,M,...] tensors small.
            keep = (base_w > 0).any(0)
            body, obs1, base_w = g["body"][keep], obs1[:, keep], base_w[:, keep]
            x = flow.new_zeros(n, 3)
            eye = torch.eye(3, device=flow.device, dtype=flow.dtype)
            for _ in range(self.iterations):
                uv, J = self._project(x, body, g["R"])
                r = uv - obs1                                        # [N,M,2] pixels
                robust = torch.rsqrt(1 + (r.square().sum(-1) / self.robust_scale_px ** 2))
                wgt = base_w * robust
                H = torch.einsum("nm,nmki,nmkj->nij", wgt, J, J)
                b = torch.einsum("nm,nmki,nmk->ni", wgt, J, r)
                lam = self.damping * (H.diagonal(dim1=-2, dim2=-1).sum(-1, keepdim=True)[..., None] + 1.)
                x = x - torch.linalg.solve(H + lam * eye, b)
            uv, _ = self._project(x, body, g["R"])
            r = (uv - obs1).square().sum(-1)
            wsum = base_w.sum(-1)
            mean_squared = (base_w * r).sum(-1).div(wsum.clamp_min(1e-6))
            # Padded/empty frames have exactly zero residual. sqrt'(0) is
            # infinite, giving NaN weight-net gradients even through masked tokens.
            # Keep a zero diagnostic at zero, with a finite derivative everywhere.
            rms = torch.where(mean_squared > 0, mean_squared.clamp_min(1e-12).sqrt(),
                              torch.zeros_like(mean_squared))
        return x, {"weight_sum": wsum, "residual_rms_px": rms}
