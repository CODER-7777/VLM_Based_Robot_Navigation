import json,sys
from pathlib import Path
import numpy as np
from scipy.signal import butter,sosfiltfilt
O=Path(__file__).resolve().parent;R=O.parents[1];H=R/'m2_training_artifacts/hardware_transfer_20260913';r=json.load(open(H/'moe_stair_debug_20260921/full_stair_result.json'));rows=r['rows'];a=np.load(O/'hardware_arrays.npz');t=a['t'];tau=np.array([x['tau_est'] for x in rows]);fault=np.array([x['motor_faults'] for x in rows]);curr=np.array([x['motor_q_current'] for x in rows]);mask=a['moe']&(t>8)&(np.linalg.norm(a['command'],axis=1)>.08)
K=np.kron(np.eye(4),np.array([[20,0,0],[0,25,10],[0,10,20]]));D=.7/20*K
pred=(a['target']-a['q'])@K.T-a['dq']@D.T;diag=20*(a['target']-a['q'])-.7*a['dq']
limit=np.tile([12.,12.,24.],4)
u=tau.copy();u[:,1::3]-=.5*tau[:,2::3]
up=pred.copy();up[:,1::3]-=.5*pred[:,2::3]
motorclip=np.clip(up,-limit,limit);motorclip[:,1::3]+=.5*motorclip[:,2::3]
summary={'joint_clip_rmse_Nm':np.sqrt(np.mean((np.clip(pred[mask],-limit,limit)-tau[mask])**2,axis=0)).tolist(),'motor_clip_rmse_Nm':np.sqrt(np.mean((motorclip[mask]-tau[mask])**2,axis=0)).tolist(),'joint_torque_limit_exceed_fraction':np.mean(abs(tau[mask])>limit+.1,axis=0).tolist(),'inferred_motor_output_peak_Nm':abs(u[mask]).max(0).tolist(),'coupled_tau_est_rmse_Nm' :np.sqrt(np.mean((pred[mask]-tau[mask])**2,axis=0)).tolist(),'diagonal_tau_est_rmse_Nm':np.sqrt(np.mean((diag[mask]-tau[mask])**2,axis=0)).tolist(),'coupled_fit_multiplier':(np.sum(pred[mask]*tau[mask],axis=0)/np.sum(pred[mask]**2,axis=0)).tolist(),'peak_abs_tau_est_Nm':abs(tau[mask]).max(0).tolist(),'fault_rows_during_commanded_motion':int((mask&np.any(fault!=0,axis=1)).sum()),'total_motion_rows':int(mask.sum()),'current_peak_abs_A':abs(curr[mask]).max(0).tolist()}
# Correlation only: repeated power frames are not independent fault events.
sos=butter(3,[8,30],btype='bandpass',fs=200,output='sos');u=np.arange(t[0],t[-1],.005);q=np.column_stack([np.interp(u,t,a['q'][:,i]) for i in range(12)]);hf=sosfiltfilt(sos,q,axis=0);power=np.mean(hf**2,axis=1);nearest=np.minimum(np.searchsorted(u,t),len(u)-1)
summary['q_hf_rms_deg_fault_rows']=float(np.rad2deg(np.sqrt(power[nearest[mask&np.any(fault!=0,axis=1)]] .mean())))
summary['q_hf_rms_deg_no_fault_rows']=float(np.rad2deg(np.sqrt(power[nearest[mask&~np.any(fault!=0,axis=1)]] .mean())))
(O/'torque_summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
