# Papers and upstream references

Metadata checked against proceedings, author/lab pages and official source repositories on 10 October 2026. The roles below describe how this project uses or interprets each work; published results are not measurements of our robot or scene.

| ID | Paper / authors | Journal or conference | Year | Relevance and boundary | Primary reference |
| --- | --- | --- | ---: | --- | --- |
| P1 | **SEA-RAFT: Simple, Efficient, Accurate RAFT for Optical Flow** — Yihan Wang, Lahav Lipson, Jia Deng | European Conference on Computer Vision (**ECCV**) | 2024 | Frozen flow extraction before GQFT; we do not retrain/reproduce its flow benchmark | [Proceedings](https://www.ecva.net/papers/eccv_2024/papers_ECCV/html/1065_ECCV_2024_paper.php), [official code](https://github.com/princeton-vl/SEA-RAFT) |
| P2 | **CTS: Concurrent Teacher-Student Reinforcement Learning for Legged Locomotion** — Hongxi Wang, Haoxiang Luo, Wei Zhang, Hua Chen | **IEEE Robotics and Automation Letters (RA-L)** | 2024 | Teacher/student learning concept referenced by pinned MoE-CTS code; the inspected student adds eight latent experts | [Paper](https://arxiv.org/abs/2405.10830), [author-lab venue confirmation](https://physicalintelligence-lab.github.io/post/cts_rfm/) |
| P3 | **Sim-to-Real: Learning Agile Locomotion For Quadruped Robots** — Jie Tan et al. | **Robotics: Science and Systems (RSS)** | 2018 | Motivates actuator/latency identification and calibrated simulation; no reproduction claimed | [Official proceedings](https://roboticsproceedings.org/rss14/p10.html) |
| P4 | **Room-Across-Room: Multilingual Vision-and-Language Navigation with Dense Spatiotemporal Grounding** — Alexander Ku et al. | **EMNLP** | 2020 | Dataset/task context for calibrated indoor observations; repaired scene is a private derivative, not the official benchmark | [ACL proceedings](https://aclanthology.org/2020.emnlp-main.356/) |
| P5 | **Habitat: A Platform for Embodied AI Research** — Manolis Savva et al. | **ICCV** | 2019 | Simulation/navigation framework; current Gaussian bridge is local engineering, not part of that paper | [CVF proceedings](https://openaccess.thecvf.com/content_ICCV_2019/html/Savva_Habitat_A_Platform_for_Embodied_AI_Research_ICCV_2019_paper.html) |
| P6 | **3D Gaussian Splatting for Real-Time Radiance Field Rendering** — Bernhard Kerbl, Georgios Kopanas, Thomas Leimkühler, George Drettakis | **ACM Transactions on Graphics 42(4) / SIGGRAPH** | 2023 | Gaussian representation and rendering foundation; this project uses fixed-surface/appearance variants and gsplat | [Author project / BibTeX](https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/) |

Related reading: [MoE-Loco: Mixture of Experts for Multitask Locomotion](https://arxiv.org/abs/2503.08564), Runhan Huang et al., **arXiv:2503.08564, 2025**. The linked preprint's architecture differs from our inspected MoE-CTS checkpoint. A peer-reviewed venue is not assigned here without a verified primary record.

## Source ancestry and engineering modifications

| Source | Local use / change | Reference |
| --- | --- | --- |
| Genesis | Go2 scene/control feasibility script; separated visual mesh and collision plane | [Upstream](https://github.com/Genesis-Embodied-AI/Genesis) |
| Supplied GQFT codebase | Baseline preserved; Attention/Yaw variants, strict loader, adapter and optional supervision-contract changes | [Project source](../../Task_2/gqft_algorithm_sharing_vivekananda/README.md); no verified external GQFT paper venue is assigned |
| MoE-CTS network implementation | Eight softmax latent experts + shared actor; source pinned by local trainer | [Pinned module](https://github.com/wty-yy/go2_rl_gym/blob/30e74dc507bec7a642a8c98be26081f2c6f0822d/rsl_rl/rsl_rl/modules/actor_critic_moe_cts.py) |
| MuJoCo | Explicit contact-ratio diagnostic; compiled solver options recorded | [impratio definition](https://mujoco.readthedocs.io/en/stable/XMLreference.html#option-impratio), [solver parameters / refsafe](https://mujoco.readthedocs.io/en/stable/modeling.html#solver-parameters) |
| gsplat | Separate RGB/expected-depth Gaussian service | [Official implementation](https://github.com/nerfstudio-project/gsplat) |
| Licensed kitchen models | Photo-guided substitutes, shape refinement and material preservation; exact brand match unclaimed | [Per-object authors, licences and source listings](../../Task_4/kitchen_product_model_replacements/README.md#sources), [toaster source](../../Task_4/toaster_selected_model/README.md) |

[Source/change index](CODE_INDEX.md) connects these references to the actual tools and measured results. Proposed fixes and controlled experiments are listed in the task READMEs; they are not attributed to papers as established outcomes.
