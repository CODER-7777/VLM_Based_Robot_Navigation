"""Capture HSGM-camera RGB motion sequences from Matterport3D Habitat scenes.

The front sensor exactly follows HSGM's R2R-CE contract: 960x540, 135 degree
horizontal FOV, 1.2 m above the agent, and 30 degrees downward pitch.  Motion is
sampled at the integration controller's 5 Hz cadence.  Generated paths are
collision checked against Habitat only to keep rendered motion physically valid;
the navmesh is never stored or exposed to the learned models.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import cv2
import habitat_sim
import magnum as mn
import numpy as np
import quaternion
from habitat_sim.utils.common import quat_from_angle_axis


WIDTH, HEIGHT = 960, 540
HFOV_DEG = 135.0
CAMERA_HEIGHT_M = 1.2
PITCH_DOWN_DEG = 30.0
DT = 0.2
FPS = 1.0 / DT
SENSOR_VERSION = "hsgm_r2rce_front_v1"

# Habitat world (x right, y up, z back) -> proper right-handed z-up world.
HABITAT_TO_ZUP = np.array([[1.0, 0.0, 0.0],
                            [0.0, 0.0, -1.0],
                            [0.0, 1.0, 0.0]])
# OpenCV camera (x right, y down, z forward) -> Habitat camera.
OPENCV_TO_HABITAT_CAMERA = np.diag([1.0, -1.0, -1.0])


def build_sim(scene: Path) -> habitat_sim.Simulator:
    backend = habitat_sim.SimulatorConfiguration()
    backend.scene_id = str(scene)
    backend.enable_physics = False
    rgb = habitat_sim.CameraSensorSpec()
    rgb.uuid = "color_sensor"
    rgb.sensor_type = habitat_sim.SensorType.COLOR
    rgb.resolution = [HEIGHT, WIDTH]
    rgb.hfov = HFOV_DEG
    rgb.position = mn.Vector3([0.0, CAMERA_HEIGHT_M, 0.0])
    rgb.orientation = mn.Vector3([-math.radians(PITCH_DOWN_DEG), 0.0, 0.0])
    agent = habitat_sim.agent.AgentConfiguration()
    agent.radius = 0.10
    agent.height = 1.5
    agent.sensor_specifications = [rgb]
    sim = habitat_sim.Simulator(habitat_sim.Configuration(backend, [agent]))
    if not sim.pathfinder.is_loaded:
        raise RuntimeError(f"scene has no loaded navmesh: {scene}")
    return sim


def motion_commands(rng: np.random.Generator, frames: int, variant: int):
    """Return per-interval (speed m/s, yaw-rate rad/s) commands."""
    count = frames - 1
    t = np.arange(count, dtype=np.float64) * DT
    family = variant % 8
    speed = rng.uniform(0.10, 0.36)
    sign = -1.0 if (variant // 8) % 2 else 1.0
    if family == 0:  # straight
        omega = np.zeros(count)
    elif family == 1:  # constant arc
        omega = np.full(count, sign * rng.uniform(0.12, 0.42))
    elif family == 2:  # gradually increasing turn
        omega = sign * np.linspace(0.0, rng.uniform(0.25, 0.60), count)
    elif family == 3:  # S curve
        omega = sign * rng.uniform(0.25, 0.55) * np.sin(2.0 * np.pi * t / max(t[-1], DT))
    elif family == 4:  # bounded random smooth curve
        knots = rng.uniform(-0.45, 0.45, 6)
        omega = np.interp(np.linspace(0, 5, count), np.arange(6), knots)
        omega = np.convolve(omega, np.ones(5) / 5.0, mode="same")
    elif family == 5:  # stop-go curve
        omega = sign * rng.uniform(0.12, 0.35) * np.ones(count)
        speed = np.full(count, speed)
        speed[count // 3:count // 3 + max(2, count // 8)] = 0.0
        speed[2 * count // 3:2 * count // 3 + max(2, count // 8)] = 0.0
    elif family == 6:  # straight then turn
        omega = np.zeros(count)
        omega[count // 2:] = sign * rng.uniform(0.22, 0.50)
    else:  # gentle alternating curvature, representative of MPPI corrections
        omega = sign * (0.10 + 0.18 * np.sin(4.0 * np.pi * t / max(t[-1], DT)))
    if np.isscalar(speed):
        speed = np.full(count, float(speed))
    return np.asarray(speed), np.asarray(omega), family


def plan_trajectory(sim, rng, frames: int, variant: int, attempts: int = 400):
    speed, omega, family = motion_commands(rng, frames, variant)
    for _ in range(attempts):
        position = np.asarray(sim.pathfinder.get_random_navigable_point(), dtype=np.float64)
        if not np.all(np.isfinite(position)):
            continue
        yaw = rng.uniform(-math.pi, math.pi)
        positions = [position.copy()]
        yaws = [yaw]
        valid = True
        for v, w in zip(speed, omega):
            mid = yaw + 0.5 * w * DT
            proposal = position + np.array([-math.sin(mid) * v * DT, 0.0,
                                             -math.cos(mid) * v * DT])
            filtered = np.asarray(sim.pathfinder.try_step_no_sliding(
                position.astype(np.float32), proposal.astype(np.float32)), dtype=np.float64)
            requested = float(np.linalg.norm(proposal - position))
            moved = float(np.linalg.norm(filtered - position))
            if requested > 1e-5 and moved < 0.97 * requested:
                valid = False
                break
            position = filtered
            yaw += w * DT
            positions.append(position.copy())
            yaws.append(yaw)
        if valid and len(positions) == frames:
            return np.asarray(positions), np.asarray(yaws), speed, omega, family
    raise RuntimeError(f"could not sample a collision-free variant {variant}")


def camera_pose_zup(agent_state):
    sensor = agent_state.sensor_states["color_sensor"]
    center = HABITAT_TO_ZUP @ np.asarray(sensor.position, dtype=np.float64)
    rotation_habitat = quaternion.as_rotation_matrix(sensor.rotation)
    rotation = HABITAT_TO_ZUP @ rotation_habitat @ OPENCV_TO_HABITAT_CAMERA
    q = quaternion.from_rotation_matrix(rotation)
    return center, np.array([q.x, q.y, q.z, q.w], dtype=np.float64)


def write_sequence(sim, output: Path, scene_id: str, split: str, seed: int,
                   variant: int, frames: int):
    rng = np.random.default_rng(seed)
    positions, yaws, speed, omega, family = plan_trajectory(sim, rng, frames, variant)
    output.mkdir(parents=True, exist_ok=False)
    rgb_dir = output / "rgb"
    rgb_dir.mkdir()
    rows = []
    floor_z = None
    agent = sim.get_agent(0)
    for index, (position, yaw) in enumerate(zip(positions, yaws)):
        state = habitat_sim.AgentState()
        state.position = position.astype(np.float32)
        state.rotation = quat_from_angle_axis(float(yaw), np.array([0.0, 1.0, 0.0]))
        agent.set_state(state)
        obs = sim.get_sensor_observations(0)["color_sensor"][:, :, :3]
        actual = agent.get_state()
        center, q = camera_pose_zup(actual)
        if floor_z is None:
            floor_z = float(center[2] - CAMERA_HEIGHT_M)
        timestamp = index * DT
        filename = f"{timestamp:012.6f}.png"
        if not cv2.imwrite(str(rgb_dir / filename), cv2.cvtColor(obs, cv2.COLOR_RGB2BGR)):
            raise RuntimeError(f"failed to write {filename}")
        rows.append(np.concatenate([[timestamp], center, q]))

    fx = WIDTH / (2.0 * math.tan(math.radians(HFOV_DEG) / 2.0))
    np.savetxt(output / "groundtruth.txt", np.asarray(rows), fmt="%.9f",
               header="ground truth camera trajectory\ntimestamp tx ty tz qx qy qz qw")
    (output / "calibration.txt").write_text(f"{fx} {fx} {WIDTH / 2.0} {HEIGHT / 2.0}\n")
    meta = {
        "name": output.name, "scenario": scene_id, "environment": scene_id,
        "split": split, "shape_family": int(family), "variant": int(variant),
        "seed": int(seed), "fps": FPS, "frames": frames, "dt_s": DT,
        "speed_mps_min": float(np.min(speed)), "speed_mps_max": float(np.max(speed)),
        "yaw_rate_rps_min": float(np.min(omega)), "yaw_rate_rps_max": float(np.max(omega)),
        "cam_height_above_floor_m": CAMERA_HEIGHT_M,
        "camera_pitch_down_deg": PITCH_DOWN_DEG, "floor_z_m": floor_z,
        "res": [WIDTH, HEIGHT], "hfov_deg": HFOV_DEG,
        "intrinsics_fx_fy_cx_cy": [fx, fx, WIDTH / 2.0, HEIGHT / 2.0],
        "sensor_model_version": SENSOR_VERSION,
        "source": "Habitat MP3D RGB using the HSGM R2R-CE front-camera contract",
    }
    (output / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene", required=True)
    parser.add_argument("--scene-id", required=True)
    parser.add_argument("--split", choices=("train", "val", "test"), required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--count", type=int, default=24)
    parser.add_argument("--frames", type=int, default=49)
    parser.add_argument("--seed", type=int, default=20260821)
    args = parser.parse_args()
    if args.count < 1 or args.frames < 32:
        raise SystemExit("count must be positive and frames must be at least 32")
    root = Path(args.out)
    root.mkdir(parents=True, exist_ok=True)
    sim = build_sim(Path(args.scene))
    try:
        for index in range(args.count):
            name = f"hsgm_{args.scene_id}_{args.split}_v{index:03d}"
            destination = root / name
            if destination.exists():
                print(f"CAPTURE_SKIP {name}", flush=True)
                continue
            write_sequence(sim, destination, args.scene_id, args.split,
                           args.seed + index * 7919, index, args.frames)
            print(f"CAPTURE_OK {name}", flush=True)
    finally:
        sim.close()


if __name__ == "__main__":
    main()
