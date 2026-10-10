"""Seconds-fast preview: drop product candidates (world-space GLBs, glTF Y-up = habitat frame) into the tapless base scene
as rigid objects and render real photo | v10 | candidate at the fixture's photo views, plus 2 unphotographed angles.
usage: product_preview.py BASE_GLB V10_GLB FIXTURE OUT.jpg [CAND_GLB ...]
(no candidates: the last column is BASE itself, labelled $LBL_BASE -- a before/after close-up of a finished build)"""
import sys, os, json, math, numpy as np, habitat_sim
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mp3d_cams import load_conf, make_sim, render, photo, W as RW, H as RH

BASE, V10, FIX, OUT = sys.argv[1:5]; CANDS = sys.argv[5:]
R = json.load(open("/data/robotics/toshith/rxr_author/refined/kitchen/products/%s/ranking.json" % FIX))
by = {c["color"]: c for c in load_conf()}


def lookat(eye, target):
    f = target - eye; f /= np.linalg.norm(f); r = np.cross(f, [0, 0, 1.0]); r /= np.linalg.norm(r); u = np.cross(r, f)
    M = np.eye(4); M[:3, 0], M[:3, 1], M[:3, 2], M[:3, 3] = r, u, -f, eye; return {"c2w": M, "color": "synthetic"}


def label(img, text):
    t = Image.fromarray(img); d = ImageDraw.Draw(t); d.rectangle([0, 0, 7 * len(text) + 8, 15], fill=(0, 0, 0)); d.text((4, 2), text, fill=(255, 255, 0))
    return np.asarray(t)


c = np.array(R["base"]) + [0, 0, R["height"] / 2]
cams = [by[v] for v in R["views"][:3]]
seen = [math.atan2(*(c - cam["c2w"][:3, 3])[1::-1]) for cam in cams]
import quaternion
from mp3d_cams import C3
_sc = habitat_sim.SimulatorConfiguration(); _sc.scene_id = V10; _sc.enable_physics = False
_ds = habitat_sim.CameraSensorSpec(); _ds.uuid = "depth"; _ds.sensor_type = habitat_sim.SensorType.DEPTH; _ds.resolution = [64, 64]; _ds.position = [0, 0, 0]
_dsim = habitat_sim.Simulator(habitat_sim.Configuration(_sc, [habitat_sim.agent.AgentConfiguration(sensor_specifications=[_ds])]))


def clear(eye, target):  # nothing between the eye and the fixture (centre-pixel depth reaches it)
    st = habitat_sim.AgentState(); st.position = (C3 @ eye).astype(np.float32)
    st.rotation = quaternion.from_rotation_matrix(C3 @ lookat(eye, target)["c2w"][:3, :3])
    _dsim.get_agent(0).set_state(st, reset_sensors=True, infer_sensor_states=True)
    return float(_dsim.get_sensor_observations()["depth"][32, 32]) > np.linalg.norm(target - eye) - 0.1


novel = sorted(((min(abs((az - s + math.pi) % (2 * math.pi) - math.pi) for s in seen), az) for az in np.radians(np.arange(0, 360, 20))), reverse=True)
picked = []
for _, az in novel:
    eye = c - 0.5 * np.array([math.cos(az), math.sin(az), 0]) + [0, 0, 0.25]
    if clear(eye, c):
        picked.append(lookat(eye, c))
    if len(picked) == 2:
        break
_dsim.close(); cams += picked
# crop window per camera: the fixture's box (+-0.7 height around the base, up to 1.2 height) projected
H_ = R["height"]; corners = np.array([np.array(R["base"]) + [dx * H_, dy * H_, dz * H_] for dx in (-0.7, 0.7) for dy in (-0.7, 0.7) for dz in (-0.1, 1.2)])


def crop_box(cam, w=RW, h=RH):
    if cam["color"] == "synthetic":
        return None
    fx = fy = by[cam["color"]]["fx"] * w / 1280.0; cx, cy = w / 2, h / 2  # centred pp: a few px off, fine for a crop
    R_, t = cam["c2w"][:3, :3], cam["c2w"][:3, 3]; q = (corners - t) @ R_; z = -q[:, 2]
    u = fx * q[:, 0] / z + cx; v = cy - fy * q[:, 1] / z
    x0, x1, y0, y1 = max(0, u.min()), min(w, u.max()), max(0, v.min()), min(h, v.max())
    side = max(x1 - x0, y1 - y0, 40); xc, yc = (x0 + x1) / 2, (y0 + y1) / 2
    return [int(max(0, xc - side / 2)), int(max(0, yc - side / 2)), int(min(w, xc + side / 2)), int(min(h, yc + side / 2))]


BOXES = [crop_box(cam) for cam in cams]


def zoom(img, i):
    b = BOXES[i]
    if b is None:
        return img
    return np.asarray(Image.fromarray(img[b[1]:b[3], b[0]:b[2]]).resize((img.shape[1], img.shape[0])))


s10 = make_sim(V10); cols = [[label(zoom(photo(cam), i), "real photo") if cam["color"] != "synthetic" else label(np.zeros_like(render(s10, cam)), "no photo from here") for i, cam in enumerate(cams)],
                             [label(zoom(render(s10, cam), i), os.environ.get("LBL_V10", "v10 now")) for i, cam in enumerate(cams)]]
s10.close()
if not CANDS:
    s = make_sim(BASE); cols.append([label(zoom(render(s, cam), i), os.environ.get("LBL_BASE", "base")) for i, cam in enumerate(cams)]); s.close()
for g in CANDS:
    s = make_sim(BASE); tm, om = s.get_object_template_manager(), s.get_rigid_object_manager()
    cfg = g[:-4] + ".object_config.json"
    json.dump({"render_asset": os.path.basename(g), "shader_type": "material", "COM": [0, 0, 0]}, open(cfg, "w"))
    obj = om.add_object_by_template_id(tm.load_configs(cfg)[0]); obj.motion_type = habitat_sim.physics.MotionType.STATIC
    cols.append([label(zoom(render(s, cam), i), os.path.basename(g)[:-4]) for i, cam in enumerate(cams)]); s.close()
rows = [np.concatenate([col[i] for col in cols], 1) for i in range(len(cams))]
Image.fromarray(np.concatenate(rows, 0)).resize((len(cols) * RW * 3 // 4, len(cams) * RH * 3 // 4)).save(OUT, quality=85)
print("PREVIEW", OUT, "columns", len(cols), "rows", len(cams))
