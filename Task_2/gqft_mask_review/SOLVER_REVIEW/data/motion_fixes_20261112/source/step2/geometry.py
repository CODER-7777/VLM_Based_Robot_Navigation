"""Ground-plane anchoring and perspective-path targets shared by every Step-2 model.

The RGB scene contains obstacles, but target construction intentionally intersects the selected
keyframe pixel with an infinite obstacle-free ground plane. Camera-centre displacements are then
translated onto that anchor and projected back into the keyframe.
"""

from __future__ import annotations

from dataclasses import dataclass, fields

import numpy as np


@dataclass(frozen=True)
class CameraModel:
    width: int = 640
    height: int = 360
    fx: float = 299.57030682309323
    fy: float = 299.57030682309323
    cx: float = 320.0
    cy: float = 180.0
    camera_height_m: float = 0.48
    pitch_down_deg: float = 5.0

    @property
    def intrinsics(self) -> np.ndarray:
        return np.array([self.fx, self.fy, self.cx, self.cy], dtype=np.float64)


def camera_model_from_mapping(values: dict | None) -> CameraModel:
    """Build a camera contract from a manifest/checkpoint while preserving old defaults."""
    if not values:
        return CameraModel()
    allowed = {field.name for field in fields(CameraModel)}
    return CameraModel(**{key: value for key, value in values.items() if key in allowed})


def quat_xyzw_to_matrix(q: np.ndarray) -> np.ndarray:
    """Convert one or more normalized xyzw quaternions to rotation matrices."""
    q = np.asarray(q, dtype=np.float64)
    if q.shape[-1] != 4:
        raise ValueError(f"expected (...,4) xyzw quaternions, got {q.shape}")
    norm = np.linalg.norm(q, axis=-1, keepdims=True)
    if np.any(norm < 1e-12):
        raise ValueError("zero quaternion")
    x, y, z, w = np.moveaxis(q / norm, -1, 0)
    out = np.empty(q.shape[:-1] + (3, 3), dtype=np.float64)
    out[..., 0, 0] = 1 - 2 * (y * y + z * z)
    out[..., 0, 1] = 2 * (x * y - z * w)
    out[..., 0, 2] = 2 * (x * z + y * w)
    out[..., 1, 0] = 2 * (x * y + z * w)
    out[..., 1, 1] = 1 - 2 * (x * x + z * z)
    out[..., 1, 2] = 2 * (y * z - x * w)
    out[..., 2, 0] = 2 * (x * z - y * w)
    out[..., 2, 1] = 2 * (y * z + x * w)
    out[..., 2, 2] = 1 - 2 * (x * x + y * y)
    return out


def load_tum_camera_trajectory(path: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return timestamps, camera centres in world, and OpenCV camera-to-world rotations."""
    data = np.loadtxt(path, comments="#", ndmin=2)
    if data.shape[1] != 8:
        raise ValueError(f"{path}: expected TUM rows with 8 columns, got {data.shape[1]}")
    return data[:, 0], data[:, 1:4], quat_xyzw_to_matrix(data[:, 4:8])


def canonical_ground_normal_camera(pitch_down_deg: float) -> np.ndarray:
    """World-up expressed in the fixed OpenCV camera frame (x right, y down, z forward)."""
    p = np.deg2rad(pitch_down_deg)
    return np.array([0.0, -np.cos(p), -np.sin(p)], dtype=np.float64)


def rotate_about_axis_torch(vectors, angles, axis):
    """Rodrigues rotation of [...,3] vectors by [...] angles around a unit axis.

    Positive yaw follows world-up. In a pitched OpenCV camera this axis is the
    canonical ground normal, not camera Y. Casts remain differentiable.
    """
    import torch

    if vectors.shape[-1] != 3 or angles.shape != vectors.shape[:-1]:
        raise ValueError("Expected vectors [...,3] and matching angles [...]")
    axis = torch.as_tensor(axis, device=vectors.device, dtype=vectors.dtype)
    if axis.shape != (3,):
        raise ValueError("Expected a unit axis [3]")
    axis = axis / torch.linalg.vector_norm(axis).clamp_min(1e-8)
    angles = angles.to(vectors.dtype)
    cosine, sine = angles.cos()[..., None], angles.sin()[..., None]
    cross = torch.linalg.cross(axis.expand_as(vectors), vectors, dim=-1)
    parallel = (vectors * axis).sum(-1, keepdim=True) * axis
    return vectors * cosine + cross * sine + parallel * (1 - cosine)


def local_increment_targets_torch(displacement, yaw, axis):
    """Keyframe displacement targets -> previous-frame local increments.

    Uses ground-truth yaw at the START of each interval. Angles may be wrapped;
    rotation is invariant to full turns. No labels or camera calibration change.
    """
    if yaw.shape != displacement.shape[:-1] + (1,):
        raise ValueError("Expected displacement [B,T+1,3], yaw [B,T+1,1]")
    delta = displacement[:, 1:] - displacement[:, :-1]
    return rotate_about_axis_torch(delta, -yaw[:, :-1, 0], axis)


def ground_ray_support_torch(camera, height, width, *, near_m, far_m, device):
    """Hypothetical ground-ray depth eligibility on a resized input grid.

    This is a static geometry prior, NOT a floor/obstacle segmentation mask.
    Range is optical-axis Z depth in metres, rather than Euclidean distance.
    Pixel-centre mapping follows area-resized RGB -> flow coordinates.
    """
    import torch

    v = (torch.arange(height, device=device, dtype=torch.float32) + .5) * camera.height / height - .5
    u = (torch.arange(width, device=device, dtype=torch.float32) + .5) * camera.width / width - .5
    yy, xx = torch.meshgrid(v, u, indexing="ij")
    rays = torch.stack([(xx-camera.cx)/camera.fx, (yy-camera.cy)/camera.fy, torch.ones_like(xx)], -1)
    normal = rays.new_tensor(canonical_ground_normal_camera(camera.pitch_down_deg))
    denominator = (rays * normal).sum(-1)
    depth = -camera.camera_height_m / denominator.clamp(max=-1e-8)
    return ((denominator < -1e-8) & (depth >= near_m) & (depth <= far_m))[None, None]


def query_ground_anchor(
    query_uv: np.ndarray,
    intrinsics: np.ndarray,
    ground_normal_camera: np.ndarray,
    camera_height_m: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Intersect keyframe pixel rays with an obstacle-free ground plane.

    Returns anchors in keyframe camera coordinates and a boolean forward-ray validity mask.
    """
    q = np.asarray(query_uv, dtype=np.float64)
    fx, fy, cx, cy = np.asarray(intrinsics, dtype=np.float64)
    rays = np.stack([(q[..., 0] - cx) / fx, (q[..., 1] - cy) / fy,
                     np.ones(q.shape[:-1])], axis=-1)
    denom = rays @ np.asarray(ground_normal_camera, dtype=np.float64)
    lam = -float(camera_height_m) / denom
    valid = np.isfinite(lam) & (lam > 0.0) & (denom < -1e-8)
    return rays * lam[..., None], valid


def project_query_path(
    positions_world: np.ndarray,
    rotation_world_from_camera0: np.ndarray,
    query_uv: np.ndarray,
    intrinsics: np.ndarray,
    image_size: tuple[int, int],
    floor_z_m: float,
    *,
    z_epsilon: float = 1e-4,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Create query-conditioned 2-D targets from a ground-truth camera-centre trajectory.

    Returns `(uv, valid_prefix, displacement_camera0)`, where `uv` is `[Q,T,2]`, validity is
    `[Q,T]`, and displacement is `[T,3]`. Validity terminates permanently at the first point that
    leaves the image or passes behind the keyframe camera.
    """
    xyz = np.asarray(positions_world, dtype=np.float64)
    r0 = np.asarray(rotation_world_from_camera0, dtype=np.float64)
    q = np.asarray(query_uv, dtype=np.float64).reshape(-1, 2)
    k = np.asarray(intrinsics, dtype=np.float64)
    width, height = image_size
    if xyz.ndim != 2 or xyz.shape[1] != 3 or r0.shape != (3, 3):
        raise ValueError("positions must be [T,3] and rotation must be [3,3]")

    displacement = (xyz - xyz[0]) @ r0
    normal_camera = r0.T @ np.array([0.0, 0.0, 1.0])
    camera_height = float(xyz[0, 2] - floor_z_m)
    anchors, anchor_valid = query_ground_anchor(q, k, normal_camera, camera_height)
    points = anchors[:, None, :] + displacement[None, :, :]
    z = points[..., 2]
    safe_z = np.where(np.abs(z) > z_epsilon, z, np.where(z >= 0, z_epsilon, -z_epsilon))
    fx, fy, cx, cy = k
    uv = np.stack([fx * points[..., 0] / safe_z + cx,
                   fy * points[..., 1] / safe_z + cy], axis=-1)
    valid = (anchor_valid[:, None] & (z > z_epsilon) &
             (uv[..., 0] >= 0) & (uv[..., 0] < width) &
             (uv[..., 1] >= 0) & (uv[..., 1] < height))
    valid = np.logical_and.accumulate(valid, axis=1)
    return uv.astype(np.float32), valid, displacement.astype(np.float32)


def project_displacements_torch(displacement, query_uv, camera: CameraModel,
                                image_size: tuple[int, int] | None = None):
    """Differentiable fixed-rig projection used by GQFT.

    `displacement` is `[B,T,3]` in the keyframe camera; `query_uv` is `[B,Q,2]` in pixels.
    Returns pixel coordinates `[B,Q,T,2]` and analytic in-frame validity `[B,Q,T]`.
    """
    import torch

    if displacement.ndim != 3 or query_uv.ndim != 3:
        raise ValueError("expected displacement [B,T,3] and queries [B,Q,2]")
    dtype, device = displacement.dtype, displacement.device
    q = query_uv.to(device=device, dtype=dtype)
    normal = torch.tensor(canonical_ground_normal_camera(camera.pitch_down_deg),
                          dtype=dtype, device=device)
    rays = torch.stack([(q[..., 0] - camera.cx) / camera.fx,
                        (q[..., 1] - camera.cy) / camera.fy,
                        torch.ones_like(q[..., 0])], dim=-1)
    denom = torch.einsum("bqc,c->bq", rays, normal)
    lam = -camera.camera_height_m / denom.clamp(max=-1e-6)
    anchors = rays * lam[..., None]
    points = anchors[:, :, None, :] + displacement[:, None, :, :]
    z = points[..., 2]
    safe_z = z.clamp(min=1e-4)
    uv = torch.stack([camera.fx * points[..., 0] / safe_z + camera.cx,
                      camera.fy * points[..., 1] / safe_z + camera.cy], dim=-1)
    width, height = image_size or (camera.width, camera.height)
    valid = ((denom < -1e-6)[:, :, None] & (z > 1e-4) &
             (uv[..., 0] >= 0) & (uv[..., 0] < width) &
             (uv[..., 1] >= 0) & (uv[..., 1] < height))
    valid = torch.cumprod(valid.to(torch.int32), dim=2).bool()
    return uv, valid
