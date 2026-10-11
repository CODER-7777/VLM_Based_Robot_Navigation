import json, numpy as np
from pathlib import Path
from scipy.signal import butter,sosfiltfilt,welch
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path('/home/pil-lab/toshith'); O=R/'m2_training_artifacts/moe_jitter_audit_20260921'; H=R/'m2_training_artifacts/hardware_transfer_20260913'
r=json.load(open(H/'moe_stair_debug_20260921/full_stair_result.json'));rows=r.pop('rows');t=np.array([x['t'] for x in rows]);a={k:np.array([x[k] for x in rows],dtype=float) for k in ['q','dq','target','gyro','quaternion_xyzw','sensor_age_ms','action_age_ms','control_interval_ms']};a['command']=np.array([x.get('operator',{}).get('command',[0,0,0]) for x in rows]);a['moe']=np.array([x['phase']=='moe' for x in rows]);a['t']=t;a['sequence_start_monotonic']=r['sequence_start_monotonic'];np.savez_compressed(O/'hardware_arrays.npz',**a)
valid=a['moe']&(t>12)&(np.linalg.norm(a['command'],axis=1)>.08)
# Differentiate resampled position; compare low-pass velocity to reject differentiation noise.
u=np.arange(t[0],t[-1],.005); interp=lambda v:np.column_stack([np.interp(u,t,v[:,i]) for i in range(v.shape[1])]);q=interp(a['q']);dq=interp(a['dq']);tar=interp(a['target']);mask=np.interp(u,t,valid.astype(float))>.999
lp=butter(3,5,fs=200,output='sos');qd=sosfiltfilt(lp,np.gradient(q,.005,axis=0),axis=0);v=sosfiltfilt(lp,dq,axis=0)
ratio=(v[mask]*qd[mask]).sum(0)/(v[mask]**2).sum(0);corr=[np.corrcoef(v[mask,i],qd[mask,i])[0,1] for i in range(12)]
hp=butter(3,[8,30],btype='bandpass',fs=200,output='sos');hf=sosfiltfilt(hp,q,axis=0);ht=sosfiltfilt(hp,tar,axis=0)
windows=[]
for start in np.arange(15,u[-1]-6,2):
 m=(u>=start)&(u<start+4)
 if mask[m].mean()>.95:
  windows.append((float(np.sqrt(np.mean(hf[m]**2))),float(start)))
windows.sort(reverse=True);worst=windows[0][1]
summary={'source':'full_stair_result.json','timing':r['timing'],'velocity_fit_qdot_over_reported_dq':ratio.tolist(),'velocity_correlation':corr,'q_hf_8_30hz_rms_deg':np.rad2deg(np.sqrt(np.mean(hf[mask]**2,axis=0))).tolist(),'target_hf_8_30hz_rms_deg':np.rad2deg(np.sqrt(np.mean(ht[mask]**2,axis=0))).tolist(),'worst_windows_rms_rad_start_s':windows[:12],'motor_fault_nonzero_rows':sum(any(x['motor_faults']) for x in rows),'moving_samples':int(mask.sum())}
contract=json.load(open(H/'moe_continuous_candidate_20260921/contract.json'));bounds=np.array(contract['hardware_joint_limits']['proposed_intersection_position_rad']);lo,hi=bounds[:,0]+.05,bounds[:,1]-.05
summary['at_target_bound_fraction_per_joint']=np.mean((abs(a['target'][valid]-lo)<1e-5)|(abs(a['target'][valid]-hi)<1e-5),axis=0).tolist()
(O/'hardware_summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2),flush=True)
labels=[f'{l} {j}' for l in ['FL','FR','RL','RR'] for j in ['hip','thigh','calf']]; fig,axs=plt.subplots(4,3,figsize=(16,10),sharex=True)
m=(u>=worst)&(u<worst+4)
for i,ax in enumerate(axs.flat):
 ax.plot(u[m],np.rad2deg(q[m,i]),label='measured q',lw=1);ax.plot(u[m],np.rad2deg(tar[m,i]),label='sent target',lw=.8,alpha=.7);ax.set_title(labels[i]);ax.grid(alpha=.2)
axs[0,0].legend();fig.suptitle('Saved hardware: largest 8–30 Hz angle window during commanded motion (terrain unlabelled)');fig.supxlabel('Run time (s)');fig.supylabel('Angle (degrees)');fig.tight_layout();fig.savefig(O/'hardware_joint_angles.png',dpi=150);plt.close(fig)
fig,axs=plt.subplots(2,2,figsize=(13,8));
for i in [1,2,7,8]:
 f,p=welch(q[m,i],fs=200,nperseg=400);axs[0,0].semilogy(f,p,label=labels[i])
axs[0,0].set(xlim=(0,50),xlabel='Hz',ylabel='rad²/Hz',title='Contiguous worst-window position spectrum');axs[0,0].legend()
axs[0,1].bar(np.arange(12)-.2,np.rad2deg(np.sqrt(np.mean(hf[mask]**2,axis=0))),.4,label='q');axs[0,1].bar(np.arange(12)+.2,np.rad2deg(np.sqrt(np.mean(ht[mask]**2,axis=0))),.4,label='target');axs[0,1].set(xticks=range(12),xticklabels=labels,ylabel='8–30 Hz RMS (deg)');axs[0,1].tick_params(axis='x',rotation=70);axs[0,1].legend()
axs[1,0].plot(u[m],qd[m,2],label='d(q)/dt, 5 Hz LP');axs[1,0].plot(u[m],v[m,2],label='reported dq, 5 Hz LP');axs[1,0].set(title='FL calf velocity consistency',xlabel='Run time (s)',ylabel='rad/s');axs[1,0].legend()
axs[1,1].plot(t[::10],a['command'][::10]);axs[1,1].axvspan(worst,worst+4,alpha=.2,color='r');axs[1,1].set(xlabel='Run time (s)',title='Commands (vx, vy, yaw rate)')
fig.tight_layout();fig.savefig(O/'hardware_jitter_diagnostics.png',dpi=150)
