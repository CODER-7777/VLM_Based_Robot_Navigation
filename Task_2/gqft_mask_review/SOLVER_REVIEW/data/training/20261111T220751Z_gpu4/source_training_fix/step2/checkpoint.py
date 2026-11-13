"""Strict architecture-aware loading for released and historical GQFT checkpoints."""
from __future__ import annotations

from dataclasses import fields
from pathlib import Path

import torch

from step2.geometry import camera_model_from_mapping
from step2.models.gqft import GQFT, GQFTConfig


def config_from_checkpoint(checkpoint):
    saved = checkpoint["model"]
    attention = any(key.startswith("flow_encoder.attention.") for key in saved)
    yaw = any(key.startswith("yaw_head.") for key in saved)
    values = dict(checkpoint.get("model_config", {}))
    inferred = {"spatial_pooling": "attention_max" if attention else "mean_max",
                "predict_yaw": yaw}
    for key, value in inferred.items():
        if key in values and values[key] != value:
            raise ValueError(f"Checkpoint config {key} disagrees with saved parameters")
        values[key] = value
    allowed = {field.name for field in fields(GQFTConfig)}
    return GQFTConfig(**{key: value for key, value in values.items() if key in allowed})


def load_gqft_checkpoint(path, device="cpu"):
    checkpoint = torch.load(Path(path), map_location="cpu", weights_only=False)
    if checkpoint.get("architecture") != "GQFT":
        raise ValueError("Checkpoint is not GQFT")
    config = config_from_checkpoint(checkpoint)
    camera = camera_model_from_mapping(checkpoint.get("camera_model"))
    model = GQFT(config, camera)
    model.load_state_dict(checkpoint["model"], strict=True)
    return model.to(device).eval(), checkpoint


def initialize_gqft(model, checkpoint, *, reinitialize_motion_heads=False):
    """Strict warm start; changing increment frames requires explicit head reset.

    Preserve the destination's identically seeded delta/logvar initialization for
    controlled keyframe/local pairs. Never reinterpret old trained delta weights
    silently. Resume still requires exact configuration, handled by train_gqft.
    """
    if checkpoint.get("architecture") != "GQFT":
        raise ValueError("Init checkpoint is not GQFT")
    source_config = config_from_checkpoint(checkpoint)
    if camera_model_from_mapping(checkpoint.get("camera_model")) != model.camera:
        raise ValueError("Init checkpoint camera differs from destination model")
    if source_config.motion_integration != model.config.motion_integration and not reinitialize_motion_heads:
        raise ValueError("Changing increment frames requires explicit --reinitialize-motion-heads")
    adds_solver = (model.config.motion_prior == "ground_solver" and
                   source_config.motion_prior != "ground_solver")
    if adds_solver and not reinitialize_motion_heads:
        raise ValueError("Adding the ground solver turns motion heads into residuals; "
                         "pass --reinitialize-motion-heads")
    heads = ("delta_head", "logvar_head") + (("yaw_head",) if adds_solver else ())
    fresh = {name: {k: v.detach().clone() for k, v in getattr(model, name).state_dict().items()}
             for name in heads} if reinitialize_motion_heads else {}
    if adds_solver:
        # Only the newly added solver modules may be absent; they keep their documented init.
        result = model.load_state_dict(checkpoint["model"], strict=False)
        allowed = ("ground_solver.", "solver_embed.")
        bad = [k for k in result.missing_keys if not k.startswith(allowed)]
        if bad or result.unexpected_keys:
            raise ValueError(f"Init checkpoint mismatch: missing={bad} unexpected={result.unexpected_keys}")
    else:
        model.load_state_dict(checkpoint["model"], strict=True)
    for name, state in fresh.items():
        getattr(model, name).load_state_dict(state, strict=True)
