"""Isolated control-loop sensitivity experiments; never edits runtime or weights.

New scripted simulations, explicitly separate from manual keyboard recordings.
Policy stays at 50 Hz and external PD at 200 Hz. Fine physics uses four
substeps per PD interval and an explicit 10 ms positive contact time constant.
All control/observation changes are process-local diagnostic overrides.
"""
from __future__ import annotations
import argparse
import csv
import html
import shutil
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import mujoco
import numpy as np
import torch

import record
from analyze import band_rms, load_run, save_json

CASES = ('legacy', 'fresh', 'freeze_gate', 'actor_previous_action_delay', 'fresh_delay5ms', 'fresh_delay10ms',
         'fresh_contact10ms', 'fresh_fine800hz', 'fresh_contact20ms', 'fresh_impratio10', 'legacy_impratio10')


def metrics(path, start=5., stop=11.):
    m,s,d=load_run(path)
    mask=(d['time']>=start-1e-8)&(d['time']<stop-1e-8)
    ix=np.flatnonzero(mask & d['policy_tick'])
    row=dict(run=path.name,case=m['diagnostic_case'],checkpoint=m['checkpoint_label'],
             direction=m['command_axis'],outcome=s['outcome'],
             complete_window=bool(mask.sum()==round((stop-start)/m['dt'])),
             kp=m['kp'],kd=m['kd'],checkpoint_sha256=m['checkpoint_sha256'])
    if mask.sum()<400 or len(ix)<3:
        row['note']='Too short for a two-second band estimate; retain failure.'
        return row
    qband=band_rms(np.degrees(d['q'][mask]),200)
    v=d['base_velocity_body'][mask]
    req=d['command'][mask]
    axis=0 if m['command_axis']=='x' else 1
    steps=np.abs(np.degrees(np.diff(d['target'][ix],axis=0)))
    row.update(q_band_deg=float(qband.mean()),mean_requested_speed=float(req[:,axis].mean()),
        mean_actual_speed=float(v[:,axis].mean()),
        speed_rmse=float(np.sqrt(np.mean((v[:,axis]-req[:,axis])**2))),
        other_axis_rmse=float(np.sqrt(np.mean((v[:,1-axis]-req[:,1-axis])**2))),
        yaw_rate_rmse=float(np.sqrt(np.mean(d['angular_velocity_body'][mask,2]**2))),
        heading_change_deg=float(np.degrees(np.unwrap(d['yaw_rad'][mask])[-1]-np.unwrap(d['yaw_rad'][mask])[0])),
        max_tilt=float(d['tilt_deg'][mask].max()),
        p99_max_target_step_deg=float(np.quantile(steps.max(1),.99)),
        target_second_difference_cost=float(np.square(np.diff(d['target'][ix],n=2,axis=0)/np.asarray(m['scale'])).sum(1).mean()),
        torque_clipped_any_fraction=float((np.abs(d['torque_raw'][mask])>np.asarray(m['torque_limits'])+1e-5).any(1).mean()),
        target_clipped_fraction=float((np.abs(d['target_removed'][mask])>1e-6).mean()),
        mean_gate_step=float(np.linalg.norm(np.diff(d['gates'][ix],axis=0),axis=1).mean()),
        any_stair_contact=bool((d['foot_step_force']>1).any()),
        warnings=s['warnings'])
    return row


def dashboard(out,rows):
    cols=('checkpoint','direction','case','outcome','q_band_deg','mean_actual_speed',
          'speed_rmse','heading_change_deg','max_tilt','complete_window')
    with (out/'summary.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore');w.writeheader();w.writerows(rows)
    save_json(out/'summary.json',dict(
        protocol='protocol.json',analysis_window=[5.,11.],runs=rows,
        caveat='New scripted sensitivity cases, one initial state. Changed response is not a unique physical root cause. Rank smoothness together with tracking/support/heading. No real hardware measurements.'))
    table='<table><tr>'+''.join(f'<th>{k}</th>' for k in cols)+'</tr>'
    for r in rows:
        table+='<tr>'+''.join('<td>'+html.escape(f'{r[k]:.5g}' if isinstance(r.get(k),float) else str(r.get(k,'—')))+'</td>' for k in cols)+'</tr>'
    table+='</table>'
    (out/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Control loop audit</title>'
        '<style>body{font:16px system-ui;margin:24px}td,th{border:1px solid #ccc;padding:6px}table{border-collapse:collapse}img{max-width:100%}</style>'
        '<h1>Control-loop sensitivity audit</h1><p>NEW scripted simulations, not user keyboard recordings. '
             'Same checkpoints, standing/ramp schedule, target bounds, gains within a suite, policy 50 Hz and PD 200 Hz. '
        'Fresh variants compare against fresh baseline; fixed gate and legacy_impratio10 compare against legacy. '
        'Fine physics compares against explicit-contact10ms. Read outcomes and actual speed alongside vibration.</p>'
        '<p><a href="protocol.json">Protocol</a> · <a href="summary.json">Exact measurements</a> · '
        '<a href="summary.csv">CSV</a> · <a href="audit_control_loop.py">Exact diagnostic script</a></p>'
        '<img src="comparison.png">'+table)


def run(args):
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    shutil.copy2(__file__,out/'audit_control_loop.py')
    checkpoints=[('original90000',record.DEFAULT_MODEL),('candidate91000',args.candidate.resolve())]
    protected=[record.SIM/'controller.py',record.SIM/'scene.xml',*[p for _,p in checkpoints]]
    hashes={str(p):record.sha256(p) for p in protected}
    save_json(out/'protocol.json',dict(provenance='NEW diagnostic simulations; NOT user recordings',
        checkpoints=[dict(label=l,path=str(p),sha256=hashes[str(p)]) for l,p in checkpoints],
        cases=list(args.cases),directions=list(args.directions),request_m_s=.3,stand=3.,ramp=1.,
        seconds=args.seconds,terrain=args.terrain,y_offset=args.y_offset,yaw_offset=args.yaw_offset,
        analysis_window=[5.,11.],kp=args.kp,kd=args.kd,device=args.device,
        policy_hz=50,pd_hz=200,baseline_physics_hz=200,fine_physics_hz=800,
        protected_file_hashes=hashes,
        caveats=['Gate frozen at a moving-state tick at 5 s; experts and actor still update.',
                 'Delayed targets do not alter clipped raw previous-action history.',
                 'Actor previous-action diagnostic adds one frame of delay only on the direct actor path after 5 s; expert history is unchanged. This is not a deployable patch.',
                 'Fine physics preserves 200 Hz held PD torque, 50 Hz policy and explicit 10 ms contact time constant.',
                 'Fine contact trace records last substep forces; do not compare those as interval-average force measurements.',
                 'Single identical start per case, no general success-rate claim.']))
    old_init=record.ObservedController.__init__
    old_policy=record.ObservedController.policy_step
    old_physics=record.ObservedController.physics_step
    old_row=record.Recorder.state_row
    old_command=record.command_at
    case='legacy';axis='y'

    def init(ctrl,*a,**kw):
        old_init(ctrl,*a,**kw)
        ctrl.kp,ctrl.kd=args.kp,args.kd
        ctrl.audit_delay={'fresh_delay5ms':.005,'fresh_delay10ms':.01}.get(case,0.)
        ctrl.audit_target=ctrl.target_q.copy();ctrl.audit_queue=[]
        ctrl.audit_actor_input=np.zeros(77,dtype=np.float32)
        previous_actor=[]
        def actor_input(module,inputs):
            value=inputs[0]
            old=value[:,-12:].detach().clone()
            if case=='actor_previous_action_delay' and ctrl.data.time>=5.-1e-8 and previous_actor:
                value=value.clone();value[:,-12:]=previous_actor[0]
            previous_actor[:]=[old]
            ctrl.audit_actor_input=value.detach().cpu().numpy()[0].copy()
            return (value,)
        ctrl.policy.actor.register_forward_pre_hook(actor_input)
        if case in ('fresh_contact10ms','fresh_fine800hz','fresh_contact20ms'):
            positive=ctrl.model.geom_solref[:,0]>0
            ctrl.model.geom_solref[positive,0]=np.maximum(ctrl.model.geom_solref[positive,0],.01)
            if case=='fresh_contact20ms':
                for leg in record.LEGS:
                    g=mujoco.mj_name2id(ctrl.model,mujoco.mjtObj.mjOBJ_GEOM,leg+'_foot')
                    ctrl.model.geom_solref[g,0]=.02
        if case in ('fresh_impratio10','legacy_impratio10'):ctrl.model.opt.impratio=10
        if case=='freeze_gate':
            fixed=[]
            def hold(module,inputs,output):
                if ctrl.data.time>=5.-1e-8:
                    if not fixed:fixed.append(output.detach().clone())
                    return fixed[0]
                return output
            ctrl.policy.student_moe_encoder.moe.gating_network.register_forward_hook(hold,prepend=True)

    def policy(ctrl,command):
        previous=ctrl.target_q.copy()
        old_policy(ctrl,command)
        ctrl.audit_target=ctrl.target_q.copy()
        if ctrl.audit_delay:
            ctrl.audit_queue.append((float(ctrl.data.time)+ctrl.audit_delay,ctrl.target_q.copy()))
            ctrl.target_q=previous

    def row(rec,command,policy_tick):
        ctrl=rec.ctrl
        while ctrl.audit_queue and ctrl.audit_queue[0][0]<=rec.data.time+1e-8:
            _,ctrl.target_q=ctrl.audit_queue.pop(0)
        result=old_row(rec,command,policy_tick)
        result['target_removed']=result['requested']-ctrl.audit_target
        result['target_before_delay']=ctrl.audit_target.copy()
        result['target_delay_removed']=ctrl.audit_target-ctrl.target_q
        result['actor_input']=ctrl.audit_actor_input.copy()
        result['audit_impratio']=np.asarray(rec.model.opt.impratio)
        return result

    def physics(ctrl):
        if case!='fresh_fine800hz':return old_physics(ctrl)
        dt=float(ctrl.model.opt.timestep)
        ctrl.model.opt.timestep=dt/4
        try:
            old_physics(ctrl)
            for _ in range(3):mujoco.mj_step(ctrl.model,ctrl.data)
        finally:ctrl.model.opt.timestep=dt

    def command(t,vx,stand,ramp):
        value=vx*np.clip((t-stand)/ramp,0.,1.)
        return np.array([value if axis=='x' else 0.,value if axis=='y' else 0.,0.])

    record.ObservedController.__init__=init
    record.ObservedController.policy_step=policy
    record.ObservedController.physics_step=physics
    record.Recorder.state_row=row
    record.command_at=command
    rows=[]
    try:
        for label,checkpoint in checkpoints:
            for axis in args.directions:
                for case in args.cases:
                    name=f'{label}_{axis}_{case}'
                    print('AUDIT_CASE',name,flush=True)
                    path=record.record_run(checkpoint,out/name,
                        sensors='fresh' if case.startswith('fresh') else 'viewer',
                        device=args.device,seconds=args.seconds,vx=.3,stand=3.,ramp=1.,
                        terrain=args.terrain,y_offset=args.y_offset,yaw_offset=args.yaw_offset)
                    m,s,d=load_run(path)
                    m.update(diagnostic_case=case,checkpoint_label=label,command_axis=axis,
                        command_vector=[.3,0.,0.] if axis=='x' else [0.,.3,0.],
                        vx='Legacy amplitude field; use command_vector and actual trace commands.',
                        policy_hz=50,pd_hz=200,physics_hz=800 if case=='fresh_fine800hz' else 200,
                        impratio=float(d['audit_impratio'][0]),
                        diagnostic_script_sha256=record.sha256(__file__),
                        provenance='NEW scripted sensitivity experiment; all overrides isolated to this process.')
                    save_json(path/'manifest.json',m)
                    assert np.allclose(np.diff(d['time']),.005,atol=1e-8)
                    assert np.allclose(np.diff(d['time'][d['policy_tick']]),.02,atol=1e-8)
                    if case in ('fresh_delay5ms','fresh_delay10ms'):
                        lag=1 if case=='fresh_delay5ms' else 2
                        expected=np.concatenate([np.tile(m['q0'],(lag,1)),d['target_before_delay'][:-lag]])
                        assert np.max(np.abs(expected-d['target']))<1e-6,'Target delay buffer mismatch'
                    if case=='freeze_gate':
                        sel=(d['time']>=5-1e-8)&d['policy_tick']
                        assert np.max(np.abs(np.diff(d['gates'][sel],axis=0)))<1e-8
                    if case=='fresh_contact10ms':
                        ref=out/f'{label}_{axis}_fresh'
                        if ref.exists():
                            _,_,rd=load_run(ref)
                            mismatch=float(np.abs(d['sim_qpos']-rd['sim_qpos']).max()) if len(d['time'])==len(rd['time']) else None
                            m['explicit_contact_baseline_qpos_max_error']=mismatch
                            save_json(path/'manifest.json',m)
                            assert mismatch is not None and mismatch<1e-6, ('Contact normalization was not equivalent',mismatch)
                    rows.append(metrics(path))
                    save_json(out/'summary.json',dict(runs=rows,protocol='protocol.json'))
                    print('AUDIT_RESULT',rows[-1],flush=True)
    finally:
        record.ObservedController.__init__=old_init
        record.ObservedController.policy_step=old_policy
        record.ObservedController.physics_step=old_physics
        record.Recorder.state_row=old_row
        record.command_at=old_command
        for p in protected:assert record.sha256(p)==hashes[str(p)],f'Protected file changed: {p}'
    fig,axs=plt.subplots(2,2,figsize=(16,10))
    for j,axis in enumerate(args.directions):
        for i,key in enumerate(('q_band_deg','mean_actual_speed')):
            ax=axs[i,j]
            for k,label in enumerate(('original90000','candidate91000')):
                vals=[next((r.get(key,np.nan) for r in rows if r['checkpoint']==label and r['direction']==axis and r['case']==c),np.nan) for c in args.cases]
                ax.bar(np.arange(len(args.cases))+(k-.5)*.36,vals,width=.36,label=label)
            ax.set_xticks(np.arange(len(args.cases)),args.cases,rotation=65,ha='right',fontsize=8)
            ax.set_title(axis.upper()+' command: '+('joint 8–30 Hz RMS (degrees)' if i==0 else 'actual body speed (m/s)'))
            if i==1:ax.axhline(.3,color='black',ls='--',label='request')
            ax.legend(fontsize=8);ax.grid(axis='y',alpha=.25)
    fig.suptitle('Isolated scripted control-loop audit: compare motion and tracking together with vibration')
    fig.tight_layout();fig.savefig(out/'comparison.png',dpi=140);plt.close(fig)
    dashboard(out,rows)
    print('DASHBOARD',out/'index.html',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--candidate',type=Path,default=record.ROOT/'xterra_mjlab/evaluation_runs/moe_swing013_latest/latest.pt')
    p.add_argument('--device',default='cuda:0')
    p.add_argument('--cases',nargs='+',choices=CASES,default=list(CASES))
    p.add_argument('--directions',nargs='+',choices=('x','y'),default=['x','y'])
    p.add_argument('--terrain',choices=('flat','stairs'),default='flat')
    p.add_argument('--seconds',type=float,default=12.)
    p.add_argument('--kp',type=float,default=20.)
    p.add_argument('--kd',type=float,default=.7)
    p.add_argument('--y-offset',type=float,default=0.)
    p.add_argument('--yaw-offset',type=float,default=0.)
    run(p.parse_args())
