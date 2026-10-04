"""Compare equal steady-command windows from two actual interactive recordings.

No simulation, inference, filtering of control signals or training is performed.
Retain failed/short recordings; unmatched conditions are reported explicitly.
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from analyze import band_rms, save_json
from plot_interactive import load_attempt


def attempt_path(path):
    path=path.expanduser().resolve()
    if (path/"raw").is_dir():return path
    attempts=sorted(path.glob("attempt_*"))
    if len(attempts)!=1:
        raise ValueError(f"{path}: specify one attempt explicitly; found {len(attempts)}")
    return attempts[0]


def select(d,m,command,settle,seconds):
    good=np.all(np.isclose(d["command"],command,atol=1e-6,rtol=0),axis=1)
    starts=np.flatnonzero(good & ~np.r_[False,good[:-1]])
    stops=np.flatnonzero(good & ~np.r_[good[1:],False])+1
    if not len(starts):raise ValueError(f"No recorded command {command.tolist()}")
    need=round((settle+seconds)/m["dt"])
    long=np.flatnonzero(stops-starts>=need)
    # Prefer the first sufficient hold; otherwise retain the longest incomplete
    # hold and mark it as too short, rather than silently dropping a failure.
    k=int(long[0]) if len(long) else int(np.argmax(stops-starts))
    a,b=int(starts[k]),int(stops[k])
    lo=a+round(settle/m["dt"])
    hi=min(b,lo+round(seconds/m["dt"]))
    if hi-lo<2:
        raise ValueError("Request was not held beyond settling; raw recording retained. Hold for 12 simulation seconds.")
    return lo,hi,bool(len(long))


def main():
    p=argparse.ArgumentParser(__doc__)
    p.add_argument("original",type=Path)
    p.add_argument("candidate",type=Path)
    p.add_argument("--command",type=float,nargs=3,required=True,metavar=("VX","VY","YAW"))
    p.add_argument("--seconds",type=float,default=8)
    p.add_argument("--settle",type=float,default=1)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    if not np.isfinite([*a.command,a.seconds,a.settle]).all() or a.seconds<2 or a.settle<0:
        p.error("Use finite values, at least 2 seconds, and nonnegative settling")
    a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=True)
    loaded=[]
    for path in [a.original,a.candidate]:
        path=attempt_path(path)
        m,s,d=load_attempt(path)
        if d is None:raise ValueError(f"No samples in {path}")
        if s["status"]=="recording":raise ValueError("Close both viewers before comparison")
        if not np.isclose(m["dt"],.005) or m["decimation"]!=4:
            raise ValueError("This comparison requires 200 Hz / 50 Hz recordings")
        lo,hi,complete=select(d,m,np.asarray(a.command),a.settle,a.seconds)
        loaded.append((path,m,s,d,lo,hi,complete))
    # Sensor/control/physical contract equality; checkpoint identity is allowed
    # to differ intentionally. Source hashes ensure solver/scene/controller
    # code differences aren't hidden by identical target bounds.
    keys=["dt","decimation","joint_names","target_min","target_max","q0","scale",
          "kp","kd","transmission","torque_limits","foot_friction","foot_solref",
          "foot_radius_m","scene_sha256","observation_timing","track","initial_base_pos"]
    mismatch=[k for k in keys if loaded[0][1].get(k)!=loaded[1][1].get(k)]
    for name in ["controller.py","checkpoint_policy.py","build_scene.py","run_interactive_sim.py"]:
        values=[]
        for _,m,*_ in loaded:
            values.append(next((v for k,v in m["source_sha256"].items() if Path(k).name==name),None))
        if values[0]!=values[1]:mismatch.append("source:"+name)
    same_weights=loaded[0][1]["checkpoint_sha256"]==loaded[1][1]["checkpoint_sha256"]
    if same_weights:mismatch.append("Both recordings use the SAME weights; not original versus candidate")
    if loaded[0][1]["checkpoint_update"]!=90000:
        mismatch.append("First recording is not update 90000")
    for field in ["sim_qpos","sim_qvel"]:
        if not np.allclose(loaded[0][3][field][0],loaded[1][3][field][0],atol=1e-7,rtol=0):
            mismatch.append("initial:"+field)
    rows=[]
    for label,(path,m,s,d,lo,hi,complete) in zip(["original","candidate"],loaded):
        ticks=np.flatnonzero(d["policy_tick"] & (np.arange(len(d["time"]))>=lo) & (np.arange(len(d["time"]))<hi))
        if len(ticks)<3 or not np.allclose(np.diff(d["time"][ticks]),.02,atol=1e-8):
            raise ValueError("Need uniform policy ticks for target-difference metrics")
        rms=band_rms(np.degrees(d["q"][lo:hi]),200)
        targets=d["target"][ticks]
        steps=np.abs(np.degrees(np.diff(targets,axis=0)))
        velocity=d["base_velocity_body"][lo:hi]
        heading=np.degrees(np.unwrap(d["yaw_rad"][lo:hi]))
        row=dict(label=label,update=m["checkpoint_update"],checkpoint_sha256=m["checkpoint_sha256"],attempt=str(path),
            start_s=float(d["time"][lo]-m["start_sim_time"]),duration_s=float((hi-lo)*m["dt"]),complete_window=complete,
            mean_body_vx_m_s=float(velocity[:,0].mean()),mean_body_vy_m_s=float(velocity[:,1].mean()),
            vx_rmse_m_s=float(np.sqrt(np.mean((velocity[:,0]-a.command[0])**2))),
            vy_rmse_m_s=float(np.sqrt(np.mean((velocity[:,1]-a.command[1])**2))),
            yaw_rate_rmse_rad_s=float(np.sqrt(np.mean((d["angular_velocity_body"][lo:hi,2]-a.command[2])**2))),
            joint_8_30_hz_rms_deg=None if rms is None else float(rms.mean()),
            max_target_step_deg=float(steps.max()),p99_max_joint_target_step_deg=float(np.quantile(steps.max(1),.99)),
            normalized_target_second_difference_cost=float(np.square(np.diff(targets,n=2,axis=0)/np.asarray(m["scale"])).sum(1).mean()),
            target_clipped_fraction=float((abs(d["target_removed"][lo:hi])>1e-6).mean()),
            any_joint_torque_clipped_fraction=float((abs(d["torque_raw"][lo:hi])>np.asarray(m["torque_limits"])+1e-5).any(1).mean()),
            heading_change_deg=float(heading[-1]-heading[0]),max_tilt_deg=float(d["tilt_deg"][lo:hi].max()),
            any_stair_contact_in_window=bool((d["foot_step_force"][lo:hi]>1).any()),
            any_stair_contact_before_window=bool((d["foot_step_force"][:lo]>1).any()),
            invalid_raw_action_count=int((~d["raw_action_finite"][ticks]).sum()),recording_status=s["status"])
        rows.append(row)
    matched=not mismatch and all(r["complete_window"] for r in rows)
    flat_clean=all(not r["any_stair_contact_in_window"] and not r["any_stair_contact_before_window"] for r in rows)
    result=dict(command=a.command,settle_seconds=a.settle,requested_window_seconds=a.seconds,
        matched_recorded_contract_and_duration=matched,contract_mismatches=mismatch,flat_clean=flat_clean,runs=rows,
        caveat="Manual keyboard ramp/start timing can differ despite equal steady requests. Retain failures; no significance or general success-rate claim from one pair. Compare jitter together with tracking, heading, falls/support, not only smoothness.")
    save_json(a.out/"comparison.json",result)
    with (a.out/"comparison.csv").open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    fig,axs=plt.subplots(5,1,figsize=(12,12),sharex=True)
    for label,(_,m,s,d,lo,hi,_) in zip(["original","candidate"],loaded):
        t=d["time"][lo:hi]-d["time"][lo]
        for j in range(2):axs[j].plot(t,d["base_velocity_body"][lo:hi,j],lw=.8,label=label)
        axs[2].plot(t,d["tilt_deg"][lo:hi],lw=.8,label=label)
        q=np.arange(len(d["time"]));ticks=np.flatnonzero(d["policy_tick"]&(q>=lo)&(q<hi))
        axs[3].plot(d["time"][ticks[1:]]-d["time"][lo],abs(np.degrees(np.diff(d["target"][ticks],axis=0))).max(1),lw=.8,label=label)
        axs[4].plot(t,np.degrees(np.unwrap(d["yaw_rad"][lo:hi]))-np.degrees(d["yaw_rad"][lo]),lw=.8,label=label)
    for j in range(2):axs[j].axhline(a.command[j],color="black",ls="--",label="requested")
    for ax,ylabel in zip(axs,["Actual vx (m/s)","Actual vy (m/s)","Tilt (degrees)","Largest target jump\nper 20 ms (degrees)","Heading change (degrees)"]):
        ax.set_ylabel(ylabel);ax.grid(alpha=.2);ax.legend()
    axs[-1].set_xlabel("Seconds within selected steady-command window")
    fig.suptitle(f"Actual recordings, command {a.command}; same contract/duration: {matched}; no stair contact: {flat_clean}")
    fig.tight_layout();fig.savefig(a.out/"comparison.png",dpi=125);plt.close(fig)
    fields=["label","update","duration_s","mean_body_vx_m_s","mean_body_vy_m_s","vx_rmse_m_s","vy_rmse_m_s","joint_8_30_hz_rms_deg","max_target_step_deg","p99_max_joint_target_step_deg","normalized_target_second_difference_cost","heading_change_deg","max_tilt_deg","any_joint_torque_clipped_fraction"]
    table="".join('<tr><th>'+k+'</th>'+''.join('<td>'+html.escape(str(r[k]))+'</td>' for r in rows)+'</tr>' for k in fields)
    links="".join(f'<li><a href="{html.escape(os.path.relpath(path/"plots/index.html",a.out))}">{label} full recording</a></li>' for label,(path,*_) in zip(["original","candidate"],loaded))
    (a.out/"index.html").write_text(f'''<!doctype html><meta charset="utf-8"><title>Original/candidate comparison</title>
<style>body{{font:16px sans-serif;max-width:1100px;margin:25px auto}}td,th{{padding:7px;border:1px solid #ddd}}img{{max-width:100%}}</style>
<h1>Original versus candidate: actual manual recordings</h1><p>Command: {a.command}. Same recorded contract and full duration: <b>{matched}</b>. No stair contact before/during either window: <b>{flat_clean}</b>.</p>
<p>Configuration differences: {html.escape(str(mismatch))}. Too-short windows remain in the results and are not treated as an equal-duration comparison.</p>
<p>{result['caveat']}</p><p>Good improvement means lower rapid joint motion and target jumps while tracking remains good and the robot stays upright. A stationary robot can have excellent smoothness but fail the task. Target second difference is a discrete acceleration-like quantity, not position jerk.</p>
<table>{table}</table><img src="comparison.png"><ul>{links}</ul><p><a href="comparison.csv">CSV</a> · <a href="comparison.json">Exact metrics and checkpoint hashes</a></p>''')
    print(f"Comparison: {a.out/'index.html'}")
    print(f"Same contract/duration: {matched}; clean flat intervals: {flat_clean}; mismatches: {mismatch}")


if __name__=="__main__":main()
