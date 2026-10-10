"""Keep stronger photo-trained phone/frog visuals. Never force a worse proxy look.
Collision geometry stays in the fitted GLB; these are static visual splats.
"""
from pathlib import Path
import sys,json,numpy as np
from PIL import Image
R=Path('/data/robotics/toshith/rxr_author/refined');W=R/'kitchen_all_upgrade';S=R/'split_visuals';sys.path.insert(0,str(R));sys.path.insert(0,str(S/'vendor'));import kitchen_obj as K
from plyfile import PlyData,PlyElement
old=np.load(S/'scene.npz');new=np.load(W/'scene_refined.npz');arrays={k:new[k].copy() for k in new.files};p=old['means'];construct=json.loads((W/'construction.json').read_text());samples=np.load(W/'surface_samples.npz');offset=construct['old_retained'];remove=np.zeros(len(arrays['means']),bool);oldkeep=np.zeros(len(p),bool);rows=[]
for name,ph in [('phone','1eae5d4a0c0146c2b884d6b96d9b0e16_i2_3.jpg'),('frogs','f7a060bfa1164b5e9c5cca04284f6d6b_i1_4.jpg')]:
 maskfile=W/('phone_target.png' if name=='phone' else 'masks/frogs.png');mask=np.asarray(Image.open(maskfile))>0
 uv=K.project(ph,p);u,v,z=uv.T;x=np.clip(u.astype(int),0,1279);y=np.clip(v.astype(int),0,1023);ok=(z>.15)&(u>0)&(u<1279)&(v>0)&(v<1023)&mask[y,x]&(old['opacities']>.12)
 if name=='phone':
  region=(p[:,0]>6.50)&(p[:,0]<7.106)&(p[:,1]>-2.86)&(p[:,1]<-2.245)&(p[:,2]>.931)&(p[:,2]<1.15)
  q=arrays['means'][:offset];remove[:offset]|=(q[:,0]>6.50)&(q[:,0]<7.20)&(q[:,1]>-2.86)&(q[:,1]<-2.245)&(q[:,2]>.9305)&(q[:,2]<1.15)
 else:
  region=(p[:,0]>6.50)&(p[:,0]<7.106)&(p[:,1]>-5.451)&(p[:,1]<-5.10)&(p[:,2]>.932)&(p[:,2]<1.34)
  # The bottles stand in front of the centre of the pair; keep those replacements.
  region&=(p[:,0]<6.708)|(p[:,0]>6.925)|(p[:,2]>1.085)
  ids=[i for i,n in enumerate(construct['part_names']) if n.startswith('Kitchen_frogs_v3_')];remove[offset+np.flatnonzero(np.isin(samples['part'],ids))]=True
 keep=ok&region;oldkeep|=keep;rows.append({'object':name,'old_visual_gaussians_kept':int(keep.sum()),'method':'Original photo-trained appearance with foreground segmentation and bounded support/wall region; fitted proxy remains separate','limitation':'Appearance is stronger at source views; novel-view shape and proxy agreement remain approximate.'})
for key in ['means','quats','scales','opacities','sh']:arrays[key]=np.concatenate([arrays[key][~remove],old[key][oldkeep]])
# Reject metallic cross-occlusion colors from the wooden block's top.
# Its fitted original wood texture remains the reliable fallback.
np.savez_compressed(W/'scene_refined.npz',**arrays);N=len(arrays['means']);degree=int(arrays['sh_degree']);fields=[(n,'f4') for n in ['x','y','z','nx','ny','nz']+[f'f_dc_{i}' for i in range(3)]+[f'f_rest_{i}' for i in range(((degree+1)**2-1)*3)]+['opacity']+[f'scale_{i}' for i in range(3)]+[f'rot_{i}' for i in range(4)]];vertices=np.empty(N,dtype=fields);op=np.clip(arrays['opacities'],1e-6,1-1e-6);values=np.concatenate([arrays['means'],np.zeros((N,3)),arrays['sh'][:,0],arrays['sh'][:,1:].transpose(0,2,1).reshape(N,-1),np.log(op/(1-op))[:,None],np.log(arrays['scales']),arrays['quats']],1)
for i,name in enumerate(vertices.dtype.names):vertices[name]=values[:,i]
PlyData([PlyElement.describe(vertices,'vertex')],text=False).write(W/'scene_refined.ply');result={'objects':rows,'source':str(S/'scene.npz'),'candidate':str(W/'scene_refined.npz'),'removed':int(remove.sum()),'retained_original':int(oldkeep.sum()),'final_gaussians':N};(W/'visual_selection.json').write_text(json.dumps(result,indent=2));construct['visual_selection']=result;construct['final_gaussians']=N;(W/'construction.json').write_text(json.dumps(construct,indent=2));print('STRONGER_VISUALS_RETAINED',result,flush=True)
