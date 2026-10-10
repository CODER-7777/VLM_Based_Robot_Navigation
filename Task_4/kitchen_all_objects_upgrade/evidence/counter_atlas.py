"""Reproject only depth-consistent stone pixels onto entire physical slabs.
Geometry unchanged. Calibrated photos, object masks, exposure correction,
weighted feathering and nearest supported infill of hidden stone.
"""
from pathlib import Path
import json,numpy as np,cv2,time
from scipy.spatial import cKDTree
import trimesh
from scipy.ndimage import distance_transform_edt,gaussian_filter
from PIL import Image
R=Path('/data/robotics/toshith/rxr_author/refined');O=R/'kitchen_all_upgrade';O.mkdir(exist_ok=True)
P=Path('/home/guest-isl/rishabh/custom/habitat_building_isaac_repaired/source/photos/2azQ1b91cZZ')
cams={};K=None
for line in (P/'undistorted_camera_parameters/2azQ1b91cZZ.conf').read_text().splitlines():
 t=line.split()
 if t and t[0]=='intrinsics_matrix':K=np.array(list(map(float,t[1:]))).reshape(3,3)
 elif t and t[0]=='scan':cams[t[2]]={'K':K.copy(),'c2w':np.array(list(map(float,t[3:19]))).reshape(4,4)}
boxes={}
for line in (R/'kitchen/kitchen_items.txt').read_text().splitlines():
 t=line.split()
 if len(t)==6:
  try:boxes.setdefault(t[1],[]).append(list(map(float,t[2:])))
  except ValueError:pass
spec=json.loads((R/'kitchen/counters_spec.json').read_text())
print('SPEC_TYPE',type(spec),flush=True)
if isinstance(spec,dict):spec=spec.get('counters',spec)
# Reuse the final exact polygons; spec z is the slab underneath the 2mm surface.
slabs=[('sinkrun',[[4.41,-5.446],[7.1,-5.446],[7.1,-3.995],[6.45,-3.995],[6.45,-4.82],[4.41,-4.82]],.929),('rangeside',[[6.45,-3.081],[7.1,-3.081],[7.1,-2.236],[6.45,-2.236]],.929),('prep',[[1.55,-4.95],[2.105,-4.95],[2.105,-2.235],[1.55,-2.235]],.935),('island',[[3.85,-3.74],[5.39,-3.74],[5.47,-3.66],[5.47,-2.12],[5.39,-2.04],[3.85,-2.04],[3.77,-2.12],[3.77,-3.66]],.943),('bar',[[1.2,-4.97],[1.55,-4.97],[1.55,-2.225],[2.27,-2.225],[2.27,-1.9],[1.2,-1.9]],1.112)]
manifest=json.loads((R/'toaster_selected/manifest.json').read_text())
props=[]
for entry in manifest:
 if not isinstance(entry,str):continue
 fit=json.loads((R/entry).read_text()) if not Path(entry).is_absolute() else json.loads(Path(entry).read_text())
 n=fit.get('name','')
 if n.startswith(('counter','sink','rangetop')):continue
 meshpath=Path(fit['world_mesh']);meshpath=meshpath if meshpath.is_absolute() else R/meshpath
 if meshpath.exists():
  mesh=trimesh.load(meshpath,force='mesh');bounds=mesh.bounds.copy()
  bounds[0,:2]=np.minimum(bounds[0,:2],np.array(fit['delete_aabb'])[0,:2]);bounds[1,:2]=np.maximum(bounds[1,:2],np.array(fit['delete_aabb'])[1,:2]);props.append((n,bounds))
report=[]
for name,poly,height in slabs:
 poly=np.array(poly);lo=poly.min(0);hi=poly.max(0);shape=np.maximum(128,np.ceil((hi-lo)*450).astype(int));w,h=shape
 x=np.linspace(lo[0],hi[0],w);y=np.linspace(hi[1],lo[1],h);xx,yy=np.meshgrid(x,y)
 pts=np.c_[xx.ravel(),yy.ravel(),np.full(w*h,height)]
 boundary=np.c_[(poly[:,0]-lo[0])/(hi[0]-lo[0])*(w-1),(hi[1]-poly[:,1])/(hi[1]-lo[1])*(h-1)].astype(np.int32)
 mask=np.zeros((h,w),np.uint8);cv2.fillPoly(mask,[boundary],1)
 probes=pts[::max(1,len(pts)//3000)];candidates=[]
 for color,c in cams.items():
  if not (R/'kitchen/depth_v8'/(color[:-4]+'.npy')).exists():continue
  eye=c['c2w'][:3,3]
  if eye[2]<height+.18 or np.linalg.norm(eye-(np.r_[(lo+hi)/2,height]))>4:continue
  q=(probes-eye)@c['c2w'][:3,:3];z=-q[:,2];K=c['K']
  u=K[0,0]*q[:,0]/np.maximum(z,.01)+K[0,2];v=K[1,2]-K[1,1]*q[:,1]/np.maximum(z,.01)
  ok=(z>.2)&(u>12)&(u<1268)&(v>12)&(v<1012)
  if ok.mean()<.08:continue
  distance=np.linalg.norm(probes-eye,axis=1);score=((eye[2]-height)/np.maximum(distance,.2)**3*ok).sum()
  candidates.append((float(score),color))
 candidates=sorted(candidates,reverse=True)[:14]
 layers=[];weights=[];names=[]
 clean=mask.ravel().astype(bool)
 for pname,bounds in props:
  if abs(bounds[0,2]-height)>.05:continue
  pad=.04 if pname in ['phone_v2','grinder_v2','bottles_v20','bottles_v21','bottles_v22','bottles_v23'] else .016
  clean&=~((pts[:,0]>bounds[0,0]-pad)&(pts[:,0]<bounds[1,0]+pad)&(pts[:,1]>bounds[0,1]-pad)&(pts[:,1]<bounds[1,1]+pad))
 # Original fragmented phone had a much larger footprint than the replacement.
 if name=='rangeside':clean&=~((pts[:,0]>6.73)&(pts[:,1]>-2.70)&(pts[:,1]<-2.31))
 for _,color in candidates:
  c=cams[color];K=c['K'];eye=c['c2w'][:3,3];q=(pts-eye)@c['c2w'][:3,:3];z=-q[:,2]
  u=K[0,0]*q[:,0]/np.maximum(z,.01)+K[0,2];v=K[1,2]-K[1,1]*q[:,1]/np.maximum(z,.01)
  ok=(z>.2)&(u>10)&(u<1269)&(v>10)&(v<1013)&clean
  for box in boxes.get(color,[]):
   a,b,cc,d=box;ok&=~((u>a-12)&(u<cc+12)&(v>b-12)&(v<d+12))
  depth=np.load(R/'kitchen/depth_v8'/(color[:-4]+'.npy'))
  du=K[0,0]*q[:,0]/np.maximum(z,.01)/2+depth.shape[1]/2
  dv=depth.shape[0]/2-K[0,0]*q[:,1]/np.maximum(z,.01)/2
  dd=cv2.remap(depth.astype('float32'),du.astype('float32').reshape(h,w),dv.astype('float32').reshape(h,w),cv2.INTER_NEAREST,borderMode=cv2.BORDER_CONSTANT).ravel()
  # Only the existing planar stone can supervise the appearance, not scan fragments.
  ok&=(dd>.1)&(np.abs(dd-z)<.042)
  photo=np.asarray(Image.open(P/'undistorted_color_images'/color).convert('RGB'),dtype='float32')/255
  col=cv2.remap(photo,u.astype('float32').reshape(h,w),v.astype('float32').reshape(h,w),cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
  # Reject deep-black fragments and overexposed pale object surfaces.
  ok&=(col.reshape(-1,3).mean(1)>.13)&(col.reshape(-1,3).mean(1)<.91)
  distance=np.linalg.norm(pts-eye,axis=1)
  weight=((eye[2]-height)/np.maximum(distance,.2)**3).reshape(h,w)*ok.reshape(h,w)
  if ok.sum()<100:continue
  # Feather occlusion boundaries before blending views.
  weight*=np.minimum(1,distance_transform_edt(ok.reshape(h,w))/14)
  layers.append(col);weights.append(weight);names.append(color)
 if not layers:raise RuntimeError('No observed counter '+name)
 layers=np.stack(layers);weights=np.stack(weights)
 # Match photographic exposure only in shared visible stone, with a robust RGB gain.
 primary=int(np.argmax(weights.sum((1,2))));gains=[]
 for i in range(len(layers)):
  overlap=(weights[i]>.12)&(weights[primary]>.12)
  gain=np.ones(3)
  if overlap.sum()>400:
   gain=np.clip(np.median(layers[primary][overlap]/np.maximum(layers[i][overlap],.05),axis=0),.78,1.25)
  layers[i]*=gain;gains.append(gain.tolist())
 # Strong preference for the clearest camera retains actual stone grain.
 weights=weights**3
 summed=weights.sum(0);covered=summed>1e-8
 atlas=(layers*weights[...,None]).sum(0)/np.maximum(summed[...,None],1e-8)
 _,nearest=distance_transform_edt(~covered,return_indices=True)
 atlas[~covered]=atlas[nearest[0][~covered],nearest[1][~covered]]
 # Synthesise hidden support material from observed stone, never object pixels.
 # Low-frequency inpainting and a photo-derived grain patch avoid streaking.
 invalid=(~covered).astype('uint8')*255
 small=cv2.resize((np.clip(atlas,0,1)*255).astype('uint8'),(max(32,w//4),max(32,h//4)),interpolation=cv2.INTER_AREA)
 smask=cv2.resize(invalid,(small.shape[1],small.shape[0]),interpolation=cv2.INTER_NEAREST)
 small=cv2.inpaint(small,smask,7,cv2.INPAINT_TELEA)
 smooth=cv2.resize(small,(w,h),interpolation=cv2.INTER_CUBIC).astype(float)/255
 residual=atlas-gaussian_filter(atlas,sigma=(3,3,0))
 cleanpoints=np.argwhere(covered & (distance_transform_edt(covered)>12))
 rng=np.random.default_rng(56)
 if len(cleanpoints):
  take=cleanpoints[rng.integers(len(cleanpoints),size=w*h)];grain=residual[take[:,0],take[:,1]].reshape(h,w,3)
  smooth+=gaussian_filter(grain,sigma=(.65,.65,0))*.7
 atlas[~covered]=np.clip(smooth[~covered],0,1)
 Image.fromarray((np.clip(atlas,0,1)*255).astype('uint8')).save(O/(name+'_stone.png'))
 Image.fromarray((covered*255).astype('uint8')).save(O/(name+'_coverage.png'))
 row={'name':name,'xy_min':lo.tolist(),'xy_max':hi.tolist(),'top_z':height,'size':[int(w),int(h)],'observed_fraction':float(covered[mask.astype(bool)].mean()),'views':names,'primary':names[primary],'exposure_gains':gains,'texture':str(O/(name+'_stone.png')),'hidden_infill':'nearest observed stone, softened; not independently observed'}
 report.append(row);print('ATLAS_READY',name,row['observed_fraction'],names[primary],flush=True)
(O/'counter_materials.json').write_text(json.dumps(report,indent=2))
