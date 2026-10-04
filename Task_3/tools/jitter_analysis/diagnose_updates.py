"""Offline command/update/gate diagnostics from actual interactive recordings.

No simulation, training, action smoothing or gate modification is performed.
Optional network replay verifies the recorded checkpoint before decomposing
one-step raw-action changes. Decomposition is not a closed-loop causal test.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import welch

from analyze import band_rms, save_json
from plot_interactive import load_attempt

ROOT = Path(__file__).resolve().parents[2]


def steady_windows(t, command, contact):
    """Contiguous constant commands, separated at contact; never join gaps."""
    changes = np.flatnonzero(np.any(np.abs(np.diff(command, axis=0)) > 1e-8, axis=1)) + 1
    edges = set([0, len(t), *changes.tolist()])
    if contact is not None:
        edges.add(int(np.searchsorted(t, contact)))
    edges = sorted(edges)
    windows = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        if hi - lo < 400:  # >=2 s at the validated 200 Hz measurement rate
            continue
        end = min(hi, lo + 4000)  # inspect up to 20 s, without spanning command changes
        moving = np.linalg.norm(command[lo]) > .01
        phase = "before contact" if contact is None or t[lo] < contact else "after contact"
        windows.append((lo, end, f"{phase}, {'moving' if moving else 'zero command'}"))
    return windows


def replay(m, d, device):
    """Replay exact five-frame inputs, then symmetric latent-factor ablations."""
    import torch
    from torch.nn import functional as F
    sys.path.insert(0, str(ROOT / "xterra_mjlab/svanm2_moe_stair_sim"))
    from checkpoint_policy import load_checkpoint_policy

    path = Path(m["checkpoint"])
    if not path.is_file():
        return None, {"available": False, "reason": "Recorded checkpoint path unavailable; no substitution."}
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != m["checkpoint_sha256"]:
        raise ValueError("Checkpoint changed since recording; refusing to replay different weights")
    if "obs_policy" not in d:
        return None, {"available": False, "reason": "Actual policy frames were not recorded."}
    torch.set_num_threads(1)
    model, update = load_checkpoint_policy(path, device)
    ix = np.flatnonzero(d["policy_tick"])
    frames = d["obs_policy"][ix].astype(np.float32)
    history_ix = np.maximum(np.arange(len(ix))[:, None] + np.arange(-4, 1), 0)
    histories = frames[history_ix].reshape(-1, 225)
    output = []
    features = []
    weights = []
    with torch.inference_mode():
        for lo in range(0, len(ix), 256):
            h = torch.as_tensor(histories[lo:lo + 256], device=device)
            f = model.student_moe_encoder.moe.experts(h)
            w = model.student_moe_encoder.moe.gating_network(h)
            latent = F.normalize((w[..., None] * f).sum(1), p=2, dim=-1, eps=1e-12)
            output.append(model.actor(torch.cat([latent, h[:, -45:]], 1)).cpu().numpy())
            features.append(f.cpu().numpy())
            weights.append(w.cpu().numpy())
    actual, f, w = np.concatenate(output), np.concatenate(features), np.concatenate(weights)
    action_error = float(np.max(np.abs(actual - d["raw_action"][ix])))
    gate_error = float(np.max(np.abs(w - d["gates"][ix])))
    # Batched GEMM and recorded batch-of-one GEMV can round differently, most
    # visibly in very large raw outputs which are subsequently clipped anyway.
    # Require both relative raw agreement and absolute agreement after clipping.
    raw_ok = np.allclose(actual, d["raw_action"][ix], atol=1e-4, rtol=1e-5)
    clipped_error = float(np.max(np.abs(np.clip(actual,-6,6)-d["action"][ix])))
    if not raw_ok or clipped_error > 1e-4 or gate_error > 1e-4:
        raise ValueError(f"Replay mismatch: actions={action_error}, gates={gate_error}; do not interpret decomposition")
    contributions = {name: [] for name in ("gate", "experts", "latest_frame")}
    with torch.inference_mode():
        for lo in range(1, len(ix), 256):
            hi = min(len(ix), lo + 256)
            prev_w = torch.as_tensor(w[lo - 1:hi - 1], device=device)
            now_w = torch.as_tensor(w[lo:hi], device=device)
            prev_f = torch.as_tensor(f[lo - 1:hi - 1], device=device)
            now_f = torch.as_tensor(f[lo:hi], device=device)
            frame = torch.as_tensor(frames[lo:hi], device=device)
            def actor(ww, ff):
                latent = F.normalize((ww[..., None] * ff).sum(1), p=2, dim=-1, eps=1e-12)
                return model.actor(torch.cat([latent, frame], 1)).cpu().numpy()
            y00 = actor(prev_w, prev_f)
            y10 = actor(now_w, prev_f)
            y01 = actor(prev_w, now_f)
            y11 = actual[lo:hi]
            contributions["gate"].append(.5 * ((y10 - y00) + (y11 - y01)))
            contributions["experts"].append(.5 * ((y01 - y00) + (y11 - y10)))
            contributions["latest_frame"].append(y00 - actual[lo - 1:hi - 1])
    contributions = {k: np.concatenate(v) for k, v in contributions.items()}
    residual = float(np.max(np.abs(sum(contributions.values()) - np.diff(actual, axis=0))))
    if residual > 1e-4:
        raise ValueError("Raw-action decomposition failed its additive check")
    return contributions, dict(available=True, update=int(update), checkpoint_sha256=digest,
        replay_max_action_error=action_error, replay_max_gate_error=gate_error,
        replay_max_clipped_action_error=clipped_error, raw_tolerance="atol=1e-4, rtol=1e-5; clipped atol=1e-4",
        decomposition_max_residual=residual,
        meaning="Symmetric contributions of gate/experts at current latest frame, plus latest-frame change at previous latent. Raw outputs before clipping. Contributions can cancel; not percentages or closed-loop causality.")


def diagnose(path, device="cpu"):
    path = Path(path).resolve()
    m, status, d = load_attempt(path)
    if d is None:
        return dict(attempt=str(path), samples=0)
    if not np.isclose(m["dt"], .005) or m["decimation"] != 4:
        raise ValueError("This diagnostic currently requires the recorded 200 Hz / 50 Hz contract")
    t = d["time"] - m["start_sim_time"]
    ix = np.flatnonzero(d["policy_tick"])
    if len(ix) < 2:
        return dict(attempt=str(path), samples=len(t), note="Too short for update diagnostics")
    if not np.allclose(np.diff(t[ix]), .02, atol=1e-8):
        raise ValueError("Policy ticks are not uniform; cannot interpret a nominal 50 Hz spectrum")
    contact = status.get("first_riser_contact_s")
    contact = None if contact is None else contact - m["start_sim_time"]
    windows = steady_windows(t, d["command"], contact)
    contributions, replay_info = replay(m, d, device)
    gate_change = np.linalg.norm(np.diff(d["gates"][ix], axis=0), axis=1)
    target_rate = np.diff(d["target"][ix], axis=0) / .02
    target_step = np.linalg.norm(np.degrees(np.diff(d["target"][ix], axis=0)), axis=1)
    rows = []
    torque_limits = np.asarray(m["torque_limits"])
    for lo, hi, label in windows:
        sel = (ix >= lo) & (ix < hi)
        diff_sel = sel[1:] & sel[:-1]
        q = band_rms(np.degrees(d["q"][lo:hi]), 200)
        q_update_band = band_rms(np.degrees(d["q"][lo:hi]), 200,45,55)
        target = band_rms(np.degrees(d["target"][ix[sel]]), 50, 8, 20)
        freq, power = welch(np.degrees(d["q"][lo:hi]), fs=200, axis=0,
                            nperseg=min(400, hi-lo), detrend="linear")
        valid = (freq >= 8) & (freq <= 80)
        peak = float(freq[valid][np.argmax(power[valid].mean(1))])
        clipped = np.abs(d["torque_raw"][lo:hi]) > torque_limits + 1e-5
        row = dict(start_s=float(t[lo]), stop_s=float(t[hi-1]+.005), label=label,
            command=d["command"][lo].tolist(), mean_body_vx=float(d["base_velocity_body"][lo:hi, 0].mean()),
            mean_body_vy=float(d["base_velocity_body"][lo:hi, 1].mean()),
            vy_tracking_rmse_m_s=float(np.sqrt(np.mean((d["command"][lo:hi,1]-d["base_velocity_body"][lo:hi,1])**2))),
            yaw_rate_tracking_rmse_rad_s=float(np.sqrt(np.mean((d["command"][lo:hi,2]-d["angular_velocity_body"][lo:hi,2])**2))),
            q_8_30_hz_rms_deg=None if q is None else float(q.mean()),
            q_45_55_hz_rms_deg=None if q_update_band is None else float(q_update_band.mean()),
            target_8_20_hz_rms_deg=None if target is None else float(target.mean()),
            largest_mean_q_psd_frequency_8_80_hz=peak,
            gate_change_mean=float(gate_change[diff_sel].mean()),
            gate_change_p99=float(np.quantile(gate_change[diff_sel], .99)),
            gate_argmax_change_fraction=float(np.mean(np.argmax(d["gates"][ix[1:][diff_sel]],1) != np.argmax(d["gates"][ix[:-1][diff_sel]],1))),
            tracking_rms_deg_per_joint=np.sqrt(np.mean(np.degrees(d["target"][lo:hi]-d["q"][lo:hi])**2,0)).tolist(),
            torque_clipped_any_sample_fraction=float(clipped.any(1).mean()),
            torque_clipped_per_joint=clipped.mean(0).tolist(), max_tilt_deg=float(d["tilt_deg"][lo:hi].max()))
        if contributions:
            row["raw_action_change_rms"] = {k: float(np.sqrt(np.mean(v[diff_sel]**2))) for k,v in contributions.items()}
        rows.append(row)
    held_changes = np.any(np.abs(np.diff(d["target"], axis=0)) > 1e-7, axis=1)
    off_tick_changes = int(np.sum(held_changes & ~d["policy_tick"][1:]))
    ci = None if contact is None else int(np.argmin(np.abs(t-contact)))
    peak_i, peak_j = np.unravel_index(np.argmax(np.abs(d["torque_raw"])),d["torque_raw"].shape)
    # Independent reconstruction of this recorded controller's coupled P/D law.
    # This separates commanded torque terms, not unknown real motor dynamics.
    transmission=np.kron(np.eye(4),np.asarray(m["transmission"]))
    gear=np.diag(transmission)
    tau_p=(((d["target"]-d["q"])@transmission.T)*(m["kp"]/gear**2))@transmission
    tau_d=((-d["dq"]@transmission.T)*(m["kd"]/gear**2))@transmission
    pd_error=float(np.max(np.abs(tau_p+tau_d-d["torque_raw"])))
    if pd_error>1e-4:
        raise ValueError("P/D reconstruction does not match the recorded controller")
    result = dict(attempt=str(path), samples=len(t), duration_s=float(t[-1]),
        checkpoint=m["checkpoint"], checkpoint_update=m["checkpoint_update"],
        checkpoint_sha256=m["checkpoint_sha256"], observation_timing=m.get("observation_timing","legacy"),
        policy_hz=50, measurement_hz=200, targets_changed_outside_policy_tick=off_tick_changes,
        first_riser_contact_s=contact, windows=rows, replay=replay_info,
        first_contact=None if ci is None else dict(foot_riser_force=d["foot_riser_force"][ci].tolist(),
            foot_center_z=d["foot_pos"][ci,:,2].tolist(), target_removed=d["target_removed"][ci].tolist(),torque_raw=d["torque_raw"][ci].tolist()),
        peak_raw_torque=dict(t=float(t[peak_i]),joint=m["joint_names"][peak_j],raw_nm=float(d["torque_raw"][peak_i,peak_j]),
            applied_nm=float(d["torque_applied"][peak_i,peak_j]),dq_rad_s=float(d["dq"][peak_i,peak_j]),
            position_term_nm=float(tau_p[peak_i,peak_j]),damping_term_nm=float(tau_d[peak_i,peak_j])),
        pd_reconstruction_max_error_nm=pd_error,
        max_base_x=float(d["base_pos"][:,0].max()),max_tilt=float(d["tilt_deg"].max()),
        final_position=d["base_pos"][-1].tolist(),final_heading_deg=float(np.degrees(d["yaw_rad"][-1])),
        final_nonfoot_contact_n=float(d["nonfoot_contact_force"][-1]),
        platform_force_max_per_foot=d["foot_platform_force"].max(0).tolist(),
        caveats=["Manual commands, terrain and gait differ between windows/attempts; no causal attribution from correlation.",
            "Argmax labels summarize dense soft weights; the controller never routes only to argmax.",
            "Gate data have 25 Hz Nyquist; spectra are restricted below it. Held targets have sample/hold artifacts.",
            "Measured q has 100 Hz Nyquist; 50 Hz target updates do not establish a 50 Hz vibration.",
            "Simulation torques and contact forces are model outputs, not measured physical actuator behavior."])
    plots = path/"plots"
    plots.mkdir(exist_ok=True)
    def save(fig,name):
        fig.tight_layout();fig.savefig(plots/name,dpi=120);plt.close(fig)
    def mark(ax):
        if contact is not None: ax.axvline(contact,color="crimson",ls=":",label="first riser contact")
        ax.grid(alpha=.2)
    fig,axs=plt.subplots(5,1,figsize=(12,11),sharex=True)
    axs[0].step(t,d["command"][:,0],where="post",color="black",label="requested vx (policy input)")
    axs[0].plot(t,d["base_velocity_body"][:,0],label="actual body vx",lw=.7)
    axs[0].set_ylabel("Speed (m/s)");axs[0].legend()
    axs[1].step(t,d["command"][:,1],where="post",color="black",label="requested vy")
    axs[1].plot(t,d["base_velocity_body"][:,1],label="actual body vy",lw=.7)
    axs[1].set_ylabel("Sideways speed (m/s)");axs[1].legend()
    axs[2].step(t,d["command"][:,2],where="post",color="black",label="requested yaw rate")
    axs[2].plot(t,d["angular_velocity_body"][:,2],label="actual body angular z",lw=.7)
    axs[2].set_ylabel("Turning rate (rad/s)");axs[2].legend()
    axs[3].plot(t[ix[1:]],np.max(np.abs(target_rate),axis=1),lw=.7)
    axs[3].set_ylabel("Max target step / 20 ms\n(rad/s)")
    axs[4].plot(t,np.linalg.norm(d["torque_raw"]-d["torque_applied"],axis=1),lw=.7)
    axs[4].set_ylabel("Torque removed (L2 Nm)");axs[4].set_xlabel("Seconds since this reset")
    for ax in axs:mark(ax)
    fig.suptitle("Keyboard request, commanded target changes, and torque limiting")
    save(fig,"04_updates.png")
    fig,axs=plt.subplots(3,1,figsize=(12,9),sharex=True)
    for j in range(8):axs[0].plot(t[ix],d["gates"][ix,j],label=f"expert {j+1}",lw=.7)
    axs[0].set_ylabel("Soft mixture weight");axs[0].legend(ncol=8,fontsize=7)
    axs[1].plot(t[ix[1:]],gate_change,label="gate change L2",lw=.7)
    axs[1].set_ylabel("Gate change / update")
    if contributions:
        for name,v in contributions.items():axs[2].plot(t[ix[1:]],np.sqrt(np.mean(v**2,axis=1)),label=name,lw=.7)
        axs[2].legend();axs[2].set_ylabel("Contribution RMS\nto raw action change")
    else:axs[2].text(.1,.5,replay_info["reason"],transform=axs[2].transAxes)
    for ax in axs:mark(ax)
    axs[2].set_xlabel("Seconds since this reset");fig.suptitle("Recorded gates and verified offline raw-action decomposition (not causality)")
    save(fig,"05_gates.png")
    # Distinct phases, never concatenate standing/walking or pre/post contact.
    selected=[]
    for label in dict.fromkeys(w[2] for w in windows):
        candidates=[w for w in windows if w[2]==label]
        selected.append(max(candidates,key=lambda w:w[1]-w[0]))
    selected=selected[:4]
    if selected:
        fig,axs=plt.subplots(len(selected),2,figsize=(12,3.2*len(selected)),squeeze=False)
        for r,(lo,hi,label) in enumerate(selected):
            freq,power=welch(np.degrees(d["q"][lo:hi]),fs=200,axis=0,nperseg=min(400,hi-lo),detrend="linear")
            held,pheld=welch(np.degrees(d["target"][lo:hi]),fs=200,axis=0,nperseg=min(400,hi-lo),detrend="linear")
            axs[r,0].semilogy(freq,np.maximum(power.mean(1),1e-18),label="measured joint q")
            axs[r,0].semilogy(held,np.maximum(pheld.mean(1),1e-18),alpha=.6,label="held commanded targets")
            axs[r,0].axvline(50,color="black",ls=":",label="policy update rate");axs[r,0].set_xlim(0,90)
            axs[r,0].set_ylabel("PSD (deg²/Hz)");axs[r,0].legend(fontsize=7)
            pi=ix[(ix>=lo)&(ix<hi)]
            gf,gp=welch(d["gates"][pi],fs=50,axis=0,nperseg=min(100,len(pi)),detrend="linear")
            mask=gf<25
            axs[r,1].semilogy(gf[mask],np.maximum(gp[mask].mean(1),1e-18),label="mean of eight gate PSDs")
            axs[r,1].set_xlim(0,24.5);axs[r,1].set_ylabel("Gate PSD (weight²/Hz)")
            for ax in axs[r]:ax.set_title(f"{label}: {t[lo]:.2f}–{t[hi-1]+.005:.2f} s");ax.grid(alpha=.2);ax.set_xlabel("Frequency (Hz)")
        fig.suptitle("Frequency content within constant-command intervals; sample/hold ≠ proof of vibration")
        save(fig,"06_frequency.png")
    # Per-joint signals avoid the changing-joint maximum in the existing overview.
    center=contact if contact is not None else float(t[np.argmax(np.linalg.norm(np.diff(d["target"],axis=0),axis=1))+1])
    mask=(t>=max(0,center-1))&(t<=center+3)
    fig,axs=plt.subplots(3,1,figsize=(12,8),sharex=True)
    for j in (3,4,5):
        axs[0].plot(t[mask],np.degrees(d["target"][mask,j]),ls="--",label=m["joint_names"][j]+" target")
        axs[0].plot(t[mask],np.degrees(d["q"][mask,j]),label=m["joint_names"][j]+" measured")
        axs[1].plot(t[mask],d["torque_raw"][mask,j],ls="--",label=m["joint_names"][j]+" raw")
        axs[1].plot(t[mask],d["torque_applied"][mask,j],label=m["joint_names"][j]+" applied")
    for j,name in enumerate(("FL","FR","RL","RR")):axs[2].plot(t[mask],d["foot_riser_force"][mask,j],label=name)
    for ax in axs:mark(ax);ax.legend(fontsize=7,ncol=2)
    axs[0].set_ylabel("FR joint angles (deg)");axs[1].set_ylabel("FR torques (Nm)");axs[2].set_ylabel("Riser contact (N)")
    axs[2].set_xlabel("Seconds since this reset");save(fig,"07_actuator_event.png")
    fig,axs=plt.subplots(2,1,figsize=(12,6),sharex=True)
    mask=(t>=max(0,t[peak_i]-1))&(t<=t[peak_i]+1)
    for arr,label in ((tau_p,"position-error term"),(tau_d,"velocity/damping term"),(d["torque_raw"],"raw total"),(d["torque_applied"],"applied after clamp")):
        axs[0].plot(t[mask],arr[mask,peak_j],label=label,lw=1)
    axs[0].legend(fontsize=8);axs[0].set_ylabel("Joint torque (Nm)")
    axs[1].plot(t[mask],d["dq"][mask,peak_j],label="measured simulated joint velocity")
    axs[1].set_ylabel("Velocity (rad/s)");axs[1].set_xlabel("Seconds since this reset")
    for ax in axs:ax.grid(alpha=.2);ax.axvline(t[peak_i],color="crimson",ls=":")
    fig.suptitle(f"Largest raw torque: {m['joint_names'][peak_j]}; P/D terms reconstructed and verified")
    save(fig,"08_pd_terms.png")
    save_json(plots/"update_diagnostics.json",result)
    rows_html="".join(f"<tr><td>{r['label']}</td><td>{r['start_s']:.2f}–{r['stop_s']:.2f}</td><td>{r['command']}</td><td>{r['q_8_30_hz_rms_deg']:.4g}</td><td>{r['gate_change_mean']:.4g}</td><td>{100*r['torque_clipped_any_sample_fraction']:.1f}%</td></tr>" for r in rows)
    figures="".join(f'<h2>{name}</h2><img src="{name}">' for name in ["04_updates.png","05_gates.png","06_frequency.png","07_actuator_event.png","08_pd_terms.png"] if (plots/name).exists())
    page=f'''<!doctype html><meta charset="utf-8"><title>Update and gate diagnosis</title><style>body{{font:16px system-ui;max-width:1100px;margin:24px auto;line-height:1.5}}img{{width:100%}}td,th{{padding:8px;border:1px solid #ddd}}table{{border-collapse:collapse}}</style>
<h1>{html.escape(path.parent.name)}/{html.escape(path.name)}: update and gate diagnosis</h1>
<p>Actual saved trajectory. No simulation or training was executed. Checkpoint {m['checkpoint_update']}, hash {m['checkpoint_sha256']}.</p>
<p>Command vx is supplied by your keys, not chosen by the policy. The policy chooses 12 joint actions. Every key changes the latched request; Space stops immediately. Blue actual speed need not follow that request exactly.</p>
<p>Targets update at 50 Hz and are held during four 200 Hz physics steps. This is normal sampled control. A measured spectral peak, plus a controlled intervention, is needed to blame the hold. Gate weights update at 50 Hz and blend all eight latent experts; argmax changes do not imply hard routing.</p>
<p>Gate plots show recorded weights. The offline replay must match the recorded weights/actions. The decomposition splits raw-action changes among gate, expert features and latest actor frame, with interactions shared symmetrically. Factors can cancel and are not percentages, physical target changes or a closed-loop proof.</p>
<p>Compare intervals with constant requests. Different commands/gaits/terrain still confound comparisons. Gate spectra stop below 25 Hz. Held-target spectra contain sampling artifacts. Simulated joint torque is not hardware current, temperature or measured motor torque.</p>
<table><tr><th>Phase</th><th>Seconds</th><th>Constant command</th><th>q 8–30 Hz RMS, deg</th><th>Mean gate change</th><th>Any joint torque clipped</th></tr>{rows_html}</table>
<p><a href="update_diagnostics.json">Full metrics and replay verification</a> · <a href="index.html">Original plots</a></p>{figures}'''
    (plots/"update_diagnostics.html").write_text(page)
    original=plots/"index.html"
    if original.exists() and "update_diagnostics.html" not in original.read_text():
        original.write_text(original.read_text()+'<p><a href="update_diagnostics.html">New: keyboard command explanation, update frequencies, gate decomposition and actuator event</a></p>')
    print(path, "replay",replay_info.get("replay_max_action_error"), "steady windows",len(rows),flush=True)
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument("paths",nargs="+",type=Path,help="Interactive attempt or session directories")
    parser.add_argument("--device",default="cpu",help="Offline network replay device; never runs physics")
    parser.add_argument("--out",type=Path,help="Optional combined dashboard directory")
    args=parser.parse_args()
    paths=[]
    for path in args.paths:
        paths.extend([path] if path.name.startswith("attempt_") else sorted(path.glob("attempt_*")))
    results=[diagnose(path,args.device) for path in paths]
    if args.out:
        args.out.mkdir(parents=True,exist_ok=True)
        save_json(args.out/"summary.json",results)
        import os
        links="".join(f'<li><a href="{html.escape(os.path.relpath(Path(r["attempt"])/"plots/update_diagnostics.html",args.out))}">{html.escape(str(Path(r["attempt"]).relative_to(ROOT)))}</a></li>' for r in results)
        (args.out/"index.html").write_text('<!doctype html><meta charset="utf-8"><h1>Recorded update and gate diagnostics</h1><p>Separate checkpoints and manual command histories. No new trajectories or training.</p><ul>'+links+'</ul>')
