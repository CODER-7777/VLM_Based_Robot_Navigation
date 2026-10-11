"""Isolated, reproducible instrumentation of the existing local stair controller.

No training and no edits to the imported controller/scene. Each row is the state
at t, the action held at t, and the forces from the physics solve for [t,t+dt].
Fresh kinematics are computed on a COPY of MjData, leaving the live solver alone.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time

import mujoco
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
SIM = ROOT / "xterra_mjlab/svanm2_moe_stair_sim"
sys.path.insert(0, str(SIM))
import controller as original
from build_scene import get_spawn_pos

LEGS = ("FL", "FR", "RL", "RR")
DEFAULT_MODEL = ROOT / "xterra_mjlab/checkpoints/svanm2_moe/model_90000.pt"
CANDIDATE = ROOT / "xterra_mjlab/evaluation_runs/20261002_moe_target_bundle_updates90500/latest.pt"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def solver_contract(model):
    """Compiled model options: XML hashes alone cannot capture runtime overrides."""
    opt = model.opt
    return dict(impratio=float(opt.impratio), timestep=float(opt.timestep),
                iterations=int(opt.iterations), ls_iterations=int(opt.ls_iterations),
                tolerance=float(opt.tolerance), solver=int(opt.solver),
                integrator=int(opt.integrator), cone=int(opt.cone),
                disableflags=int(opt.disableflags))


def command_at(t, vx, stand, ramp):
    fraction = np.clip((t - stand) / ramp, 0.0, 1.0) if ramp else float(t >= stand)
    return np.array([vx * fraction, 0.0, 0.0], dtype=np.float64)


def fresh_frame(ctrl, data, command):
    rot = data.xmat[ctrl.base_body_id].reshape(3, 3).astype(np.float32)
    gyro = (data.sensordata[ctrl.gyro_adr:ctrl.gyro_adr + 3].astype(np.float32)
            if ctrl.gyro_adr >= 0 else (rot.T @ data.cvel[ctrl.base_body_id, :3]).astype(np.float32))
    return np.concatenate([
        np.asarray(command, dtype=np.float32), gyro * .25,
        rot.T @ np.array([0., 0., -1.], dtype=np.float32),
        data.qpos[ctrl.qpos_idx].astype(np.float32) - original.Q0,
        data.qvel[ctrl.qvel_idx].astype(np.float32) * .05,
        ctrl.previous_action,
    ]).astype(np.float32)


class ObservedController(original.MoeStairController):
    """Observe exact forward outputs; optionally change only the observation input."""
    def __init__(self, model, data, checkpoint, device, sensors="viewer"):
        super().__init__(model, data, checkpoint, device)
        self.sensors = sensors
        self.current_fresh_frame = None
        self.raw_action = np.zeros(12, dtype=np.float32)
        self.gates = np.zeros(8, dtype=np.float32)
        self.policy.register_forward_hook(self._action_hook)
        self.policy.student_moe_encoder.moe.gating_network.register_forward_hook(self._gates_hook)

    def _action_hook(self, module, inputs, output):
        self.raw_action = output.detach().cpu().numpy()[0].copy()
        if not np.isfinite(self.raw_action).all():
            raise FloatingPointError("Nonfinite policy output; audit stops instead of silently replacing it")

    def _gates_hook(self, module, inputs, output):
        self.gates = output.detach().cpu().numpy()[0].copy()

    def get_current_frame(self, command):
        if self.sensors == "fresh":
            if self.current_fresh_frame is None:
                raise RuntimeError("Prepare a fresh measurement before policy inference")
            return self.current_fresh_frame.copy()
        return super().get_current_frame(command)


class Recorder:
    def __init__(self, model, data, ctrl, terrain):
        self.model, self.data, self.ctrl = model, data, ctrl
        self.scratch = mujoco.MjData(model)
        self.terrain = terrain
        self.foot_ids = np.array([mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, leg + "_foot") for leg in LEGS])
        if (self.foot_ids < 0).any():
            raise ValueError("Missing named foot geometry")
        self.names = [mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, i) or f"geom_{i}" for i in range(model.ngeom)]
        self.robot = set(np.flatnonzero(model.body_rootid[model.geom_bodyid] == ctrl.base_body_id).tolist())
        self.terrain_ids = set(i for i, name in enumerate(self.names) if name == "floor" or name.startswith(("step_", "platform_", "curb_")))
        self.box_ids = [i for i in self.terrain_ids if self.names[i] != "floor" and model.geom_contype[i] != 0]
        self.foot_map = {int(g): i for i, g in enumerate(self.foot_ids)}
        self.obs_viewer = np.zeros(45)
        self.obs_fresh = np.zeros(45)

    def prepare(self):
        mujoco.mj_copyData(self.scratch, self.model, self.data)
        mujoco.mj_forward(self.model, self.scratch)

    def surface_height(self, xy):
        """Height under point x/y, for this axis-aligned scene; not edge distance."""
        xy = np.atleast_2d(xy)
        h = np.zeros(len(xy))
        for g in self.box_ids:
            pos, size = self.scratch.geom_xpos[g], self.model.geom_size[g]
            inside = (np.abs(xy - pos[:2]) <= size[:2] + 1e-10).all(axis=1)
            h[inside] = np.maximum(h[inside], pos[2] + size[2])
        return h

    def state_row(self, command, policy_tick):
        c, d, m = self.ctrl, self.scratch, self.model
        rot = d.xmat[c.base_body_id].reshape(3, 3)
        base_vel = np.zeros(6)
        mujoco.mj_objectVelocity(m, d, mujoco.mjtObj.mjOBJ_BODY, c.base_body_id, base_vel, 0)
        feet = d.geom_xpos[self.foot_ids].copy()
        foot_vel = np.zeros((4, 6))
        for i, g in enumerate(self.foot_ids):
            mujoco.mj_objectVelocity(m, d, mujoco.mjtObj.mjOBJ_GEOM, int(g), foot_vel[i], 0)
        q = d.qpos[c.qpos_idx].astype(np.float32)
        dq = d.qvel[c.qvel_idx].astype(np.float32)
        raw_tau = ((c.kp / original.GEAR ** 2) * (original.J_COUPLING @ (c.target_q - q))
                   - (c.kd / original.GEAR ** 2) * (original.J_COUPLING @ dq)) @ original.J_COUPLING
        requested = original.Q0 + original.SCALE * c.previous_action
        return dict(
            time=np.array(d.time), policy_tick=np.array(policy_tick), command=command.copy(),
            q=q, dq=dq, raw_action=c.raw_action.copy(), action=c.previous_action.copy(),
            sim_qpos=d.qpos.copy(), sim_qvel=d.qvel.copy(),
            requested=requested, target=c.target_q.copy(), torque_raw=raw_tau,
            target_removed=requested - c.target_q,
            base_pos=d.qpos[:3].copy(), base_quat=d.qpos[3:7].copy(),
            base_velocity_world=base_vel[3:].copy(), base_velocity_body=rot.T @ base_vel[3:],
            angular_velocity_body=rot.T @ base_vel[:3],
            tilt_deg=np.array(np.degrees(np.arccos(np.clip(rot[2, 2], -1, 1)))),
            yaw_rad=np.array(np.arctan2(rot[1, 0], rot[0, 0])),
            base_clearance=np.array(d.qpos[2] - self.surface_height(d.qpos[:2])[0]),
            foot_pos=feet, foot_velocity_world=foot_vel[:, 3:].copy(),
            foot_clearance=feet[:, 2] - m.geom_size[self.foot_ids, 0] - self.surface_height(feet[:, :2]),
            obs_viewer=self.obs_viewer.copy(), obs_fresh=self.obs_fresh.copy(), gates=c.gates.copy(),
        )

    def contacts_after_step(self, t):
        """mj_step computed these solve quantities at pre-integration time t."""
        foot_force = np.zeros(4)
        riser_force = np.zeros(4)
        step_force = np.zeros(4)
        platform_force = np.zeros(4)
        body_force = 0.
        details = []
        for k in range(self.data.ncon):
            contact = self.data.contact[k]
            g1, g2 = int(contact.geom1), int(contact.geom2)
            if not ((g1 in self.robot and g2 in self.terrain_ids) or (g2 in self.robot and g1 in self.terrain_ids)):
                continue
            force = np.zeros(6)
            mujoco.mj_contactForce(self.model, self.data, k, force)
            if force[0] <= 0:
                continue
            robot_g, terrain_g = (g1, g2) if g1 in self.robot else (g2, g1)
            foot = self.foot_map.get(robot_g)
            normal_z = abs(float(contact.frame[2]))
            name = self.names[terrain_g]
            if foot is not None:
                foot_force[foot] += force[0]
                if name.startswith("step_"):
                    step_force[foot] += force[0]
                    if normal_z < .3:
                        riser_force[foot] += force[0]
                if name.startswith("platform_"):
                    platform_force[foot] += force[0]
            else:
                body_force += force[0]
            details.append(dict(time=float(t), geom1=self.names[g1], geom2=self.names[g2],
                                foot=LEGS[foot] if foot is not None else None,
                                pos=contact.pos.tolist(), frame=contact.frame.tolist(),
                                force_contact=force.tolist(), distance=float(contact.dist)))
        return dict(foot_normal_force=foot_force, foot_riser_force=riser_force,
                    foot_step_force=step_force, foot_platform_force=platform_force,
                    nonfoot_contact_force=np.array(body_force)), details


def top_reached(row, ever_platform):
    return bool(ever_platform.all() and (row["foot_pos"][:, 0] > 3.622).all()
                and (np.abs(row["foot_pos"][:, 1] + 9.5) < 1.).all()
                and row["tilt_deg"] < 30 and row["base_clearance"] > .18)


def record_run(checkpoint, out, terrain="stairs", sensors="viewer", device="cuda:0",
               seconds=30., vx=.30, stand=3., ramp=1., y_offset=0., yaw_offset=0.):
    out, checkpoint = Path(out), Path(checkpoint).resolve()
    if out.exists():
        raise FileExistsError(f"Keep previous evidence; choose a new output directory: {out}")
    if seconds <= stand + ramp or ramp < 0 or stand < 0:
        raise ValueError("Require seconds > stand+ramp and nonnegative schedule durations")
    torch.set_num_threads(1)
    torch.manual_seed(0)
    np.random.seed(0)
    model = mujoco.MjModel.from_xml_path(str(SIM / "scene.xml"))
    if not np.isclose(model.opt.timestep, .005):
        raise ValueError("This audit requires the existing 5 ms physics / decimation 4 contract")
    disabled = []
    if terrain == "flat":
        for g in range(model.ngeom):
            name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, g) or ""
            if name.startswith(("step_", "platform_", "curb_")):
                model.geom_contype[g] = model.geom_conaffinity[g] = 0
                disabled.append(name)
    data = mujoco.MjData(model)
    ctrl = ObservedController(model, data, checkpoint, device, sensors)
    spawn = np.array(get_spawn_pos(1))
    spawn[1] += y_offset
    ctrl.reset(tuple(spawn), yaw_offset)
    recorder = Recorder(model, data, ctrl, terrain)
    out.mkdir(parents=True)
    source = out / "source"
    source.mkdir()
    sources = [Path(__file__), SIM / "controller.py", SIM / "checkpoint_policy.py", SIM / "build_scene.py"]
    for p in sources:
        shutil.copy2(p, source / p.name)
    foot_ids = recorder.foot_ids
    manifest = dict(checkpoint=str(checkpoint), checkpoint_sha256=sha256(checkpoint),
                    checkpoint_update=int(ctrl.checkpoint_update), scene=str(SIM / "scene.xml"),
                    scene_sha256=sha256(SIM / "scene.xml"), source_sha256={str(p): sha256(p) for p in sources},
                    mujoco=mujoco.__version__, torch=torch.__version__, numpy=np.__version__,
                    device=str(ctrl.device), gpu=torch.cuda.get_device_name(ctrl.device) if ctrl.device.type == "cuda" else None,
                    terrain=terrain, sensors=sensors, seconds=seconds, vx=vx, stand=stand, ramp=ramp,
                    dt=float(model.opt.timestep), decimation=4, y_offset=y_offset, yaw_offset=yaw_offset,
                    spawn=spawn.tolist(), disabled_collision_geoms=disabled,
                    joint_names=original.JOINTS, target_min=original.TARGET_MIN.tolist(), target_max=original.TARGET_MAX.tolist(),
                    q0=original.Q0.tolist(), scale=original.SCALE.tolist(), kp=ctrl.kp, kd=ctrl.kd,
                    transmission=original.J_LEG.tolist(), torque_limits=original.TORQUE_LIMITS.tolist(),
                    foot_friction=model.geom_friction[foot_ids].tolist(), foot_solref=model.geom_solref[foot_ids].tolist(),
                    solver_options=solver_contract(model),
                    provenance="Scripted fresh simulation, not a replay of the user's video",
                    sampling="Row state/target at t; forces from solve for [t,t+dt]; policy_tick marks 50 Hz updates")
    write_json(out / "manifest.json", manifest)
    rows = defaultdict(list)
    outcome, error = "timeout_incomplete", None
    bad_tilt = low_body = outside = success_time = 0.
    first_contact = None
    ever_platform = np.zeros(4, dtype=bool)
    started = time.monotonic()
    last_t = 0.
    try:
        with (out / "contacts.jsonl").open("w") as log:
            for k in range(round(seconds / model.opt.timestep)):
                t, dt = float(data.time), float(model.opt.timestep)
                last_t = t
                command = command_at(t, vx, stand, ramp)
                recorder.prepare()
                policy_tick = k % 4 == 0
                if policy_tick:
                    recorder.obs_viewer = original.MoeStairController.get_current_frame(ctrl, command)
                    recorder.obs_fresh = fresh_frame(ctrl, recorder.scratch, command)
                    ctrl.current_fresh_frame = recorder.obs_fresh
                    ctrl.policy_step(tuple(command))
                row = recorder.state_row(command, policy_tick)
                ctrl.physics_step()
                if not np.isfinite(data.qpos).all() or not np.isfinite(data.qvel).all() or abs(data.time - t - dt) > 1e-8:
                    raise FloatingPointError("Invalid physics state or automatic simulation reset")
                row["torque_applied"] = data.qfrc_actuator[ctrl.qvel_idx].copy()
                if not np.allclose(row["torque_applied"], np.clip(row["torque_raw"], -original.TORQUE_LIMITS, original.TORQUE_LIMITS), atol=2e-5):
                    raise RuntimeError("Actual actuator torque differs from reconstructed controller torque")
                contacts, details = recorder.contacts_after_step(t)
                row.update(contacts)
                for event in details:
                    log.write(json.dumps(event, allow_nan=False) + "\n")
                for key, value in row.items():
                    rows[key].append(np.asarray(value).copy())
                if first_contact is None and (row["foot_step_force"] > 1).any():
                    first_contact = t
                ever_platform |= row["foot_platform_force"] > 1
                bad_tilt = bad_tilt + dt if row["tilt_deg"] > 60 else 0.
                low_body = low_body + dt if row["base_clearance"] < .12 else 0.
                lane_out = first_contact is not None and (np.abs(row["foot_pos"][:, 1] + 9.5) > 1.).any()
                outside = outside + dt if lane_out else 0.
                success_time = success_time + dt if terrain == "stairs" and top_reached(row, ever_platform) else 0.
                if bad_tilt >= .25: outcome = "tip"; break
                if low_body >= .25: outcome = "low_body"; break
                if outside >= .25: outcome = "lane_exit"; break
                if success_time >= .5: outcome = "traversed"; break
            else:
                outcome = "flat_completed" if terrain == "flat" else "timeout_incomplete"
    except Exception as exc:
        error, outcome = f"{type(exc).__name__}: {exc}", "error"
    trace = {key: np.stack(value) for key, value in rows.items()}
    if trace:
        np.savez_compressed(out / "trace.npz", **trace)
    status = dict(status="failed" if error else "completed", outcome=outcome, error=error,
                  first_stair_contact_s=first_contact, last_recorded_time_s=last_t,
                  wall_seconds=time.monotonic() - started, samples=len(rows.get("time", [])),
                  warnings={str(i): int(w.number) for i, w in enumerate(data.warning) if w.number})
    write_json(out / "status.json", status)
    print(json.dumps(dict(out=str(out), **status)), flush=True)
    if error:
        raise RuntimeError(error)
    return out


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument("--checkpoint", type=Path, default=CANDIDATE)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--terrain", choices=("flat", "stairs"), default="stairs")
    p.add_argument("--sensors", choices=("viewer", "fresh"), default="viewer")
    p.add_argument("--device", default="cuda:0")
    p.add_argument("--seconds", type=float, default=30.)
    p.add_argument("--vx", type=float, default=.30)
    p.add_argument("--stand", type=float, default=3.)
    p.add_argument("--ramp", type=float, default=1.)
    p.add_argument("--y-offset", type=float, default=0.)
    p.add_argument("--yaw-offset", type=float, default=0.)
    a = p.parse_args()
    record_run(**vars(a))


if __name__ == "__main__":
    main()
