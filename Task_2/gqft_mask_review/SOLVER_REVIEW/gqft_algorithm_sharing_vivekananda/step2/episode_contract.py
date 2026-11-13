"""Shared flow units and ground-axis conversions for recorded episode adapters."""
from __future__ import annotations

import math
import numpy as np


def pack_normalized_flow(flow, confidence, valid):
    """Pack SEA-RAFT's du/W,dv/H output without performing another normalization."""
    flow = np.asarray(flow, dtype=np.float32)
    confidence = np.asarray(confidence, dtype=np.float32)
    valid = np.asarray(valid, dtype=np.float32)
    if flow.ndim != 4 or flow.shape[-1] != 2:
        raise ValueError('Expected normalized flow [T,H,W,2]')
    if confidence.shape != flow.shape[:-1] or valid.shape != confidence.shape:
        raise ValueError('Flow, confidence, and validity shapes disagree')
    if not all(np.isfinite(x).all() for x in (flow, confidence, valid)):
        raise ValueError('Non-finite flow features')
    features = np.concatenate([flow * valid[..., None], confidence[..., None],
                               valid[..., None]], axis=-1)
    return np.moveaxis(features, -1, 1).copy()


def camera_displacement_to_ground_xy(displacement, pitch_down_deg):
    """OpenCV camera displacement -> (forward, left), with positive downward pitch."""
    d = np.asarray(displacement, dtype=np.float64).reshape(3)
    pitch = math.radians(pitch_down_deg)
    forward = np.array([0., -math.sin(pitch), math.cos(pitch)])
    left = np.array([-1., 0., 0.])
    return float(d @ forward), float(d @ left)
