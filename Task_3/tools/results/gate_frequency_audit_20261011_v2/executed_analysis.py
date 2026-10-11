"""CPU-only audit of saved recordings: no MuJoCo stepping or training.

Replays recorded policy inputs, separates three network pathways with an exact
three-factor Shapley decomposition, and rechecks the September hardware/sim data.
The pathway probes are instantaneous counterfactuals, not closed-loop rollouts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ.setdefault("MPLCONFIGDIR", "/tmp/svanm2_gate_audit_matplotlib")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import butter, sosfiltfilt, welch
from scipy.stats import spearmanr
import torch
from torch.nn import functional as F

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "xterra_mjlab/svanm2_moe_stair_sim"))
from checkpoint_policy import load_checkpoint_policy
from plot_interactive import load_attempt


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def psd(values, fs):
    return welch(values, fs=fs, axis=0, nperseg=min(len(values), round(2 * fs)), detrend="linear")


def band(values, fs, low, high):
    if len(values) < round(2 * fs):
        return None
    f, p = psd(values, fs)
    mask = (f >= low) & (f <= high)
    return np.sqrt(np.trapezoid(p[mask], f[mask], axis=0))


def peak(values, fs, low, high):
    if len(values) < round(2 * fs):
        return None
    f, p = psd(values, fs)
    mask = (f >= low) & (f <= high)
    return float(f[mask][np.argmax(p[mask].mean(axis=1))])


def histories(frames):
    # Controller repeats the first valid frame after each reset.
    padded = np.concatenate([np.repeat(frames[:1], 4, axis=0), frames])
    return np.stack([padded[i:i + 5].reshape(225) for i in range(len(frames))])


def traversal_recheck(d, m):
    """Apply the existing recorder's success/failure conditions to saved states."""
    loaded = np.zeros(4, dtype=bool)
    contact = False
    durations = dict(tip=0., low_body=0., lane_exit=0., traversed=0.)
    center = (m["track"] - 1 - 2.5) * 3.8
    for i in range(len(d["time"])):
        contact |= bool((d["foot_step_force"][i] > 1).any())
        loaded |= d["foot_platform_force"][i] > 1
        lane = (np.abs(d["foot_pos"][i, :, 1] - center) > 1).any()
        top = (loaded.all() and (d["foot_pos"][i, :, 0] > 3.622).all()
               and not lane and d["tilt_deg"][i] < 30 and d["base_clearance"][i] > .18)
        flags = dict(tip=d["tilt_deg"][i] > 60, low_body=d["base_clearance"][i] < .12,
                     lane_exit=contact and lane, traversed=top)
        for key in durations:
            durations[key] = durations[key] + m["dt"] if flags[key] else 0.
        for key, duration in durations.items():
            if duration >= (.5 if key == "traversed" else .25) - 1e-8:
                return dict(outcome=key, elapsed_s=float(d["time"][i] - m["start_sim_time"]),
                            all_feet_loaded_platform=loaded.tolist(),
                            min_foot_x_m=float(d["foot_pos"][i, :, 0].min()),
                            tilt_deg=float(d["tilt_deg"][i]), clearance_m=float(d["base_clearance"][i]),
                            caveat="Post-hoc application of recorder criteria. Manual steering/variable commands remain; not a controlled success-rate experiment.")
    return dict(outcome="no_success_or_failure_threshold_before_recording_end",
                elapsed_s=float(d["time"][-1] - m["start_sim_time"]), all_feet_loaded_platform=loaded.tolist())


def pathways(policy, h, manifest):
    """Exact vector decomposition of consecutive outputs into gate/expert/direct paths.

    Evaluate all eight old/new combinations, averaging marginal differences over
    all six possible component orders. The components sum to the true delta;
    individual component energies need not add, because effects can cancel.
    """
    gates, features, actions = [], [], []
    with torch.inference_mode():
        for start in range(0, len(h), 128):
            x = torch.from_numpy(h[start:start + 128])
            moe = policy.student_moe_encoder.moe
            g, e = moe.gating_network(x), moe.experts(x)
            latent = F.normalize((g.unsqueeze(-1) * e).sum(1), dim=-1)
            a = policy.actor(torch.cat([latent, x[:, -45:]], dim=-1))
            gates.append(g.numpy()); features.append(e.numpy()); actions.append(a.numpy())
    g, e, a = map(np.concatenate, [gates, features, actions])
    subsets = [[] for _ in range(8)]
    frames = h[:, -45:]
    with torch.inference_mode():
        for start in range(0, len(h) - 1, 128):
            end = min(start + 128, len(h) - 1)
            for subset in range(8):
                gg = torch.from_numpy(g[start + bool(subset & 1):end + bool(subset & 1)])
                ee = torch.from_numpy(e[start + bool(subset & 2):end + bool(subset & 2)])
                oo = torch.from_numpy(frames[start + bool(subset & 4):end + bool(subset & 4)])
                zz = F.normalize((gg.unsqueeze(-1) * ee).sum(1), dim=-1)
                subsets[subset].append(policy.actor(torch.cat([zz, oo], dim=-1)).numpy())
    subsets = np.stack([np.concatenate(x) for x in subsets])
    np.testing.assert_allclose(subsets[0], a[:-1], rtol=1e-4, atol=1e-5)
    np.testing.assert_allclose(subsets[7], a[1:], rtol=1e-4, atol=1e-5)
    q0, scale, lo, hi = [np.asarray(manifest[k]) for k in ("q0", "scale", "target_min", "target_max")]
    targets = np.clip(q0 + scale * np.clip(subsets, -6, 6), lo, hi)

    def decompose(values):
        phis = []
        for bit in (1, 2, 4):
            phi = np.zeros_like(values[0])
            for subset in range(8):
                if subset & bit:
                    continue
                size = subset.bit_count()
                weight = 1 / 6 if size == 1 else 1 / 3
                phi += weight * (values[subset | bit] - values[subset])
            phis.append(phi)
        result = np.stack(phis, axis=1)
        np.testing.assert_allclose(result.sum(1), values[7] - values[0], atol=2e-5, rtol=1e-4)
        return result

    latent_norm = np.linalg.norm((g[..., None] * e).sum(1), axis=1)
    return g, a, decompose(subsets), np.degrees(decompose(targets)), latent_norm


def phase_metrics(d, m, lo, hi, name, attribution=None):
    elapsed = d["time"] - m["start_sim_time"]
    mask = (elapsed >= lo - 1e-8) & (elapsed < hi - 1e-8)
    ticks = np.flatnonzero(d["policy_tick"])
    pt = elapsed[ticks]
    # Consecutive gate/action transitions must have both endpoints inside a phase.
    changes = (pt[1:] >= lo - 1e-8) & (pt[:-1] >= lo - 1e-8) & (pt[1:] < hi - 1e-8)
    policy_mask = mask & d["policy_tick"]
    fs, fps = 1 / m["dt"], 1 / (m["dt"] * m["decimation"])
    g = d["gates"][policy_mask]
    dg = np.abs(np.diff(d["gates"][ticks], axis=0)).sum(1)[changes]
    q = np.degrees(d["q"][mask]); target = np.degrees(d["target"][policy_mask])
    qb = band(q, fs, 8, 30); q50 = band(q, fs, 45, 55)
    tb = band(target, fps, 8, 20)
    entropy = -(g * np.log(np.maximum(g, 1e-30))).sum(1)
    removed = np.abs(d["target_removed"][mask]) > 1e-6
    delta_obs = d["obs_viewer"][policy_mask] - d["obs_fresh"][policy_mask]
    row = dict(name=name, window_s=[lo, hi], samples=int(mask.sum()), policy_samples=int(policy_mask.sum()),
               command_min=d["command"][mask].min(0).tolist(), command_max=d["command"][mask].max(0).tolist(),
               q_8_30_mean_deg=None if qb is None else float(qb.mean()),
               q_45_55_mean_deg=None if q50 is None else float(q50.mean()),
               target_8_20_mean_deg=None if tb is None else float(tb.mean()),
               q_peak_8_30_hz=peak(q, fs, 8, 30), target_peak_8_20_hz=peak(target, fps, 8, 20),
               gate_L1_step_mean=float(dg.mean()), gate_L1_step_p99=float(np.quantile(dg, .99)),
               gate_max_weight=float(g.max()), gate_effective_experts_mean=float(np.exp(entropy).mean()),
               gate_sum_max_error=float(np.abs(g.sum(1) - 1).max()),
               max_tilt_deg=float(d["tilt_deg"][mask].max()),
               calf_target_removed_fraction=removed.mean(0)[[2, 5, 8, 11]].tolist(),
               any_torque_clipped_fraction=float((np.abs(d["torque_raw"][mask]) > np.asarray(m["torque_limits"]) + 1e-5).any(1).mean()),
               gyro_mixed_time_rms_rad_s=float(np.sqrt(np.mean((delta_obs[:, 3:6] / .25) ** 2))),
               gravity_mixed_time_rms=float(np.sqrt(np.mean(delta_obs[:, 6:9] ** 2))),
               q_dq_frame_max_error=float(np.abs(delta_obs[:, 9:33]).max()))
    if attribution is not None:
        phi = attribution[changes]
        row["target_delta_path_rms_deg"] = dict(zip(("gate", "expert_features", "direct_actor_frame"), np.sqrt(np.mean(phi ** 2, axis=(0, 2))).tolist()))
        row["actual_target_delta_rms_deg"] = float(np.sqrt(np.mean(np.diff(target, axis=0) ** 2)))
    return row


def september_recheck(folder):
    summary = json.loads((folder / "suite_summary.json").read_text())
    checked = []
    for row in summary:
        # Baseline/filter comparisons, retaining both deterministic starts.
        if row["terrain"] not in ("flat", "stairs_up_15") or row["profile"] != "hardware" or row["command_mode"] != "forward":
            continue
        if row["dt"] != .005 or row["delay_s"] != .005 or row["contact_timeconst"] != .01 or row.get("torque_model", "joint") != "joint":
            continue
        path = folder / "runs" / row["tag"] / "trace.npz"
        with np.load(path, allow_pickle=False) as z:
            dt = float(np.median(np.diff(z["t"])))
            hf = sosfiltfilt(butter(3, [8, 30], fs=1 / dt, btype="bandpass", output="sos"), z["q"], axis=0)
            selected = (z["t"] > 5.5) & (z["t"] < 20) & (z["tilt"] < 45)
            rms = float(np.degrees(np.sqrt(np.mean(hf[selected] ** 2))))
            if abs(rms - row["q_hf_deg"]) > 1e-8:
                raise ValueError(f"September raw recheck mismatch: {path}")
        checked.append(dict(tag=row["tag"], q_hf_deg_recomputed=rms, stored_q_hf_deg=row["q_hf_deg"],
                            samples=int(selected.sum()), outcome=row["outcome"], validated_traversal=row["validated_traversal"],
                            forward_tracking_rmse=row["command_rmse"][0], trace_sha256=sha(path)))
    with np.load(folder / "hardware_arrays.npz", allow_pickle=False) as a:
        t = a["t"]; u = np.arange(t[0], t[-1], .005)
        interp = lambda key: np.column_stack([np.interp(u, t, a[key][:, i]) for i in range(a[key].shape[1])])
        q, target, command = interp("q"), interp("target"), interp("command")
        sos = butter(3, [8, 30], fs=200, btype="bandpass", output="sos")
        hf, ht = sosfiltfilt(sos, q, axis=0), sosfiltfilt(sos, target, axis=0)
        windows = []
        for start in np.arange(15, t[-1] - 4, 4):
            mask = (u >= start) & (u < start + 4); raw = (t >= start) & (t < start + 4)
            if np.mean(np.linalg.norm(command[mask], axis=1) > .08) < .95 or not a["moe"][raw].all():
                continue
            windows.append(dict(start_s=float(start), q_hf_deg=float(np.degrees(np.sqrt(np.mean(hf[mask] ** 2)))),
                                target_hf_deg=float(np.degrees(np.sqrt(np.mean(ht[mask] ** 2)))),
                                max_interval_ms=float(a["control_interval_ms"][raw].max()),
                                max_sensor_age_ms=float(a["sensor_age_ms"][raw].max()), max_action_age_ms=float(a["action_age_ms"][raw].max())))
    correlations = {key: float(spearmanr([w["q_hf_deg"] for w in windows], [w[key] for w in windows]).statistic)
                    for key in ("target_hf_deg", "max_interval_ms", "max_sensor_age_ms", "max_action_age_ms")}
    reference = json.loads((folder / "deep_hardware_summary.json").read_text())
    for key, value in correlations.items():
        assert abs(value - reference["window_correlations"][key]) < 1e-10
    return dict(valid_suite_rows=len(summary), excluded=["pre_sensor_refresh_runs", "invalidated_prototype"],
                raw_filter_rechecks=checked, hardware_windows=windows, hardware_window_correlations=correlations,
                caveat="These HF metrics reproduce the September Butterworth definition; do not equate them numerically to the new Welch phase metric. Original hardware histories/status rows are not in this copied folder.")


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument("--session", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(); out = args.out.resolve(); out.mkdir(parents=True, exist_ok=False)
    session = args.session.resolve(); torch.set_num_threads(1)
    timing = []
    for path in sorted(session.glob("attempt_*")):
        m, s, d = load_attempt(path)
        if d is None:
            continue
        intervals = np.diff(d["time"][d["policy_tick"]])
        assert np.allclose(intervals, m["dt"] * m["decimation"], atol=1e-8)
        ticks = d["policy_tick"]
        wall = 1000 * (d["policy_wall_end_s"][ticks] - d["wall_s"][ticks])
        timing.append(dict(attempt=path.name, samples=len(d["time"]), policy_ticks=int(ticks.sum()),
                           policy_sim_interval_ms=[float(intervals.min() * 1000), float(intervals.max() * 1000)],
                           policy_plus_bookkeeping_wall_ms_p50_p99_max=np.percentile(wall, [50, 99, 100]).tolist(),
                           invalid_policy_count=int((~d["raw_action_finite"][ticks]).sum()),
                           traversal_recheck=traversal_recheck(d, m)))
    path = session / "attempt_004"; m, s, d = load_attempt(path)
    checkpoint = Path(m["checkpoint"]); assert sha(checkpoint) == m["checkpoint_sha256"]
    ticks = np.flatnonzero(d["policy_tick"]); h = histories(d["obs_policy"][ticks])
    policy, update = load_checkpoint_policy(checkpoint, "cpu")
    g, a, raw_phi, target_phi, latent_norm = pathways(policy, h, m)
    np.testing.assert_allclose(g, d["gates"][ticks], rtol=1e-4, atol=1e-5)
    np.testing.assert_allclose(a, d["raw_action"][ticks], rtol=1e-4, atol=1e-5)
    assert np.max(np.abs(d["action"] - np.clip(d["raw_action"], -6, 6))) < 1e-5
    requested = np.asarray(m["q0"]) + np.asarray(m["scale"]) * d["action"]
    assert np.max(np.abs(d["target"] - np.clip(requested, m["target_min"], m["target_max"]))) < 1e-5
    intervals = [(0, 4.825, "approach"), (4.825, 8, "first_stair_contact"), (8, 16, "later_ascent"),
                 (16.285, 19.645, "platform_stopped"), (25, 45, "platform_mixed_motion"), (65, 77, "descent")]
    phases = [phase_metrics(d, m, lo, hi, name, target_phi) for lo, hi, name in intervals]
    september = september_recheck(ROOT / "moe_jitter_audit_20260921")
    np.savez_compressed(out / "pathway_probe.npz", elapsed_s=d["time"][ticks][1:] - m["start_sim_time"],
                        raw_action_shapley=raw_phi, target_shapley_deg=target_phi, gates=g, mixed_latent_norm=latent_norm)
    result = dict(scope="Saved-data analysis and CPU policy replay only; no new physics, training, CUDA use, hardware action, or runtime edits.",
                  checkpoint_update=int(update), checkpoint_sha256=sha(checkpoint),
                  replay_max_abs_action_error=float(np.abs(a - d["raw_action"][ticks]).max()),
                  replay_max_abs_gate_error=float(np.abs(g - d["gates"][ticks]).max()),
                  latent_norm_p0_p1_p50=np.percentile(latent_norm, [0, 1, 50]).tolist(), timing=timing, phases=phases,
                  september=september, attribution_definition="Three-factor Shapley vector delta: gate weights, expert features, direct actor frame. Averaged over all six component orders, after the real action/target clamps. This is open-loop local sensitivity, not causal contribution to physical jitter or a closed-loop fix. RMS component energies may cancel and are not causal percentages.",
                  input_sha256={str(f.relative_to(ROOT)): sha(f) for f in [Path(__file__), session / "manifest.json", path / "manifest.json", *sorted((path / "raw").glob("chunk_*.npz")), ROOT / "moe_jitter_audit_20260921/hardware_arrays.npz", ROOT / "moe_jitter_audit_20260921/suite_summary.json", ROOT / "tools/results/control_loop_audit_20261006_v2/summary.json"]})
    save(out / "analysis.json", result)
    elapsed = d["time"] - m["start_sim_time"]; pt = elapsed[ticks]
    fig, axes = plt.subplots(4, 1, figsize=(13, 12), sharex=True)
    axes[0].plot(elapsed, d["tilt_deg"]); axes[0].set_ylabel("Body tilt (degrees)")
    axes[1].plot(pt, d["gates"][ticks]); axes[1].set_ylabel("Eight soft gate weights")
    for bit, label in enumerate(("Gate", "Expert features", "Direct actor frame")):
        # 0.2 s moving average of RMS magnitude for legibility; stored probes are unsmoothed.
        magnitude = np.sqrt(np.mean(target_phi[:, bit] ** 2, axis=1))
        axes[2].plot(pt[1:], np.convolve(magnitude, np.ones(10) / 10, mode="same"), label=label)
    axes[2].set_ylabel("Target-delta probe RMS\n(degrees per policy tick)"); axes[2].legend()
    axes[3].plot(elapsed, d["command"][:, 0], label="vx"); axes[3].plot(elapsed, d["command"][:, 2], label="yaw rate")
    axes[3].set_ylabel("Recorded command"); axes[3].set_xlabel("Seconds since attempt 4 reset"); axes[3].legend()
    for ax in axes:
        ax.axvline(4.825, color="crimson", ls=":"); ax.grid(alpha=.25)
    fig.suptitle("Recorded 91000 / impratio 10: gate changes and three policy pathways\nOpen-loop probe magnitudes are not fractions of physical jitter")
    fig.tight_layout(); fig.savefig(out / "gate_pathways.png", dpi=140); plt.close(fig)
    fig, axes = plt.subplots(3, 1, figsize=(11, 11))
    for lo, hi, name in intervals[:4]:
        mask = (elapsed >= lo - 1e-8) & (elapsed < hi - 1e-8); pm = mask & d["policy_tick"]
        for ax, key, fs, conversion in [(axes[0], "q", 200, 180 / np.pi), (axes[1], "target", 50, 180 / np.pi), (axes[2], "gates", 50, 1)]:
            values = d[key][mask if key == "q" else pm] * conversion
            f, power = psd(values, fs); ax.semilogy(f, power.mean(1), label=name)
    for ax, ylabel, xmax in zip(axes, ("Joint position PSD (deg²/Hz)", "Policy target PSD (deg²/Hz)", "Gate-weight PSD (1/Hz)"), (60, 25, 25)):
        ax.set(xlim=(0, xmax), xlabel="Frequency (Hz)", ylabel=ylabel); ax.legend(); ax.grid(alpha=.25)
    axes[0].axvline(50, color="gray", ls=":")
    fig.suptitle("Contiguous recorded phases; policy/gate spectra stay below 25 Hz Nyquist")
    fig.tight_layout(); fig.savefig(out / "frequency_phases.png", dpi=140); plt.close(fig)
    print(json.dumps(dict(output=str(out), action_replay_error=result["replay_max_abs_action_error"],
                          gate_replay_error=result["replay_max_abs_gate_error"],
                          september_raw_rechecks=len(september["raw_filter_rechecks"]),
                          traversal=[dict(attempt=x["attempt"], **x["traversal_recheck"]) for x in timing]), indent=2))


if __name__ == "__main__":
    main()
