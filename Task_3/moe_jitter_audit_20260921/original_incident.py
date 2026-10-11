import json
from pathlib import Path
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
O=Path(__file__).resolve().parent;R=O.parents[1];rows=json.load(open(R/'m2_training_artifacts/hardware_transfer_20260913/moe_full_controls_candidate_20260921/pi_full_result.json'))['rows'];t=np.array([r['t'] for r in rows]);q=np.array([r['q'] for r in rows]);tar=np.array([r['target'] for r in rows]);quat=np.array([r['quaternion_xyzw'] for r in rows]);tilt=np.degrees(np.arccos(np.clip(1-2*(quat[:,0]**2+quat[:,1]**2),-1,1)));cmd=np.array([r.get('operator',{}).get('command',[0,0,0]) for r in rows]);dt=np.median(np.diff(t));active=np.array([r["phase"]=="moe" for r in rows]);k=int(np.argmax(np.where(active,tilt,-1)))
first_tip=int(np.flatnonzero(active&(tilt>60))[0]);
summary={'first_60deg_tilt_time_s':float(t[first_tip]),'file':'moe_full_controls_candidate_20260921/pi_full_result.json','rows':len(rows),'median_logging_dt_s':float(dt),'nominal_Nyquist_Hz':float(.5/dt),'global_peak_including_recovery_deg':float(tilt.max()),'peak_tilt_deg':float(tilt[k]),'peak_tilt_time_s':float(t[k]),'peak_tilt_phase':rows[k]['phase'],'command_at_peak_tilt':cmd[k].tolist(),'high_frequency_jitter_identifiable':False};(O/'original_incident_summary.json').write_text(json.dumps(summary,indent=2))
fig,axs=plt.subplots(4,3,figsize=(15,10),sharex=True);m=(t>=t[first_tip]-6)&(t<t[first_tip]+2);labels=[f'{l} {j}' for l in ['FL','FR','RL','RR'] for j in ['hip','thigh','calf']]
for j,ax in enumerate(axs.flat):
 ax.plot(t[m],np.degrees(q[m,j]),'.-',ms=2,label='measured q');ax.plot(t[m],np.degrees(tar[m,j]),label='sent target');ax.set_title(labels[j]);ax.axvline(t[first_tip],ls=':',color='r');ax.grid(alpha=.2)
axs[0,0].legend();fig.suptitle(f'Original incident: first >60° tilt at {t[first_tip]:.2f}s; 20 Hz log cannot resolve 8–30 Hz jitter');fig.supxlabel('Run time (s)');fig.supylabel('Angle (degrees)');fig.tight_layout();fig.savefig(O/'original_incident_joint_angles.png',dpi=150)
print(summary)
