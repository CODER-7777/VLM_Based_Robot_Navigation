from pathlib import Path
import sys,json,numpy as np,cv2
from PIL import Image
R=Path('/data/robotics/toshith/rxr_author/refined');W=R/'kitchen_all_upgrade';S=R/'split_visuals';sys.path.insert(0,str(R));sys.path.insert(0,str(S/'vendor'));import kitchen_obj as K
from plyfile import PlyData,PlyElement
old=np.load(S/'scene.npz');raw=np.load(W/'scene_refined.npz');arrays={k:raw[k].copy() for k in raw.files}
p=old['means'];ph='f7a060bfa1164b5e9c5cca04284f6d6b_i1_4.jpg';mask=np.array(Image.open(W/'masks/frogs.png'))>0;mask=cv2.dilate(mask.astype('uint8'),np.ones((7,7),np.uint8)).astype(bool);u,v,z=K.project(ph,p).T;x=np.clip(u.astype(int),0,1279);y=np.clip(v.astype(int),0,1023);keep=(z>.1)&(u>0)&(u<1279)&(v>0)&(v<1023)&mask[y,x]&(p[:,0]>6.55)&(p[:,0]<7.20)&(p[:,1]>-5.52)&(p[:,1]<-5.0)&(p[:,2]>.925)&(p[:,2]<1.36)&(old['opacities']>.05);keep&=(p[:,0]<6.708)|(p[:,0]>6.925)|(p[:,2]>1.085)

walls=json.loads((W/'wall_materials.json').read_text());wall_count=sum(len(np.arange(row['horizontal'][0]+.0035/2,row['horizontal'][1],.0035))*len(np.arange(row['vertical'][0]+.0035/2,row['vertical'][1],.0035)) for row in walls)
N=len(arrays['means']);nf=int(keep.sum());start=N-wall_count-nf;new=old['means'][keep].copy();shift=np.array([-.095,.075,.005]);new+=shift
arrays['means'][start:start+nf]=new
np.savez_compressed(W/'scene_refined.npz',**arrays);N=len(arrays['means']);degree=int(arrays['sh_degree']);fields=[(n,'f4') for n in ['x','y','z','nx','ny','nz']+[f'f_dc_{i}' for i in range(3)]+[f'f_rest_{i}' for i in range(((degree+1)**2-1)*3)]+['opacity']+[f'scale_{i}' for i in range(3)]+[f'rot_{i}' for i in range(4)]];vertices=np.empty(N,dtype=fields);op=np.clip(arrays['opacities'],1e-6,1-1e-6);values=np.concatenate([arrays['means'],np.zeros((N,3)),arrays['sh'][:,0],arrays['sh'][:,1:].transpose(0,2,1).reshape(N,-1),np.log(op/(1-op))[:,None],np.log(arrays['scales']),arrays['quats']],1)
for i,name in enumerate(vertices.dtype.names):vertices[name]=values[:,i]
PlyData([PlyElement.describe(vertices,'vertex')],text=False).write(W/'scene_refined.ply')

result=json.loads((W/'visual_selection.json').read_text());result['frogs'].update(method='Prior photo-trained decorative reconstruction moved rigidly inward from the backsplash',translation_m=shift.tolist(),limitation='Sparse original reconstruction; visible shape and separate proxy are approximate. Not an exact newly reconstructed statue.');(W/'visual_selection.json').write_text(json.dumps(result,indent=2));d=json.loads((W/'construction.json').read_text());d['visual_selection']=result;(W/'construction.json').write_text(json.dumps(d,indent=2));print('FROG_RIGID_CORRECTION',nf,new.min(0),new.max(0),flush=True)
