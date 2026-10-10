"""Photo-fit countertop, geometry-based contact occlusion, PBR-teacher SH fit.

All Gaussian positions, rotations and scales stay fixed on repaired surfaces.
Only the replacement toaster's appearance coefficients are optimized.
"""
from pathlib import Path
import sys,json,math,time,os
import numpy as np
from PIL import Image
import trimesh
from scipy.spatial import cKDTree
R=Path('/data/robotics/toshith/rxr_author/refined');W=R/'split_visuals';O=W/'corner_v2'
sys.path.insert(0,str(W/'vendor'))
os.environ.setdefault('TORCH_EXTENSIONS_DIR',str(W/'torch_extensions'))
os.environ.setdefault('TORCH_CUDA_ARCH_LIST','8.6')
os.environ.setdefault('MAX_JOBS','4')
os.environ['PATH']='/data/robotics/toshith/envs/kitchen3d/bin:'+os.environ.get('PATH','')
import torch
from gsplat import rasterization
from plyfile import PlyData,PlyElement
torch.manual_seed(42);rng=np.random.default_rng(42);C0=.28209479177387814
started=time.perf_counter()
raw=np.load(O/'scene.npz');arrays={k:raw[k].copy() for k in raw.files}
samples=np.load(O/'corner_samples.npz');local_count=len(samples['means']);offset=len(arrays['means'])-local_count
local=arrays['means'][offset:]
product=samples['product'].astype(bool)
counter=(~product)&(np.abs(local[:,2]-.929)<.0001)
ids=np.flatnonzero(counter);points=local[ids]
colors=arrays['sh'][offset:][ids,0]*C0+.5
records=json.loads((W/'data/cameras.json').read_text())
sum_colors=np.zeros_like(colors);sum_weights=np.zeros(len(points));photo_hits=np.zeros(len(points),int)
for record in records:
 if record['split']!='train':continue
 c2w=np.array(record['c2w_raw_gl']);K=np.array(record['K'])
 cam=(points-c2w[:3,3])@c2w[:3,:3];z=-cam[:,2]
 u=K[0,0]*cam[:,0]/np.maximum(z,.001)+K[0,2]
 v=K[1,2]-K[1,1]*cam[:,1]/np.maximum(z,.001)
 x=np.clip(u.astype(int),0,record['width']-1);y=np.clip(v.astype(int),0,record['height']-1)
 photo=np.asarray(Image.open(W/'data/photos'/record['name']).convert('RGB'),dtype=float)/255.
 mask=np.load(W/'data/photos'/(record['name']+'.mask.npy'))
 valid=(z>.1)&(u>2)&(u<record['width']-3)&(v>2)&(v<record['height']-3)&(mask[y,x]>.5)
 # Use measured depth where present. It rejects image colors from occluding
 # objects without borrowing either held-out photograph.
 depth=np.load(W/'data/photos'/(record['name']+'.depth.npy'))
 measured=depth[y,x]
 if not depth.any():
  cached=np.load(R/'kitchen/depth_v8'/(record['name'][:-4]+'.npy'))
  # Cached scan depth was rendered with centered intrinsics and equal fx/fy.
  cu=K[0,0]*cam[:,0]/np.maximum(z,.001)+record['width']/2
  cv=record['height']/2-K[0,0]*cam[:,1]/np.maximum(z,.001)
  cx=np.clip(cu.astype(int),0,cached.shape[1]-1);cy=np.clip(cv.astype(int),0,cached.shape[0]-1)
  measured=cached[cy,cx]
 valid&=(measured>.1)&(np.abs(measured-z)<.045)
 distance=np.linalg.norm(points-c2w[:3,3],axis=1)
 weight=np.maximum(c2w[2,3]-points[:,2],0)/np.maximum(distance,.1)**3
 weight*=valid
 sum_colors+=photo[y,x]*weight[:,None];sum_weights+=weight;photo_hits+=valid
supported=sum_weights>0
target=colors.copy();target[supported]=sum_colors[supported]/sum_weights[supported,None]
if supported.any():
 # Exposure-match fallback UV colors where all photographs hide the surface.
 gain=np.clip(np.median(target[supported],axis=0)/np.maximum(np.median(colors[supported],axis=0),.05),.5,1.8)
 target[~supported]=np.clip(colors[~supported]*gain,0,1)
else:gain=np.ones(3)
print('COUNTER_PHOTO_FIT',len(ids),int(supported.sum()),'supported',flush=True)

# Estimate soft contact occlusion from the actual fitted toaster, not an image
# overlay. This is ambient occlusion, not a measured HDR illumination solution.
scene=trimesh.load(R/'kitchen/objects/toaster_v4/world_baked.glb',force='scene')
C=np.array([[1,0,0],[0,0,1],[0,-1,0.]])
meshes=[]
for node in scene.graph.nodes_geometry:
 transform,key=scene.graph[node];m=scene.geometry[key].copy()
 m.vertices=trimesh.transform_points(m.vertices,transform)@C
 meshes.append(m)
toaster=trimesh.util.concatenate(meshes)
near=np.flatnonzero(np.linalg.norm(points[:,:2]-[4.52,-5.19],axis=1)<.31)
if len(near)>4500:near=rng.choice(near,4500,replace=False)
query=points[near].copy();query[:,2]+=.001
count=24;a=rng.random(count);b=rng.random(count)*2*np.pi
directions=np.stack([np.sqrt(a)*np.cos(b),np.sqrt(a)*np.sin(b),np.sqrt(1-a)],1)
origins=np.repeat(query,count,axis=0);rays=np.tile(directions,(len(query),1))
locations,ray_ids,_=toaster.ray.intersects_location(origins,rays,multiple_hits=False)
occlusion=np.zeros(len(origins));dist=np.linalg.norm(locations-origins[ray_ids],axis=1)
occlusion[ray_ids]=np.exp(-dist/.065)
amount=occlusion.reshape(len(query),count).mean(1)
tree=cKDTree(query[:,:2]);d,index=tree.query(points[:,:2],k=4)
weights=1/np.maximum(d,.002)**2
ao=(amount[index]*weights).sum(1)/weights.sum(1)
ao[np.min(d,axis=1)>.06]=0
target*=1-.55*ao[:,None]
arrays['sh'][offset+ids,0]=(target-.5)/C0
print('CONTACT_OCCLUSION',len(query),'samples',float(ao.max()),flush=True)

# Fit view-dependent product color against the original metallic material's
# teacher renders. Geometry, support height, opacity and coverage cannot drift.
product_ids=offset+np.flatnonzero(product)
device='cuda';degree=int(arrays['sh_degree'])
params={n:torch.as_tensor(arrays[n][product_ids],device=device) for n in ['means','quats','scales','opacities']}
initial=torch.as_tensor(arrays['sh'][product_ids],device=device)
sh=torch.nn.Parameter(initial.clone())
optimizer=torch.optim.Adam([sh],lr=.012)
views=[]
for record in records:
 if record['split']!='train':continue
 teacher=np.asarray(Image.open(W/'data/teacher'/(record['name']+'.png')).convert('RGBA'),dtype=np.float32)/255.
 mask=teacher[...,3]>.98
 if mask.sum()<30:continue
 matrix=np.linalg.inv(np.asarray(record['c2w_raw_gl'])@np.diag([1.,-1.,-1.,1.]))
 views.append((record,torch.as_tensor(teacher[...,:3],device=device),torch.as_tensor(mask,device=device),torch.as_tensor(matrix[None],dtype=torch.float32,device=device),torch.as_tensor(np.array(record['K'])[None],dtype=torch.float32,device=device)))
assert views,'No usable PBR supervision'
losses=[]
for step in range(2200):
 record,teacher,mask,view,K=views[int(torch.randint(len(views),(1,)))]
 prediction,alpha,_=rasterization(**params,colors=sh,viewmats=view,Ks=K,width=record['width'],height=record['height'],sh_degree=degree,render_mode='RGB',near_plane=.05,far_plane=12.,packed=True)
 loss=(prediction[0][mask]-teacher[mask]).abs().mean()+.0003*sh[:,1:].square().mean()+.0001*(sh[:,0]-initial[:,0]).square().mean()
 loss.backward();optimizer.step();optimizer.zero_grad(set_to_none=True)
 with torch.no_grad():
  sh[:,0].clamp_(-.5/C0,.5/C0);sh[:,1:].clamp_(-.7,.7)
 if step%200==0:
  losses.append({'step':step,'loss':float(loss.detach())});print('PBR_APPEARANCE',losses[-1],flush=True)
 if step==1400:
  for group in optimizer.param_groups:group['lr']*=.35
arrays['sh'][product_ids]=sh.detach().cpu().numpy()
np.savez_compressed(O/'scene_refined.npz',**arrays)
N=len(arrays['means'])
fields=[(n,'f4') for n in ['x','y','z','nx','ny','nz']+[f'f_dc_{i}' for i in range(3)]+[f'f_rest_{i}' for i in range(((degree+1)**2-1)*3)]+['opacity']+[f'scale_{i}' for i in range(3)]+[f'rot_{i}' for i in range(4)]]
vertices=np.empty(N,dtype=fields);opacity=np.clip(arrays['opacities'],1e-6,1-1e-6)
values=np.concatenate([arrays['means'],np.zeros((N,3)),arrays['sh'][:,0],arrays['sh'][:,1:].transpose(0,2,1).reshape(N,-1),np.log(opacity/(1-opacity))[:,None],np.log(arrays['scales']),arrays['quats']],axis=1)
for i,name in enumerate(vertices.dtype.names):vertices[name]=values[:,i]
PlyData([PlyElement.describe(vertices,'vertex')],text=False).write(O/'scene_refined.ply')
report={'counter_gaussians':len(ids),'counter_photo_supported':int(supported.sum()),'fallback_exposure_gain':gain.tolist(),'contact_occlusion_samples':len(query),'contact_occlusion_max':float(ao.max()),'pbr_teacher_train_views':len(views),'pbr_appearance_iterations':2200,'geometry_optimized':False,'product_gaussians':int(product.sum()),'loss_history':losses,'elapsed_seconds':time.perf_counter()-started,'limits':['Local repaired corner only; broader scan distortions remain.','SH fits pre-rendered metallic appearance; it is not a relightable PBR material.','Countertop contact shading is approximate ambient occlusion.']}
(O/'appearance.json').write_text(json.dumps(report,indent=2));print('APPEARANCE_READY',json.dumps(report),flush=True)
