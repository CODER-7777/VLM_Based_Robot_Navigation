"""Build and validate the environment-disjoint HSGM-camera training manifest."""

from __future__ import annotations

import argparse
import glob
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

from step2.capture_hsgm_habitat import (CAMERA_HEIGHT_M, HEIGHT, HFOV_DEG,
                                         PITCH_DOWN_DEG, SENSOR_VERSION, WIDTH)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sequences", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--flow-name", default="flow_searaft_160x90.npz")
    parser.add_argument("--require-flow", action="store_true")
    parser.add_argument("--train-scenes", required=True)
    parser.add_argument("--val-scenes", required=True)
    parser.add_argument("--test-scenes", required=True)
    parser.add_argument("--max-per-scene", type=int, default=0)
    args = parser.parse_args()
    root = Path(args.sequences).resolve()
    entries = []
    scenes_by_split = defaultdict(set)
    requested = {
        "train": set(args.train_scenes.split(",")),
        "val": set(args.val_scenes.split(",")),
        "test": set(args.test_scenes.split(",")),
    }
    scene_to_split = {}
    for split, scenes in requested.items():
        for scene in scenes:
            if scene in scene_to_split:
                raise SystemExit(f"scene requested in multiple splits: {scene}")
            scene_to_split[scene] = split
    accepted_per_scene = Counter()
    fx = WIDTH / (2.0 * math.tan(math.radians(HFOV_DEG) / 2.0))
    for meta_name in sorted(glob.glob(str(root / "*" / "meta.json"))):
        seq = Path(meta_name).parent
        meta = json.loads(Path(meta_name).read_text())
        if meta.get("sensor_model_version") != SENSOR_VERSION:
            continue
        scene = meta["scenario"]
        split = scene_to_split.get(scene)
        if split is None:
            continue
        if args.max_per_scene and accepted_per_scene[scene] >= args.max_per_scene:
            continue
        scenes_by_split[split].add(scene)
        flow = seq / args.flow_name
        if args.require_flow and not flow.is_file():
            continue
        rgb_count = len(list((seq / "rgb").glob("*.png")))
        gt_count = sum(1 for line in (seq / "groundtruth.txt").read_text().splitlines()
                       if line.strip() and not line.startswith("#"))
        if rgb_count != gt_count or rgb_count != int(meta["frames"]):
            raise SystemExit(f"frame mismatch in {seq}")
        entries.append({"sequence": seq.name, "scenario": scene, "environment": scene,
                        "split": split, "frames": rgb_count, "flow_ready": flow.is_file(),
                        "flow_name": args.flow_name, "shape": meta.get("shape_family"),
                        "speed_mps": meta.get("speed_mps_max"),
                        "sensor_model_version": SENSOR_VERSION})
        accepted_per_scene[scene] += 1
    split_sets = {key: set(scenes_by_split[key]) for key in ("train", "val", "test")}
    if any(not values for values in split_sets.values()):
        raise SystemExit(f"every split needs at least one scene: {split_sets}")
    for left, right in (("train", "val"), ("train", "test"), ("val", "test")):
        overlap = split_sets[left] & split_sets[right]
        if overlap:
            raise SystemExit(f"scene leakage between {left}/{right}: {sorted(overlap)}")
    payload = {
        "version": "hsgm_r2rce_camera_v1", "sensor_model_version": SENSOR_VERSION,
        "sequences_root": str(root),
        "camera_model": {"width": WIDTH, "height": HEIGHT, "fx": fx, "fy": fx,
                         "cx": WIDTH / 2.0, "cy": HEIGHT / 2.0,
                         "camera_height_m": CAMERA_HEIGHT_M,
                         "pitch_down_deg": PITCH_DOWN_DEG},
        "capture_rate_hz": 5.0,
        "split_scenarios": {key: sorted(value) for key, value in split_sets.items()},
        "counts": dict(Counter(entry["split"] for entry in entries)),
        "entries": entries,
    }
    destination = Path(args.out)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2) + "\n")
    print("HSGM_MANIFEST_OK " + json.dumps({"counts": payload["counts"],
                                             "scenes": payload["split_scenarios"]}))


if __name__ == "__main__":
    main()
