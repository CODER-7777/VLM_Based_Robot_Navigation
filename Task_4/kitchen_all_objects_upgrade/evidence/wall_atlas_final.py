"""Local planar backsplash repair, using calibrated, depth-consistent photographs.
Hidden portions are inpainted tile color, not independently reconstructed.
"""
from pathlib import Path
import numpy as np,json,cv2,trimesh
from scipy.ndimage import distance_transform_edt
from PIL import Image
R=Path('/data/robotics/toshith/rxr_author/refined');W=R/'kitchen_all_upgrade';P=Path('/home/guest-isl/rishabh/custom/habitat_building_isaac_repaired/source/photos/2azQ1b91cZZ');cams={};K=None
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
boxes.setdefault('f7a060bfa1164b5e9c5cca04284f6d6b_i1_4.jpg',[]).append([470,620,900,985])
object_boxes=[]
for entry in json.loads((R/'toaster_selected/manifest.json').read_text()):
 if not isinstance(entry,str):continue
 path=Path(entry);path=path if path.is_absolute() else R/path;fit=json.loads(path.read_text())
 if fit['name'].startswith(('counter_','sink_')) or fit['name']=='rangetop':continue
 mp=Path(fit['world_mesh']);mp=mp if mp.is_absolute() else R/mp;bounds=trimesh.load(mp,force='mesh').bounds.copy();bounds[0]-=.025;bounds[1]+=.025
 corners=np.array([[x,y,z] for x in bounds[:,0] for y in bounds[:,1] for z in bounds[:,2]])
 object_boxes.append(corners)
planes=[('sink_back',0,-5.447,[4.41,7.10],[.932,1.40],[0,1,0]),('sink_right',1,7.103,[-5.447,-3.995],[.932,1.40],[-1,0,0]),('range_right',1,7.103,[-3.081,-2.236],[.932,1.40],[-1,0,0])]
report=[]
for name,axis,fixed,horizontal,vertical,normal in planes:
 w=int((horizontal[1]-horizontal[0])*650);h=int((vertical[1]-vertical[0])*650);xx,zz=np.meshgrid(np.linspace(*horizontal,w),np.linspace(vertical[1],vertical[0],h));pts=np.c_[xx.ravel(),np.full(w*h,fixed),zz.ravel()] if axis==0 else np.c_[np.full(w*h,fixed),xx.ravel(),zz.ravel()]
 normal=np.array(normal);probe=pts[::max(1,len(pts)//2000)];candidate=[]
 for ph,c in cams.items():
  if not (R/'kitchen/depth_v8'/(ph[:-4]+'.npy')).exists():continue
  eye=c['c2w'][:3,3];distance=np.linalg.norm(probe-eye,axis=1);cos=((eye-probe)*normal).sum(1)/distance
  if cos.mean()<.2 or distance.mean()>4:continue
  q=(probe-eye)@c['c2w'][:3,:3];z=-q[:,2];K=c['K'];u=K[0,0]*q[:,0]/np.maximum(z,.01)+K[0,2];v=K[1,2]-K[1,1]*q[:,1]/np.maximum(z,.01);ok=(z>.15)&(u>10)&(u<1270)&(v>10)&(v<1014)
  if ok.mean()<.1:continue
  candidate.append((float((ok*cos/distance**2).sum()),ph))
 candidate=sorted(candidate,reverse=True)[:12];sums=np.zeros((h,w,3));weights=np.zeros((h,w));views=[]
 for _,ph in candidate:
  c=cams[ph];K=c['K'];eye=c['c2w'][:3,3];q=(pts-eye)@c['c2w'][:3,:3];z=-q[:,2];u=K[0,0]*q[:,0]/np.maximum(z,.01)+K[0,2];v=K[1,2]-K[1,1]*q[:,1]/np.maximum(z,.01)
  good=(z>.15)&(u>10)&(u<1270)&(v>10)&(v<1014)
  for a,b,cc,d in boxes.get(ph,[]):good&=~((u>a-14)&(u<cc+14)&(v>b-14)&(v<d+14))
  for corners in object_boxes:
   qq=(corners-eye)@c['c2w'][:3,:3];zz=-qq[:,2]
   if zz.min()<.1 or zz.mean()>5:continue
   uu=K[0,0]*qq[:,0]/zz+K[0,2];vv=K[1,2]-K[1,1]*qq[:,1]/zz
   good&=~((u>uu.min()-10)&(u<uu.max()+10)&(v>vv.min()-10)&(v<vv.max()+10)&(z>zz.min()-.01))
  depth=np.load(R/'kitchen/depth_v8'/(ph[:-4]+'.npy'));du=K[0,0]*q[:,0]/np.maximum(z,.01)/2+320;dv=256-K[0,0]*q[:,1]/np.maximum(z,.01)/2
  dd=cv2.remap(depth.astype('float32'),du.astype('float32').reshape(h,w),dv.astype('float32').reshape(h,w),cv2.INTER_NEAREST,borderMode=cv2.BORDER_CONSTANT).ravel();good&=(dd>.1)&(np.abs(dd-z)<.05)
  image=np.asarray(Image.open(P/'undistorted_color_images'/ph).convert('RGB'),float)/255;col=cv2.remap(image,u.astype('float32').reshape(h,w),v.astype('float32').reshape(h,w),cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
  good&=(col.reshape(-1,3).mean(1)>.18)
  dist=np.linalg.norm(pts-eye,axis=1);cos=np.maximum(0,((eye-pts)*normal).sum(1))/dist;weight=((cos/dist**2)**3*good).reshape(h,w);weight*=np.minimum(1,distance_transform_edt(good.reshape(h,w))/12)
  if weight.sum()<1:continue
  sums+=col*weight[...,None];weights+=weight;views.append(ph)
 observed=weights>1e-8
 Image.fromarray((observed*255).astype('uint8')).save(W/(name+'_observed.png'))
 if not observed.any():
  # Completely hidden tile: repeat the photographed neighboring backsplash.
  reference=np.asarray(Image.open(W/'sink_back_tile.png').convert('RGB'),float)/255
  atlas=cv2.resize(reference,(w,h),interpolation=cv2.INTER_LINEAR)
  tex=W/(name+'_tile.png');Image.fromarray(np.clip(atlas*255,0,255).astype('uint8')).save(tex)
  row={'name':name,'axis':axis,'fixed':fixed,'horizontal':horizontal,'vertical':vertical,'normal':normal.tolist(),'texture':str(tex),'observed_fraction':0.,'views':[],'fallback':'neighboring photographic tile; fully masked foreground'};report.append(row);print('WALL_ATLAS_FALLBACK',name,flush=True);continue
 atlas=sums/np.maximum(weights[...,None],1e-8);_,near=distance_transform_edt(~observed,return_indices=True);atlas[~observed]=atlas[near[0][~observed],near[1][~observed]]
 small=cv2.resize(np.clip(atlas*255,0,255).astype('uint8'),(w//3,h//3),interpolation=cv2.INTER_AREA);mask=cv2.resize((~observed).astype('uint8')*255,(w//3,h//3),interpolation=cv2.INTER_NEAREST);smooth=cv2.inpaint(small,mask,9,cv2.INPAINT_TELEA);smooth=cv2.resize(smooth,(w,h),interpolation=cv2.INTER_CUBIC);atlas[~observed]=smooth[~observed]/255
 tex=W/(name+'_tile.png');Image.fromarray(np.clip(atlas*255,0,255).astype('uint8')).save(tex)
 row={'name':name,'axis':axis,'fixed':fixed,'horizontal':horizontal,'vertical':vertical,'normal':normal.tolist(),'texture':str(tex),'observed_fraction':float(observed.mean()),'views':views};report.append(row);print('WALL_ATLAS',name,row['observed_fraction'],flush=True)
(W/'wall_materials.json').write_text(json.dumps(report,indent=2))
