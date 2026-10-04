"""Passive recording of the user's live viewer session, with reset boundaries.

Uses the existing recorder's scratch-data measurements. No command schedule,
inference modification, solver refresh on live data, or training is performed.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import queue
import shutil
import time

import mujoco
import numpy as np
import torch

from record import ROOT, SIM, Recorder, fresh_frame, original, sha256, write_json
from teleop import KeyboardTeleop


class RecordedTeleop(KeyboardTeleop):
    """Apply key callbacks on the simulation thread, before measurement/stepping.

Terminal and viewer callbacks only enqueue events. This prevents a reset from
mutating MjData halfway through a logged physics step. Commands retain the
existing increments/limits and are sampled by the policy at its existing rate.
"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pending = queue.SimpleQueue()

    def handle_char(self, ch):
        self.pending.put(("terminal", ch, time.monotonic()))

    def handle_key(self, keycode):
        self.pending.put(("viewer", keycode, time.monotonic()))

    def apply_pending(self, session):
        while True:
            try:
                source, key, received = self.pending.get_nowait()
            except queue.Empty:
                break
            before = self.command
            if source == "terminal":
                reset = key.lower() in "123456rt" and len(key) == 1
                super().handle_char(key)
            else:
                reset = 49 <= key <= 54 or key in (ord('R'), ord('r'), ord('T'), ord('t'))
                super().handle_key(key)
            if reset:
                session.new_episode(f"{source} reset/teleport key {key!r}", self)
            session.event(dict(type="key", source=source, key=key,
                               received_wall_s=received - session.started,
                               before_command=list(before), after_command=list(self.command),
                               reset=reset, track=self.current_track))


class InteractiveSession:
    chunk_samples = 1000  # Five simulation seconds at the current 200 Hz.

    def __init__(self, model, data, ctrl, teleop, out=None, decimation=4):
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self.out = (Path(out) if out else ROOT / "tools/results/interactive" / stamp).resolve()
        self.out.mkdir(parents=True, exist_ok=False)
        self.model, self.data, self.ctrl = model, data, ctrl
        self.started = time.monotonic()
        self.decimation = decimation
        self.closed = False
        self.episode_id = 0
        self.events = (self.out / "events.jsonl").open("w", buffering=1)
        self.handles = []
        # Hooks observe the existing outputs without replacing the policy.
        ctrl.raw_action = np.zeros(12, dtype=np.float32)
        ctrl.gates = np.zeros(8, dtype=np.float32)
        self.handles.append(ctrl.policy.register_forward_hook(self._action_hook))
        self.handles.append(ctrl.policy.student_moe_encoder.moe.gating_network.register_forward_hook(self._gate_hook))
        self.recorder = Recorder(model, data, ctrl, "interactive_stairs")
        sources = [Path(__file__), SIM / "run_interactive_sim.py", SIM / "controller.py",
                   SIM / "teleop.py", SIM / "checkpoint_policy.py", SIM / "build_scene.py",
                   Path(__file__).with_name("record.py"), Path(__file__).with_name("plot_interactive.py")]
        snapshot = self.out / "source"
        snapshot.mkdir()
        for source in sources:
            shutil.copy2(source, snapshot / source.name)
        shutil.copy2(SIM / "scene.xml", snapshot / "scene.xml")
        self.manifest = dict(
            recording_kind="interactive_user_commands", created_utc=datetime.now(timezone.utc).isoformat(),
            checkpoint=str(ctrl.checkpoint_path), checkpoint_update=int(ctrl.checkpoint_update),
            checkpoint_sha256=sha256(ctrl.checkpoint_path), device=str(ctrl.device),
            gpu=torch.cuda.get_device_name(ctrl.device) if ctrl.device.type == "cuda" else None,
            scene_sha256=sha256(SIM / "scene.xml"), source_sha256={str(p): sha256(p) for p in sources},
            mujoco=mujoco.__version__, torch=torch.__version__, numpy=np.__version__,
            dt=float(model.opt.timestep), decimation=decimation, joint_names=original.JOINTS,
            target_min=original.TARGET_MIN.tolist(), target_max=original.TARGET_MAX.tolist(),
            scale=original.SCALE.tolist(), q0=original.Q0.tolist(), kp=ctrl.kp, kd=ctrl.kd,
            transmission=original.J_LEG.tolist(), torque_limits=original.TORQUE_LIMITS.tolist(),
            track_configs=teleop.track_configs,
            foot_friction=model.geom_friction[self.recorder.foot_ids].tolist(),
            foot_solref=model.geom_solref[self.recorder.foot_ids].tolist(),
            foot_radius_m=model.geom_size[self.recorder.foot_ids, 0].tolist(),
            sampling="State/target at t; contact solve and applied torque for [t,t+dt]. Actual policy command is held between ticks.",
            observation_timing=ctrl.observation_timing,
            observation_convention="Policy input uses selected timing. obs_viewer is legacy; obs_fresh is refreshed; obs_policy is the frame actually used. Refresh is on copied MjData only.",
            input_handling="Keys are queued and applied between physics steps to prevent concurrent reset/measurement races.",
            provenance="User-operated MuJoCo session. No scripted command schedule; this is simulator data, not real hardware.",
        )
        write_json(self.out / "manifest.json", self.manifest)
        self.new_episode("initial spawn", teleop)
        print(f"[RECORD] Saving your interactive session to: {self.out}", flush=True)

    def _action_hook(self, module, inputs, output):
        self.ctrl.raw_action = output.detach().cpu().numpy()[0].copy()

    def _gate_hook(self, module, inputs, output):
        self.ctrl.gates = output.detach().cpu().numpy()[0].copy()

    def event(self, item):
        item = dict(item, sim_time=float(self.data.time), wall_s=time.monotonic() - self.started,
                    episode=self.episode_id)
        self.events.write(json.dumps(item, allow_nan=False) + "\n")

    def new_episode(self, reason, teleop):
        if self.episode_id:
            self._finish_episode("reset_or_teleport")
        self.episode_id += 1
        self.episode = self.out / f"attempt_{self.episode_id:03d}"
        (self.episode / "raw").mkdir(parents=True)
        self.rows = defaultdict(list)
        self.chunks = []
        self.samples = 0
        self.first_contact = None
        self.first_riser = None
        self.t0 = float(self.data.time)
        self.last_command = np.zeros(3)
        self.ctrl.raw_action = np.zeros(12, dtype=np.float32)
        self.ctrl.gates = np.zeros(8, dtype=np.float32)
        self.contacts = (self.episode / "contacts.jsonl").open("w", buffering=1)
        manifest = dict(self.manifest, episode=self.episode_id, reason=reason,
                        track=teleop.current_track, start_sim_time=self.t0,
                        initial_base_pos=self.data.qpos[:3].tolist())
        write_json(self.episode / "manifest.json", manifest)
        self.event(dict(type="attempt_start", reason=reason, track=teleop.current_track))
        self._status("recording")

    def prepare_policy(self, command, policy_tick):
        self.recorder.prepare()
        if policy_tick:
            self.last_command = np.array(command, dtype=float)
            self.recorder.obs_viewer = self.ctrl.get_legacy_frame(tuple(command))
            self.recorder.obs_fresh = fresh_frame(self.ctrl, self.recorder.scratch, command)
        self.tick = policy_tick
        self.wall_before = time.monotonic() - self.started

    def before_physics(self, input_command, track):
        self.row = self.recorder.state_row(self.last_command, self.tick)
        self.row["obs_policy"] = self.ctrl.history[-1].copy()
        self.row.update(input_command=np.asarray(input_command), track=np.array(track),
                        wall_s=np.array(self.wall_before),
                        policy_wall_end_s=np.array(time.monotonic() - self.started),
                        raw_action_finite=np.array(np.isfinite(self.ctrl.raw_action).all()))

    def after_physics(self):
        row = self.row
        row["torque_applied"] = self.data.qfrc_actuator[self.ctrl.qvel_idx].copy()
        row["motor_ctrl"] = self.data.ctrl.copy()
        contacts, details = self.recorder.contacts_after_step(float(row["time"]))
        row.update(contacts)
        for detail in details:
            self.contacts.write(json.dumps(detail, allow_nan=False) + "\n")
        if self.first_contact is None and (row["foot_step_force"] > 1).any():
            self.first_contact = float(row["time"])
        if self.first_riser is None and (row["foot_riser_force"] > 1).any():
            self.first_riser = float(row["time"])
        for key, value in row.items():
            self.rows[key].append(np.asarray(value).copy())
        self.samples += 1
        if len(self.rows["time"]) >= self.chunk_samples:
            self.flush()
        if self.data.time <= float(row["time"]):
            raise RuntimeError("MuJoCo time reset unexpectedly; logged episode cannot continue across that discontinuity")

    def flush(self):
        if not self.rows.get("time"):
            return
        name = f"raw/chunk_{len(self.chunks):05d}.npz"
        target = self.episode / name
        tmp = target.with_suffix(".tmp")
        with tmp.open("wb") as f:
            np.savez_compressed(f, **{k: np.stack(v) for k, v in self.rows.items()})
        tmp.replace(target)
        self.chunks.append(name)
        self.rows.clear()
        self.contacts.flush()
        self._status("recording")

    def _status(self, state, error=None):
        write_json(self.episode / "status.json", dict(
            status=state, samples=self.samples, chunks=self.chunks,
            first_stair_contact_s=self.first_contact, first_riser_contact_s=self.first_riser,
            error=error, warnings={str(i): int(w.number) for i, w in enumerate(self.data.warning) if w.number}))

    def _finish_episode(self, reason, error=None):
        self.flush()
        self._status(reason, error)
        self.contacts.close()

    def close(self, error=None):
        if self.closed:
            return
        self.closed = True
        self._finish_episode("error" if error else "closed", error)
        self.event(dict(type="session_end", error=error))
        self.events.close()
        for handle in self.handles:
            handle.remove()
        write_json(self.out / "status.json", dict(status="error" if error else "closed",
                                                  attempts=self.episode_id, error=error))
        print(f"\n[RECORD] Data saved: {self.out}", flush=True)
