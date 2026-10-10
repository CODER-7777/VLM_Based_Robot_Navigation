"""Suppress underconstrained SH ripple; keep a coherent countertop texture."""
from pathlib import Path
import sys,json,shutil
import numpy as np
import trimesh
from scipy.spatial import cKDTree
R=Path('/data/robotics/toshith/rxr_author/refined');W=R/'split_visuals';O=W/'corner_v2'
sys.path.insert(0,str(W/'vendor'))
from plyfile import PlyData,PlyElement
source=np.load(O/'scene.npz');fit=np.load(O/'scene_refined.npz')
arrays={k:fit[k].copy() for k in fit.files};samples=np.load(O/'corner_samples.npz')
offset=len(arrays['means'])-len(samples['means']);local=arrays['means'][offset:];product=samples['product']
ids=offset+np.flatnonzero(product);means=arrays['means'][ids]
delta=arrays['sh'][ids]-source['sh'][ids]
quats=arrays['quats'][ids];w,x,y,z=quats.T
normals=np.stack([2*(x*z+w*y),2*(y*z-w*x),1-2*(x*x+y*y)],1)
tree=cKDTree(means);smooth=np.empty_like(delta)
for start in range(0,len(ids),8000):
 end=min(start+8000,len(ids));distance,neighbors=tree.query(means[start:end],k=24)
 weights=np.exp(-distance**2/(2*.0028**2))
 weights*=(normals[neighbors]*normals[start:end,None]).sum(-1)>.97
 weights/=np.maximum(weights.sum(1,keepdims=True),1e-8)
 smooth[start:end]=(delta[neighbors]*weights[:,:,None,None]).sum(1)
arrays['sh'][ids]=source['sh'][ids]+.30*smooth

# Preserve the original continuous UV pattern. Multi-view photo projection
# supplies a global exposure/color fit instead of a patchwork of view textures.
counter=(~product)&(np.abs(local[:,2]-.929)<.0001);counter_ids=np.flatnonzero(counter);points=local[counter_ids]
appearance=json.loads((O/'appearance.json').read_text());gain=np.array(appearance['fallback_exposure_gain'])
colors=np.clip((source['sh'][offset+counter_ids,0]*.28209479177387814+.5)*gain,0,1)
scene=trimesh.load(R/'kitchen/objects/toaster_v4/world_baked.glb',force='scene');C=np.array([[1,0,0],[0,0,1],[0,-1,0.]])
parts=[]
for node in scene.graph.nodes_geometry:
 transform,key=scene.graph[node];m=scene.geometry[key].copy();m.vertices=trimesh.transform_points(m.vertices,transform)@C;parts.append(m)
toaster=trimesh.util.concatenate(parts);rng=np.random.default_rng(42)
near=np.flatnonzero(np.linalg.norm(points[:,:2]-[4.52,-5.19],axis=1)<.31)
if len(near)>4500:near=rng.choice(near,4500,replace=False)
query=points[near].copy();query[:,2]+=.001
count=24;a=rng.random(count);b=rng.random(count)*2*np.pi
directions=np.stack([np.sqrt(a)*np.cos(b),np.sqrt(a)*np.sin(b),np.sqrt(1-a)],1)
origins=np.repeat(query,count,axis=0);rays=np.tile(directions,(len(query),1))
locations,ray_ids,_=toaster.ray.intersects_location(origins,rays,multiple_hits=False)
occlusion=np.zeros(len(origins));dist=np.linalg.norm(locations-origins[ray_ids],axis=1);occlusion[ray_ids]=np.exp(-dist/.065)
amount=occlusion.reshape(len(query),count).mean(1);distance,index=cKDTree(query[:,:2]).query(points[:,:2],k=4)
weights=1/np.maximum(distance,.002)**2;ao=(amount[index]*weights).sum(1)/weights.sum(1);ao[distance.min(1)>.06]=0
colors*=1-.55*ao[:,None];arrays['sh'][offset+counter_ids,0]=(colors-.5)/.28209479177387814
backup=O/'scene_pbr_fit_unfiltered.npz'
if not backup.exists():shutil.copy2(O/'scene_refined.npz',backup)
np.savez_compressed(O/'scene_refined.npz',**arrays)
N=len(arrays['means']);degree=int(arrays['sh_degree'])
fields=[(n,'f4') for n in ['x','y','z','nx','ny','nz']+[f'f_dc_{i}' for i in range(3)]+[f'f_rest_{i}' for i in range(((degree+1)**2-1)*3)]+['opacity']+[f'scale_{i}' for i in range(3)]+[f'rot_{i}' for i in range(4)]]
vertices=np.empty(N,dtype=fields);opacity=np.clip(arrays['opacities'],1e-6,1-1e-6)
values=np.concatenate([arrays['means'],np.zeros((N,3)),arrays['sh'][:,0],arrays['sh'][:,1:].transpose(0,2,1).reshape(N,-1),np.log(opacity/(1-opacity))[:,None],np.log(arrays['scales']),arrays['quats']],axis=1)
for i,name in enumerate(vertices.dtype.names):vertices[name]=values[:,i]
PlyData([PlyElement.describe(vertices,'vertex')],text=False).write(O/'scene_refined.ply')
report={'product_appearance_residual_weight':.30,'spatial_neighbors':24,'smoothing_sigma_m':.0028,'normal_cosine_threshold':.97,'counter_appearance':'Continuous source UV texture, median photographic exposure fit, geometry-based contact occlusion','geometry_changed':not np.array_equal(arrays['means'],source['means']),'note':'Conservative appearance blend chosen after novel-view inspection; not a relightable metal BRDF.'}
assert not report['geometry_changed']
(O/'stabilization.json').write_text(json.dumps(report,indent=2));print('STABILIZED_APPEARANCE_READY',json.dumps(report),flush=True)
