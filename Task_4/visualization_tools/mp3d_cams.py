"""Matterport undistorted cameras (.conf) -> habitat renders at the exact photo pose.

conf: an `intrinsics_matrix fx 0 cx 0 fy cy 0 0 1` line precedes its `scan depth color <16 c2w>` lines;
c2w is in raw MP3D Z-up world. Habitat world = C @ raw. CONVENTION picks the camera axes (measured).
"""
import math, os, numpy as np, habitat_sim, quaternion  # noqa: F401  (numpy-quaternion)

PHOTOS = "/home/guest-isl/rishabh/custom/habitat_building_isaac_repaired/source/photos/2azQ1b91cZZ"
C3 = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], float)
W, H = int(os.environ.get("MP3D_W", 320)), int(os.environ.get("MP3D_W", 320)) * 4 // 5  # photos are 1280x1024


def load_conf():
    cams, K = [], None
    for line in open(PHOTOS + "/undistorted_camera_parameters/2azQ1b91cZZ.conf"):
        t = line.split()
        if not t:
            continue
        if t[0] == "intrinsics_matrix":
            K = [float(v) for v in t[1:]]
        elif t[0] == "scan":
            cams.append({"color": t[2], "pano": t[2].split("_")[0], "fx": K[0], "c2w": np.array(t[3:19], float).reshape(4, 4)})
    return cams


def make_sim(glb, fx=1075.0):
    sc = habitat_sim.SimulatorConfiguration(); sc.scene_id = glb; sc.gpu_device_id = 0; sc.enable_physics = False
    c = habitat_sim.CameraSensorSpec(); c.uuid = "rgb"; c.resolution = [H, W]; c.position = [0, 0, 0]
    c.hfov = math.degrees(2 * math.atan(640.0 / fx))
    return habitat_sim.Simulator(habitat_sim.Configuration(sc, [habitat_sim.agent.AgentConfiguration(sensor_specifications=[c])]))


def render(sim, cam, convention="opengl"):
    R = cam["c2w"][:3, :3]
    if convention == "opencv":  # +z forward, y down -> habitat camera (-z forward, y up)
        R = R @ np.diag([1.0, -1.0, -1.0])
    Rh = C3 @ R
    st = habitat_sim.AgentState(); st.position = (C3 @ cam["c2w"][:3, 3]).astype(np.float32)
    st.rotation = quaternion.from_rotation_matrix(Rh)
    sim.get_agent(0).set_state(st, reset_sensors=True, infer_sensor_states=True)
    return sim.get_sensor_observations()["rgb"][..., :3].copy()


def photo(cam):
    from PIL import Image
    return np.asarray(Image.open(PHOTOS + "/undistorted_color_images/" + cam["color"]).convert("RGB").resize((W, H)))


def ncc(a, b):
    a = a.astype(float).mean(2); b = b.astype(float).mean(2)
    a = (a - a.mean()) / (a.std() + 1e-6); b = (b - b.mean()) / (b.std() + 1e-6)
    return float((a * b).mean())


if __name__ == "__main__":
    ORIG = "/home/guest-isl/rishabh/NAVIDA/data/scene_dataset/mp3d/2azQ1b91cZZ/2azQ1b91cZZ.glb"
    cams = load_conf(); sim = make_sim(ORIG)
    for cam in cams[::777][:5]:
        p = photo(cam)
        print(cam["color"], {cv: round(ncc(p, render(sim, cam, cv)), 3) for cv in ("opengl", "opencv")})
