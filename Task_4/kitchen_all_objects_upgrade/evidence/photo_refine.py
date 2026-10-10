"""Ground the fixed prop surfaces in their actual photos. No geometry fitting.
Visible, segmented, front-facing surfaces only; preserve unseen finish colors.
"""
from pathlib import Path
import json,sys,numpy as np,cv2,time
from PIL import Image
R=Path('/data/robotics/toshith/rxr_author/refined');W=R/'kitchen_all_upgrade';sys.path.insert(0,str(R));sys.path.insert(0,str(R/'split_visuals/vendor'))
import kitchen_obj as K
from plyfile import PlyData,PlyElement
C0=.28209479177387814;start=time.time();raw=np.load(W/'scene.npz');arrays={k:raw[k].copy() for k in raw.files};samples=np.load(W/'surface_samples.npz');parts=samples['part'];points=samples['means'];normals=samples['normals'];report=json.loads((W/'construction.json').read_text());offset=report['old_retained'];names=report['part_names']
items={}
for line in (R/'kitchen/kitchen_items.txt').read_text().splitlines():
 t=line.split()
 if len(t)==6:
  try:items[t[0]]=(t[1],list(map(int,t[2:])))
  except ValueError:pass
items.update(frogs=('f7a060bfa1164b5e9c5cca04284f6d6b_i1_4.jpg',[485,650,880,960]),paper_towel=('f7a060bfa1164b5e9c5cca04284f6d6b_i2_4.jpg',[925,0,1120,260]))
alias={'hot_tap':'hot_tap_s4_style','soap_dish':'soap_dish_p','soap_pump':'soap_pump_p_lathe','air_gap':'air_gap_p_lathe','coffee_machine':'coffee_machine2'}
(W/'masks').mkdir(exist_ok=True);evidence=[]
for item,(ph,box) in items.items():
 if item in ['phone','toaster']:continue
 tag='Kitchen_'+alias.get(item,item)+'_'
 selectedparts=[i for i,n in enumerate(names) if n.startswith(tag)]
 if item=='knife_block':selectedparts=[i for i,n in enumerate(names) if n.startswith('Kitchen_knife_block_v3_')]
 if not selectedparts:continue
 ids=np.flatnonzero(np.isin(parts,selectedparts));p=points[ids];maskpath=W/'masks'/(item+'.png')
 if maskpath.exists():mask=np.asarray(Image.open(maskpath))>0
 else:
  mask=K.sam_mask(ph,box);Image.fromarray((mask*255).astype('uint8')).save(maskpath)
 mask=cv2.erode(mask.astype('uint8'),np.ones((3,3),np.uint8)).astype(bool)
 uv=K.project(ph,p);u,v,z=uv.T;x=np.clip(u.astype(int),0,1279);y=np.clip(v.astype(int),0,1023);direction=K.CAMS[ph]['c2w'][:3,3]-p;direction/=np.linalg.norm(direction,axis=1)[:,None];facing=(normals[ids]*direction).sum(1)
 good=(z>.1)&(u>0)&(u<1279)&(v>0)&(v<1023)&mask[y,x]&(facing>.25)
 photo=K.photo(ph)[y,x].astype('float32')/255
 # Prevent foreground cross-occlusions from painting a different finish.
 if item=='blue_jug':good&=(photo[:,2]>photo[:,0]*1.06)&(photo[:,2]>photo[:,1]*.9)&(photo.mean(1)<.58)
 if item=='knife_block':
  body=p[:,2]<1.065
  good&=(~body)|((photo[:,0]>photo[:,2]*1.12)&(photo[:,0]>photo[:,1]*1.02))
 if item=='frogs':good&=(photo[:,1]>photo[:,0]*.90)&(photo[:,1]>photo[:,2]*.85)
 validids=offset+ids[good];existing=arrays['sh'][validids,0]*C0+.5;target=photo[good];blend=.78
 if item in ['canister_l','canister_r','knife_block','grinder']:blend=.88
 color=existing*(1-blend)+target*blend;arrays['sh'][validids,0]=(color-.5)/C0
 # Photo radiance already includes the primary-view highlights. Reduce extra
 # synthetic highlights on supervised portions to avoid doubling the lustre.
 arrays['sh'][validids,1:]*=.45
 evidence.append({'object':item,'photo':ph,'surface_samples':len(ids),'photo_supported':int(good.sum()),'fraction':float(good.mean()),'mask':str(maskpath)})
 print('PHOTO_SURFACE',item,int(good.sum()),'of',len(ids),flush=True)
# Restore the final miniature-jug geometry from the fitted surface samples.
ids=np.flatnonzero(np.isin(parts,[i for i,n in enumerate(names) if n.startswith('Kitchen_blue_jug_v4_')]))
for key in ['means','quats','scales']:arrays[key][offset+ids]=samples[key][ids]
np.savez_compressed(W/'scene_refined.npz',**arrays); N=len(arrays['means']);degree=int(arrays['sh_degree']);fields=[(n,'f4') for n in ['x','y','z','nx','ny','nz']+[f'f_dc_{i}' for i in range(3)]+[f'f_rest_{i}' for i in range(((degree+1)**2-1)*3)]+['opacity']+[f'scale_{i}' for i in range(3)]+[f'rot_{i}' for i in range(4)]];vertices=np.empty(N,dtype=fields);op=np.clip(arrays['opacities'],1e-6,1-1e-6);values=np.concatenate([arrays['means'],np.zeros((N,3)),arrays['sh'][:,0],arrays['sh'][:,1:].transpose(0,2,1).reshape(N,-1),np.log(op/(1-op))[:,None],np.log(arrays['scales']),arrays['quats']],1)
for i,name in enumerate(vertices.dtype.names):vertices[name]=values[:,i]
PlyData([PlyElement.describe(vertices,'vertex')],text=False).write(W/'scene_refined.ply');(W/'photo_appearance.json').write_text(json.dumps({'objects':evidence,'geometry_changed':False,'elapsed_s':time.time()-start,'limitations':'Colors are photo-grounded, hidden surfaces remain approximate; this is fixed-light Gaussian appearance, not relightable PBR.'},indent=2));print('PHOTO_REFINE_READY',flush=True)
