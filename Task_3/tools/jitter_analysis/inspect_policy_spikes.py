"""Read-only policy input probes and spike plots for recorded user attempts.

Probes change one input branch for one inference only, on the recorded state.
They do not roll out a modified controller or prove a physical root cause.
Raw chunks, checkpoints and runtime controller files are never written.
"""
from __future__ import annotations

import argparse
import hashlib
import html
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
from torch.nn import functional as F
from scipy.signal import welch

from analyze import band_rms, save_json
from diagnose_updates import ROOT, replay, steady_windows
from plot_interactive import load_attempt


GROUPS = {"command": slice(0, 3), "gyro": slice(3, 6),
          "gravity": slice(6, 9), "joint_position": slice(9, 21),
          "joint_velocity": slice(21, 33), "previous_action": slice(33, 45)}


def inspect(path, device, reference_checkpoint=None):
    path = Path(path).resolve()
    m, status, d = load_attempt(path)
    if d is None or np.count_nonzero(d["policy_tick"]) < 2:
        raise ValueError("Need at least two recorded policy updates")
    # Includes checkpoint SHA, exact-history replay and additive checks.
    _, verification = replay(m, d, device)
    if not verification.get("available"):
        raise ValueError(verification["reason"])
    sys.path.insert(0, str(ROOT / "xterra_mjlab/svanm2_moe_stair_sim"))
    from checkpoint_policy import load_checkpoint_policy
    model, _ = load_checkpoint_policy(Path(m["checkpoint"]), device)
    ix = np.flatnonzero(d["policy_tick"])
    if not np.isclose(m["dt"], .005) or m["decimation"] != 4 or not np.allclose(np.diff(d["time"][ix]), .02, atol=1e-8):
        raise ValueError("Require recorded 200 Hz measurements and uniform 50 Hz policy ticks")
    frame = d["obs_policy"][ix].astype(np.float32)
    hi = np.maximum(np.arange(len(ix))[:, None] + np.arange(-4, 1), 0)
    h = torch.as_tensor(frame[hi].reshape(-1, 225), device=device)
    q0, scale = np.asarray(m["q0"]), np.asarray(m["scale"])
    lower, upper = np.asarray(m["target_min"]), np.asarray(m["target_max"])
    def targets(a):
        return np.clip(q0 + scale * np.clip(a, -6, 6), lower, upper)
    reference = None
    reference_info = None
    if reference_checkpoint is not None:
        reference_checkpoint=reference_checkpoint.expanduser().resolve()
        refmodel,refupdate=load_checkpoint_policy(reference_checkpoint,device)
        outputs=[]
        with torch.inference_mode():
            for lo in range(0,len(h),256):outputs.append(refmodel(h[lo:lo+256]).cpu().numpy())
        reference=np.concatenate(outputs)
        reference_info=dict(checkpoint=str(reference_checkpoint),update=int(refupdate),
            sha256=hashlib.sha256(reference_checkpoint.read_bytes()).hexdigest(),
            meaning="Reference weights on candidate's recorded observation/history, including candidate's previous actions. Not reference's own trajectory, stability, tracking or stair-success estimate.")
    # Keep batches modest for laptop GPUs.
    differences = {name: [] for name in [*GROUPS, "gate", "expert_features"]}
    latent_norms = []
    with torch.inference_mode():
        for lo in range(1, len(ix), 256):
            end = min(lo + 256, len(ix))
            hist, prev = h[lo:end], h[lo-1:end-1]
            w = model.student_moe_encoder.moe.gating_network(hist)
            wp = model.student_moe_encoder.moe.gating_network(prev)
            f = model.student_moe_encoder.moe.experts(hist)
            fp = model.student_moe_encoder.moe.experts(prev)
            weighted = (w[..., None] * f).sum(1)
            latent_norms.append(weighted.norm(dim=1).cpu().numpy())
            latent = F.normalize(weighted, dim=1, eps=1e-12)
            latest, previous = hist[:, -45:], prev[:, -45:]
            actual = model.actor(torch.cat([latent, latest], 1)).cpu().numpy()
            actual_target = targets(actual)
            if np.max(abs(actual_target-d["target"][ix[lo:end]])) > 1e-4:
                raise ValueError("Mapped replay targets disagree with recorded targets")
            for name, sl in GROUPS.items():
                hybrid = latest.clone()
                hybrid[:, sl] = previous[:, sl]
                alternative = model.actor(torch.cat([latent, hybrid], 1)).cpu().numpy()
                differences[name].append(actual_target-targets(alternative))
            for name, ww, ff in [("gate", wp, f), ("expert_features", w, fp)]:
                ll = F.normalize((ww[..., None] * ff).sum(1), dim=1, eps=1e-12)
                alternative = model.actor(torch.cat([ll, latest], 1)).cpu().numpy()
                differences[name].append(actual_target-targets(alternative))
    differences = {k: np.concatenate(v) for k,v in differences.items()}
    latent_norms = np.concatenate(latent_norms)
    t = d["time"]-m["start_sim_time"]
    contact = status["first_riser_contact_s"]
    if contact is not None: contact -= m["start_sim_time"]
    rows = []
    for lo, end, label in steady_windows(t, d["command"], contact):
        mask = (ix[1:] >= lo) & (ix[1:] < end) & (ix[:-1] >= lo)
        p = ix[(ix >= lo) & (ix < end)]
        target_step = np.diff(d["target"][p], axis=0)
        v = d["base_velocity_body"][lo:end]
        vrms = band_rms(v, 200)
        freq, psd = welch(v, fs=200, nperseg=min(400,len(v)), axis=0, detrend="linear")
        low = (freq >= .5) & (freq < 8)
        peak = (freq >= .5) & (freq <= 30)
        row = dict(start_s=float(t[lo]), stop_s=float(t[end-1]+m["dt"]),
            command=d["command"][lo].tolist(), phase=label,
            lateral_outside_saved_training_range=bool(abs(d["command"][lo,1])>.300001),
            body_velocity_min=v.min(0).tolist(), body_velocity_max=v.max(0).tolist(),
            body_velocity_8_30_hz_rms_m_s=None if vrms is None else vrms.tolist(),
            body_velocity_0_5_to_8_hz_rms_m_s=np.sqrt(np.trapezoid(psd[low],freq[low],axis=0)).tolist(),
            body_velocity_peak_0_5_to_30_hz=freq[peak][np.argmax(psd[peak],axis=0)].tolist(),
            raw_action_abs_max=float(abs(d["raw_action"][p]).max()),
            raw_action_clipped_fraction=float((abs(d["raw_action"][p])>6).mean()),
            max_target_step_deg=float(np.degrees(abs(target_step).max())),
            mean_normalized_target_second_difference_cost=float(np.square(np.diff(d["target"][p],n=2,axis=0)/scale).sum(1).mean()),
            input_branch_hold_probe_target_rms_deg={k:float(np.sqrt(np.mean(np.degrees(vv[mask])**2))) for k,vv in differences.items()},
            latent_pre_normalization_norm_min=float(latent_norms[mask].min()),
            measured_dq_abs_max_rad_s=float(abs(d["dq"][lo:end]).max()),
            max_summed_foot_normal_force_n=float(d["foot_normal_force"][lo:end].sum(1).max()))
        rows.append(row)
        if reference is not None:
            sel_ref=(ix>=lo)&(ix<end)
            row["reference_same_recorded_input_raw_action_abs_max"]=float(abs(reference[sel_ref]).max())
            row["reference_same_recorded_input_raw_clipped_fraction"]=float((abs(reference[sel_ref])>6).mean())
    result = dict(attempt=str(path), verification=verification, windows=rows,
        reference_same_inputs=reference_info,
        interpretation="One-step leave-one-branch-at-previous-value target probes. Current latent is held for actor-input probes; gate/features probes keep the other factors current. Nonlinear/clipped contributions interact and do not add. These are sensitivity measures, not causal vibration percentages or predicted rollout outcomes.")
    # A two-second view of the largest speed change within a constant motion
    # request, away from keyboard transitions. Display state before a step and
    # forces applied over that step; velocity difference belongs to its end.
    dv = np.diff(d["base_velocity_body"][:, :2], axis=0)
    eligible = np.zeros(len(dv), dtype=bool)
    for lo,end,_ in steady_windows(t,d["command"],contact):
        if np.linalg.norm(d["command"][lo])>.01:
            eligible[lo+50:max(lo+50,end-50)] = True
    if not eligible.any():
        raise ValueError("No steady moving window for a spike plot")
    event = int(np.argmax(np.where(eligible,np.linalg.norm(dv,axis=1),-1)))
    centre = float(t[event])
    sel = (t >= centre-1) & (t <= centre+1)
    ticks = ix[(t[ix]>=centre-1)&(t[ix]<=centre+1)]
    j = int(np.argmax(np.std(d["target"][sel],axis=0)))
    result["spike_event"] = dict(start_of_force_interval_s=centre,
        velocity_before=d["base_velocity_body"][event].tolist(),
        velocity_after=d["base_velocity_body"][event+1].tolist(),
        command=d["command"][event].tolist(), displayed_joint=m["joint_names"][j],
        foot_force_n=d["foot_normal_force"][event].tolist(),
        nonfoot_contact_force_n=float(d["nonfoot_contact_force"][event]),
        policy_tick=bool(d["policy_tick"][event]))
    fig,axs=plt.subplots(6,1,figsize=(13,14),sharex=True)
    for k,name in enumerate(["vx","vy"]):
        axs[0].plot(t[sel],d["base_velocity_body"][sel,k],label="actual "+name)
        axs[0].plot(t[sel],d["command"][sel,k],ls="--",label="requested "+name)
    axs[0].set_ylabel("Speed (m/s)")
    for k,leg in enumerate(["FL","FR","RL","RR"]):
        axs[1].plot(t[sel],d["foot_normal_force"][sel,k],label=leg,lw=.8)
    axs[1].plot(t[sel],d["nonfoot_contact_force"][sel],color="black",label="non-foot collision",lw=.8)
    axs[1].set_ylabel("Foot normal force (N)")
    axs[2].step(t[ticks],np.degrees(d["target"][ticks,j]),where="post",label="commanded target")
    axs[2].plot(t[sel],np.degrees(d["q"][sel,j]),label="actual joint angle")
    axs[2].set_ylabel(m["joint_names"][j]+"\nAngle (deg)")
    axs[3].plot(t[sel],d["torque_raw"][sel,j],label="requested PD torque")
    axs[3].plot(t[sel],d["torque_applied"][sel,j],label="applied torque")
    axs[3].set_ylabel("Torque (Nm)")
    for k in range(8):axs[4].plot(t[ticks],d["gates"][ticks,k],lw=.8,label=f"expert {k+1}")
    axs[4].set_ylabel("Gate weights")
    di=np.flatnonzero((t[ix[1:]]>=centre-1)&(t[ix[1:]]<=centre+1))
    for name in ["joint_velocity","joint_position","previous_action","gate","expert_features"]:
        axs[5].plot(t[ix[1:][di]],np.sqrt(np.mean(np.degrees(differences[name][di])**2,axis=1)),label=name)
    axs[5].set_ylabel("One-step branch probe\ntarget RMS (deg)");axs[5].set_xlabel("Seconds since reset")
    for ax in axs:
        ax.axvline(centre,color="crimson",ls=":")
        ax.grid(alpha=.2);ax.legend(fontsize=8,ncol=4)
    fig.suptitle("Actual recorded speed spike, forces, targets and policy sensitivity; no altered rollout")
    fig.tight_layout()
    plots=path/"plots";plots.mkdir(exist_ok=True)
    fig.savefig(plots/"09_spike_chain.png",dpi=125);plt.close(fig)
    # Focus on the earliest ordinary moving window and largest joint-target
    # jump window. Display every probe, including the previous-action input.
    moving=[r for r in rows if np.linalg.norm(r["command"])>.01]
    focus=[moving[0],max(moving,key=lambda r:r["max_target_step_deg"])]
    if focus[0] is focus[1]:focus=focus[:1]
    fig,axs=plt.subplots(len(focus),2,figsize=(13,4*len(focus)),squeeze=False)
    for n,r in enumerate(focus):
        ax=axs[n,0]; probes=r["input_branch_hold_probe_target_rms_deg"]
        names=list(probes);ax.barh(names,[probes[k] for k in names]);ax.invert_yaxis()
        ax.set_xlabel("One-step target sensitivity RMS (degrees), all frequencies")
        ax.set_title(f'{r["start_s"]:.2f}–{r["stop_s"]:.2f}s, command {r["command"]}')
        sel2=(t>=r["start_s"]-1e-8)&(t<r["stop_s"]-1e-8)
        ff,pp=welch(d["base_velocity_body"][sel2],fs=200,nperseg=min(400,sel2.sum()),axis=0,detrend="linear")
        ax=axs[n,1]
        for k,name in enumerate(["vx","vy","vz"]):ax.semilogy(ff,np.maximum(pp[:,k],1e-16),label=name)
        ax.axvspan(8,30,alpha=.1,color="red",label="8–30 Hz diagnostic band")
        ax.set_xlim(0,60);ax.set_ylabel("Velocity PSD ((m/s)²/Hz)");ax.set_xlabel("Frequency (Hz)");ax.legend()
        ax.grid(alpha=.2)
    fig.suptitle("Policy sensitivity is not a causal percentage; speed spikes are not all high-frequency jitter")
    fig.tight_layout();fig.savefig(plots/"10_policy_probes.png",dpi=125);plt.close(fig)
    save_json(plots/"policy_spike_review.json",result)
    tab="".join(f'<tr><td>{r["start_s"]:.2f}–{r["stop_s"]:.2f}</td><td>{r["command"]}</td><td>{r["max_target_step_deg"]:.2f}</td><td>{html.escape(str({k:round(v,3) for k,v in r["input_branch_hold_probe_target_rms_deg"].items()}))}</td></tr>' for r in rows)
    page=f'''<!doctype html><meta charset="utf-8"><title>Policy spike review</title>
<style>body{{font:16px sans-serif;max-width:1300px;margin:25px auto}}td,th{{padding:8px;border:1px solid #ccc}}img{{max-width:100%}}</style>
<h1>Policy spike review: {html.escape(path.parent.name)} / {path.name}</h1>
<p>Black/command curves are inputs; measured velocities are responses, not policy outputs. The network produces 12 position actions.</p>
<p>{html.escape(result['interpretation'])}</p><p>Each force row acts during [t,t+5 ms]; the next velocity sample is at its end. The selected red marker is a speed-change interval, not first stair contact. Entire-run overview cannot distinguish gait from high-frequency motion.</p>
<p>Sideways requests above ±0.30 m/s are outside the saved training range. Command intervals differ; no matched causal claim is made.</p>
<p>Optional reference-checkpoint results are in the JSON: it receives the candidate's recorded history (including previous actions), not its own rollout. Similar output on those states does not predict its actual stair success.</p>
<table><tr><th>Seconds</th><th>Constant command</th><th>Largest target jump /20 ms (degrees)</th><th>Physical-target probe RMS (degrees), all frequencies</th></tr>{tab}</table>
<img src="10_policy_probes.png"><img src="09_spike_chain.png"><p><a href="policy_spike_review.json">Exact metrics and verification</a> · <a href="update_diagnostics.html">Gate spectra and original diagnostics</a> · <a href="index.html">Overview</a></p>'''
    (plots/"policy_spike_review.html").write_text(page)
    for name in ["index.html","update_diagnostics.html"]:
        p=plots/name
        if p.exists() and "policy_spike_review.html" not in p.read_text():
            p.write_text(p.read_text()+'<p><a href="policy_spike_review.html">New: speed spike, contact/target/torque chain and actor-input probes</a></p>')
    print(plots/"policy_spike_review.html",flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument("paths",nargs="+",type=Path,help="Closed recorded attempt directories")
    parser.add_argument("--device",default="cpu")
    parser.add_argument("--reference-checkpoint",type=Path,help="Optional other weights on identical recorded inputs; never runs physics")
    a=parser.parse_args()
    for path in a.paths:inspect(path,a.device,a.reference_checkpoint)
