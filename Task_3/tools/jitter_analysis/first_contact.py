"""Inspect the first loaded stair contact, including an explicitly static target-pose check."""
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mujoco
import numpy as np

from analyze import load_run, save_json, phase_metrics
from plot_help import refresh_page


def analyze_contact(path, flat=None):
    path = Path(path)
    m, s, d = load_run(path)
    onset = s["first_stair_contact_s"]
    if onset is None: return None
    model = mujoco.MjModel.from_xml_path(m["scene"])
    if hashlib.sha256(Path(m["scene"]).read_bytes()).hexdigest() != m["scene_sha256"]:
        raise ValueError("Scene changed since recording; target-pose analysis requires the original scene")
    scratch = mujoco.MjData(model)
    joints = [model.jnt_qposadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)] for name in m["joint_names"]]
    legs = ["FL", "FR", "RL", "RR"]
    feet = [mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, leg + "_foot") for leg in legs]
    first = {}
    top_steps = {leg: 0 for leg in legs}
    for line in (path / "contacts.jsonl").open():
        e = json.loads(line)
        terrain = next((name for name in (e["geom1"], e["geom2"]) if name.startswith("step_")), None)
        if not terrain or e["foot"] is None or e["force_contact"][0] <= 1: continue
        leg = e["foot"]
        first.setdefault(leg, e)
        if abs(e["frame"][2]) > .7:
            top_steps[leg] = max(top_steps[leg], int(terrain.split("_")[-1]))
    k = int(np.argmin(np.abs(d["time"] - onset)))
    leg_index = int(np.argmax(d["foot_step_force"][k]))
    joint_slice = slice(3 * leg_index, 3 * leg_index + 3)
    radius = float(model.geom_size[feet[leg_index], 0])
    # This protocol's first riser is 0.10 m high; validate rather than assume silently.
    first_step = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "step_1_1")
    step_top = float(model.geom_pos[first_step, 2] + model.geom_size[first_step, 2])
    indices = np.flatnonzero((d["time"] >= onset - 1) & (d["time"] <= onset + 1.5))
    static_target = []
    for i in indices:
        scratch.qpos[:] = d["sim_qpos"][i]
        scratch.qpos[joints] = d["target"][i]
        mujoco.mj_kinematics(model, scratch)
        static_target.append(scratch.geom_xpos[feet[leg_index]].copy())
    static_target = np.asarray(static_target)
    target_at_contact = static_target[np.flatnonzero(indices == k)[0]]
    summary = dict(
        time_s=float(onset), first_foot=legs[leg_index], step_top_m=step_top, foot_radius_m=radius,
        approximate_center_z_for_flat_top_clearance_m=step_top + radius,
        measured_foot_xyz_m=d["foot_pos"][k, leg_index].tolist(),
        static_clamped_target_foot_xyz_m=target_at_contact.tolist(),
        static_pose_caveat="Forward kinematics with recorded base frozen and joints set to current clamped targets; not a dynamic prediction or a feasible contact state",
        target_removed_on_first_leg_rad=d["target_removed"][k, joint_slice].tolist(),
        raw_torque_on_first_leg_Nm=d["torque_raw"][k, joint_slice].tolist(),
        torque_limits_on_first_leg_Nm=m["torque_limits"][joint_slice],
        q_on_first_leg_rad=d["q"][k, joint_slice].tolist(),
        target_on_first_leg_rad=d["target"][k, joint_slice].tolist(),
        first_loaded_step_contact_per_foot=first,
        highest_step_with_any_top_or_diagonal_support_per_foot=top_steps,
        top_contact_caveat="Any sample >1 N with abs(normal_z)>0.7; does not require sustained support or prove traversal",
    )
    if flat is not None:
        fm, _, fd = load_run(Path(flat))
        for key in ("checkpoint_sha256", "sensors", "vx", "stand", "ramp", "y_offset", "yaw_offset"):
            if fm[key] != m[key]: raise ValueError(f"Unmatched flat run: {key}")
        n = min(len(d["time"]), len(fd["time"]))
        changed = np.flatnonzero(np.max(np.abs(d["q"][:n] - fd["q"][:n]), axis=1) > 1e-6)
        summary["first_joint_difference_vs_matched_flat_s"] = float(d["time"][changed[0]]) if len(changed) else None
        summary["matched_flat"] = str(flat)
        stop = min(onset + 6., float(d["time"][-1] + m["dt"]), float(fd["time"][-1] + fm["dt"]))
        summary["same_time_after_contact_comparison"] = {
            "stairs": phase_metrics(d, m, onset, stop),
            "flat": phase_metrics(fd, fm, onset, stop),
        }
        fig, axs = plt.subplots(3, 1, figsize=(12, 9), sharex=True)
        for label, dd in [("stairs", d), ("flat", fd)]:
            use = (dd["time"] >= onset - 1.) & (dd["time"] < stop)
            axs[0].plot(dd["time"][use] - onset, dd["base_pos"][use, 0], label=label)
            axs[1].plot(dd["time"][use] - onset, dd["tilt_deg"][use], label=label)
            use &= dd["policy_tick"]
            cost = np.sum((np.diff(dd["target"][use], n=2, axis=0) / np.asarray(m["scale"])) ** 2, axis=1)
            axs[2].plot(dd["time"][use][2:] - onset, cost, label=label, alpha=.7)
        for ax in axs:
            ax.axvline(0, color="crimson", ls=":"); ax.grid(alpha=.25); ax.legend()
        axs[0].set_ylabel("Base x (m)"); axs[1].set_ylabel("Tilt (degrees)")
        axs[2].set_ylabel("Target second-difference cost")
        axs[2].set_xlabel("Seconds relative to first loaded foot/stair contact")
        fig.suptitle("Same policy, start, command and observation mode; stair collisions enabled versus disabled")
        fig.tight_layout(); fig.savefig(path / "09_flat_comparison.png", dpi=140); plt.close(fig)
    save_json(path / "first_contact_analysis.json", summary)

    tw = d["time"][indices]
    fig, axs = plt.subplots(3, 2, figsize=(14, 11), sharex=True)
    axs[0, 0].plot(tw, d["foot_pos"][indices, leg_index, 2], label="measured center z")
    axs[0, 0].plot(tw, static_target[:, 2], label="static target-pose center z")
    axs[0, 0].axhline(step_top + radius, color="black", ls="--", label="first top + radius")
    axs[0, 0].set_ylabel("Foot center z (m)"); axs[0, 0].legend(fontsize=8)
    axs[0, 1].plot(tw, d["foot_pos"][indices, leg_index, 0], label="measured x")
    axs[0, 1].plot(tw, static_target[:, 0], label="static target-pose x")
    axs[0, 1].axhline(0, color="black", ls="--", label="first riser x")
    axs[0, 1].set_ylabel("Foot x (m)"); axs[0, 1].legend(fontsize=8)
    axs[1, 0].plot(tw, d["foot_riser_force"][indices, leg_index], label="riser normal force")
    axs[1, 0].plot(tw, d["foot_normal_force"][indices, leg_index], alpha=.6, label="all normal force")
    axs[1, 0].set_ylabel("Contact force (N)"); axs[1, 0].legend(fontsize=8)
    axs[1, 1].plot(tw, d["tilt_deg"][indices], label="tilt")
    axs[1, 1].plot(tw, np.degrees(np.unwrap(d["yaw_rad"]))[indices], label="heading")
    axs[1, 1].set_ylabel("Body angle (deg)"); axs[1, 1].legend(fontsize=8)
    for j, stage in enumerate(["hip", "thigh", "calf"]):
        joint = 3 * leg_index + j
        color = f"C{j}"
        axs[2, 0].plot(tw, np.degrees(d["q"][indices, joint]), color=color, label=stage + " measured")
        axs[2, 0].plot(tw, np.degrees(d["target"][indices, joint]), color=color, ls="--", label=stage + " target")
        axs[2, 1].plot(tw, d["torque_raw"][indices, joint], color=color, ls="--", alpha=.6)
        axs[2, 1].plot(tw, d["torque_applied"][indices, joint], color=color, label=stage)
    axs[2, 0].set_ylabel("Joint angle (deg)"); axs[2, 0].legend(ncol=2, fontsize=8)
    axs[2, 1].set_ylabel("Joint torque (Nm)\ndashed = before clipping"); axs[2, 1].legend(fontsize=8)
    for ax in axs.flat:
        ax.axvline(onset, color="crimson", ls=":"); ax.grid(alpha=.25)
    fig.supxlabel("Simulation time (s)")
    fig.suptitle(f"{path.name}: first contact is {legs[leg_index]} at {onset:.3f} s\nStatic target pose freezes base and ignores contact dynamics; it is not a predicted trajectory", fontsize=11)
    fig.tight_layout(); fig.savefig(path / "08_first_contact.png", dpi=140); plt.close(fig)
    page = path / "index.html"
    addition = '<h2>First contact: geometry, targets, force and body response</h2><p><a href="first_contact_analysis.json">Event data and static-pose limitations</a></p><a href="08_first_contact.png"><img src="08_first_contact.png" loading="lazy"></a>'
    text = page.read_text()
    if 'href="08_first_contact.png"' not in text: page.write_text(text.replace('</html>', addition + '</html>'))
    text = page.read_text()
    if flat is not None and 'href="09_flat_comparison.png"' not in text:
        page.write_text(text.replace('</html>', '<h2>Controlled terrain comparison</h2><a href="09_flat_comparison.png"><img src="09_flat_comparison.png" loading="lazy"></a></html>'))
    refresh_page(page)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--flat", type=Path)
    args = parser.parse_args()
    print(json.dumps(analyze_contact(args.run, args.flat), indent=2))
