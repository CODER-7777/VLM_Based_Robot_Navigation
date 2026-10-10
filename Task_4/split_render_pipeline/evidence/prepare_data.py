"""Prepare a kitchen-only Gaussian baseline from calibrated photos and depth.

Cached depth is rendered scan geometry, not claimed to be raw sensor depth.
Repaired wall and selected toaster replace their old points. Their appearance
is supervised by real photos and by separate PBR toaster renders respectively.
"""
import sys,json
from pathlib import Path
import numpy as np
from PIL import Image
import trimesh
sys.path.insert(0,'/data/robotics/toshith/rxr_author/refined')
from kitchen_obj import CAMS,DEPTH,PHOTOS
R=Path('/data/robotics/toshith/rxr_author/refined');W=R/'split_visuals'
D=W/'data';D.mkdir(exist_ok=True);(D/'photos').mkdir(exist_ok=True);(D/'teacher').mkdir(exist_ok=True)
rng=np.random.default_rng(42)
width,height=640,512
primary='58348305b0f84dd8b161aaf2d5b945ef_i2_4.jpg'
targets=np.array([[5.7,-4.3,1.1],[4.52,-5.19,1.04],[6.8,-5.1,1.1],[6.8,-2.6,1.1]])
choices=[]
for name,c in CAMS.items():
 path=Path(DEPTH)/(name[:-4]+'.npy')
 if not path.exists():continue
 pos=c['c2w'][:3,3]
 if np.linalg.norm((pos-targets[0])[:2])>4.1 or not .8<pos[2]<2.4:continue
 q=(targets-pos)@c['c2w'][:3,:3];z=-q[:,2]
 fx,fy,cx,cy=c['K'];u=fx*q[:,0]/np.maximum(z,1e-6)+cx;v=cy-fy*q[:,1]/np.maximum(z,1e-6)
 depth=np.load(path);vis=0
 for uu,vv,zz in zip(u,v,z):
  if zz>.3 and 20<uu<1260 and 20<vv<1004:
   dd=float(depth[min(511,int(vv/2)),min(639,int(uu/2))])
   if dd>zz-.4:vis+=1
 if vis or name==primary:choices.append((-vis,np.linalg.norm(pos-targets[0]),name))
choices.sort()
names=[n for _,_,n in choices[:36]]
if primary not in names and primary in CAMS:names.insert(0,primary)
# Keep one distinct scan position for a real held-out-view check.
panos=list(dict.fromkeys(n.split('_')[0] for n in names))
holdout=next((p for p in reversed(panos) if p!=primary.split('_')[0]),None)
oldlo=np.array([4.38,-5.38,.932]);oldhi=np.array([4.66,-4.99,1.19])
corners=np.array([[x,y,z] for x in [oldlo[0],oldhi[0]] for y in [oldlo[1],oldhi[1]] for z in [oldlo[2],oldhi[2]]])
wall=json.loads((R/'toaster_wall_repair/patch_spec.json').read_text())
records=[];all_points=[];all_colors=[];all_normals=[];measured_count=0
for index,name in enumerate(names):
 c=CAMS[name];s=width/1280;fx,fy,cx,cy=np.array(c['K'])*s
 photo=np.asarray(Image.open(Path(PHOTOS)/'undistorted_color_images'/name).convert('RGB').resize((width,height),Image.Resampling.LANCZOS))
 Image.fromarray(photo).save(D/'photos'/name,quality=97)
 q=(corners-c['c2w'][:3,3])@c['c2w'][:3,:3];z=-q[:,2]
 mask=np.ones((height,width),np.uint8)
 if (z>.05).all():
  u=fx*q[:,0]/z+cx;v=cy-fy*q[:,1]/z
  x0=max(0,int(np.floor(u.min()))-4);x1=min(width,int(np.ceil(u.max()))+4)
  y0=max(0,int(np.floor(v.min()))-4);y1=min(height,int(np.ceil(v.max()))+4)
  if x1>x0 and y1>y0:mask[y0:y1,x0:x1]=0
 K=[[fx,0,cx],[0,fy,cy],[0,0,1]]
 records.append({'name':name,'c2w_raw_gl':c['c2w'].tolist(),'K':K,'width':width,'height':height,'split':'val' if name.startswith(str(holdout)) else 'train'})
 path=Path(DEPTH)/(name[:-4]+'.npy')
 measured=Path(PHOTOS)/'undistorted_depth_images'/(name.replace('_i','_d')[:-4]+'.png')
 if measured.exists():
  dep=np.asarray(Image.open(measured).resize((width,height),Image.Resampling.NEAREST),dtype=np.float32)/4000.
  measured_count+=1
 else:
  dep=np.asarray(Image.fromarray(np.load(path).astype('float32'),mode='F').resize((width,height),Image.Resampling.NEAREST))
 np.save(D/'photos'/(name+'.depth.npy'),dep if measured.exists() else np.zeros_like(dep))
 yy,xx=np.mgrid[0:height:2,0:width:2];zz=dep[::2,::2]
 # Measured depth is aligned to the real calibrated K; cached mesh depth is centered.
 q=np.stack([(xx+.5-(cx if measured.exists() else width/2))/fx*zz,-(yy+.5-(cy if measured.exists() else height/2))/(fy if measured.exists() else fx)*zz,-zz],-1)
 points=q.reshape(-1,3)@c['c2w'][:3,:3].T+c['c2w'][:3,3]
 pu=fx*q[...,0]/np.maximum(zz,1e-6)+cx;pv=cy-fy*q[...,1]/np.maximum(zz,1e-6)
 colors=photo[np.clip(pv.astype(int),0,height-1),np.clip(pu.astype(int),0,width-1)].reshape(-1,3)/255.
 valid=(zz.reshape(-1)>.1)&(zz.reshape(-1)<5.5)&(points[:,0]>2.4)&(points[:,0]<8.8)&(points[:,1]>-7)&(points[:,1]<-.8)&(points[:,2]>-.3)&(points[:,2]<3.)
 coverage=np.asarray(Image.fromarray(valid.reshape(height//2,width//2).astype(np.uint8)).resize((width,height),Image.Resampling.NEAREST))
 mask*=coverage
 np.save(D/'photos'/(name+'.mask.npy'),mask)
 dy,dx=np.gradient(q,axis=(0,1));normal=np.cross(dy,dx).reshape(-1,3)@c['c2w'][:3,:3].T
 normal/=np.maximum(np.linalg.norm(normal,axis=1,keepdims=True),1e-8)
 valid &= (np.linalg.norm(dx,axis=2).reshape(-1)<.10)&(np.linalg.norm(dy,axis=2).reshape(-1)<.10)
 valid &= ~((points>=oldlo)&(points<=oldhi)).all(1)
 for low,high in wall['delete_boxes']:
  valid &= ~((points>=low)&(points<=high)).all(1)
 # Do not initialize from held-out photo colors.
 if records[-1]['split']=='train':all_points.append(points[valid]);all_colors.append(colors[valid]);all_normals.append(normal[valid])
C=np.array([[1,0,0],[0,0,1],[0,-1,0.]])
def add_textured_mesh(path,count):
 scene=trimesh.load(path,force='scene');area=sum(m.area for m in scene.geometry.values())
 for node in scene.graph.nodes_geometry:
  transform,key=scene.graph[node];mesh=scene.geometry[key]
  num=max(100,int(count*mesh.area/max(area,1e-8)))
  points,ids=trimesh.sample.sample_surface(mesh,num,seed=42)
  bary=trimesh.triangles.points_to_barycentric(mesh.triangles[ids],points)
  uv=(mesh.visual.uv[mesh.faces[ids]]*bary[:,:,None]).sum(1)
  mat=mesh.visual.material;image=getattr(mat,'baseColorTexture',None)
  if image is None:image=getattr(mat,'image',None)
  colors=trimesh.visual.color.uv_to_color(uv,image)[:,:3]/255. if image is not None else np.full((num,3),.55)
  points=trimesh.transform_points(points,transform)@C
  normal=mesh.face_normals[ids]@transform[:3,:3].T@C
  normal/=np.maximum(np.linalg.norm(normal,axis=1,keepdims=True),1e-8)
  all_points.append(points);all_colors.append(colors);all_normals.append(normal)
add_textured_mesh(R/'kitchen/objects/toaster_v4/world_baked.glb',16000)
add_textured_mesh(R/'toaster_wall_repair/wall_patch.glb',24000)
points=np.concatenate(all_points);colors=np.concatenate(all_colors);normals=np.concatenate(all_normals)
# Voxel sampling bounds the initial model and keeps aligned real-world units.
order=rng.permutation(len(points));points=points[order];colors=colors[order];normals=normals[order]
_,unique=np.unique(np.floor(points/.004).astype(np.int32),axis=0,return_index=True)
if len(unique)>350000:unique=rng.choice(unique,350000,replace=False)
points=points[unique].astype(np.float32);colors=colors[unique].astype(np.float32);normals=normals[unique].astype(np.float32)
np.savez_compressed(D/'initial_points.npz',means=points,colors=colors,normals=normals)
(D/'cameras.json').write_text(json.dumps(records,indent=2))
meta={'views':len(records),'panoramas':len(panos),'train_views':sum(c['split']=='train' for c in records),'validation_views':sum(c['split']=='val' for c in records),'holdout_panorama':holdout,'gaussians':len(points),'width':width,'height':height,'raw_world_units':'metres, Z up','measured_depth_views':measured_count,'depth_initialization':'Aligned measured depth where available (uint16/4000 metres); cached Habitat v8 scan depth elsewhere','edited_geometry':'Old toaster/return-wall points removed; selected licensed toaster and repaired wall sampled instead','old_toaster_box':[oldlo.tolist(),oldhi.tolist()]}
(W/'dataset.json').write_text(json.dumps(meta,indent=2));print('GAUSSIAN_DATA_READY',json.dumps(meta),flush=True)
