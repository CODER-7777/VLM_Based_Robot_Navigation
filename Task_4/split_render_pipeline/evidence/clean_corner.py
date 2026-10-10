"""Remove local Gaussian floaters unsupported by the repaired visual geometry."""
from pathlib import Path
import json,shutil,sys
import numpy as np
import trimesh
from plyfile import PlyData,PlyElement
R=Path('/data/robotics/toshith/rxr_author/refined');W=R/'split_visuals'
sys.path.insert(0,str(W/'vendor'))
source=W/'scene_trained_unfiltered.npz'
if not source.exists():shutil.copy2(W/'scene.npz',source)
data=np.load(source);arrays={key:data[key].copy() for key in data.files}
lo=np.array([4.30,-5.53,.926]);hi=np.array([4.68,-4.92,1.60])
scene=trimesh.load(R/'toaster_selected/test.glb',force='scene')
parts=[]
for node in scene.graph.nodes_geometry:
 transform,key=scene.graph[node];mesh=scene.geometry[key]
 vertices=trimesh.transform_points(mesh.vertices,transform)
 if np.any(vertices.max(0)<lo-.025) or np.any(vertices.min(0)>hi+.025):continue
 triangle=vertices[mesh.faces]
 keep=((triangle.max(1)>=lo-.025)&(triangle.min(1)<=hi+.025)).all(1)
 if keep.any():parts.append(trimesh.Trimesh(vertices,mesh.faces[keep],process=False))
surface=trimesh.util.concatenate(parts)
surface.remove_unreferenced_vertices()
means=arrays['means'];region=((means>=lo)&(means<=hi)).all(1);ids=np.flatnonzero(region)
_,dist,_=trimesh.proximity.closest_point(surface,means[ids])
keep=np.ones(len(means),bool);keep[ids[dist>.008]]=False
for key,value in arrays.items():
 if value.ndim and len(value)==len(means):arrays[key]=value[keep]
local=((arrays['means']>=lo)&(arrays['means']<=hi)).all(1)
arrays['scales'][local]=np.minimum(arrays['scales'][local],.004)
np.savez_compressed(W/'scene.npz',**arrays)
N=len(arrays['means']);degree=int(arrays['sh_degree'])
fields=[(n,'f4') for n in ['x','y','z','nx','ny','nz']+[f'f_dc_{i}' for i in range(3)]+[f'f_rest_{i}' for i in range(((degree+1)**2-1)*3)]+['opacity']+[f'scale_{i}' for i in range(3)]+[f'rot_{i}' for i in range(4)]]
vertices=np.empty(N,dtype=fields);opacity=np.clip(arrays['opacities'],1e-6,1-1e-6)
values=np.concatenate([arrays['means'],np.zeros((N,3)),arrays['sh'][:,0],arrays['sh'][:,1:].transpose(0,2,1).reshape(N,-1),np.log(opacity/(1-opacity))[:,None],np.log(arrays['scales']),arrays['quats']],axis=1)
for i,name in enumerate(vertices.dtype.names):vertices[name]=values[:,i]
PlyData([PlyElement.describe(vertices,'vertex')],text=False).write(W/'scene.ply')
report={'source_checkpoint':str(source),'reference_surface':str(R/'toaster_selected/test.glb'),'region_m':[lo.tolist(),hi.tolist()],'distance_tolerance_m':.008,'local_splat_sigma_cap_m':.004,'checked_gaussians':len(ids),'removed_unsupported_gaussians':int((~keep).sum()),'final_gaussians':N,'reference_triangles':len(surface.faces),'scope':'Local toaster/cabinet corner only; global validation and photorealism are not guaranteed by surface proximity.'}
(W/'corner_cleaning.json').write_text(json.dumps(report,indent=2));print('CORNER_CLEANED',json.dumps(report),flush=True)
