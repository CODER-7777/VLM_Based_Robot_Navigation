#!/usr/bin/env python3
"""Render independent project diagrams; no cross-project architecture is implied."""
from pathlib import Path
import os
os.environ.setdefault("MPLCONFIGDIR", "/tmp/vlm_diagram_mpl")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT = Path(__file__).resolve().parents[1] / "diagrams"
INK, MUTED = "#12243A", "#526477"
BLUE, TEAL, AMBER = "#245EC7", "#007D79", "#AC6510"
POSITIONS = [(0.65, 3.65), (5.1, 3.65), (9.55, 3.65),
             (9.55, 1.5), (5.1, 1.5), (0.65, 1.5)]
WIDTH, HEIGHT = 3.65, 1.25


def box(ax, pos, title, body, pending=False):
    x, y = pos
    color = AMBER if pending else BLUE
    ax.add_patch(FancyBboxPatch((x, y), WIDTH, HEIGHT,
        boxstyle="round,pad=0.025,rounding_size=0.10",
        facecolor="#FFF7EA" if pending else "#EFF5FD", edgecolor=color,
        linewidth=1.5, linestyle="--" if pending else "-"))
    ax.text(x + .18, y + .91, title, fontsize=16, weight="bold", color=INK,
            va="center")
    ax.text(x + .18, y + .43, body, fontsize=14, color=MUTED, va="center",
            linespacing=1.35)


def arrow(ax, a, b, label=None):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=17,
                                linewidth=1.7, color=TEAL))
    if label:
        ax.text((a[0]+b[0])/2, (a[1]+b[1])/2+.12, label,
                fontsize=12, color=TEAL, ha="center")


def render(name, title, subtitle, nodes, note, feedback=False):
    fig, ax = plt.subplots(figsize=(14, 6.2), dpi=180)
    fig.patch.set_facecolor("white")
    ax.set(xlim=(0,14), ylim=(0,6.2))
    ax.axis("off")
    ax.text(.65,5.78,title,fontsize=25,weight="bold",color=INK)
    ax.text(.65,5.31,subtitle,fontsize=14,color=MUTED)
    for pos, node in zip(POSITIONS, nodes):
        box(ax,pos,*node)
    arrow(ax,(4.35,4.27),(5.00,4.27))
    arrow(ax,(8.8,4.27),(9.45,4.27))
    arrow(ax,(11.38,3.55),(11.38,2.88))
    arrow(ax,(9.45,2.12),(8.8,2.12))
    arrow(ax,(5.00,2.12),(4.35,2.12))
    if feedback:
        arrow(ax,(2.47,2.87),(2.47,3.55),"feedback")
    ax.text(.65,.68,note,fontsize=13,color=MUTED,linespacing=1.4)
    fig.subplots_adjust(left=0,right=1,top=1,bottom=0)
    OUT.mkdir(parents=True,exist_ok=True)
    for ext in ["png","svg"]:
        fig.savefig(OUT/f"{name}.{ext}", dpi=180, facecolor="white")
    plt.close(fig)


def main():
    render("task1_simulation", "Task 1 | Go2 simulator feasibility",
        "Current prototype and the collision-proxy experiment that remains pending",
        [("Detailed office asset", "High-detail visual mesh\nReported collision-processing OOM"),
         ("Separate geometry", "Visual mesh: collision off\nSupport: plane collider"),
         ("Go2 policy control", "45-D observation / 12 actions\nPretrained joint-position targets"),
         ("Office demonstration", "Robot + visual environment\nFurniture collisions absent"),
         ("Furniture proxies", "Simplified collision geometry\nSame visual scene and policy", True),
         ("Controlled evaluation", "Peak VRAM / latency / tracking\nObstacle collision checks", True)],
        "Dashed boxes: pending. Reported OOM has no saved numerical memory profile.")
    render("task2_gqft_pipeline", "Task 2 | GQFT visual trajectory estimation",
        "Observed RGB motion is mapped to camera displacement and ground-plane image coordinates",
        [("Consecutive RGB", "960 × 540, 5 Hz\nCalibrated camera geometry"),
         ("Frozen SEA-RAFT", "Optical flow + confidence\n160 × 90 flow grid"),
         ("Spatial CNN pooling", "Mean/max: baseline\nAttention/max: candidate"),
         ("Causal Transformer", "Temporal motion context\nLearned time embeddings"),
         ("Displacement heads", "Delta xyz → accumulated path\nOptional supervised yaw"),
         ("Ground projection", "3-D motion → pixel trajectory\nADE/FDE + direct 3-D error")],
        "Flow, pitch, anchor and checkpoint must agree. This estimates motion; obstacle avoidance is unmeasured.")
    render("task2_geometry_diagnosis", "Task 2 | Evidence → controlled label experiment",
        "Confirmed interface defects and an oracle inconsistency motivate separate engineering changes",
        [("Overlay inconsistency", "Flow / pitch / anchor mismatch\nWrong checkpoint label"),
         ("Contract repair", "Normalize once / pitch conversion\nStrict architecture loading"),
         ("Ground-truth oracle", "Project exact 3-D motion\n3 of 104 windows conflict"),
         ("Height mismatch", "Sequence-floor labels\nversus fixed 1.2 m rig"),
         ("Paired label test", "Same Attention, no yaw/flips\nChange only label height", True),
         ("Matched validation", "Oracle + ADE/FDE + 3-D error\nHistory gate; test held fixed", True)],
        "Oracle max discrepancy: 65.525 px; matched label height: 0.000126 px. Retraining benefit remains a hypothesis.")
    render("task3_control_loop", "Task 3 | Sampled MoE locomotion feedback",
        "The diagnosed interaction spans policy feedback, coupled actuation and simulated foot contact",
        [("Measured-state history", "5 × 45 values, oldest first\nCommand + previous raw action"),
         ("MoE + shared actor", "8 softmax-weighted latent experts\n50 Hz policy; newest frame"),
         ("Bounded joint targets", "12 actions → scale + offset\nCurrent position-target limits"),
         ("Coupled PD actuator", "Jᵀ motor torque + effort limits\n200 Hz target-error feedback"),
         ("Dynamics + foot contact", "Contact ratio A/B: 100 vs 10\nSame policy / gains / limits"),
         ("Next measured state", "Joint/body motion + support\nTracking / band RMS / traversal")],
        "Eight experts blend latent features, not hard-switched motor controllers. Hardware initiating cause is unresolved.",
        feedback=True)
    render("task4_mesh_repair", "Task 4 | Calibrated mesh and PBR repair",
        "Latest product-mesh revision; distinct from the Gaussian reconstruction branch",
        [("Photo / scan audit", "Silhouette / texture / support\nCalibrated reference views"),
         ("Asset / shape selection", "Licensed source or photo-built\nFidelity before polygon count"),
         ("Fit and refine", "Metre scale / support height\nSubdivision / bevel / PBR"),
         ("Private mesh assembly", "Bounded scan deletion\nPreserve original toaster maps"),
         ("Browser verification", "22 selectable objects checked\n33-prop placement audit"),
         ("Quality comparison", "Real / earlier mesh / current mesh\nNovel-view quality pending")],
        "Ten objects revised; two generic size flags remain. Approximate models are not exact product recovery.")
    render("task4_rgbd_pipeline", "Task 4 | Separate physics and Gaussian RGB-D",
        "Calibrated observation bridge for a static navigation agent; no articulated robot coupling yet",
        [("Navigation action", "Velocity / turn request\nStatic scene configuration"),
         ("Sensorless Habitat", "Proxy + Bullet / NavMesh\nStatic geometric constraints"),
         ("Calibrated pose bridge", "Pose + intrinsics + frame ID\nExplicit coordinate conversion"),
         ("CUDA Gaussian render", "4.378M saved Gaussians\nRGB / expected Z / alpha"),
         ("Synchronized export", "Matching frame and camera\nInvalid depth → NaN"),
         ("Held-out evaluation", "RGB + measured-depth accuracy\nFull pipeline p50/p95 latency", True)],
        "99.0068% valid depth is one-frame coverage. 12.0576 ms is raster-kernel time, not end-to-end RGB-D latency.")
    print("Generated six independent PNG/SVG diagram pairs.")


if __name__ == "__main__":
    main()
