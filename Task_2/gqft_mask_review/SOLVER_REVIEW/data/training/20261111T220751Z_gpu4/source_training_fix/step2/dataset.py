"""Windowed optical-flow dataset with query-conditioned perspective-path targets."""

from __future__ import annotations

import json
import os
from collections import OrderedDict
from dataclasses import dataclass

import numpy as np
import torch
from torch.utils.data import Dataset

from .geometry import (CameraModel, camera_model_from_mapping, canonical_ground_normal_camera,
                       load_tum_camera_trajectory, project_query_path)


@dataclass(frozen=True)
class WindowSpec:
    sequence_index: int
    start: int


class FlowPathDataset(Dataset):
    """Samples variable flow histories without leaking environments across splits."""

    def __init__(self, manifest_path: str, split: str, *, sequences_root: str | None = None,
                 min_history: int = 2, max_history: int = 30, window_stride: int = 5,
                 queries: int = 8, seed: int = 0, deterministic_history: int | None = None,
                 sequence_cache_size: int = 8, virtual_extension_px: int = 0,
                 target_ground_plane: str = "sequence_floor"):
        with open(manifest_path) as f:
            manifest = json.load(f)
        if split not in {"train", "val", "test"}:
            raise ValueError(split)
        self.root = sequences_root or manifest["sequences_root"]
        self.camera = camera_model_from_mapping(manifest.get("camera_model"))
        self.entries = [x for x in manifest["entries"] if x["split"] == split and x["flow_ready"]]
        if not self.entries:
            raise ValueError(f"no flow-ready sequences for split {split!r}")
        self.split = split
        self.min_history = min_history
        self.max_history = max_history
        self.window_stride = window_stride
        self.queries = queries
        self.seed = seed
        self.deterministic_history = deterministic_history
        self.sequence_cache_size = max(int(sequence_cache_size), 1)
        self.virtual_extension_px = int(virtual_extension_px)
        if target_ground_plane not in {"sequence_floor", "fixed_rig"}:
            raise ValueError("target_ground_plane must be sequence_floor or fixed_rig")
        self.target_ground_plane = target_ground_plane
        if self.virtual_extension_px < 0:
            raise ValueError("virtual_extension_px must be non-negative")
        if deterministic_history is not None and not (min_history <= deterministic_history <= max_history):
            raise ValueError("deterministic_history must be inside [min_history, max_history]")
        self._sequence_cache = OrderedDict()
        self._train_rng = None
        self.windows = []
        required_history = deterministic_history or min_history
        for i, entry in enumerate(self.entries):
            last_start = entry["frames"] - 1 - required_history
            self.windows.extend(WindowSpec(i, s) for s in range(0, last_start + 1, window_stride))
        if not self.windows:
            raise ValueError("no valid temporal windows")

    def __len__(self):
        return len(self.windows)

    def _load_sequence(self, i):
        if i in self._sequence_cache:
            self._sequence_cache.move_to_end(i)
            return self._sequence_cache[i]
        entry = self.entries[i]
        seq = os.path.join(self.root, entry["sequence"])
        flow_path = os.path.join(seq, entry["flow_name"])
        with np.load(flow_path) as z:
            flow = z["flow"].astype(np.float32)
            confidence = z["confidence"].astype(np.float32)
            valid = z["valid"].astype(np.float32)
        if flow.ndim != 4 or flow.shape[-1] != 2:
            raise ValueError(f"{flow_path}: expected flow [T,H,W,2], got {flow.shape}")
        if confidence.shape != flow.shape[:-1] or valid.shape != flow.shape[:-1]:
            raise ValueError(f"{flow_path}: confidence/valid shape mismatch")
        ts, xyz, rotations = load_tum_camera_trajectory(os.path.join(seq, "groundtruth.txt"))
        with open(os.path.join(seq, "meta.json")) as f:
            meta = json.load(f)
        if len(flow) != len(xyz) - 1:
            raise ValueError(f"{seq}: {len(flow)} flows for {len(xyz)} poses")
        normals = np.einsum("tji,j->ti", rotations, np.array([0.0, 0.0, 1.0]))
        expected = canonical_ground_normal_camera(float(meta["camera_pitch_down_deg"]))
        if np.max(np.abs(normals - expected)) > 2e-4:
            raise ValueError(f"{seq}: a pose pitch/roll disagrees with fixed rig")
        item = (flow, confidence, valid, ts, xyz, rotations, meta)
        self._sequence_cache[i] = item
        self._sequence_cache.move_to_end(i)
        while len(self._sequence_cache) > self.sequence_cache_size:
            self._sequence_cache.popitem(last=False)
        return item

    def _sample_history(self, available, rng):
        upper = min(self.max_history, available)
        if self.deterministic_history is not None:
            if self.deterministic_history > upper:
                raise RuntimeError("window does not contain the requested deterministic history")
            return self.deterministic_history
        # Log-spread lengths prevent the longest windows from dominating training.
        choices = np.array([2, 3, 4, 6, 8, 12, 18, 24, 30])
        choices = choices[(choices >= self.min_history) & (choices <= upper)]
        return int(rng.choice(choices)) if len(choices) else upper

    def _sample_queries(self, rng):
        if self.virtual_extension_px:
            bottom = self.camera.height + self.virtual_extension_px - 1
            return np.repeat(np.array([[self.camera.cx, bottom]], np.float32),
                             self.queries, axis=0)
        q = np.empty((self.queries, 2), np.float32)
        # Stratify horizontally and vertically, then shuffle: edge queries are always represented.
        for i in range(self.queries):
            col_bin = i % min(self.queries, 4)
            row_bin = (i // min(self.queries, 4)) % 2
            q[i, 0] = rng.uniform(col_bin * self.camera.width / 4,
                                  (col_bin + 1) * self.camera.width / 4 - 1e-3)
            q[i, 1] = rng.uniform(self.camera.height / 2 + row_bin * self.camera.height / 4,
                                  self.camera.height / 2 + (row_bin + 1) * self.camera.height / 4 - 1e-3)
        rng.shuffle(q)
        return q

    def __getitem__(self, index):
        spec = self.windows[index]
        flow, confidence, valid, ts, xyz, rotations, meta = self._load_sequence(spec.sequence_index)
        if self.split == "train":
            # Each worker owns a repeatable stream that continues across epochs.
            if self._train_rng is None:
                rng_seed = (self.seed + int(torch.initial_seed())) % (2 ** 32)
                self._train_rng = np.random.default_rng(rng_seed)
            rng = self._train_rng
        else:
            rng = np.random.default_rng((self.seed + index) % (2 ** 32))
        history = self._sample_history(len(flow) - spec.start, rng)
        sl_flow = flow[spec.start:spec.start + history]
        sl_conf = confidence[spec.start:spec.start + history]
        sl_valid = valid[spec.start:spec.start + history]
        # Invalid vectors are zeroed twice (cache and loader) to make corruption impossible to miss.
        sl_flow = sl_flow * sl_valid[..., None]
        features = np.concatenate([sl_flow, sl_conf[..., None], sl_valid[..., None]], axis=-1)
        features = np.moveaxis(features, -1, 1)  # [T,4,H,W]

        pose_slice = slice(spec.start, spec.start + history + 1)
        queries = self._sample_queries(rng)
        # Keep the released labels by default. The explicit fixed_rig experiment
        # anchors every window with the same mounting height used at inference.
        target_floor = (float(meta["floor_z_m"]) if self.target_ground_plane == "sequence_floor"
                        else float(xyz[spec.start, 2] - self.camera.camera_height_m))
        uv, target_valid, displacement = project_query_path(
            xyz[pose_slice], rotations[spec.start], queries, self.camera.intrinsics,
            (self.camera.width, self.camera.height + self.virtual_extension_px),
            target_floor)

        rot_slice=rotations[pose_slice]
        fwd=rot_slice[:,:,2]
        f0_x,f0_y=fwd[0,0],fwd[0,1]
        ft_x,ft_y=fwd[:,0],fwd[:,1]

        rel_yaw = np.arctan2(f0_x * ft_y - f0_y * ft_x, f0_x * ft_x + f0_y * ft_y)[:, None].astype(np.float32)
        uv[..., 0] /= self.camera.width - 1
        uv[..., 1] /= self.camera.height - 1
        query_norm = queries.copy()
        query_norm[:, 0] /= self.camera.width - 1
        query_norm[:, 1] /= self.camera.height - 1
        return {
            "flow": torch.from_numpy(features),
            "query_uv": torch.from_numpy(queries),
            "query_norm": torch.from_numpy(query_norm),
            "target_uv": torch.from_numpy(uv),
            "target_valid": torch.from_numpy(target_valid),
            "displacement": torch.from_numpy(displacement),
            "target_yaw":torch.from_numpy(rel_yaw),
            "history": history,
            "sequence": self.entries[spec.sequence_index]["sequence"],
            "start": spec.start,
        }


def collate_windows(batch):
    """Pad only to the longest history in this batch."""
    b, max_h = len(batch), max(x["history"] for x in batch)
    q = batch[0]["query_uv"].shape[0]
    c, h, w = batch[0]["flow"].shape[1:]
    flow = torch.zeros(b, max_h, c, h, w)
    history_mask = torch.zeros(b, max_h, dtype=torch.bool)
    displacement = torch.zeros(b, max_h + 1, 3)
    target_yaw=torch.zeros(b,max_h+1,1)
    target_uv = torch.zeros(b, q, max_h + 1, 2)
    target_valid = torch.zeros(b, q, max_h + 1, dtype=torch.bool)
    query_uv = torch.stack([x["query_uv"] for x in batch])
    query_norm = torch.stack([x["query_norm"] for x in batch])
    for i, x in enumerate(batch):
        n = x["history"]
        flow[i, :n] = x["flow"]
        history_mask[i, :n] = True
        displacement[i, :n + 1] = x["displacement"]
        target_yaw[i,:n+1] = x["target_yaw"]
        target_uv[i, :, :n + 1] = x["target_uv"]
        target_valid[i, :, :n + 1] = x["target_valid"]
    return {"flow": flow, "history_mask": history_mask, "query_uv": query_uv,
            "query_norm": query_norm, "displacement": displacement,
            "target_yaw":target_yaw,
            "target_uv": target_uv, "target_valid": target_valid,
            "history": torch.tensor([x["history"] for x in batch]),
            "sequence": [x["sequence"] for x in batch],
            "start": torch.tensor([x["start"] for x in batch])}
