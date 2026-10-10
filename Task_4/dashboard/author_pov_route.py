#!/usr/bin/env python3
"""Drive through a Habitat scene in first person and save the driven route.

The UI is served over HTTP so it works on headless machines through VS Code
port forwarding. The route is the sequence of positions actually traversed by
the user, while the start pose, final position, and typed instruction become a
one-episode R2R-CE dataset for NaVIDA.
"""

import argparse
import copy
import gzip
import io
import json
import math
import os
import queue
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import habitat
import numpy as np
from habitat.config import read_write
from habitat.config.default_structured_configs import HabitatSimSemanticSensorConfig
from habitat_baselines.config.default import get_config
from habitat.utils.geometry_utils import quaternion_rotate_vector
from PIL import Image

# Register NaVIDA's R2R-CE dataset implementation and custom measures.
from habitat_extensions import measures, task  # noqa: F401
from src.eval.static_blockers import (
    BLOCKER_INFO_KEY,
    FORCE_RECOMPUTE_INFO_KEY,
    install_blockers,
    shortest_path,
)
from src.eval.mp3d_object_cloner import extract_semantic_object


HTML = r"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Habitat POV Route Author</title>
  <style>
    body { margin: 0; background: #17191d; color: #eee; font: 15px system-ui; }
    main { max-width: 1120px; margin: auto; padding: 16px; }
    h2 { margin: 0 0 10px; }
    #view { width: 100%; max-height: 68vh; object-fit: contain; background: #000; cursor: crosshair; }
    .row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px; }
    button { padding: 10px 15px; font-weight: 650; cursor: pointer; }
    input { flex: 1; min-width: 280px; padding: 10px; }
    label input { min-width: 0; width: 70px; flex: none; }
    #status, #notes { margin-top: 9px; color: #cbd5e1; white-space: pre-wrap; }
    .save { background: #24a148; color: white; border: 0; }
    .danger { background: #b42318; color: white; border: 0; }
    kbd { border: 1px solid #777; border-radius: 3px; padding: 1px 5px; }
  </style>
</head>
<body><main>
  <h2>Habitat first-person route author</h2>
  <div id="source" style="margin-bottom:10px;color:#facc15"></div>
  <img id="view" src="frame.jpg?v=0" alt="Habitat RGB observation">
  <div style="margin-top:6px;color:#9ca3af">Doors &amp; drawers: click one in the view, or press <kbd>E</kbd> next to one, to open/close it.</div>
  <div class="row">
    <button onclick="act('left')">↶ Turn left 15° (<kbd>A</kbd>)</button>
    <button onclick="act('forward')">↑ Forward 25 cm (<kbd>W</kbd>)</button>
    <button onclick="act('backward')">↓ Backward 25 cm (<kbd>S</kbd>)</button>
    <button onclick="act('right')">Turn right 15° (<kbd>D</kbd>) ↷</button>
    <button class="danger" onclick="resetRoute()">Reset route</button>
  </div>
  <div class="row">
    <input id="landmark" placeholder="Optional landmark note at current position">
    <button onclick="markLandmark()">Mark landmark</button>
  </div>
  <div class="row">
    <label>Width m <input id="bw" type="number" min="0.2" step="0.1" value="1.4"></label>
    <label>Height m <input id="bh" type="number" min="0.2" step="0.1" value="2.0"></label>
    <label>Depth m <input id="bd" type="number" min="0.1" step="0.1" value="0.3"></label>
    <label>Ahead m <input id="ba" type="number" min="0.3" step="0.1" value="1.5"></label>
    <button onclick="placeBlocker()">Add box ahead</button>
  </div>
  <div class="row">
    <button onclick="enableObjectSelection()">Select furniture assembly (then click image)</button>
    <label>Scale <input id="os" type="number" min="0.2" step="0.1" value="1.0"></label>
    <label>Ahead m <input id="oa" type="number" min="0.3" step="0.1" value="1.5"></label>
    <label>Yaw ° <input id="oy" type="number" step="15" value="0"></label>
    <button onclick="placeClone()">Add textured furniture copy</button>
    <button onclick="request('remove-last')">Remove last object</button>
    <button onclick="request('remove-blocker')">Clear all objects</button>
  </div>
  <div class="row">
    <label>Complete asset
      <select id="libraryAsset" style="padding:10px">
        <option value="chair_01">ReplicaCAD armchair 01</option>
        <option value="chair_04">ReplicaCAD chair 04</option>
        <option value="chair_05">ReplicaCAD chair 05</option>
        <option value="sofa">ReplicaCAD sofa</option>
        <option value="table_01">ReplicaCAD table 01</option>
        <option value="stool_02">ReplicaCAD stool 02</option>
        <option value="beanbag">ReplicaCAD beanbag</option>
      </select>
    </label>
    <label>Scale <input id="ls" type="number" min="0.2" step="0.1" value="1.0"></label>
    <label>Ahead m <input id="la" type="number" min="0.5" step="0.1" value="2.0"></label>
    <label>Yaw ° <input id="ly" type="number" step="15" value="0"></label>
    <button onclick="placeLibraryAsset()">Add complete furniture asset</button>
  </div>
  <div class="row">
    <label>Case name <input id="caseName" value="case_01" pattern="[A-Za-z0-9._-]+"></label>
    <input id="caseInstruction" placeholder="Case instruction (blank keeps original R2R instruction)">
    <button class="save" onclick="saveChallenge()">Save matched case</button>
  </div>
  <div class="row">
    <input id="instruction" placeholder="Type the navigation instruction after driving the route">
    <button class="save" onclick="saveRoute()">Save NaVIDA episode</button>
  </div>
  <div id="status">Loading…</div>
  <div id="notes"></div>
</main>
<script>
let busy = false;
let selectingObject = false;
async function request(path, payload={}) {
  if (busy) return;
  busy = true;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10000);
  try {
    const response = await fetch(path, {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload), signal: controller.signal
    });
    const data = await response.json();
    document.getElementById('status').textContent = data.message || '';
    document.getElementById('notes').textContent = data.landmarks || '';
    if (data.source_instruction) document.getElementById('source').textContent =
      'Original instruction: ' + data.source_instruction;
    if (data.step !== undefined) {
      document.getElementById('view').src = 'frame.jpg?v=' + data.step + '-' + Date.now();
    }
  } catch (error) {
    document.getElementById('status').textContent =
      'Server request failed: ' + error + '. Reload after confirming port 8766 is running.';
  } finally { clearTimeout(timeout); busy = false; }
}
function act(action) { request('action', {action}); }
function resetRoute() {
  if (confirm('Return to the original start and erase this driven route?')) request('reset');
}
function markLandmark() {
  const box = document.getElementById('landmark');
  if (box.value.trim()) request('mark', {label: box.value.trim()});
  box.value = '';
}
function placeBlocker() {
  request('blocker', {
    width: Number(document.getElementById('bw').value),
    height: Number(document.getElementById('bh').value),
    depth: Number(document.getElementById('bd').value),
    distance: Number(document.getElementById('ba').value)
  });
}
function enableObjectSelection() {
  selectingObject = true;
  document.getElementById('status').textContent = 'Click near the centre of the chair or furniture.';
}
document.getElementById('view').addEventListener('click', event => {
  const rect = event.currentTarget.getBoundingClientRect();
  if (!selectingObject) {
    request('toggle-part', {
      x: (event.clientX - rect.left) / rect.width,
      y: (event.clientY - rect.top) / rect.height
    });
    return;
  }
  selectingObject = false;
  request('select-object', {
    x: (event.clientX - rect.left) / rect.width,
    y: (event.clientY - rect.top) / rect.height
  });
});
function placeClone() {
  request('clone', {
    scale: Number(document.getElementById('os').value),
    distance: Number(document.getElementById('oa').value),
    yaw: Number(document.getElementById('oy').value)
  });
}
function placeLibraryAsset() {
  request('library-asset', {
    asset: document.getElementById('libraryAsset').value,
    scale: Number(document.getElementById('ls').value),
    distance: Number(document.getElementById('la').value),
    yaw: Number(document.getElementById('ly').value)
  });
}
function saveChallenge() {
  const caseName = document.getElementById('caseName').value.trim();
  if (!caseName) { alert('Enter a case name, such as case_01.'); return; }
  request('save-challenge', {
    case_name: caseName,
    instruction: document.getElementById('caseInstruction').value.trim()
  });
}
function saveRoute() {
  const text = document.getElementById('instruction').value.trim();
  if (!text) { alert('Type an instruction first.'); return; }
  request('save', {instruction: text});
}
document.addEventListener('keydown', event => {
  if (event.target.tagName === 'INPUT') return;
  const key = event.key.toLowerCase();
  if (key === 'w' || key === 'arrowup') act('forward');
  if (key === 's' || key === 'arrowdown') act('backward');
  if (key === 'a' || key === 'arrowleft') act('left');
  if (key === 'd' || key === 'arrowright') act('right');
  if (key === 'e') request('toggle-near');
  if (['w','a','s','d','arrowup','arrowleft','arrowdown','arrowright'].includes(key)) event.preventDefault();
});
request('state');
</script></body></html>"""


def parse_args():
    root = Path(__file__).resolve().parents[1]
    pilot = root / "pilot/navida_r2rce_control50"
    full_val_unseen = Path(
        "/home/guest-isl/rishabh/VLA-paper/data/datasets/"
        "R2R_VLNCE_v1-3/val_unseen/val_unseen.json.gz"
    )
    parser = argparse.ArgumentParser(
        description="Author a NaVIDA route by driving Habitat from the RGB POV."
    )
    parser.add_argument(
        "--dataset",
        default=str(
            full_val_unseen
            if os.access(full_val_unseen, os.R_OK)
            else pilot / "data/pilot50.json.gz"
        ),
    )
    parser.add_argument(
        "--config", default=str(pilot / "vln_r2rce_pilot50.yaml")
    )
    parser.add_argument("--episode-id", default="1757")
    parser.add_argument(
        "--output", default=str(root / "custom/pov_route.json.gz")
    )
    parser.add_argument(
        "--challenge-output",
        default=str(root / "custom/blocked_r2r_episode.json.gz"),
        help="original R2R episode plus the authored static blocker",
    )
    parser.add_argument(
        "--baseline-output",
        default=str(root / "custom/baseline_r2r_episode.json.gz"),
        help="matched episode with navmesh recomputation but no blocker",
    )
    parser.add_argument("--goal-radius", type=float, default=1.0)
    parser.add_argument("--scenes-dir", default="", help="override scenes_dir (e.g. refined scenes)")
    parser.add_argument("--parts-dir", default="", help="interactive doors/drawers (export_parts.py index)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--jpeg-quality", type=int, default=90)
    parser.add_argument(
        "--cases-dir", default=str(root / "custom/cases"),
        help="directory containing separately named matched cases",
    )
    parser.add_argument(
        "--extracted-assets-dir", default=str(root / "custom/extracted_mp3d_objects"),
    )
    parser.add_argument(
        "--replica-cad-dir", default=str(root / "data/replica_cad"),
        help="ReplicaCAD root containing configs/objects",
    )
    return parser.parse_args()


def load_json(path):
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt") as handle:
        return json.load(handle)


def save_json_gz(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with gzip.open(temporary, "wt") as handle:
        json.dump(payload, handle, indent=2)
    os.replace(temporary, path)


def pose_dict(state):
    rotation = state.rotation
    return {
        "position": [float(value) for value in state.position],
        "rotation_xyzw": [
            float(rotation.imag[0]),
            float(rotation.imag[1]),
            float(rotation.imag[2]),
            float(rotation.real),
        ],
    }


class RouteSession:
    ACTIONS = {"forward": 1, "backward": 1, "left": 2, "right": 3}
    LIBRARY_ASSETS = {
        "chair_01": ("frl_apartment_chair_01.object_config.json", "chair"),
        "chair_04": ("frl_apartment_chair_04.object_config.json", "chair"),
        "chair_05": ("frl_apartment_chair_05.object_config.json", "chair"),
        "sofa": ("frl_apartment_sofa.object_config.json", "sofa"),
        "table_01": ("frl_apartment_table_01.object_config.json", "table"),
        "stool_02": ("frl_apartment_stool_02.object_config.json", "stool"),
        "beanbag": ("frl_apartment_beanbag.object_config.json", "beanbag"),
    }

    def __init__(self, args):
        self.args = args
        self.jobs = queue.Queue()
        self.source = load_json(args.dataset)
        self.raw_episode = next(
            (
                episode for episode in self.source["episodes"]
                if str(episode["episode_id"]) == str(args.episode_id)
            ),
            None,
        )
        if self.raw_episode is None:
            raise SystemExit(
                "Episode {} is not present in {}".format(args.episode_id, args.dataset)
            )

        config = get_config(args.config)
        with read_write(config):
            config.habitat.dataset.data_path = str(Path(args.dataset).resolve())
            config.habitat.dataset.split = "custom"
            if args.scenes_dir:
                config.habitat.dataset.scenes_dir = args.scenes_dir
            # Route authoring should not stop at the normal 500-step episode limit.
            config.habitat.environment.max_episode_steps = 10000
            # NDTW reads {split}_gt files that do not exist for split=custom; authoring never needs it.
            config.habitat.task.measurements.pop("ndtw", None)
            rgb = config.habitat.simulator.agents.main_agent.sim_sensors.rgb_sensor
            depth = config.habitat.simulator.agents.main_agent.sim_sensors.depth_sensor
            depth.width, depth.height, depth.hfov = rgb.width, rgb.height, rgb.hfov
            self.click_hfov = float(rgb.hfov)
            config.habitat.simulator.agents.main_agent.sim_sensors.semantic_sensor = (
                HabitatSimSemanticSensorConfig(
                    width=rgb.width, height=rgb.height, hfov=rgb.hfov
                )
            )

        dataset = habitat.datasets.make_dataset(
            id_dataset=config.habitat.dataset.type, config=config.habitat.dataset
        )
        dataset.episodes = [
            episode for episode in dataset.episodes
            if str(episode.episode_id) == str(args.episode_id)
        ]
        if not dataset.episodes:
            raise SystemExit("Habitat could not load the requested episode")
        self.env = habitat.Env(config.habitat, dataset)
        self.scene_glb = (
            Path(config.habitat.dataset.scenes_dir) / self.raw_episode["scene_id"]
        ).resolve()
        self.blocker_specs = []
        self.selected_object = None
        self.blocker_validation = None
        self.reset()
        # Isaac-repaired doors/drawers as separate STATIC objects, so the recompute below bakes them.
        self.parts = None
        self.last_part = None
        if args.parts_dir:
            from parts_rt import Parts
            self.parts = Parts(self.env.sim, args.parts_dir)
        # Use the same recomputation in both matched conditions so the box is
        # the only navigation difference between baseline and blocked runs.
        install_blockers(self.env.sim, [], force_recompute=True)
        self.baseline_navigation = shortest_path(
            self.env.sim.pathfinder,
            self.raw_episode["start_position"],
            self.raw_episode["goals"][0]["position"],
        )

    def reset(self):
        self.observation = self.env.reset()
        self.step = 0
        self.actions = []
        self.landmarks = []
        self.start_pose = pose_dict(self.env.sim.get_agent_state())
        self.route = [self.start_pose["position"]]
        self.distance = 0.0
        self._refresh_frame()

    def act(self, action_name):
        if action_name not in self.ACTIONS:
            raise ValueError("Unknown action: {}".format(action_name))
        before = np.asarray(self.env.sim.get_agent_state().position, dtype=np.float64)
        if action_name == "backward":
            # Reverse translation while preserving heading and Habitat collisions.
            actuation = self.env.sim.get_agent(0).agent_config.action_space[
                self.ACTIONS["forward"]
            ].actuation
            original_amount = actuation.amount
            try:
                actuation.amount = -abs(original_amount)
                self.observation = self.env.step({"action": self.ACTIONS[action_name]})
            finally:
                actuation.amount = original_amount
        else:
            self.observation = self.env.step({"action": self.ACTIONS[action_name]})
        after = np.asarray(self.env.sim.get_agent_state().position, dtype=np.float64)
        movement = float(np.linalg.norm(after - before))
        if movement > 1e-5:
            self.route.append(after.tolist())
            self.distance += movement
        self.actions.append(action_name)
        self.step += 1
        self._refresh_frame()
        return movement

    def _refresh_frame(self):
        image = Image.fromarray(self.observation["rgb"].astype(np.uint8)).convert("RGB")
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=self.args.jpeg_quality)
        self.frame = buffer.getvalue()

    def submit(self, operation, *args):
        """Ask the simulator-owning main thread to execute one operation."""
        completed = threading.Event()
        job = {
            "operation": operation,
            "args": args,
            "completed": completed,
            "result": None,
            "error": None,
        }
        self.jobs.put(job)
        if not completed.wait(timeout=15):
            raise TimeoutError("Habitat simulator did not answer within 15 seconds")
        if job["error"] is not None:
            raise job["error"]
        return job["result"]

    def process_next_job(self, timeout=0.5):
        """Execute one queued browser operation on Habitat's GL owner thread."""
        try:
            job = self.jobs.get(timeout=timeout)
        except queue.Empty:
            return
        try:
            operation = job["operation"]
            if operation == "action":
                movement = self.act(*job["args"])
                suffix = (
                    "" if movement > 1e-5
                    else " (no translation; possibly a turn or collision)"
                )
                job["result"] = self.state("Action applied" + suffix)
            elif operation == "reset":
                self.reset()
                job["result"] = self.state("Route reset to the source start pose")
            elif operation == "mark":
                self.mark(*job["args"])
                job["result"] = self.state("Landmark recorded")
            elif operation == "save":
                self.save(*job["args"])
                job["result"] = self.state(
                    "Saved NaVIDA dataset to {}".format(self.args.output)
                )
            elif operation == "blocker":
                self.place_blocker(*job["args"])
                job["result"] = self.state("Blocker placed and navmesh recomputed")
            elif operation == "select_object":
                selected = self.select_object(*job["args"])
                job["result"] = self.state(
                    "Selected {} assembly {} (RGB geometry inside its full semantic bounds)".format(
                        selected["category"], selected["semantic_object_id"]
                    )
                )
            elif operation == "clone":
                self.place_selected_clone(*job["args"])
                job["result"] = self.state("Object copy placed and navmesh recomputed")
            elif operation == "library_asset":
                label = self.place_library_asset(*job["args"])
                job["result"] = self.state(
                    "Complete {} placed and navmesh recomputed".format(label)
                )
            elif operation == "remove_last":
                self.remove_last_blocker()
                job["result"] = self.state("Removed the last placed object")
            elif operation == "remove_blocker":
                self.remove_blocker()
                job["result"] = self.state("All placed objects removed")
            elif operation == "save_challenge":
                baseline_path, blocked_path = self.save_blocked_challenge(*job["args"])
                job["result"] = self.state(
                    "Saved matched case: {} and {}".format(baseline_path, blocked_path)
                )
            elif operation == "toggle_click":
                job["result"] = self.state(self.click_part(*job["args"]))
            elif operation == "toggle_near":
                job["result"] = self.state(self.near_part())
            elif operation == "state":
                job["result"] = self.state()
            else:
                raise ValueError("Unknown queued operation: {}".format(operation))
        except Exception as error:
            job["error"] = error
        finally:
            job["completed"].set()
            self.jobs.task_done()

    def _toggle_part(self, part_id):
        state = self.parts.toggle(part_id)  # re-poses the part and recomputes the navmesh
        self.last_part = part_id
        self.observation.update(self.env.sim.get_sensor_observations())
        self._refresh_frame()
        part = next(p for p in self.parts.index if p["id"] == part_id)
        unit = "deg" if part["kind"] == "revolute" else "m"
        return "{} {} ({:g} {}) | navmesh recomputed".format(
            part_id, "moved" if state else "back to default", part["values"][state], unit)

    def _require_parts(self):
        if self.parts is None:
            raise ValueError("Doors are not interactive in this run (start it with INTERACTIVE=1)")

    def click_part(self, x_fraction, y_fraction):
        self._require_parts()
        depth = np.asarray(self.env.sim.get_sensor_observations()["depth"]).squeeze()
        h, w = depth.shape
        u = min(w - 1, max(0, int(float(x_fraction) * w)))
        v = min(h - 1, max(0, int(float(y_fraction) * h)))
        z = float(depth[v, u])
        if not z > 0:
            raise ValueError("Nothing under the cursor")
        f = (w / 2.0) / math.tan(math.radians(self.click_hfov) / 2.0)
        cam = np.array([(u + 0.5 - w / 2.0) / f * z, -(v + 0.5 - h / 2.0) / f * z, -z])
        sensor = self.env.sim.get_agent_state().sensor_states["depth"]
        world = quaternion_rotate_vector(sensor.rotation, cam) + np.asarray(sensor.position)
        part_id = self.parts.pick(world)
        if part_id is None:
            raise ValueError("No door or drawer under the cursor ({:.2f} m away)".format(z))
        return self._toggle_part(part_id)

    def near_part(self):
        self._require_parts()
        state = self.env.sim.get_agent_state()
        forward = quaternion_rotate_vector(state.rotation, np.asarray([0.0, 0.0, -1.0]))
        sensor = state.sensor_states["depth"]
        depth = np.asarray(self.env.sim.get_sensor_observations()["depth"]).squeeze()
        h, w = depth.shape
        f = (w / 2.0) / math.tan(math.radians(self.click_hfov) / 2.0)
        inverse = sensor.rotation.inverse()
        part_id = None
        for _, candidate, point in self.parts.nearest(np.asarray(sensor.position), forward):
            if np.linalg.norm(point - np.asarray(sensor.position)) < 0.25:
                part_id = candidate  # the robot is practically touching it (e.g. a leaf swung onto it)
                break
            # Line of sight: the depth image must not hit a wall before the part's nearest point.
            cam = quaternion_rotate_vector(inverse, point - np.asarray(sensor.position))
            if cam[2] >= -0.05:
                continue
            u = int(f * cam[0] / -cam[2] + w / 2.0); v = int(-f * cam[1] / -cam[2] + h / 2.0)
            if 0 <= u < w and 0 <= v < h and depth[v, u] >= -cam[2] - 0.15:
                part_id = candidate
                break
        if part_id is None and self.last_part is not None:
            # A leaf swung out of view (e.g. outward through its doorway) can still be closed with E.
            lo, hi = self.parts.world_aabb(self.last_part)
            eye = np.asarray(sensor.position)
            if float(np.linalg.norm((np.clip(eye, lo, hi) - eye)[[0, 2]])) <= 3.0:
                part_id = self.last_part
        if part_id is None:
            raise ValueError("No visible door or drawer within 1.5 m in front of the robot")
        return self._toggle_part(part_id)

    def mark(self, label):
        pose = pose_dict(self.env.sim.get_agent_state())
        self.landmarks.append({"label": label, **pose, "step": self.step})

    def _reference_intersects_blocker(self, spec):
        rotation = spec["rotation_xyzw"]
        world_to_blocker = np.quaternion(
            rotation[3], rotation[0], rotation[1], rotation[2]
        ).inverse()
        center = np.asarray(spec["position"], dtype=np.float64)
        half = np.asarray(spec["half_extents"], dtype=np.float64)
        if spec.get("position_is_floor_origin", False):
            center[1] += half[1]
        margin = 0.1  # Match the configured NaVIDA agent radius.
        reference = self.raw_episode.get("reference_path", [])
        for start, end in zip(reference[:-1], reference[1:]):
            start = np.asarray(start, dtype=np.float64)
            end = np.asarray(end, dtype=np.float64)
            distance = float(np.linalg.norm(end - start))
            sample_count = max(2, int(math.ceil(distance / 0.05)) + 1)
            for alpha in np.linspace(0.0, 1.0, sample_count):
                point = start + alpha * (end - start)
                local = quaternion_rotate_vector(world_to_blocker, point - center)
                if (
                    abs(local[0]) <= half[0] + margin
                    and abs(local[2]) <= half[2] + margin
                    and abs(local[1]) <= half[1] + 0.25
                ):
                    return True
        return False

    def place_blocker(self, width, height, depth, distance_ahead):
        dimensions = [float(width), float(height), float(depth)]
        distance_ahead = float(distance_ahead)
        if any(not math.isfinite(value) or value <= 0 for value in dimensions):
            raise ValueError("Blocker width, height, and depth must be positive")
        if not math.isfinite(distance_ahead) or distance_ahead <= dimensions[2] / 2:
            raise ValueError("Place the blocker farther ahead than half its depth")

        state = self.env.sim.get_agent_state()
        forward = quaternion_rotate_vector(
            state.rotation, np.asarray([0.0, 0.0, -1.0])
        )
        forward[1] = 0.0
        norm = float(np.linalg.norm(forward))
        if norm < 1e-6:
            raise ValueError("Could not determine the agent's horizontal heading")
        forward /= norm
        center = np.asarray(state.position, dtype=np.float64) + forward * distance_ahead
        center[1] = float(state.position[1]) + dimensions[1] / 2.0
        rotation = pose_dict(state)["rotation_xyzw"]
        spec = {
            "kind": "box",
            "position": center.tolist(),
            "rotation_xyzw": rotation,
            "half_extents": [value / 2.0 for value in dimensions],
        }
        self.blocker_specs.append(spec)
        self._refresh_blocker_state()

    def select_object(self, x_fraction, y_fraction):
        x_fraction = float(x_fraction)
        y_fraction = float(y_fraction)
        if not 0.0 <= x_fraction <= 1.0 or not 0.0 <= y_fraction <= 1.0:
            raise ValueError("Clicked image coordinate is outside the frame")
        objects = self.env.sim.semantic_scene.objects
        camera = self.env.sim.get_agent_state().sensor_states["rgb"]
        aspect = 640.0 / 480.0
        tangent_h = math.tan(math.radians(90.0) / 2.0)
        direction_local = np.asarray(
            [
                (2.0 * x_fraction - 1.0) * tangent_h,
                (1.0 - 2.0 * y_fraction) * tangent_h / aspect,
                -1.0,
            ],
            dtype=np.float64,
        )
        direction_local /= np.linalg.norm(direction_local)
        direction = quaternion_rotate_vector(camera.rotation, direction_local)
        origin = np.asarray(camera.position, dtype=np.float64)
        architectural = {
            "ceiling", "floor", "wall", "door", "doorframe", "window",
            "stairs", "railing", "column", "beam", "void", "remove",
        }
        candidates = []
        for object_id, semantic_object in enumerate(objects):
            if semantic_object is None or semantic_object.category is None:
                continue
            category = semantic_object.category.name().lower()
            if category in architectural:
                continue
            center = np.asarray(semantic_object.aabb.center, dtype=np.float64)
            half = np.asarray(semantic_object.aabb.sizes, dtype=np.float64) / 2.0
            if np.any(half <= 0.0) or np.max(half * 2.0) > 5.0:
                continue
            lower, upper = center - half, center + half
            with np.errstate(divide="ignore", invalid="ignore"):
                first = (lower - origin) / direction
                second = (upper - origin) / direction
            near = float(np.max(np.minimum(first, second)))
            far = float(np.min(np.maximum(first, second)))
            if far >= max(near, 0.0):
                candidates.append((max(near, 0.0), object_id, semantic_object, category))
        if not candidates:
            raise ValueError(
                "No furniture/object bounding box was hit; click near its centre"
            )
        nearest = min(item[0] for item in candidates)
        furniture_categories = {
            "chair", "sofa", "couch", "stool", "bench", "table", "desk",
            "cabinet", "bed", "shelf", "dresser", "recliner", "ottoman",
        }
        furniture = [
            item for item in candidates
            if item[0] <= nearest + 0.75
            and any(word in item[3] for word in furniture_categories)
        ]
        _, object_id, semantic_object, _ = min(
            furniture or candidates, key=lambda item: item[0]
        )
        category = semantic_object.category.name() if semantic_object.category else "object"
        self.selected_object = {
            "semantic_object_id": object_id,
            "semantic_id": semantic_object.id,
            "category": category,
            "source_center": [float(value) for value in semantic_object.aabb.center],
            "source_dimensions": [float(value) for value in semantic_object.aabb.sizes],
        }
        return self.selected_object

    def place_selected_clone(self, scale, distance_ahead, yaw_degrees):
        if self.selected_object is None:
            raise ValueError("Select an object in the image before adding a copy")
        scale = float(scale)
        distance_ahead = float(distance_ahead)
        yaw_degrees = float(yaw_degrees)
        if not math.isfinite(scale) or scale <= 0:
            raise ValueError("Object scale must be positive")
        if not math.isfinite(distance_ahead) or distance_ahead <= 0:
            raise ValueError("Object distance must be positive")
        if not math.isfinite(yaw_degrees):
            raise ValueError("Object yaw must be finite")
        extracted = extract_semantic_object(
            self.scene_glb,
            self.selected_object["semantic_object_id"],
            self.args.extracted_assets_dir,
            category=self.selected_object["category"],
            source_bounds={
                "center": self.selected_object["source_center"],
                "sizes": self.selected_object["source_dimensions"],
            },
        )
        dimensions = np.asarray(extracted["dimensions_m"], dtype=np.float64) * scale
        state = self.env.sim.get_agent_state()
        forward = quaternion_rotate_vector(
            state.rotation, np.asarray([0.0, 0.0, -1.0])
        )
        forward[1] = 0.0
        norm = float(np.linalg.norm(forward))
        if norm < 1e-6:
            raise ValueError("Could not determine the agent's horizontal heading")
        forward /= norm
        position = np.asarray(state.position, dtype=np.float64) + forward * distance_ahead
        position[1] = float(state.position[1])
        half_angle = math.radians(yaw_degrees) / 2.0
        spec = {
            "kind": "mesh",
            "asset_config": extracted["config_path"],
            "semantic_object_id": self.selected_object["semantic_object_id"],
            "category": self.selected_object["category"],
            "position": position.tolist(),
            "position_is_floor_origin": True,
            "rotation_xyzw": [0.0, math.sin(half_angle), 0.0, math.cos(half_angle)],
            "scale": [scale, scale, scale],
            "half_extents": (dimensions / 2.0).tolist(),
            "source_scene": str(self.scene_glb),
        }
        self.blocker_specs.append(spec)
        self._refresh_blocker_state()

    def place_library_asset(self, asset_name, scale, distance_ahead, yaw_degrees):
        asset_name = str(asset_name)
        if asset_name not in self.LIBRARY_ASSETS:
            raise ValueError("Unknown furniture-library asset: {}".format(asset_name))
        scale = float(scale)
        distance_ahead = float(distance_ahead)
        yaw_degrees = float(yaw_degrees)
        if not math.isfinite(scale) or scale <= 0:
            raise ValueError("Object scale must be positive")
        if not math.isfinite(distance_ahead) or distance_ahead <= 0:
            raise ValueError("Object distance must be positive")
        config_name, category = self.LIBRARY_ASSETS[asset_name]
        config_path = (
            Path(self.args.replica_cad_dir) / "configs" / "objects" / config_name
        ).resolve()
        if not config_path.is_file():
            raise FileNotFoundError(
                "ReplicaCAD asset is missing: {}. Download replica_cad_dataset first.".format(
                    config_path
                )
            )

        template_manager = self.env.sim.get_object_template_manager()
        object_manager = self.env.sim.get_rigid_object_manager()
        template_ids = template_manager.load_configs(str(config_path))
        if not template_ids:
            raise RuntimeError("Habitat could not load {}".format(config_path))
        template = template_manager.get_template_by_id(template_ids[0])
        template.scale = np.asarray([scale, scale, scale], dtype=np.float32)
        probe_handle = "navida_library_probe_{}_{}".format(asset_name, len(self.blocker_specs))
        probe_id = template_manager.register_template(template, probe_handle)
        probe = object_manager.add_object_by_template_id(probe_id)
        if probe is None:
            raise RuntimeError("Habitat could not inspect {}".format(asset_name))
        try:
            bounds = probe.root_scene_node.cumulative_bb
            dimensions = np.asarray(list(bounds.size()), dtype=np.float64)
            local_floor_y = float(bounds.min[1])
        finally:
            object_manager.remove_object_by_id(probe.object_id)

        state = self.env.sim.get_agent_state()
        forward = quaternion_rotate_vector(
            state.rotation, np.asarray([0.0, 0.0, -1.0])
        )
        forward[1] = 0.0
        forward /= max(float(np.linalg.norm(forward)), 1e-12)
        position = np.asarray(state.position, dtype=np.float64) + forward * distance_ahead
        position[1] = float(state.position[1])
        half_angle = math.radians(yaw_degrees) / 2.0
        spec = {
            "kind": "mesh",
            "asset_config": str(config_path),
            "asset_library": "ReplicaCAD",
            "asset_name": asset_name,
            "category": category,
            "position": position.tolist(),
            "position_is_floor_origin": True,
            "local_floor_y": local_floor_y,
            "rotation_xyzw": [0.0, math.sin(half_angle), 0.0, math.cos(half_angle)],
            "scale": [scale, scale, scale],
            "half_extents": (dimensions / 2.0).tolist(),
        }
        self.blocker_specs.append(spec)
        self._refresh_blocker_state()
        return "{} ({})".format(category, asset_name)

    def _refresh_blocker_state(self):
        install_blockers(self.env.sim, self.blocker_specs, force_recompute=True)
        post_block = shortest_path(
            self.env.sim.pathfinder,
            self.raw_episode["start_position"],
            self.raw_episode["goals"][0]["position"],
        )
        self.blocker_validation = {
            "original_reference_intersects_blocker": any(
                self._reference_intersects_blocker(spec) for spec in self.blocker_specs
            ),
            "goal_reachable_after_block": post_block["reachable"],
            "baseline_geodesic_distance": self.baseline_navigation["geodesic_distance"],
            "post_block_geodesic_distance": post_block["geodesic_distance"],
            "geodesic_detour_delta": (
                post_block["geodesic_distance"]
                - self.baseline_navigation["geodesic_distance"]
                if post_block["reachable"] else float("inf")
            ),
            "post_block_shortest_path": post_block["points"],
        }
        self.observation.update(self.env.sim.get_sensor_observations())
        self._refresh_frame()

    def remove_last_blocker(self):
        if not self.blocker_specs:
            raise ValueError("There are no placed objects to remove")
        self.blocker_specs.pop()
        if self.blocker_specs:
            self._refresh_blocker_state()
        else:
            self.remove_blocker()

    def remove_blocker(self):
        install_blockers(self.env.sim, [])
        self.blocker_specs = []
        self.blocker_validation = None
        self.observation.update(self.env.sim.get_sensor_observations())
        self._refresh_frame()

    def save_blocked_challenge(self, case_name="", instruction=""):
        if not self.blocker_specs or self.blocker_validation is None:
            raise ValueError("Place a blocker before saving the challenge")
        if not self.blocker_validation["goal_reachable_after_block"]:
            raise ValueError(
                "The blocker makes the goal unreachable; move or resize it"
            )
        case_name = str(case_name or "").strip()
        if case_name and not re.match(r"^[A-Za-z0-9._-]+$", case_name):
            raise ValueError(
                "Case name may contain only letters, numbers, dot, underscore, and hyphen"
            )
        episode = copy.deepcopy(self.raw_episode)
        episode["episode_id"] = "blocked_{}_{}".format(
            self.args.episode_id, case_name or "default"
        )
        try:
            episode["trajectory_id"] = 970000 + int(self.args.episode_id)
        except ValueError:
            episode["trajectory_id"] = 970000
        if not isinstance(episode.get("info"), dict):
            episode["info"] = {}
        episode["info"][BLOCKER_INFO_KEY] = copy.deepcopy(self.blocker_specs)
        episode["info"][FORCE_RECOMPUTE_INFO_KEY] = True
        episode["info"]["navida_blocker_validation"] = self.blocker_validation
        episode["info"]["source_episode_id"] = str(self.args.episode_id)
        if self.parts is not None:
            episode["info"]["isaac_part_values"] = self.parts.states()
        instruction = str(instruction or "").strip()
        if instruction:
            episode["instruction"] = {
                "instruction_text": instruction,
                "instruction_tokens": [],
            }
        baseline_episode = copy.deepcopy(self.raw_episode)
        baseline_episode["episode_id"] = "baseline_{}_{}".format(
            self.args.episode_id, case_name or "default"
        )
        try:
            baseline_episode["trajectory_id"] = 960000 + int(self.args.episode_id)
        except ValueError:
            baseline_episode["trajectory_id"] = 960000
        if not isinstance(baseline_episode.get("info"), dict):
            baseline_episode["info"] = {}
        baseline_episode["info"][BLOCKER_INFO_KEY] = []
        baseline_episode["info"][FORCE_RECOMPUTE_INFO_KEY] = True
        baseline_episode["info"]["source_episode_id"] = str(self.args.episode_id)
        if self.parts is not None:
            baseline_episode["info"]["isaac_part_values"] = self.parts.states()
        if instruction:
            baseline_episode["instruction"] = copy.deepcopy(episode["instruction"])
        if case_name:
            case_dir = Path(self.args.cases_dir) / case_name
            baseline_path = case_dir / "baseline.json.gz"
            blocked_path = case_dir / "blocked.json.gz"
        else:
            baseline_path = Path(self.args.baseline_output)
            blocked_path = Path(self.args.challenge_output)
        save_json_gz(
            blocked_path,
            {
                "episodes": [episode],
                "instruction_vocab": self.source.get("instruction_vocab", {}),
            },
        )
        save_json_gz(
            baseline_path,
            {
                "episodes": [baseline_episode],
                "instruction_vocab": self.source.get("instruction_vocab", {}),
            },
        )
        return str(baseline_path), str(blocked_path)

    def state(self, message=None):
        pose = pose_dict(self.env.sim.get_agent_state())
        notes = "\n".join(
            "{}: {} at [{:.2f}, {:.2f}, {:.2f}]".format(
                index + 1, item["label"], *item["position"]
            )
            for index, item in enumerate(self.landmarks)
        )
        blocker_status = ""
        if self.blocker_validation is not None:
            blocker_status = (
                " | placed objects: {}"
                " | blocker intersects original route: {}"
                " | alternate path reachable: {}"
                " | geodesic {:.2f} -> {:.2f} m"
            ).format(
                len(self.blocker_specs),
                self.blocker_validation["original_reference_intersects_blocker"],
                self.blocker_validation["goal_reachable_after_block"],
                self.blocker_validation["baseline_geodesic_distance"],
                self.blocker_validation["post_block_geodesic_distance"],
            )
        return {
            "step": self.step,
            "message": (
                message or (
                    "Step {} | driven {:.2f} m | position [{:.3f}, {:.3f}, {:.3f}]"
                ).format(self.step, self.distance, *pose["position"])
            ) + blocker_status,
            "landmarks": notes,
            "source_instruction": self.raw_episode["instruction"]["instruction_text"],
            "selected_object": self.selected_object,
        }

    def save(self, instruction):
        if len(self.route) < 2:
            raise ValueError("Move forward before saving; the route has no translation yet")
        episode = copy.deepcopy(self.raw_episode)
        episode["episode_id"] = "custom_pov_{}".format(self.args.episode_id)
        try:
            episode["trajectory_id"] = 950000 + int(self.args.episode_id)
        except ValueError:
            episode["trajectory_id"] = 950000
        episode["start_position"] = self.start_pose["position"]
        episode["start_rotation"] = self.start_pose["rotation_xyzw"]
        episode["goals"] = [
            {"position": self.route[-1], "radius": float(self.args.goal_radius)}
        ]
        episode["reference_path"] = self.route
        episode["instruction"] = {
            "instruction_text": instruction,
            "instruction_tokens": [],
        }
        episode["info"] = {
            "authoring_method": "first_person_manual_drive",
            "recorded_path_length": self.distance,
            "authoring_landmarks": self.landmarks,
            "recorded_actions": self.actions,
        }
        if self.parts is not None:
            episode["info"]["isaac_part_values"] = self.parts.states()
        save_json_gz(
            self.args.output,
            {
                "episodes": [episode],
                "instruction_vocab": self.source.get("instruction_vocab", {}),
            },
        )


def make_handler(session):
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(10)

        def log_message(self, fmt, *args):
            return

        def send_bytes(self, status, content_type, payload):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)

        def send_json(self, payload, status=200):
            self.send_bytes(status, "application/json", json.dumps(payload).encode())

        def do_GET(self):
            if self.path.startswith("/frame.jpg"):
                # JPEG bytes are produced on the Habitat thread and then immutable.
                self.send_bytes(200, "image/jpeg", session.frame)
            elif self.path == "/" or self.path.startswith("/?"):
                self.send_bytes(200, "text/html; charset=utf-8", HTML.encode())
            else:
                self.send_json({"message": "Not found"}, 404)

        def do_POST(self):
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length > 1024 * 1024:
                    raise ValueError("Request body is too large")
                body = json.loads(self.rfile.read(length) or b"{}")
                if self.path == "/action":
                    response = session.submit("action", body.get("action"))
                elif self.path == "/reset":
                    response = session.submit("reset")
                elif self.path == "/mark":
                    response = session.submit(
                        "mark", str(body.get("label", "landmark"))
                    )
                elif self.path == "/save":
                    instruction = str(body.get("instruction", "")).strip()
                    if not instruction:
                        raise ValueError("Instruction cannot be empty")
                    response = session.submit("save", instruction)
                elif self.path == "/blocker":
                    response = session.submit(
                        "blocker",
                        body.get("width"),
                        body.get("height"),
                        body.get("depth"),
                        body.get("distance"),
                    )
                elif self.path == "/select-object":
                    response = session.submit(
                        "select_object", body.get("x"), body.get("y")
                    )
                elif self.path == "/clone":
                    response = session.submit(
                        "clone",
                        body.get("scale"),
                        body.get("distance"),
                        body.get("yaw"),
                    )
                elif self.path == "/library-asset":
                    response = session.submit(
                        "library_asset",
                        body.get("asset"),
                        body.get("scale"),
                        body.get("distance"),
                        body.get("yaw"),
                    )
                elif self.path == "/remove-last":
                    response = session.submit("remove_last")
                elif self.path == "/remove-blocker":
                    response = session.submit("remove_blocker")
                elif self.path == "/save-challenge":
                    response = session.submit(
                        "save_challenge",
                        str(body.get("case_name", "")).strip(),
                        str(body.get("instruction", "")).strip(),
                    )
                elif self.path == "/toggle-part":
                    response = session.submit("toggle_click", body.get("x"), body.get("y"))
                elif self.path == "/toggle-near":
                    response = session.submit("toggle_near")
                elif self.path == "/state":
                    response = session.submit("state")
                else:
                    self.send_json({"message": "Not found"}, 404)
                    return
                self.send_json(response)
            except Exception as error:
                self.send_json(
                    {
                        "step": session.step,
                        "message": "Error: {}".format(error),
                        "landmarks": "",
                        "source_instruction": session.raw_episode["instruction"]["instruction_text"],
                    },
                    400,
                )

    return Handler


def main():
    args = parse_args()
    session = RouteSession(args)
    server = ThreadingHTTPServer((args.host, args.port), make_handler(session))
    server.daemon_threads = True
    print("Habitat POV route author is ready.")
    print("Open http://{}:{} through VS Code port forwarding.".format(args.host, args.port))
    print("Source instruction:", session.raw_episode["instruction"]["instruction_text"])
    print("Output:", args.output)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    try:
        # Habitat-Sim's GL context belongs to this main thread. Browser request
        # threads enqueue work here instead of touching the simulator directly.
        while True:
            session.process_next_job()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=2)
        session.env.close()


if __name__ == "__main__":
    main()
