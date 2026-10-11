from pathlib import Path
import sys,json,numpy as np,torch
from scipy.signal import butter,sosfiltfilt,welch
from scipy.stats import spearmanr
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
O=Path(__file__).resolve().parent;R=O.parents[1];H=R/'m2_training_artifacts/hardware_transfer_20260913';torch.set_num_threads(1)
a=np.load(O/'hardware_arrays.npz');t=a['t'];quat=a['quaternion_xyzw'];tilt=np.rad2deg(np.arccos(np.clip(1-2*(quat[:,0]**2+quat[:,1]**2),-1,1)))
u=np.arange(t[0],t[-1],.005);inter=lambda v:np.column_stack([np.interp(u,t,v[:,i]) for i in range(v.shape[1])]);q=inter(a['q']);target=inter(a['target']);command=inter(a['command']);sos=butter(3,[8,30],btype='bandpass',fs=200,output='sos');hf=sosfiltfilt(sos,q,axis=0);hft=sosfiltfilt(sos,target,axis=0)
windows=[]
for start in np.arange(15,t[-1]-4,4):
 m=(u>=start)&(u<start+4);r=(t>=start)&(t<start+4)
 if np.mean(np.linalg.norm(command[m],axis=1)>.08)<.95 or not a['moe'][r].all():continue
 windows.append(dict(t=float(start),q_hf_deg=float(np.rad2deg(np.sqrt(np.mean(hf[m]**2)))),target_hf_deg=float(np.rad2deg(np.sqrt(np.mean(hft[m]**2)))),mean_command=np.mean(command[m],axis=0).tolist(),max_tilt=float(tilt[r].max()),max_interval_ms=float(a['control_interval_ms'][r].max()),max_sensor_age_ms=float(a['sensor_age_ms'][r].max()),max_action_age_ms=float(a['action_age_ms'][r].max())))
# Separate per-contiguous-window spectra; never concatenate disjoint motion segments.
f,ps=welch(q[(u>=465)&(u<469)],fs=200,nperseg=400,axis=0);_,pt=welch(target[(u>=465)&(u<469)],fs=200,nperseg=400,axis=0)
z=np.load(H/'moe_stair_debug_20260921/full_stair_policy_trace.npz');h=z['history'].reshape(-1,5,45)[:,::-1].copy().reshape(-1,225);p=torch.jit.load(str(R/'m2_training_artifacts/moe_hw_candidate_90000/offline_inference.ts')).eval()
with torch.inference_mode():gates=np.concatenate([p.encoder.moe.gating_network(torch.from_numpy(h[i:i+256])).numpy() for i in range(0,len(h),256)])
print(p.encoder.moe.gating_network.code,flush=True)
gdiff=np.abs(np.diff(gates,axis=0)).sum(1);adiff=np.linalg.norm(np.diff(z['raw_action'],axis=0),axis=1)
r=json.load(open(H/'moe_stair_debug_20260921/full_stair_result.json'));fault=[x for x in r['rows'] if any(x['motor_faults'])]
summary={'windows':windows,'window_correlations':{key:float(spearmanr([w['q_hf_deg'] for w in windows],[w[key] for w in windows]).statistic) for key in ['target_hf_deg','max_tilt','max_interval_ms','max_sensor_age_ms','max_action_age_ms']},'faults':{'count':len(fault),'first_t':fault[0]['t'],'last_t':fault[-1]['t'],'phases':list(set(x['phase'] for x in fault)),'unique_codes':list(set(v for x in fault for v in x['motor_faults']))},'gates':{'shape':list(gates.shape),'min':float(gates.min()),'max':float(gates.max()),'max_sum_error':float(abs(gates.sum(1)-1).max()),'mean':gates.mean(0).tolist(),'median_L1_step':float(np.median(gdiff)),'p99_L1_step':float(np.quantile(gdiff,.99)),'gate_action_step_spearman':float(spearmanr(gdiff,adiff).statistic)},'timing_percentiles':{k:np.percentile(a[k][a['moe']],[50,95,99,100]).tolist() for k in ['sensor_age_ms','action_age_ms','control_interval_ms']}}
(O/'deep_hardware_summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps({k:v for k,v in summary.items() if k!='windows'},indent=2),flush=True)
fig,ax=plt.subplots(3,1,figsize=(14,10));
ax[0].plot([w['t'] for w in windows],[w['q_hf_deg'] for w in windows],'.-',label='measured q');ax[0].plot([w['t'] for w in windows],[w['target_hf_deg'] for w in windows],'.-',label='sent target');ax[0].set(ylabel='8–30 Hz RMS (deg)',title='Hardware: disjoint 4s moving windows, terrain unlabelled');ax[0].legend()
for j in [2,5,8,11]:ax[1].semilogy(f,ps[:,j],label=['FL','FR','RL','RR'][j//3]+' calf')
ax[1].set(xlim=(0,50),xlabel='Hz',ylabel='Position PSD (rad²/Hz)',title='Worst 465–469 s contiguous window');ax[1].legend()
tp=z['times'][:,0]-float(a['sequence_start_monotonic']);m=(tp>=465)&(tp<469);ax[2].plot(tp[m],gates[m]);ax[2].set(xlabel='Run time (s)',ylabel='Expert weight',title='MoE gate is a continuous mixture, not hard expert selection')
fig.tight_layout();fig.savefig(O/'hardware_spectra_gates.png',dpi=150)
