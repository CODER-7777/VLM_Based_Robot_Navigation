"""Explicit frozen-inference controls; legacy GQFT/solver behavior is untouched.

These controls are experiments, not established fixes: central-floor selection,
rotation/translation cue separation, rolling context and solver-quality fusion.
"""
from __future__ import annotations
import torch

from step2.geometry import canonical_ground_normal_camera, rotate_about_axis_torch
from step2.ground_solver import GroundPlaneSolver, planar_to_camera_increment


def safe_rms(residual_squared, weights):
    mean = (residual_squared*weights).sum(-1)/weights.sum(-1).clamp_min(1e-6)
    return torch.where(mean > 0, mean.clamp_min(1e-12).sqrt(), torch.zeros_like(mean))


class DirectionalGroundSolver(GroundPlaneSolver):
    """Center-floor joint solve, or far-ray yaw followed by near-floor translation.

    A far ray-ground intersection is a geometric prior, not measured scene depth
    or a guarantee that the visible object is distant. Failures remain possible.
    """
    def __init__(self, camera, *, variant='center', center_ratio=.5,
                 far_near_m=3., far_far_m=8., **kwargs):
        if variant not in {'center', 'split'} or center_ratio <= 0 or not 0 < far_near_m < far_far_m:
            raise ValueError('Invalid directional solver configuration')
        super().__init__(camera, **kwargs)
        self.variant, self.center_ratio = variant, center_ratio
        self.far_near_m, self.far_far_m = far_near_m, far_far_m

    def pixel_weights(self, flow):
        weight = super().pixel_weights(flow)
        g = self.grid(*flow.shape[-2:], flow.device)
        forward, left = g['body'][:, 0], g['body'][:, 1]
        center = (forward > 0) & (left.abs() <= self.center_ratio*forward)
        return weight*center[None]

    def forward(self, flow):
        if self.variant == 'center':
            return super().forward(flow)
        if flow.ndim != 4 or flow.shape[1] != 4:
            raise ValueError('Expected flow [N,4,H,W]')
        with torch.autocast(device_type=flow.device.type, enabled=False):
            flow = torch.nan_to_num(flow.float())
            n, _, h, w = flow.shape
            g = self.grid(h, w, flow.device)
            obs = g['uv0'][None]+flow[:, :2].flatten(2).transpose(1, 2)*flow.new_tensor([self.camera.width, self.camera.height])
            # First fit a pure-yaw homography to geometrically far viewing rays.
            rays = torch.cat([g['rays'].flatten(1).T, flow.new_ones(h*w, 1)], -1)
            ray_body = rays @ g['R']
            dist = torch.linalg.vector_norm(g['body'][:, :2], dim=-1)
            hits = (rays @ g['R'][:, 2]) < -1e-6
            far_prior = (torch.sigmoid((dist-self.far_near_m)/.2)*
                         torch.sigmoid((self.far_far_m-dist)/.2)*hits)
            far_weight = ((flow[:, 3] > .5)*flow[:, 2].clamp_min(1e-3)).flatten(1)*far_prior[None]
            keep = (far_weight > 0).any(0)
            rb, observed, fw = ray_body[keep], obs[:, keep], far_weight[:, keep]
            yaw = flow.new_zeros(n)
            for _ in range(self.iterations):
                x = torch.cat([flow.new_zeros(n, 2), yaw[:, None]], -1)
                uv, jac = self._project(x, rb, g['R'])
                residual, jy = uv-observed, jac[..., 2]
                robust = torch.rsqrt(1+residual.square().sum(-1)/self.robust_scale_px**2)
                weight = fw*robust
                H = (weight[..., None]*jy.square()).sum((1, 2))
                b = (weight[..., None]*jy*residual).sum((1, 2))
                yaw = yaw-b/(H+self.damping*(H+1))
            uv, _ = self._project(torch.cat([flow.new_zeros(n, 2), yaw[:, None]], -1), rb, g['R'])
            yaw_rms = safe_rms((uv-observed).square().sum(-1), fw)
            # Then solve translation on central near-floor rays, holding yaw fixed.
            near_weight = self.pixel_weights(flow)
            keep = (near_weight > 0).any(0)
            body, observed, nw = g['body'][keep], obs[:, keep], near_weight[:, keep]
            shift = flow.new_zeros(n, 2)
            eye = torch.eye(2, device=flow.device)
            for _ in range(self.iterations):
                x = torch.cat([shift, yaw[:, None]], -1)
                uv, jac = self._project(x, body, g['R'])
                residual, jt = uv-observed, jac[..., :2]
                robust = torch.rsqrt(1+residual.square().sum(-1)/self.robust_scale_px**2)
                weight = nw*robust
                H = torch.einsum('nm,nmki,nmkj->nij', weight, jt, jt)
                b = torch.einsum('nm,nmki,nmk->ni', weight, jt, residual)
                damping = self.damping*(H.diagonal(dim1=-2, dim2=-1).sum(-1, keepdim=True)[..., None]+1)
                shift = shift-torch.linalg.solve(H+damping*eye, b)
            motion = torch.cat([shift, yaw[:, None]], -1)
            uv, _ = self._project(motion, body, g['R'])
            rms = safe_rms((uv-observed).square().sum(-1), nw)
            return motion, {'weight_sum': nw.sum(-1), 'residual_rms_px': rms,
                            'yaw_weight_sum': fw.sum(-1), 'yaw_residual_rms_px': yaw_rms}


def integrate_local_steps(delta_local, delta_yaw, pitch_down_deg):
    """Integrate local 3-D steps with previous cumulative predicted yaw."""
    if delta_local.ndim != 2 or delta_local.shape[1] != 3 or delta_yaw.shape != delta_local.shape[:1]:
        raise ValueError('Expected [T,3] local steps and [T] yaw increments')
    yaw = torch.cat([delta_yaw.new_zeros(1), delta_yaw.cumsum(0)])
    axis = delta_local.new_tensor(canonical_ground_normal_camera(pitch_down_deg))
    delta = rotate_about_axis_torch(delta_local, yaw[:-1], axis)
    displacement = torch.cat([delta.new_zeros(1, 3), delta.cumsum(0)], 0)
    return displacement, yaw


@torch.inference_mode()
def neural_local_steps(model, features, *, window=24, mode='sliding'):
    """Reuse one frozen checkpoint; rolling mode emits only each newest local step.

    Chunked mode is a control using identical local-coordinate integration. Query
    and camera contracts are taken from the checkpoint; no pose input is used.
    """
    if mode not in {'chunked', 'sliding'} or not 1 <= window <= model.config.max_history:
        raise ValueError('Invalid context mode/window')
    if features.ndim != 4 or features.shape[1] != 4 or not model.config.predict_yaw:
        raise ValueError('Need [T,4,H,W] features and a yaw checkpoint')
    device = features.device
    q = features.new_tensor([[[model.camera.cx, model.config.canvas_height-1.]]])
    qnorm = q/q.new_tensor([model.camera.width-1, model.camera.height-1])
    axis = features.new_tensor(canonical_ground_normal_camera(model.camera.pitch_down_deg))
    delta, yaw = [], []
    ranges = ([(max(0, end-window), end) for end in range(1, len(features)+1)] if mode == 'sliding'
              else [(begin, min(begin+window, len(features))) for begin in range(0, len(features), window)])
    for begin, end in ranges:
        x = features[begin:end][None]
        mask = torch.ones(1, end-begin, dtype=torch.bool, device=device)
        out = model(x, mask, q, qnorm)
        if 'delta_local' in out:
            local = out['delta_local'][0].float()
        else:
            diff = out['displacement'][0, 1:].float()-out['displacement'][0, :-1].float()
            local = rotate_about_axis_torch(diff, -out['yaw'][0, :-1, 0].float(), axis)
        dy = out['yaw'][0, 1:, 0].float()-out['yaw'][0, :-1, 0].float()
        delta.append(local[-1:] if mode == 'sliding' else local)
        yaw.append(dy[-1:] if mode == 'sliding' else dy)
    return ((torch.cat(delta), torch.cat(yaw)) if delta else
            (features.new_zeros(0, 3), features.new_zeros(0)))


def quality_fuse(neural_delta, neural_yaw, solver_motion, info, camera, *, good_px=2., bad_px=5., min_support=1.):
    """Experimental quality gate between an independent neural head and a solver.

    The neural estimate must be the unconstrained yaw-local reference, rather
    than a small residual head trained to depend on the same failing solver.
    Thresholds are predeclared controls; they are not established stair detectors.
    """
    if not 0 <= good_px < bad_px or min_support <= 0:
        raise ValueError('Invalid quality thresholds')
    rms = info['residual_rms_px']
    support = info['weight_sum'] >= min_support
    if 'yaw_residual_rms_px' in info:
        rms = torch.maximum(rms, info['yaw_residual_rms_px'])
        support = support & (info['yaw_weight_sum'] >= min_support)
    observed = support & torch.isfinite(rms) & torch.isfinite(solver_motion).all(-1)
    alpha = ((bad_px-torch.nan_to_num(rms, nan=bad_px))/ (bad_px-good_px)).clamp(0, 1)
    alpha = torch.where(observed, alpha, torch.zeros_like(alpha))
    solver_motion = torch.nan_to_num(solver_motion)
    solver_delta = planar_to_camera_increment(solver_motion, camera.pitch_down_deg)
    return (alpha[:, None]*solver_delta+(1-alpha[:, None])*neural_delta,
            alpha*solver_motion[:, 2]+(1-alpha)*neural_yaw, alpha)
