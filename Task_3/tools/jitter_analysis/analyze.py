"""Plots and explicit, phase-specific metrics for record.py traces."""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import welch
from plot_help import plot_explanation, reading_intro


def spectrum(values, fs):
    return welch(values, fs=fs, axis=0, nperseg=min(len(values), round(2 * fs)), detrend="linear")


def band_rms(values, fs, low=8., high=30.):
    """Welch band RMS, >=2 contiguous seconds; output in input units."""
    if len(values) < round(2 * fs):
        return None
    if high >= fs / 2:
        raise ValueError("Band must remain below Nyquist")
    freq, psd = spectrum(values, fs)
    band = (freq >= low) & (freq <= high)
    return np.sqrt(np.trapezoid(psd[band], freq[band], axis=0))


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def load_run(path):
    manifest = json.loads((path / "manifest.json").read_text())
    status = json.loads((path / "status.json").read_text())
    with np.load(path / "trace.npz", allow_pickle=False) as z:
        d = {key: z[key] for key in z.files}
    t = d["time"]
    if len(t) < 2 or not np.allclose(np.diff(t), manifest["dt"], atol=1e-9):
        raise ValueError("Trace timestamps must be uniform and increasing")
    for name, value in d.items():
        if len(value) != len(t) or not np.isfinite(value).all():
            raise ValueError(f"Invalid trace field: {name}")
    if d["q"].shape[1:] != (12,) or d["foot_pos"].shape[1:] != (4, 3):
        raise ValueError("Unexpected joint or foot layout")
    return manifest, status, d


def phase_metrics(d, m, start, stop):
    mask = (d["time"] >= start - 1e-8) & (d["time"] < stop - 1e-8)
    if not mask.any():
        return None
    policy = mask & d["policy_tick"]
    q, target = d["q"][mask], d["target"][mask]
    scale = np.asarray(m["scale"])
    rate = 1 / m["dt"]
    qrms = band_rms(np.degrees(q), rate)
    trms = band_rms(np.degrees(d["target"][policy]), rate / m["decimation"], 8., 20.)
    actions, targets = d["action"][policy], d["target"][policy]
    saturated = np.abs(d["target_removed"][mask]) > 1e-7
    torque_sat = np.abs(d["torque_raw"][mask]) > np.asarray(m["torque_limits"]) + 1e-5
    return dict(
        start_s=float(d["time"][mask][0]), duration_s=float(mask.sum() * m["dt"]),
        q_8_30_hz_rms_deg_per_joint=None if qrms is None else qrms.tolist(),
        q_8_30_hz_rms_deg_mean=None if qrms is None else float(qrms.mean()),
        target_8_20_hz_rms_deg_per_joint=None if trms is None else trms.tolist(),
        target_8_20_hz_rms_deg_mean=None if trms is None else float(trms.mean()),
        target_removed_fraction_per_joint=saturated.mean(axis=0).tolist(),
        target_removed_fraction_mean=float(saturated.mean()),
        torque_clipped_fraction_per_joint=torque_sat.mean(axis=0).tolist(),
        torque_clipped_fraction_mean=float(torque_sat.mean()),
        tracking_error_rms_deg_per_joint=np.sqrt(np.mean(np.degrees(target - q) ** 2, axis=0)).tolist(),
        vx_body_rmse=float(np.sqrt(np.mean((d["base_velocity_body"][mask, 0] - d["command"][mask, 0]) ** 2))),
        mean_vx_body=float(d["base_velocity_body"][mask, 0].mean()),
        mean_vx_world=float(d["base_velocity_world"][mask, 0].mean()),
        max_tilt_deg=float(d["tilt_deg"][mask].max()),
        action_rate_cost=float(np.mean(np.sum(np.diff(actions, axis=0) ** 2, axis=1))) if len(actions) > 1 else None,
        target_second_difference_cost=float(np.mean(np.sum((np.diff(targets, n=2, axis=0) / scale) ** 2, axis=1))) if len(targets) > 2 else None,
        saturation_pressure_cost=float(np.mean(np.sum((d["target_removed"][policy] / scale) ** 2, axis=1))) if policy.any() else None,
        gyro_freshness_rms_rad_s=float(np.sqrt(np.mean(((d["obs_viewer"][policy, 3:6] - d["obs_fresh"][policy, 3:6]) / .25) ** 2))) if policy.any() else None,
        riser_contact_seconds_per_foot=((d["foot_riser_force"][mask] > 1).sum(axis=0) * m["dt"]).tolist(),
        foot_contact_seconds_per_foot=((d["foot_normal_force"][mask] > 1).sum(axis=0) * m["dt"]).tolist(),
    )


def analyze_run(path):
    path = Path(path)
    m, s, d = load_run(path)
    t, contact = d["time"], s["first_stair_contact_s"]
    end = float(t[-1] + m["dt"])
    motion_start = m["stand"] + m["ramp"]
    intervals = {
        "standing": (max(0., m["stand"] - 2), m["stand"]),
        "approach": (motion_start, end if contact is None else contact),
        "fixed_motion_4_8": (4., min(8., end)),
        "motion_all": (motion_start, end),
    }
    if contact is not None:
        intervals["after_contact"] = (contact, min(contact + 6., end))
    phases = {name: phase_metrics(d, m, a, b) for name, (a, b) in intervals.items()}
    metrics = dict(
        run=path.name, outcome=s["outcome"], update=m["checkpoint_update"],
        checkpoint_sha256=m["checkpoint_sha256"], terrain=m["terrain"], sensors=m["sensors"],
        first_contact_s=contact, end_s=end, final_base_x=float(d["base_pos"][-1, 0]),
        max_base_x=float(d["base_pos"][:, 0].max()), max_tilt_deg=float(d["tilt_deg"].max()),
        max_abs_y_deviation=float(np.abs(d["base_pos"][:, 1] + 9.5).max()),
        final_yaw_deg=float(np.degrees(np.unwrap(d["yaw_rad"])[-1])),
        peak_nonfoot_force_N=float(d["nonfoot_contact_force"].max()), phases=phases,
        warnings=s["warnings"], execution_status=s["status"],
    )
    save_json(path / "metrics.json", metrics)
    plots = []

    def finish(fig, name, title):
        fig.suptitle(title, fontsize=12)
        fig.tight_layout()
        fig.savefig(path / (name + ".png"), dpi=140)
        plt.close(fig)
        plots.append((name + ".png", title))

    def mark(ax):
        if contact is not None:
            ax.axvline(contact, color="crimson", linestyle=":", linewidth=1)
        ax.grid(alpha=.25)

    fig, axs = plt.subplots(5, 1, figsize=(12, 12), sharex=True)
    axs[0].plot(t, d["base_pos"][:, 0], label="base x")
    if m["terrain"] == "stairs":
        axs[0].axhline(0, color="gray", ls="--", label="first riser")
        axs[0].axhline(3.6, color="green", ls=":", label="top platform starts")
    axs[0].set_ylabel("Progress (m)"); axs[0].legend(ncol=3)
    axs[1].plot(t, d["command"][:, 0], color="black", label="command vx")
    axs[1].plot(t, d["base_velocity_body"][:, 0], label="body-frame vx")
    axs[1].plot(t, d["base_velocity_world"][:, 0], alpha=.6, label="world vx")
    axs[1].set_ylabel("Velocity (m/s)"); axs[1].legend(ncol=3)
    axs[2].plot(t, d["base_pos"][:, 2], label="world z")
    axs[2].plot(t, d["base_clearance"], label="z above surface at base x/y")
    axs[2].set_ylabel("Height (m)"); axs[2].legend()
    axs[3].plot(t, d["tilt_deg"], label="tilt")
    axs[3].plot(t, np.degrees(np.unwrap(d["yaw_rad"])), label="heading")
    axs[3].set_ylabel("Angle (deg)"); axs[3].legend()
    axs[4].plot(t, d["base_pos"][:, 1] + 9.5)
    axs[4].set_ylabel("Lateral offset (m)"); axs[4].set_xlabel("Simulation time (s)")
    for ax in axs: mark(ax)
    contact_caption = "red dotted = first foot/stair contact" if contact is not None else "no stair contact recorded"
    finish(fig, "01_motion", f"{path.name}: motion and outcome = {s['outcome']}; {contact_caption}")

    window_start = max(0., contact - 1.) if contact is not None else motion_start
    window_end = min(end, contact + 3. if contact is not None else motion_start + 4.)
    w = (t >= window_start) & (t <= window_end)
    for kind in ("angles", "torques"):
        fig, axs = plt.subplots(4, 3, figsize=(16, 11), sharex=True)
        for j, ax in enumerate(axs.flat):
            if kind == "angles":
                ax.plot(t[w], np.degrees(d["requested"][w, j]), color="green", alpha=.55, label="requested")
                ax.plot(t[w], np.degrees(d["target"][w, j]), color="darkorange", label="clamped target")
                ax.plot(t[w], np.degrees(d["q"][w, j]), color="tab:blue", label="measured q")
                for limit in (m["target_min"][j], m["target_max"][j]):
                    if np.degrees(limit) > ax.get_ylim()[0] and np.degrees(limit) < ax.get_ylim()[1]:
                        ax.axhline(np.degrees(limit), color="gray", ls=":")
            else:
                ax.plot(t[w], d["torque_raw"][w, j], alpha=.7, label="unlimited PD torque")
                ax.plot(t[w], d["torque_applied"][w, j], label="applied torque")
                for limit in (-m["torque_limits"][j], m["torque_limits"][j]):
                    ax.axhline(limit, color="gray", ls=":")
            ax.set_title(m["joint_names"][j].replace("_joint", "").replace("_", " "))
            mark(ax)
        axs[0, 0].legend(fontsize=8)
        fig.supxlabel("Simulation time (s)")
        fig.supylabel("Angle (degrees)" if kind == "angles" else "Joint torque (Nm)")
        finish(fig, "02_angles" if kind == "angles" else "03_torques", f"{path.name}: {kind} around first contact (or flat motion)")

    fig, axs = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
    for i, leg in enumerate(("FL", "FR", "RL", "RR")):
        axs[0].plot(t, d["foot_normal_force"][:, i], label=leg, alpha=.75)
        axs[1].plot(t, d["foot_riser_force"][:, i], label=leg, alpha=.75)
        axs[2].plot(t, d["foot_clearance"][:, i], label=leg, alpha=.75)
    axs[0].set_ylabel("Foot normal force (N)"); axs[0].legend(ncol=4)
    axs[1].set_ylabel("Riser normal force (N)")
    axs[2].set_ylabel("Clearance (m)"); axs[2].set_xlabel("Simulation time (s)")
    for ax in axs: mark(ax)
    finish(fig, "04_contacts", "Contacts and clearance: vertical-face classification |normal_z| < 0.3; clearance is height under foot center")

    fig, axs = plt.subplots(2, 2, figsize=(12, 8), sharex=True, sharey=True)
    for i, ax in enumerate(axs.flat):
        if m["terrain"] == "stairs":
            sx = [-1.8, 0.]; sz = [0., 0.]
            for k in range(12):
                sx.extend([k * .3, (k + 1) * .3]); sz.extend([(k + 1) * .1] * 2)
            sx.append(6.6); sz.append(1.2)
            ax.plot(sx, sz, color="black", label="stair surface")
        sc = ax.scatter(d["foot_pos"][:, i, 0], d["foot_pos"][:, i, 2], c=t, s=2, cmap="viridis")
        ax.set_title(("FL", "FR", "RL", "RR")[i]); ax.grid(alpha=.25)
        ax.set_xlim(max(-2, d["foot_pos"][:, :, 0].min() - .2), min(7, d["foot_pos"][:, :, 0].max() + .3))
    fig.colorbar(sc, ax=list(axs.flat), label="Simulation time (s)", shrink=.8)
    fig.supxlabel("World foot x (m)"); fig.supylabel("Foot sphere center z (m)")
    fig.subplots_adjust(top=.9, right=.8, hspace=.3)
    fig.suptitle("Foot trajectories projected to x/z; y motion is omitted, so intersections are not collision proof")
    fig.savefig(path / "05_feet.png", dpi=140); plt.close(fig)
    plots.append(("05_feet.png", "Foot trajectories: geometric evidence, not a collision test"))

    p = d["policy_tick"]
    tp, targets, actions = t[p], d["target"][p], d["action"][p]
    scale = np.asarray(m["scale"])
    fig, axs = plt.subplots(4, 1, figsize=(12, 11), sharex=True)
    axs[0].plot(tp[1:], np.sum(np.diff(actions, axis=0) ** 2, axis=1), label="action first-difference cost")
    axs[0].plot(tp[2:], np.sum((np.diff(targets, n=2, axis=0) / scale) ** 2, axis=1), label="normalized target second-difference cost")
    axs[0].set_ylabel("Unweighted cost"); axs[0].legend()
    axs[1].plot(tp, np.sum((d["target_removed"][p] / scale) ** 2, axis=1))
    axs[1].set_ylabel("Saturation cost")
    axs[2].plot(tp, np.linalg.norm((d["obs_viewer"][p, 3:6] - d["obs_fresh"][p, 3:6]) / .25, axis=1))
    axs[2].set_ylabel("Gyro stale/fresh\ndifference (rad/s)")
    for i in range(8): axs[3].plot(tp, d["gates"][p, i], label=str(i), linewidth=.8)
    axs[3].set_ylabel("Soft expert weight"); axs[3].legend(ncol=8, fontsize=8)
    axs[3].set_xlabel("Simulation time (s)")
    for ax in axs: mark(ax)
    finish(fig, "06_policy", "Policy costs, observation freshness and continuous MoE weights; costs are diagnostics, not measured vibration")

    fig, axs = plt.subplots(1, 2, figsize=(13, 5))
    for name in ("approach", "after_contact"):
        if name not in intervals: continue
        a, b = intervals[name]
        mask = (t >= a - 1e-8) & (t < b - 1e-8)
        for ax, values, rate, maxfreq in [(axs[0], d["q"][mask], 1 / m["dt"], 50),
                                           (axs[1], d["target"][mask & p], 1 / (m["dt"] * m["decimation"]), 24)]:
            if len(values) < round(2 * rate): continue
            f, psd = spectrum(np.degrees(values), rate)
            use = (f > 0) & (f <= maxfreq)
            ax.semilogy(f[use], np.maximum(psd[use].mean(axis=1), 1e-12), label=f"{name}: {len(values)/rate:.2f} s")
    axs[0].axvspan(8, 30, alpha=.1); axs[1].axvspan(8, 20, alpha=.1)
    axs[0].set_title("Measured joints: 200 Hz samples; RMS band 8–30 Hz")
    axs[1].set_title("Targets at policy ticks: 50 Hz; RMS band 8–20 Hz")
    for ax in axs:
        ax.set_xlabel("Frequency (Hz)"); ax.set_ylabel("Mean joint PSD (deg²/Hz)"); ax.grid(alpha=.25)
        if ax.lines: ax.legend(fontsize=8)
    finish(fig, "07_spectra", "Welch spectra: short/nonstationary windows and different gait phases limit interpretation")

    body = [f"<h1>{html.escape(path.name)}</h1>", reading_intro(m, s, path), f"<p>Outcome: <b>{s['outcome']}</b>. Model update {m['checkpoint_update']}; {m['sensors']} observations; {m['terrain']}.</p>",
            '<p><a href="manifest.json">Provenance</a> · <a href="metrics.json">Metrics</a> · <a href="trace.npz">Numeric trace</a> · <a href="contacts.jsonl">Contact events</a></p>',
            '<p>This page shows a fresh scripted simulation. The outcome and reading guide above explain whether a task failure occurred.</p>']
    for image, title in plots:
        body.append(f'<h2>{html.escape(title)}</h2>{plot_explanation(image, m, s, metrics)}<a href="{image}"><img src="{image}" loading="lazy"></a>')
    (path / "index.html").write_text('<!doctype html><html><meta charset="utf-8"><title>MoE trace analysis</title><style>body{font:16px system-ui;max-width:1500px;margin:24px auto;padding:16px}img{width:100%}a{color:#1760a5}.plot-help table{border-collapse:collapse;width:100%;margin:12px 0}.plot-help td,.plot-help th{border:1px solid #bdcddd;padding:8px;text-align:left}</style>' + '\n'.join(body) + '</html>')
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    print(json.dumps(analyze_run(args.run), indent=2))
