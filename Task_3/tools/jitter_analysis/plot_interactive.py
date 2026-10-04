"""Plot saved user-operated sessions only; never opens MuJoCo or runs a policy."""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from analyze import band_rms, save_json


def load_attempt(path):
    m = json.loads((path / "manifest.json").read_text())
    s = json.loads((path / "status.json").read_text())
    chunks = sorted((path / "raw").glob("chunk_*.npz"))
    if not chunks:
        return m, s, None
    fields = {}
    for chunk in chunks:
        with np.load(chunk, allow_pickle=False) as z:
            for key in z.files:
                fields.setdefault(key, []).append(z[key])
    d = {key: np.concatenate(values) for key, values in fields.items()}
    t = d["time"]
    if len(t) > 1 and not np.allclose(np.diff(t), m["dt"], atol=1e-8):
        raise ValueError(f"Nonuniform timestamps in {path}; do not plot across a reset/gap")
    if any(len(v) != len(t) for v in d.values()):
        raise ValueError("Trace fields do not share timestamps")
    for key in ("q", "target", "torque_applied", "base_pos", "command"):
        if not np.isfinite(d[key]).all():
            raise ValueError(f"Nonfinite {key}: raw data retained, ordinary metrics would be misleading")
    return m, s, d


def analyze_attempt(path, start=None, stop=None):
    m, s, d = load_attempt(path)
    if d is None:
        return dict(attempt=path.name, samples=0, message="No recorded physics steps")
    elapsed = d["time"] - m["start_sim_time"]
    selected = np.ones(len(elapsed), dtype=bool)
    if start is not None: selected &= elapsed >= start
    if stop is not None: selected &= elapsed < stop
    if selected.sum() < 2:
        raise ValueError(f"Window contains fewer than two samples: {path}")
    x = elapsed[selected]
    fs = 1 / m["dt"]
    qrms = band_rms(np.degrees(d["q"][selected]), fs) if fs / 2 > 30 else None
    removed = np.abs(d["target_removed"][selected]) > 1e-6
    clipped = np.abs(d["torque_raw"][selected]) > np.asarray(m["torque_limits"]) + 1e-5
    contact = s["first_riser_contact_s"]
    if contact is None: contact = s["first_stair_contact_s"]
    event_elapsed = None if contact is None else contact - m["start_sim_time"]
    window = selected.copy()
    # Only the joint-detail plot zooms in; the overview retains the user's full selected run.
    if event_elapsed is not None and x[0] <= event_elapsed <= x[-1]:
        window &= (elapsed >= event_elapsed - 1) & (elapsed <= event_elapsed + 3)
    else:
        moving = selected & (np.linalg.norm(d["command"], axis=1) > .01)
        onset = elapsed[np.flatnonzero(moving)[0]] if moving.any() else x[0]
        window &= (elapsed >= max(x[0], onset - 1)) & (elapsed <= onset + 3)
    track_cfg = m["track_configs"][m["track"] - 1]
    metrics = dict(attempt=path.name, checkpoint_update=m["checkpoint_update"],
                   observation_timing=m.get("observation_timing", "legacy"),
                   checkpoint_sha256=m["checkpoint_sha256"], samples=int(selected.sum()),
                   start_elapsed_s=float(x[0]), end_elapsed_s=float(x[-1]),
                   first_stair_contact_elapsed_s=None if s["first_stair_contact_s"] is None else s["first_stair_contact_s"] - m["start_sim_time"],
                   first_riser_contact_elapsed_s=event_elapsed if s["first_riser_contact_s"] is not None else None,
                   mean_joint_8_30_hz_rms_deg=None if qrms is None else float(qrms.mean()),
                   joint_8_30_hz_rms_deg_per_joint=None if qrms is None else qrms.tolist(),
                   target_clipped_fraction_per_joint=removed.mean(axis=0).tolist(),
                   torque_clipped_fraction_per_joint=clipped.mean(axis=0).tolist(),
                   vx_tracking_rmse_m_s=float(np.sqrt(np.mean((d["command"][selected, 0] - d["base_velocity_body"][selected, 0]) ** 2))),
                   vy_tracking_rmse_m_s=float(np.sqrt(np.mean((d["command"][selected, 1] - d["base_velocity_body"][selected, 1]) ** 2))),
                   yaw_rate_tracking_rmse_rad_s=float(np.sqrt(np.mean((d["command"][selected, 2] - d["angular_velocity_body"][selected, 2]) ** 2))),
                   command_min=d["command"][selected].min(axis=0).tolist(),
                   command_max=d["command"][selected].max(axis=0).tolist(),
                   max_tilt_deg=float(d["tilt_deg"][selected].max()),
                   max_base_x_m=float(d["base_pos"][selected, 0].max()),
                   invalid_policy_action_count=int((selected & d["policy_tick"] & ~d["raw_action_finite"]).sum()),
                   note="Observed interactive attempt; no automatic claim of full traversal. RMS includes gait, impacts and corrections in the selected window.")
    plots = path / "plots"
    plots.mkdir(exist_ok=True)
    save_json(plots / "metrics.json", metrics)

    def mark(ax):
        if event_elapsed is not None and x[0] <= event_elapsed <= x[-1]:
            ax.axvline(event_elapsed, color="crimson", ls=":", label="first recorded stair contact")
        ax.grid(alpha=.25)

    def save(fig, name):
        fig.tight_layout()
        fig.savefig(plots / name, dpi=125)
        plt.close(fig)

    fig, axs = plt.subplots(4, 2, figsize=(12, 12), sharex=True)
    ax = axs[0, 0]
    ax.plot(x, d["command"][selected, 0], color="black", label="vx sent to policy")
    ax.plot(x, d["base_velocity_body"][selected, 0], label="actual body vx")
    ax.set_ylabel("Forward speed (m/s)"); ax.legend(fontsize=8)
    ax = axs[0, 1]
    ax.plot(x, d["command"][selected, 1], color="black", label="vy sent to policy")
    ax.plot(x, d["base_velocity_body"][selected, 1], label="actual body vy")
    ax.set_ylabel("Sideways speed (m/s)"); ax.legend(fontsize=8)
    ax = axs[1, 0]
    ax.plot(x, d["command"][selected, 2], color="black", label="yaw rate sent to policy")
    ax.plot(x, d["angular_velocity_body"][selected, 2], label="actual body angular z")
    ax.set_ylabel("Turning rate (rad/s)"); ax.legend(fontsize=8)
    ax = axs[1, 1]
    for i, label in enumerate(("vx input", "vy input", "yaw input")):
        ax.plot(x, d["input_command"][selected, i], label=label)
    ax.set_ylabel("Keyboard command (m/s, yaw rad/s)"); ax.legend(fontsize=8)
    ax = axs[2, 0]
    ax.plot(x, d["base_pos"][selected, 0], label="world x progress")
    ax.plot(x, d["base_pos"][selected, 2], label="body height world z")
    ax.set_ylabel("Position (m)"); ax.legend(fontsize=8)
    ax = axs[2, 1]
    ax.plot(x, d["base_pos"][selected, 1], label="world y position")
    ax.set_ylabel("Sideways position (m)"); ax.legend(fontsize=8)
    ax = axs[3, 0]
    ax.plot(x, d["tilt_deg"][selected], label="body tilt")
    ax.set_ylabel("Tilt (degrees)"); ax.legend(fontsize=8)
    ax = axs[3, 1]
    ax.plot(x, np.degrees(np.unwrap(d["yaw_rad"]))[selected], label="heading")
    ax.set_ylabel("Angle (degrees)"); ax.legend(fontsize=8)
    for ax in axs.flat: mark(ax); ax.set_xlabel("Seconds since this attempt's reset")
    fig.suptitle(f"{path.name}: actual user commands and robot response")
    save(fig, "01_overview.png")

    fig, axs = plt.subplots(4, 3, figsize=(13, 9), sharex=True)
    for j, ax in enumerate(axs.flat):
        ax.plot(elapsed[window], np.degrees(d["requested"][window, j]), alpha=.5, label="requested")
        ax.plot(elapsed[window], np.degrees(d["target"][window, j]), label="clamped target")
        ax.plot(elapsed[window], np.degrees(d["q"][window, j]), label="measured")
        ax.set_title(m["joint_names"][j].replace("_joint", ""), fontsize=9)
        mark(ax)
    axs[0, 0].legend(fontsize=7)
    fig.supxlabel("Seconds since this attempt's reset"); fig.supylabel("Joint angle (degrees)")
    fig.suptitle("Short event window: requested targets versus actual joint angles")
    save(fig, "02_joint_event.png")

    fig, axs = plt.subplots(2, 2, figsize=(12, 7), sharex=True)
    for foot, label in enumerate(("FL", "FR", "RL", "RR")):
        axs[0, 0].plot(x, d["foot_pos"][selected, foot, 2], label=label)
        axs[0, 1].plot(x, d["foot_riser_force"][selected, foot], label=label)
    for radius in sorted(set(m["foot_radius_m"])):
        axs[0, 0].axhline(track_cfg["height"] + radius, color="black", ls="--", label="first top + radius (approx.)")
    axs[0, 0].set_ylabel("Foot center world height (m)"); axs[0, 0].legend(fontsize=7, ncol=3)
    axs[0, 1].set_ylabel("Foot / vertical riser force (N)"); axs[0, 1].legend(fontsize=7, ncol=4)
    axs[1, 0].plot(x, np.linalg.norm(d["target_removed"][selected], axis=1))
    axs[1, 0].set_ylabel("Total removed target (rad, L2 norm)")
    axs[1, 1].plot(x, np.max(np.abs(d["torque_applied"][selected]), axis=1), label="largest applied joint torque")
    axs[1, 1].plot(x, np.max(np.abs(d["torque_raw"][selected]), axis=1), alpha=.6, label="largest raw joint torque")
    axs[1, 1].set_ylabel("Torque magnitude (Nm)"); axs[1, 1].legend(fontsize=7)
    for ax in axs.flat: mark(ax); ax.set_xlabel("Seconds since this attempt's reset")
    fig.suptitle("Recorded foot interaction and controller limiting")
    save(fig, "03_contacts_control.png")

    rms_text = "Unavailable: fewer than two seconds or insufficient sample rate" if qrms is None else f"{qrms.mean():.3f} degrees"
    body = f'''<h1>{html.escape(path.name)} — your interactive recording</h1>
<p>Track {m['track']} ({html.escape(track_cfg['label'])}); checkpoint update {m['checkpoint_update']};
observation timing: {html.escape(m.get('observation_timing', 'legacy'))}.
These figures read saved data only. No policy or new simulation was run to draw them.</p>
<p><a href="../manifest.json">Exact checkpoint, limits and settings</a> · <a href="metrics.json">Numbers</a> ·
<a href="../contacts.jsonl">Contact data</a> · <a href="../../events.jsonl">Your key events</a></p>
<p><b>Mean joint 8–30 Hz RMS:</b> {rms_text}, calculated over {x[0]:.2f}–{x[-1]:.2f} seconds.
This includes impacts and useful corrections; it is not proof of a jitter cause or successful ascent.</p>
<h2>1. Your commands and the response</h2><p>Black vx is the request actually supplied to the policy. Actual vx is how fast the body moves forward.
Black vy is the requested sideways speed; actual body vy is sideways motion relative to the robot's current heading.
Yaw-rate request is compared with measured body angular z, in radians/second; heading is the accumulated direction in degrees.
Zero yaw-rate request does not lock the heading. World y position is different from body-relative vy when the robot turns.
The keyboard-input panel records all three commands. Requests can stay constant because keys change a latched command.
Position shows progress/height; tilt shows leaning and heading shows turning. These panels also support pure sideways runs with vx=0.</p><img src="01_overview.png">
<h2>2. A short joint window</h2><p>Requested is before target limiting; clamped target is after limiting; measured is the actual angle.
When requested and clamped separate, a limit removes part of the command. When measured differs, the joint has tracking error.
Red dotted lines mark first recorded riser/stair contact; no line means none was recorded in the selected interval.
Without a stair event, the window follows the first nonzero motion command in the selected interval, or the beginning if standing throughout.</p><img src="02_joint_event.png">
<h2>3. Contacts and limiting</h2><p>Foot heights and vertical-face forces show when a foot meets a riser.
The dashed height is an approximate geometric threshold for the first tread only, not later steps or a dynamic prediction.
Removed-target magnitude is not measured jitter. Torque maxima summarize all joints and may refer to different joints at different times;
the JSON includes separate clipping fractions. A figure alone does not establish full climbing.</p><img src="03_contacts_control.png">'''
    if (plots / "update_diagnostics.html").exists():
        body += '<p><a href="update_diagnostics.html">Update-rate, gate and actuator diagnostics</a></p>'
    (plots / "index.html").write_text('<!doctype html><meta charset="utf-8"><title>Your MoE recording</title>'
        '<style>body{font:16px system-ui;max-width:1100px;margin:24px auto;padding:16px;line-height:1.5}img{width:100%}</style>' + body)
    return metrics


def plot_session(session, episode=None, start=None, stop=None):
    session = Path(session).resolve()
    manifest = json.loads((session / "manifest.json").read_text())
    if manifest.get("recording_kind") != "interactive_user_commands":
        raise ValueError("Use an interactive session directory, not the older scripted suite")
    paths = sorted(session.glob("attempt_*")) if episode is None else [session / f"attempt_{episode:03d}"]
    if not paths: raise ValueError("No attempts recorded")
    results = [analyze_attempt(p, start, stop) for p in paths]
    links = ''.join(f'<li><a href="{html.escape(r["attempt"])}/plots/index.html">{html.escape(r["attempt"])}</a></li>'
                    if r["samples"] else f'<li>{html.escape(r["attempt"])}: no samples</li>' for r in results)
    (session / "index.html").write_text('<!doctype html><meta charset="utf-8"><h1>Your interactive MoE session</h1>'
        '<p>Each reset/teleport starts a separate attempt. Plots are derived from saved keyboard-controlled data only.</p><ul>' + links + '</ul>')
    print(f"Plots: {session / 'index.html'}")
    return results


if __name__ == "__main__":
    p = argparse.ArgumentParser(__doc__)
    p.add_argument("session", type=Path)
    p.add_argument("--episode", type=int)
    p.add_argument("--start", type=float, help="Seconds since attempt reset")
    p.add_argument("--stop", type=float, help="Exclusive end, seconds since attempt reset")
    args = p.parse_args()
    plot_session(**vars(args))
