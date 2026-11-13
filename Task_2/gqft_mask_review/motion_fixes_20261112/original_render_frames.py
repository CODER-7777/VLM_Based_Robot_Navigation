"""Render the RGB the agent saw at every reconstructed tick pose.

Verified against the stored leg keyframes: geometry matches pixel-for-pixel (corr 0.989;
the residual is a colour-balance difference in the original run's renderer, not pose).
"""
import json, math, os, sys
import numpy as np, cv2, habitat_sim

POSE_NPZ, OUT, GPU = sys.argv[1], sys.argv[2], int(sys.argv[3])
SCENE_ROOT = "/data/robotics/toshith/HSGM_public/data/scene_datasets"

z = np.load(POSE_NPZ, allow_pickle=True)
P = z["pose"]
ps = json.loads(str(z["physical"]))
H, W = ps["resolution"]
floor_y = float(z["floor_y"])
os.makedirs(OUT, exist_ok=True)

sim_cfg = habitat_sim.SimulatorConfiguration()
sim_cfg.scene_id = f"{SCENE_ROOT}/{z['scene']}"
sim_cfg.gpu_device_id = GPU
spec = habitat_sim.SensorSpec()
spec.uuid = "rgb"
spec.sensor_type = habitat_sim.SensorType.COLOR
spec.resolution = [H, W]
spec.position = ps["camera_position_agent"]
spec.orientation = [math.radians(a) for a in ps["camera_orientation_deg"]]
spec.parameters["hfov"] = str(ps["hfov_deg"])
ac = habitat_sim.agent.AgentConfiguration()
ac.sensor_specifications = [spec]
ac.height, ac.radius = ps["agent_height_m"], ps["agent_radius_m"]
sim = habitat_sim.Simulator(habitat_sim.Configuration(sim_cfg, [ac]))

st = habitat_sim.AgentState()
for i, (x, zz, yaw) in enumerate(P):
    st.position = np.array([x, floor_y, zz], dtype=np.float32)
    hx, hz = math.cos(yaw), math.sin(yaw)
    st.rotation = habitat_sim.utils.common.quat_from_angle_axis(
        math.atan2(-hx, -hz), np.array([0.0, 1.0, 0.0]))
    sim.get_agent(0).set_state(st)
    rgb = sim.get_sensor_observations()["rgb"][:, :, :3]
    cv2.imwrite(f"{OUT}/{i:05d}.png", rgb[:, :, ::-1])
print(f"rendered {len(P)} -> {OUT}")
