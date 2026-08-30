import genesis as gs
import numpy as np
import torch
from genesis.vis.keybindings import Key, KeyAction, Keybind

class Go2Controller:
    def __init__(self, policy_path):
        self.device = torch.device("cuda:0")
        self.policy_path = policy_path
        
        # RL Config Scales
        self.action_scale = np.array([
            0.125, 0.25, 0.25,  0.125, 0.25, 0.25,
            0.125, 0.25, 0.25,  0.125, 0.25, 0.25,
        ], dtype=np.float32)
        self.ang_vel_scale = 0.25
        self.dof_pos_scale = 1.0
        self.dof_vel_scale = 0.05
        self.gravity_world = np.array([0.0, 0.0, -1.0], dtype=np.float32)
        
        # PD Gains
        self.fixed_kp, self.fixed_kd = 150.0, 5.0
        self.rl_kp, self.rl_kd = 40.0, 1.0
        
        # State & Buffers
        self.state = {"mode": "stand", "vx": 0.0, "vy": 0.0, "yaw": 0.0}
        self.is_running = True
        self.last_actions = np.zeros(12, dtype=np.float32)
        
        self._init_genesis()

    def _init_genesis(self):
        gs.init(backend=gs.gpu)
        self.scene = gs.Scene(
            sim_options=gs.options.SimOptions(dt=0.02, substeps=2),
            rigid_options=gs.options.RigidOptions(
                enable_self_collision=False,
                max_contacts=4096,
            ),
            viewer_options=gs.options.ViewerOptions(
                camera_pos=(2.0, 0.0, 2.5),
                camera_lookat=(0.0, 0.0, 0.5),
                camera_fov=40,
            ),
            show_viewer=True,
        )

    def load_environment(self, office_mesh_path="../genesis-world/office-env/Office+2.glb"):
        # Invisible plane for physics
        self.scene.add_entity(gs.morphs.URDF(file="urdf/plane/plane.urdf", fixed=True))
        
        # Visual-only office to prevent OOM
        self.scene.add_entity(
            gs.morphs.Mesh(
                file=office_mesh_path,
                scale=1.0, fixed=True, convexify=False,
                collision=False,  
            )
        )
        
        # Robot
        self.robot = self.scene.add_entity(
            gs.morphs.URDF(
                file="urdf/go2/urdf/go2.urdf",
                pos=(0.0, 0.0, 0.42),
            ),
        )
        
        self.scene.build()
        self._setup_joint_mappings()
        self._setup_initial_pose()
        self.load_policy()
        self._setup_keybinds()

    def _setup_joint_mappings(self):
        self.urdf_joint_names = [j.name for j in self.robot.joints[1:]]
        self.policy_joint_order = [
            "FR_hip_joint", "FR_thigh_joint", "FR_calf_joint",
            "FL_hip_joint", "FL_thigh_joint", "FL_calf_joint",
            "RR_hip_joint", "RR_thigh_joint", "RR_calf_joint",
            "RL_hip_joint", "RL_thigh_joint", "RL_calf_joint",
        ]
        
        self.policy_to_urdf = [self.urdf_joint_names.index(name) for name in self.policy_joint_order]
        self.urdf_to_policy = [0] * 12
        for pi, ui in enumerate(self.policy_to_urdf):
            self.urdf_to_policy[ui] = pi
            
        self.all_motor_dofs = list(range(6, 6 + len(self.urdf_joint_names)))

    def _setup_initial_pose(self):
        default_angles = {
            "FR_hip_joint": 0.0,  "FR_thigh_joint": 0.8,  "FR_calf_joint": -1.5,
            "FL_hip_joint": 0.0,  "FL_thigh_joint": 0.8,  "FL_calf_joint": -1.5,
            "RR_hip_joint": 0.0,  "RR_thigh_joint": 1.0,  "RR_calf_joint": -1.5,
            "RL_hip_joint": 0.0,  "RL_thigh_joint": 1.0,  "RL_calf_joint": -1.5,
        }
        
        self.stand_pos_urdf = np.array([default_angles.get(j.name, 0.0) for j in self.robot.joints[1:]], dtype=np.float32)
        self.stand_pos_policy = np.array([default_angles[name] for name in self.policy_joint_order], dtype=np.float32)
        
        init_qpos = np.concatenate([[0.0, 0.0, 0.42], [1.0, 0.0, 0.0, 0.0], self.stand_pos_urdf])
        self.robot.set_qpos(init_qpos, zero_velocity=True)
        
        # Start in stand mode
        self.robot.set_dofs_kp(np.full(12, self.fixed_kp), self.all_motor_dofs)
        self.robot.set_dofs_kv(np.full(12, self.fixed_kd), self.all_motor_dofs)

    def load_policy(self):
        self.policy = torch.jit.load(self.policy_path, map_location=self.device)
        self.policy.eval()
        print(f"✓ RL Policy loaded on {self.device}")

    def _setup_keybinds(self):
        def activate_stand():
            self.state["mode"] = "stand"
            self.state["vx"] = self.state["vy"] = self.state["yaw"] = 0.0
            self.robot.set_dofs_kp(np.full(12, self.fixed_kp), self.all_motor_dofs)
            self.robot.set_dofs_kv(np.full(12, self.fixed_kd), self.all_motor_dofs)
            print(">>> STAND MODE")

        def activate_walk():
            self.state["mode"] = "walk"
            self.robot.set_dofs_kp(np.full(12, self.rl_kp), self.all_motor_dofs)
            self.robot.set_dofs_kv(np.full(12, self.rl_kd), self.all_motor_dofs)
            print(">>> WALK MODE")

        def set_fwd():   self.state["vx"] = 0.3
        def set_bwd():   self.state["vx"] = -0.3
        def set_left():  self.state["yaw"] = 0.3
        def set_right(): self.state["yaw"] = -0.3
        def stop_fb():   self.state["vx"] = 0.0
        def stop_lr():   self.state["yaw"] = 0.0
        def stop_all():  self.state["vx"] = self.state["vy"] = self.state["yaw"] = 0.0
        def quit_sim():  self.is_running = False

        self.scene.viewer.register_keybinds(
            Keybind("stand",    Key.NUM_0, KeyAction.RELEASE, callback=activate_stand),
            Keybind("walk",     Key.NUM_1, KeyAction.RELEASE, callback=activate_walk),
            Keybind("fwd",      Key.UP,    KeyAction.PRESS,   callback=set_fwd),
            Keybind("fwd_r",    Key.UP,    KeyAction.RELEASE, callback=stop_fb),
            Keybind("bwd",      Key.DOWN,  KeyAction.PRESS,   callback=set_bwd),
            Keybind("bwd_r",    Key.DOWN,  KeyAction.RELEASE, callback=stop_fb),
            Keybind("left",     Key.LEFT,  KeyAction.PRESS,   callback=set_left),
            Keybind("left_r",   Key.LEFT,  KeyAction.RELEASE, callback=stop_lr),
            Keybind("right",    Key.RIGHT, KeyAction.PRESS,   callback=set_right),
            Keybind("right_r",  Key.RIGHT, KeyAction.RELEASE, callback=stop_lr),
            Keybind("stop",     Key.SPACE, KeyAction.RELEASE, callback=stop_all),
            Keybind("quit",     Key.ESCAPE,KeyAction.RELEASE, callback=quit_sim),
        )

    def _quat_rotate_inverse(self, q, v):
        w, x, y, z = q
        xyz = np.array([x, y, z])
        t = 2.0 * np.cross(xyz, v)
        return v - w * t + np.cross(xyz, t)

    def _get_observation(self):
        quat = self.robot.get_quat().cpu().numpy().flatten()
        ang_vel_world = self.robot.get_ang().cpu().numpy().flatten()
        ang_vel_body = self._quat_rotate_inverse(quat, ang_vel_world)
        gravity_body = self._quat_rotate_inverse(quat, self.gravity_world)

        dof_pos_urdf = self.robot.get_dofs_position(self.all_motor_dofs).cpu().numpy().flatten()
        dof_vel_urdf = self.robot.get_dofs_velocity(self.all_motor_dofs).cpu().numpy().flatten()

        dof_pos_policy = dof_pos_urdf[self.policy_to_urdf]
        dof_vel_policy = dof_vel_urdf[self.policy_to_urdf]

        commands = np.array([self.state["vx"], self.state["vy"], self.state["yaw"]], dtype=np.float32)

        obs = np.concatenate([
            ang_vel_body * self.ang_vel_scale,
            gravity_body,
            commands,
            (dof_pos_policy - self.stand_pos_policy) * self.dof_pos_scale,
            dof_vel_policy * self.dof_vel_scale,
            self.last_actions,
        ]).astype(np.float32)
        return obs

    def run(self):
        print("\n" + "=" * 50)
        print("  GO2 KEYBOARD CONTROL (OOP MODULAR)")
        print("=" * 50)
        print("  [0] = Stand Up    [1] = Walk")
        print("  [↑/↓] = Fwd/Bwd  [←/→] = Turn")
        print("  [Space] = Stop    [Esc] = Quit")
        print("==================================================")
        
        step = 0
        try:
            while self.is_running:
                if self.state["mode"] == "stand":
                    self.robot.control_dofs_position(self.stand_pos_urdf, self.all_motor_dofs)
                else:
                    obs = self._get_observation()
                    obs_t = torch.tensor(obs, dtype=torch.float32, device=self.device).unsqueeze(0)
                    with torch.no_grad():
                        act_t = self.policy(obs_t)
                    actions_policy = act_t.squeeze(0).cpu().numpy()
                    actions_policy = np.clip(actions_policy, -100.0, 100.0)

                    target_policy = self.stand_pos_policy + actions_policy * self.action_scale
                    target_urdf = np.zeros(12, dtype=np.float32)
                    for pi in range(12):
                        target_urdf[self.policy_to_urdf[pi]] = target_policy[pi]

                    self.robot.control_dofs_position(target_urdf, self.all_motor_dofs)
                    self.last_actions = actions_policy.copy()

                self.scene.step()
                step += 1

                if step % 500 == 0:
                    pos = self.robot.get_pos().cpu().numpy().flatten()
                    print(f"[{self.state['mode']:5s}] Step {step:5d} | z={pos[2]:.3f} | vx={self.state['vx']:.1f} yaw={self.state['yaw']:.1f}")

        except KeyboardInterrupt:
            print("\nStopped.")
        finally:
            print("Done.")


if __name__ == "__main__":
    controller = Go2Controller(policy_path="/home/vivekananda/UGP/rl_sar/rl_ws/src/rl_sar/policy/go2/robot_lab/policy.pt")
    controller.load_environment(office_mesh_path="../genesis-world/office-env/Office+2.glb")
    controller.run()
