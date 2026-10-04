"""Review every saved interactive attempt; never run a policy or simulation."""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import butter, sosfiltfilt
from scipy.stats import spearmanr

from analyze import band_rms, save_json
from plot_interactive import load_attempt


def sustained(mask, count):
    run = 0
    for i, value in enumerate(mask):
        run = run + 1 if value else 0
        if run >= count: return i - count + 1
    return None


def costs(d, m):
    p = d['policy_tick'].astype(bool)
    q = d['target'][p]
    c2 = np.sum((np.diff(q, n=2, axis=0) / m['scale'])**2, axis=1)
    a2 = np.sum(np.diff(d['action'][p], n=2, axis=0)**2, axis=1)
    return d['time'][p][2:], c2, a2


def constant_windows(d, m, seconds=4.):
    """Nonoverlapping windows: fixed command, moving, upright, one contact phase."""
    n = round(seconds / m['dt'])
    t = d['time']
    cuts = np.r_[0, np.flatnonzero(np.any(np.abs(np.diff(d['command'], axis=0)) > 1e-6, axis=1)) + 1, len(t)]
    ever_stairs = np.maximum.accumulate((d['foot_step_force'] > 1).any(axis=1))
    tp, c2, a2 = costs(d, m)
    rows = []
    for a, b in zip(cuts[:-1], cuts[1:]):
        # Skip 0.2 s after a key-driven command change, including startup.
        for i in range(a + round(.2 / m['dt']), b - n + 1, n):
            j = i + n
            cmd = d['command'][i]
            if np.linalg.norm(cmd) <= .03: continue
            if np.any(d['tilt_deg'][i:j] >= 30) or np.any(d['base_clearance'][i:j] <= .18): continue
            if ever_stairs[i] != ever_stairs[j - 1]: continue
            cp = (tp >= t[i] - 1e-9) & (tp < t[j - 1] + m['dt'] - 1e-9)
            rms = band_rms(np.degrees(d['q'][i:j]), 1/m['dt'])
            if rms is None or not cp.any(): continue
            rows.append(dict(start_s=float(t[i]-m['start_sim_time']), duration_s=seconds,
                phase='after_stair_contact' if ever_stairs[i] else 'before_stair_contact',
                vx=float(cmd[0]), vy=float(cmd[1]), yaw=float(cmd[2]),
                target_second_difference_cost=float(c2[cp].mean()), action_second_difference_cost=float(a2[cp].mean()),
                joint_8_30_hz_rms_deg=float(rms.mean()),
                target_clipped_fraction=float((np.abs(d['target_removed'][i:j])>1e-6).mean()),
                torque_clipped_fraction=float((np.abs(d['torque_raw'][i:j])>np.array(m['torque_limits'])+1e-5).mean()),
                riser_contact_fraction=float((d['foot_riser_force'][i:j]>1).any(axis=1).mean())))
    return rows


def support_steps(path):
    result = {leg: 0 for leg in ('FL','FR','RL','RR')}
    for line in (path/'contacts.jsonl').read_text().splitlines():
        c = json.loads(line)
        if c['foot'] not in result or c['force_contact'][0] <= 1 or abs(c['frame'][2]) <= .7: continue
        name = next((v for v in (c['geom1'],c['geom2']) if v.startswith('step_')), None)
        if name:
            result[c['foot']] = max(result[c['foot']], int(name.rsplit('_',1)[1]))
    return result


def summarize(path):
    m, s, d = load_attempt(path)
    if d is None: return dict(run=f'{path.parent.name}/{path.name}', category='empty', samples=0), []
    t = d['time']; dt = m['dt']; cmd = d['command']; motion=np.linalg.norm(cmd,axis=1)>.03
    kind = 'ascent_start' if m['initial_base_pos'][0]<0 else 'top_spawn_descent_or_standing'
    failed = sustained((d['tilt_deg']>60)|(d['base_clearance']<.12),round(.25/dt))
    # Platform spawn does not count as successful ascent.
    all_supported=np.maximum.accumulate(d['foot_platform_force']>1,axis=0).all(axis=1)
    top=(d['foot_pos'][:,:,0]>3.6+max(m['foot_radius_m'])).all(axis=1)&all_supported
    top &= (np.abs(d['foot_pos'][:,:,1]-m['initial_base_pos'][1])<1).all(axis=1)
    top &= (d['tilt_deg']<30)&(d['base_clearance']>.18)
    top_i = sustained(top,round(.5/dt)) if kind=='ascent_start' else None
    tc,c2,a2=costs(d,m)
    pc=np.linalg.norm(cmd[d['policy_tick'].astype(bool)][2:],axis=1)>.03
    phealthy=d['tilt_deg'][d['policy_tick'].astype(bool)][2:]<60
    eligible=pc&phealthy
    phase_metrics={}
    for label, after in [('before_contact',False),('after_contact',True)]:
        contact=s['first_stair_contact_s']
        phase=(t<contact) if contact is not None and not after else (t>=contact) if contact is not None else np.ones(len(t),bool) if not after else np.zeros(len(t),bool)
        if after and contact is not None: phase &= t<contact+6
        if failed is not None: phase &= np.arange(len(t))<failed
        inds=np.flatnonzero(phase&motion)
        # Use one continuous interval; omit post-fall data and report duration.
        if len(inds):
            i,j=inds[0],inds[-1]+1
            rms=band_rms(np.degrees(d['q'][i:j]),1/dt)
            phase_metrics[label]=dict(start_s=float(t[i]-m['start_sim_time']),duration_s=(j-i)*dt,
                rms_deg=None if rms is None else float(rms.mean()))
    contact=s.get('first_riser_contact_s')
    first_foot=None; first_height=None
    if contact is not None:
        i=int(np.argmin(np.abs(t-contact)))
        f=int(np.argmax(d['foot_riser_force'][i]))
        first_foot=('FL','FR','RL','RR')[f]; first_height=float(d['foot_pos'][i,f,2])
    windows=constant_windows(d,m)
    for w in windows: w.update(run=f'{path.parent.name}/{path.name}',limit_profile='wide' if m['target_max'][2]>0 else 'tight',start_kind=kind)
    result=dict(run=f'{path.parent.name}/{path.name}',category=kind,
        limit_profile='wide' if m['target_max'][2]>0 else 'tight',hip_upper=m['target_max'][0],calf_upper=m['target_max'][2],
        checkpoint_update=m['checkpoint_update'],checkpoint_sha256=m['checkpoint_sha256'],samples=len(t),duration_s=len(t)*dt,
        moving_seconds=float(motion.sum()*dt),max_vx=float(cmd[:,0].max()),min_vx=float(cmd[:,0].min()),
        max_abs_vy=float(np.abs(cmd[:,1]).max()),max_abs_yaw=float(np.abs(cmd[:,2]).max()),
        first_stair_contact_s=None if s['first_stair_contact_s'] is None else s['first_stair_contact_s']-m['start_sim_time'],
        first_riser_foot=first_foot,first_riser_center_z_m=first_height,
        max_base_x_m=float(d['base_pos'][:,0].max()),max_base_z_m=float(d['base_pos'][:,2].max()),
        max_tilt_deg=float(d['tilt_deg'].max()),last_base_x_m=float(d['base_pos'][-1,0]),
        sustained_failure_s=None if failed is None else float(t[failed]-m['start_sim_time']),
        top_entry_detected=top_i is not None,
        moving_target_second_difference_cost=None if not eligible.any() else float(c2[eligible].mean()),
        moving_action_second_difference_cost=None if not eligible.any() else float(a2[eligible].mean()),
        target_clip_fraction_moving=None if not motion.any() else float((np.abs(d['target_removed'][motion])>1e-6).mean()),
        torque_clip_fraction_moving=None if not motion.any() else float((np.abs(d['torque_raw'][motion])>np.array(m['torque_limits'])+1e-5).mean()),
        actual_torque_reconstruction_max_error_Nm=float(np.max(np.abs(d['torque_applied']-np.clip(d['torque_raw'],-np.array(m['torque_limits']),np.array(m['torque_limits']))))),
        invalid_policy_actions=int((d['policy_tick']&~d['raw_action_finite']).sum()),warnings=s['warnings'],
        supported_steps=support_steps(path),phase_metrics=phase_metrics,constant_command_windows=len(windows))
    return result, windows


def detail_plot(path, out, start=None):
    m,s,d=load_attempt(path);t=d['time']-m['start_sim_time'];fs=1/m['dt']
    contact=s['first_riser_contact_s']
    if contact is None: contact=s['first_stair_contact_s']
    center=contact-m['start_sim_time'] if contact is not None else t[-1]/2
    lo=max(0,center-1) if start is None else start;hi=min(t[-1],lo+4)
    mask=(t>=lo)&(t<=hi)
    rms=band_rms(np.degrees(d['q'][mask]),fs)
    j=int(np.argmax(rms)) if rms is not None else 2
    sos=butter(4,[8,30],btype='bandpass',fs=fs,output='sos')
    # Filter the whole attempt for display only. RMS statistics use Welch independently.
    qhf=sosfiltfilt(sos,np.degrees(d['q'][:,j])) if len(t)>30 else np.full(len(t),np.nan)
    tp,c2,a2=costs(d,m);tp-=m['start_sim_time'];p=(tp>=lo)&(tp<=hi)
    fig,axs=plt.subplots(4,1,figsize=(11,9),sharex=True)
    axs[0].plot(t[mask],np.degrees(d['requested'][mask,j]),alpha=.5,label='requested angle')
    axs[0].plot(t[mask],np.degrees(d['target'][mask,j]),label='clamped target')
    axs[0].plot(t[mask],np.degrees(d['q'][mask,j]),label='actual joint')
    axs[0].set_ylabel('Angle (degrees)');axs[0].legend(fontsize=8,ncol=3)
    axs[1].plot(tp[p],c2[p],label='clamped-target second-difference cost')
    axs[1].plot(tp[p],a2[p],alpha=.6,label='clipped-action second-difference cost')
    axs[1].set_ylabel('Unweighted cost\n(sum over 12 joints)');axs[1].legend(fontsize=8)
    axs[2].plot(t[mask],qhf[mask]);axs[2].set_ylabel('Actual joint 8–30 Hz\ncomponent (degrees)')
    axs[3].plot(t[mask],d['torque_applied'][mask,j],label='actual applied torque (Nm)')
    twin=axs[3].twinx();twin.plot(t[mask],d['foot_riser_force'][mask].sum(axis=1),color='red',alpha=.5,label='riser force (N)')
    axs[3].set_ylabel('Joint torque (Nm)');twin.set_ylabel('Riser force sum (N)',color='red')
    axs[3].legend(loc='upper left',fontsize=8);twin.legend(loc='upper right',fontsize=8)
    for ax in axs:
        ax.grid(alpha=.2)
        if contact is not None: ax.axvline(center,color='crimson',ls=':')
    axs[-1].set_xlabel('Seconds since this attempt reset')
    fig.suptitle(f'{path.parent.name}/{path.name}: {m["joint_names"][j]} — target cost is not measured jitter')
    fig.tight_layout();name=f'{path.parent.name}_{path.name}_signal_chain.png';fig.savefig(out/name,dpi=130);plt.close(fig)
    return dict(run=f'{path.parent.name}/{path.name}',image=name,start_s=lo,stop_s=hi,joint=m['joint_names'][j])


def riser_height_plot(results, out):
    """First-riser heights only for entrance-spawn attempts, never descents."""
    rows=[r for r in results if r['category']=='ascent_start' and r.get('first_riser_center_z_m') is not None]
    fig,ax=plt.subplots(figsize=(13,5))
    labels=[r['run'].replace('attempt_','a').replace('with_the_hardware_limits_01','tight') for r in rows]
    ax.bar(np.arange(len(rows)),[r['first_riser_center_z_m']*100 for r in rows],
           color=['#bf3b3b' if r['limit_profile']=='tight' else '#2973a1' for r in rows])
    ax.axhline(12.2,color='green',ls='--',label='10 cm first tread + 2.2 cm sphere radius')
    ax.set_xticks(np.arange(len(rows)),labels,rotation=75,ha='right',fontsize=7)
    ax.set_ylabel('Contacting foot-center height (cm)');ax.legend(fontsize=9)
    ax.set_title('Every recorded ascent: the first vertical-face hit occurs below direct tread clearance')
    ax.grid(axis='y',alpha=.2);fig.tight_layout();fig.savefig(out/'first_riser_clearance.png',dpi=130);plt.close(fig)


def training_plot(path,out):
    if path is None:return None
    from tensorboard.backend.event_processing.event_accumulator import EventAccumulator
    ea=EventAccumulator(str(path),size_guidance={'scalars':0});ea.Reload()
    tags=['RewardRaw/target_second_difference_l2','RewardRaw/action_rate_l2','RewardRate/target_saturation_l2',
          'RewardRate/target_second_difference_l2','RewardRate/track_linear_velocity','RewardRate/track_angular_velocity']
    result={}
    fig,axs=plt.subplots(2,2,figsize=(12,7))
    for tag,ax in zip(tags[:4],axs.flat):
        vals=ea.Scalars(tag);v=np.array([e.value for e in vals]);steps=np.array([e.step for e in vals])
        result[tag]=dict(first50_mean=float(v[:50].mean()),last50_mean=float(v[-50:].mean()),records=len(v))
        ax.plot(steps,v,alpha=.2,label='logged updates')
        if len(v)>=20:ax.plot(steps[19:],np.convolve(v,np.ones(20)/20,mode='valid'),label='20-update mean')
        ax.set_title(tag,fontsize=10);ax.grid(alpha=.2);ax.set_xlabel('Training update')
    for tag in tags[4:]:
        v=np.array([e.value for e in ea.Scalars(tag)])
        result[tag]=dict(first50_mean=float(v[:50].mean()),last50_mean=float(v[-50:].mean()),records=len(v))
    fig.suptitle('Actual saved training logs: active penalties, not proof of reduced measured jitter')
    fig.tight_layout();fig.savefig(out/'training_penalties.png',dpi=130);plt.close(fig)
    result['source']=str(path.resolve());save_json(out/'training_log_summary.json',result)
    return result


def review(root,out,training_log=None):
    out.mkdir(parents=True,exist_ok=False)
    results=[];windows=[];hashes={};events={}
    for session in sorted(root.iterdir()):
        if not session.is_dir() or not (session/'manifest.json').exists():continue
        state=json.loads((session/'status.json').read_text())
        if state['status']=='recording':raise ValueError(f'Close {session} before analysis')
        events[session.name]=[json.loads(v) for v in (session/'events.jsonl').read_text().splitlines()]
        for p in (session/'manifest.json',session/'status.json',session/'events.jsonl'):
            hashes[str(p.resolve())]=hashlib.sha256(p.read_bytes()).hexdigest()
        for attempt in sorted(session.glob('attempt_*')):
            result,ws=summarize(attempt);results.append(result);windows.extend(ws)
            for p in [attempt/'manifest.json',attempt/'status.json',attempt/'contacts.jsonl',*sorted((attempt/'raw').glob('*.npz'))]:
                hashes[str(p.resolve())]=hashlib.sha256(p.read_bytes()).hexdigest()
            print(result['run'], 'max x',result.get('max_base_x_m'),'failure',result.get('sustained_failure_s'),flush=True)
    save_json(out/'attempts.json',results);save_json(out/'constant_command_windows.json',windows)
    save_json(out/'input_sha256.json',hashes)
    riser_height_plot(results,out)
    fields=[k for k in results[0] if k not in ('supported_steps','phase_metrics','warnings')]
    with (out/'attempts.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(results)
    observation_fields=['run','limit_profile','category','max_vx','first_stair_contact_s',
        'first_riser_foot','first_riser_center_z_m','max_base_x_m','sustained_failure_s',
        'what_I_saw_before_contact','what_I_saw_after_contact','target_vs_actual_observation','my_hypothesis','next_check']
    with (out/'observations.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=observation_fields,extrasaction='ignore')
        writer.writeheader();writer.writerows(results)
    for r in results:r['phase_metrics']=r.get('phase_metrics',{})
    fig,axs=plt.subplots(2,1,figsize=(13,8),sharex=True)
    ascent=[r for r in results if r['category']=='ascent_start' and r['first_stair_contact_s'] is not None]
    labels=[r['run'].replace('attempt_','a').replace('with_the_hardware_limits_01','tight') for r in ascent]
    colors=['#bf3b3b' if r['limit_profile']=='tight' else '#2973a1' for r in ascent]
    axs[0].bar(np.arange(len(ascent)),[r['max_base_x_m'] for r in ascent],color=colors)
    axs[0].axhline(3.6,color='green',ls='--',label='platform begins');axs[0].set_ylabel('Maximum body x (m)');axs[0].legend()
    axs[1].bar(np.arange(len(ascent)),[r['max_vx'] for r in ascent],color=colors);axs[1].set_ylabel('Maximum requested vx (m/s)')
    axs[1].set_xticks(np.arange(len(ascent)),labels,rotation=75,ha='right',fontsize=7)
    for ax in axs:ax.grid(axis='y',alpha=.2)
    fig.suptitle('All interactive ascent/contact attempts: differing commands prevent causal limit comparisons')
    fig.tight_layout();fig.savefig(out/'all_ascent_progress.png',dpi=130);plt.close(fig)
    scatter_note={}
    if windows:
        fig,ax=plt.subplots(figsize=(9,6))
        for profile in ['wide','tight']:
            for phase,marker in [('before_stair_contact','o'),('after_stair_contact','^')]:
                ws=[w for w in windows if w['limit_profile']==profile and w['phase']==phase]
                if ws:ax.scatter([w['target_second_difference_cost'] for w in ws],[w['joint_8_30_hz_rms_deg'] for w in ws],marker=marker,label=f'{profile}, {phase}',alpha=.65)
        ax.set_xlabel('Mean normalized clamped-target second-difference cost');ax.set_ylabel('Mean measured joint 8–30 Hz RMS (degrees)')
        ax.legend(fontsize=8);ax.grid(alpha=.2);ax.set_title('Four-second constant-command upright windows; association is not causation')
        fig.tight_layout();fig.savefig(out/'cost_vs_jitter.png',dpi=130);plt.close(fig)
        corr=spearmanr([w['target_second_difference_cost'] for w in windows],[w['joint_8_30_hz_rms_deg'] for w in windows])
        scatter_note=dict(windows=len(windows),pooled_spearman=float(corr.statistic) if np.isfinite(corr.statistic) else None,note='Repeated windows, varied speed/terrain/limits; not independent trials or causal evidence')
        for name,ws in [('entrance_starts',[w for w in windows if w['start_kind']=='ascent_start']),
            ('entrance_after_contact',[w for w in windows if w['start_kind']=='ascent_start' and w['phase']=='after_stair_contact'])]:
            rho=spearmanr([w['target_second_difference_cost'] for w in ws],[w['joint_8_30_hz_rms_deg'] for w in ws]).statistic if len(ws)>2 else np.nan
            scatter_note[name]=dict(windows=len(ws),spearman=float(rho) if np.isfinite(rho) else None)
    selected=[('user_run_01','attempt_005'),('user_run_03','attempt_013'),('user_run_03','attempt_006'),
              ('with_the_hardware_limits_01','attempt_001'),('user_run_02','attempt_003'),('with_the_hardware_limits_01','attempt_004'),
              ('with_the_hardware_limits_02','attempt_002'),('with_the_hardware_limits_02','attempt_005')]
    images=[detail_plot(root/session/attempt,out) for session,attempt in selected if (root/session/attempt).exists()]
    train=training_plot(training_log,out)
    summary=dict(sessions=len(events),attempts=len(results),total_simulation_seconds=sum(r.get('duration_s',0) for r in results),
        ascents_with_contact=len(ascent),top_entry_detected=sum(r.get('top_entry_detected',False) for r in results),
        checkpoint_hashes=sorted(set(r['checkpoint_sha256'] for r in results if 'checkpoint_sha256' in r)),
        stable_windows=scatter_note,selected_images=images,training_logs=train)
    save_json(out/'summary.json',summary)
    evidence={}
    if training_log is not None:
        for p in training_log.rglob('*'):
            if p.is_file() and (p.name.startswith('events.out.tfevents') or p.name in ('env.yaml','resume.json','progress.json')):
                evidence[str(p.resolve())]=hashlib.sha256(p.read_bytes()).hexdigest()
    source=Path(__file__).resolve()
    save_json(out/'analysis_provenance.json',dict(analysis_source=str(source),
        analysis_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),training_evidence_sha256=evidence,
        method='Offline analysis of saved interactive recordings only; no simulation or policy inference'))
    (out/'REPORT.md').write_text(f'''# Offline interactive review

Reviewed {summary['sessions']} sessions, {len(results)} attempts, {summary['total_simulation_seconds']:.3f} recorded seconds.
Entrance starts with loaded stair contact: {len(ascent)}. Recorded sustained top entry: {summary['top_entry_detected']}.
Distinct checkpoint hashes: {len(summary['checkpoint_hashes'])}. Different commands, starts and limits prevent a causal reward/limit comparison.

Read `attempts.csv`, `constant_command_windows.json`, `training_log_summary.json` (when supplied), and fill `observations.csv`.
`input_sha256.json` identifies original inputs and `analysis_provenance.json` identifies this analysis.

Target cost is sum(((q[t]-2*q[t-1]+q[t-2])/scale)^2), using 50 Hz policy ticks.
It is a normalized target second difference, not measured acceleration or third-derivative jerk.
Measured 8–30 Hz RMS uses 200 Hz joint samples and includes impacts and corrections.
The displayed bandpass is a zero-phase analysis filter, not a controller filter; do not infer lead/lag from it.
The four-second plot shows one selected joint but costs sum 12 joints and riser forces sum all feet.

Failure means >60-degree tilt or <0.12 m body clearance for 0.25 s. An incomplete recording is not automatically a fall/stall.
Top entry requires all feet past the staircase, prior platform support, upright posture and remaining in the lane for 0.5 s; top spawns are excluded.
Maximum body x and highest loaded step can include later/fall motion and are not traversal tests.
Four-second windows hold a fixed command, exclude startup/large tilt/low clearance, and never cross first stair contact.
After-contact windows need not be continuously on stairs. Pooled associations mix terrain phases and repeated windows and are not causal proof.

For the detailed 2026-10-03 interpretation, read Task_3/notes/21_INTERACTIVE_RUN_REVIEW_AND_OBSERVATIONS.md.
''')
    rows=''.join(f'<tr><td><a href="../interactive/{html.escape(r["run"])}/plots/index.html">{html.escape(r["run"])}</a></td><td>{r["limit_profile"]}</td><td>{r["category"]}</td><td>{r["duration_s"]:.2f}</td><td>{r["max_vx"]:.2f}</td><td>{r["max_base_x_m"]:.3f}</td><td>{r["max_tilt_deg"]:.1f}</td><td>{r["sustained_failure_s"]}</td></tr>' for r in results if r['samples'])
    body=f'<h1>Review of your actual interactive recordings</h1><p>{len(results)} attempts; raw files retained. No new simulation or policy inference was run.</p><p><a href="REPORT.md">Read conclusions</a> · <a href="attempts.csv">Every attempt</a> · <a href="observations.csv">Your observations worksheet</a> · <a href="constant_command_windows.json">Constant-command windows</a> · <a href="input_sha256.json">Input hashes</a></p>'
    body+='<h2>Start with these two figures</h2><p>Blue uses wider bounds, red uses tighter bounds. Compare the speeds too; different commands prevent a clean limit-only conclusion.</p><img src="all_ascent_progress.png"><p>Each dot is one four-second constant-command upright interval. Higher target cost often accompanies more rapid joint motion, but impacts and feedback can drive both.</p><img src="cost_vs_jitter.png">'
    body+='<h2>First-foot placement in every ascent</h2><p>These are measured heights at the first recorded vertical-face contact, not desired swing-height reward values. A low initial hit does not prove the foot can never recover or climb. Descent/top-spawn attempts are excluded.</p><img src="first_riser_clearance.png">'
    if train:body+='<h2>Was the penalty used in training?</h2><p>Yes. These are actual TensorBoard logs from updates 90001–90500. Raw cost, weighted contribution and measured robot jitter are different quantities.</p><img src="training_penalties.png">'
    for im in images:
        body+=f'<h2>{html.escape(im["run"])}</h2><p>Short event window {im["start_s"]:.2f}–{im["stop_s"]:.2f} s. The joint was selected for the largest 8–30 Hz RMS in this window. Top: requested/clamped/actual angle. Second: costs over all joints, without reward weights. Third: analysis-filtered measured motion; the controller was not filtered. Bottom: measured torque and riser force. Red dotted marks first riser/stair contact. A common spike does not prove which signal caused it.</p><img src="{im["image"]}">'
    body+='<h2>Every recorded attempt</h2><table><tr><th>Run</th><th>Limits</th><th>Start</th><th>Seconds</th><th>Max vx</th><th>Max x</th><th>Max tilt</th><th>Sustained failure at s</th></tr>'+rows+'</table>'
    (out/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Interactive review</title><style>body{font:16px system-ui;max-width:1200px;margin:25px auto;padding:15px;line-height:1.5}img{width:100%}table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:5px}</style>'+body)
    print(json.dumps(summary,indent=2));return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__)
    p.add_argument('--root',type=Path,default=Path('tools/results/interactive'))
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--training-log',type=Path)
    a=p.parse_args();review(a.root,a.out,a.training_log)
