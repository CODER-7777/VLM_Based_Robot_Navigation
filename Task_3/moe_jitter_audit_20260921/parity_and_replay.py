from pathlib import Path
import sys,json,hashlib,numpy as np,torch
R=Path('/home/pil-lab/toshith');O=Path(__file__).resolve().parent;H=R/'m2_training_artifacts/hardware_transfer_20260913';C=H/'moe_continuous_candidate_20260921';sys.path.insert(0,str(C));from moe_observation import MoeObservation
sys.path.insert(0,str(R/'svanm2_moe_hardware_audit'));from controller import TARGET_MIN,TARGET_MAX,J_LEG
contract=json.load(open(C/'contract.json'));adapter=MoeObservation(contract);torch.set_num_threads(1);p=torch.jit.load(str(R/'m2_training_artifacts/moe_hw_candidate_90000/offline_inference.ts')).eval()
def infer(h):
 with torch.inference_mode():return p(torch.from_numpy(h.reshape(-1,5,45)[:,::-1].copy().reshape(-1,225))).numpy()
h=np.fromfile(C/'parity_history.f32',dtype=np.float32).reshape(-1,225);a=np.fromfile(C/'parity_actions.f32',dtype=np.float32).reshape(-1,12);pred=infer(h)
np.testing.assert_allclose(pred,a,rtol=1e-4,atol=1e-5)
np.testing.assert_allclose(TARGET_MIN,adapter.bounds[:,0]+.05,atol=1e-6);np.testing.assert_allclose(TARGET_MAX,adapter.bounds[:,1]-.05,atol=1e-6)
z=np.load(H/'moe_stair_debug_20260921/full_stair_policy_trace.npz');hh=z['history'];aa=z['raw_action'];pp=np.concatenate([infer(hh[i:i+256]) for i in range(0,len(hh),256)])
error=pp-aa
# Replay isolation: zero only the velocity term of every frame, preserving all other recorded inputs.
novel=hh.copy().reshape(-1,5,45);novel[:,:,21:33]=0;novel=novel.reshape(-1,225)
no_dq=np.concatenate([infer(novel[i:i+256]) for i in range(0,len(novel),256)])
# Gate probabilities via frozen scripted gating submodule; inspect code separately before interpreting.
print(p.encoder.moe.code)
summary={'fixture_count':len(h),'fixture_max_abs':float(abs(pred-a).max()),'recorded_frames':len(hh),'replay_max_abs':float(abs(error).max()),'replay_rms':float(np.sqrt(np.mean(error**2))),'replay_allclose_1e4_1e5':bool(np.allclose(pp,aa,rtol=1e-4,atol=1e-5)),'zero_dq_raw_action_rms_difference':float(np.sqrt(np.mean((no_dq-pp)**2))),'effective_K_leg':(J_LEG.T@np.diag(20/np.array([8,8,16])**2)@J_LEG).tolist(),'files_sha256':{str(f.relative_to(R)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [R/'m2_training_artifacts/moe_hw_candidate_90000/offline_inference.ts',C/'policy.onnx',C/'operator_control.py',C/'moe_observation.py',C/'contract.json']}}
(O/'parity_summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
np.savez_compressed(O/'policy_replay.npz',time=z['times'][:,0],action=pp,action_without_dq=no_dq)
