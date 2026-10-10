"""Habitat renders of a scene GLB from given eyes (raw coords). usage: look.py GLB OUT.jpg "ex,ey,ez,tx,ty,tz" [...]  (MP3D_W sets size)"""
import sys, os, numpy as np
sys.path.insert(0, "/data/robotics/toshith/rxr_author/refined")
from mp3d_cams import make_sim, render
from PIL import Image
def lookat(eye, target):
    f = target - eye; f /= np.linalg.norm(f); r = np.cross(f, [0, 0, 1.0]); r /= np.linalg.norm(r); u = np.cross(r, f)
    M = np.eye(4); M[:3, 0], M[:3, 1], M[:3, 2], M[:3, 3] = r, u, -f, eye; return {"c2w": M, "color": "synthetic"}
s = make_sim(sys.argv[1]); ims = []
if os.environ.get("OBJ"):  # also drop a world-space GLB (glTF Y-up = habitat frame) into the scene as a static object
    import json, habitat_sim
    g = os.environ["OBJ"]; cfg = g[:-4] + ".object_config.json"
    json.dump({"render_asset": os.path.basename(g), "shader_type": "material", "COM": [0, 0, 0]}, open(cfg, "w"))
    tm, om = s.get_object_template_manager(), s.get_rigid_object_manager()
    o = om.add_object_by_template_id(tm.load_configs(cfg)[0]); o.motion_type = habitat_sim.physics.MotionType.STATIC
for e in sys.argv[3:]:
    v = np.array([float(x) for x in e.split(",")]); ims.append(render(s, lookat(v[:3], v[3:])))
Image.fromarray(np.concatenate(ims, 1)).save(sys.argv[2], quality=90); print("LOOK", sys.argv[2])
