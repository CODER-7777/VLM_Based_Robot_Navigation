# Task 1: Photorealistic Simulator Evaluation for Quadruped Locomotion

> **Quick Link:** [Jump straight to Deep Analysis & Hardware Workarounds](#1-deep-analysis--architectural-trade-offs)

---

## 1. Deep Analysis & Architectural Trade-offs
### The Core Challenge: VRAM Ceilings & Simulator Architectures
During this evaluation, we confronted the fundamental tension in modern robotics simulation: the division between **physics computation** and **photorealistic rendering**. 

1. **The Game Engine Trap (Unreal/Unity):** While engines like Unreal provide unparalleled visual realism (Lumen/Nanite) and particle systems for adverse conditions, they require massive storage footprints (often >100GB). Simulating high-frequency legged locomotion contact dynamics natively is difficult, and bridging them with a physics engine like MuJoCo introduces complex IPC (Inter-Process Communication) overhead.
2. **The Physics-First Approach (Isaac Sim):** Platforms like NVIDIA Isaac Sim integrate exceptional RL pipelines with photorealism. However, they assume the heavy ray-traced renderer is always active. On hardware with limited VRAM (e.g., 4GB RTX 3050), Isaac Sim will trigger Out-of-Memory (OOM) errors before a scene even initializes.
3. **The Decoupled Solution (Genesis):** Genesis solves this by intentionally decoupling physics from photorealism. Rigid-body physics computation requires a fraction of a Gigabyte. By default, Genesis utilizes a fast rasterizer (Pyrender) for live previews, allowing smooth RL policy execution on low-end GPUs. True photorealism in Genesis is achieved by explicitly switching to the Ray-Tracer backend (`gs.options.renderers.RayTracer()`) for offline rendering, allowing us to capture high-fidelity data without crashing the hardware.

### Hardware-Specific Workaround (Genesis Office Environment)
When loading the massive photorealistic 3D Office environment (`Office+2.glb`), Genesis attempted to calculate convex collision hulls for the entire mesh, which instantly exceeded our 4GB VRAM limit and killed the process. 
**Our Solution:** We set the high-fidelity office mesh to be purely visual (`collision=False`, `convexify=False`) and instantiated an invisible physics plane (`plane.urdf`) underneath it. This allowed the quadruped to interact perfectly with a stable physical floor while maintaining the photorealistic visual context of the office, successfully bypassing the hardware limits.

---

## 2. Comparison Table

| Criterion | Genesis | Isaac Sim / Isaac Lab | Unreal Engine / Unity (CARLA) | AI Habitat | MuJoCo / MJX |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Environment library** | Excellent. Loads standard `.gltf`/`.obj` environments directly.I have tried this on my laptop it is working fine. | Excellent (Omniverse USDs), but massive downloads. | Massive libraries, but assets are heavy and not RL-ready. | Great for indoor scans, weak for outdoors. | Very poor native photorealism. |
| **Visual realism** | High (native path tracing). | Very High. | Very High. | High. | Low. |
| **Quadruped support** | Excellent. Unitree Go2 models are there, physics work robustly. | Excellent, but computationally expensive. | Hard to simulate physics bridging with Python RL frameworks. | Weak contact physics for quadrupeds. | Excellent physics, but no photorealism. |
| **Performance** | High. Fully GPU-accelerated without extreme footprint. | Low for average hardware. Requires huge VRAM. | Low. Game engines have heavy overhead for RL parallelization. | High. | Very High. |
| **Setup effort** | Very Low. Simple `pip install genesis-world`. | Very High. Strict driver specs, huge footprint. | Very High. >100GB installs, massive complex bridging overhead. | Medium. | Low. |
| **Licensing** | Open-source (Apache 2.0). | Free for research. | Engine royalties apply. | MIT (Research datasets restricted). | Open-source (Apache 2.0). |

---

## 3. Ranked Shortlist

1. **Genesis:** Native Python, loads standard photorealistic meshes (`.gltf`), and existing Go2 quadruped models are already there with robust physics. Zero bloat compared to massive game engines.
2. **Isaac Lab:** The industry standard for RL + photorealism, but its requirements are very high; it is extremely heavy and requires a massive GPU footprint to run smoothly.
3. **Unreal Engine / Unity:** Incredible visual realism, but takes almost 100GB to install, and setting up robust, fast physics simulation for quadruped RL is notoriously difficult.

---

## 4. Recommendation + Risks

**Recommendation:** Genesis
Genesis hits the perfect sweet spot for this project. It provides the blazing-fast GPU-accelerated physics needed for quadruped RL (rivaling MuJoCo) while featuring a built-in, lightweight photorealistic renderer that natively accepts standard 3D formats. We successfully achieved a working Unitree Go2 quadruped in a photorealistic office environment on highly constrained hardware.

**Biggest Risk:** 
Ecosystem Immaturity. Genesis has a smaller community compared to Isaac or Unreal. Finding highly complex, pre-rigged interactive environments (like working elevators or specific doors) will require more manual work to convert standard `.glb` assets into functional URDFs.
Also in Genesis if you have a VRAM then only try to ru Physics cause it will cause OOM errors like basically the out of memory errors.

## A.Some additional points of the analysis:
1. The first thing is we need to have a crazy gpu for the things like ISSAC SIM it has a min requirements of RTX 4070 and min VRAM of 8GB.
---

## 5. Working Demo & Setup Notes

**Video Demonstration:**
* [Watch the Genesis Quadruped Demo on Google Drive](https://drive.google.com/file/d/1hBrvVq-9UNVSSecGrkjWfZmLAOO4rz1X/view?usp=sharing)

**Setup Notes (Raj's Team and Krishna):**
Genesis is the most practical because it actually works on standard hardware without taking 100GB.
Below are the exact commands you need to get it running from scratch:

**1. Clone the Repos & Install Dependencies:**
```bash
# Clone the main repository
git clone https://github.com/YOUR_GITHUB_USERNAME/VLM_Based_Robot_Navigation.git

# Clone the rl_sar repository (which contains the pre-trained Go2 policy)
# (Clone this into the same parent folder, e.g., your UGP directory)
git clone https://github.com/fan-ziqi/rl_sar.git

cd VLM_Based_Robot_Navigation

# Install the Genesis simulator and required libraries
pip install genesis-world torch numpy
```

**2. Configure the Policy Path:**
Open `genesis-world/run_go2.py` and ensure the `policy_path` on line 125 exactly matches where you cloned `rl_sar` (e.g., `/home/your_username/UGP/rl_sar/rl_ws/src/rl_sar/policy/go2/robot_lab/policy.pt`).

**3. Run the Simulation:**
```bash
cd genesis-world
python run_go2.py
```

**4. Training vs Rendering Separation:** Do NOT use the Ray-Tracer for live development. Keep using the fast rasterizer (Pyrender) for policy training. When you need photorealistic frames, write a script to render offline (one camera, one frame at a time, at a reduced resolution like 640x480) to prevent OOM errors.
**5. Collision Workaround:** If your GPU crashes loading an environment, set the visual mesh to `collision=False` and place an invisible `plane.urdf` underneath it for physics.

---

## 6. Links / References
- **Genesis Documentation:** https://genesis-world.readthedocs.io/
- **rl_sar Quadruped RL Policy Repository:** https://github.com/fan-ziqi/rl_sar
- **Our Working Script:** Reference the `run_go2.py` setup script in the genesis-world root folder.
