"""Replace underconstrained corner splats with dense, surface-anchored samples.

Private candidate only. Does not modify the live checkpoint or scene GLB.
Preserves texture UVs and samples the already fitted/repaired physical mesh.
"""
from pathlib import Path
import sys, json, time
import numpy as np
import trimesh
from PIL import Image

R=Path('/data/robotics/toshith/rxr_author/refined')
W=R/'split_visuals'
O=W/'corner_v2'
O.mkdir(exist_ok=True)
sys.path.insert(0,str(W/'vendor'))
from plyfile import PlyData, PlyElement
started=time.perf_counter()
lo=np.array([4.24,-5.56,.90])
hi=np.array([4.94,-4.70,1.75])
rng=np.random.default_rng(1234)
scene=trimesh.load(R/'toaster_selected/test.glb',force='scene')
parts=[]

def clip_polygon(polygon,axis,edge,positive):
    output=[]
    for i,b in enumerate(polygon):
        a=polygon[i-1]
        ain=(a[axis]>=edge) if positive else (a[axis]<=edge)
        bin=(b[axis]>=edge) if positive else (b[axis]<=edge)
        if ain!=bin:
            t=(edge-a[axis])/(b[axis]-a[axis])
            output.append(a+(b-a)*t)
        if bin:output.append(b)
    return output

for node in scene.graph.nodes_geometry:
    transform,key=scene.graph[node]
    mesh=scene.geometry[key]
    vertices=trimesh.transform_points(mesh.vertices,transform)
    if np.any(vertices.max(0)<lo) or np.any(vertices.min(0)>hi):continue
    tri=vertices[mesh.faces]
    selected=((tri.max(1)>=lo)&(tri.min(1)<=hi)).all(1)
    if not selected.any():continue
    uv=getattr(mesh.visual,'uv',None)
    mat=getattr(mesh.visual,'material',None)
    texture=getattr(mat,'baseColorTexture',None)
    if texture is None:texture=getattr(mat,'image',None)
    factor_value=getattr(mat,'baseColorFactor',None)
    factor=np.array([255,255,255,255] if factor_value is None else factor_value,dtype=float)
    if factor.max()>1:factor/=255.
    if texture is not None:texture=texture.convert('RGBA')
    clipped=[]
    for face in np.flatnonzero(selected):
        f=mesh.faces[face]
        polygon=[np.r_[vertices[v],uv[v] if uv is not None else [0,0]] for v in f]
        for axis in range(3):
            polygon=clip_polygon(polygon,axis,lo[axis],True)
            if len(polygon)<3:break
            polygon=clip_polygon(polygon,axis,hi[axis],False)
            if len(polygon)<3:break
        if len(polygon)<3:continue
        for i in range(1,len(polygon)-1):clipped.append([polygon[0],polygon[i],polygon[i+1]])
    if not clipped:continue
    triangles=np.array(clipped)
    normals=np.cross(triangles[:,1,:3]-triangles[:,0,:3],triangles[:,2,:3]-triangles[:,0,:3])
    twice=np.linalg.norm(normals,axis=1)
    good=twice>1e-10
    triangles=triangles[good];normals=normals[good]/twice[good,None];areas=twice[good]/2
    if not len(areas):continue
    product='toaster_v4' in str(node).lower()
    parts.append(dict(node=str(node),triangles=triangles,normals=normals,areas=areas,texture=texture,factor=factor,product=product))

total_area=sum(p['areas'].sum() for p in parts)
print('CORNER_SURFACE',len(parts),'parts',total_area,'m2',flush=True)
points=[];colors=[];normals=[];product_flags=[];radii=[];provenance=[]
for part in parts:
    area=part['areas'].sum()
    # More than one sample per output pixel even at close range. Surface geometry
    # is frozen, so no optimization can stretch it into wall/toaster floaters.
    spacing=.0013 if part['product'] else .0022
    count=max(128,int(np.ceil(area/spacing**2)))
    face=rng.choice(len(part['areas']),size=count,p=part['areas']/area)
    a=np.sqrt(rng.random(count));b=rng.random(count)
    bary=np.stack([1-a,a*(1-b),a*b],1)
    sample=(part['triangles'][face]*bary[:,:,None]).sum(1)
    if part['texture'] is not None:
        col=trimesh.visual.color.uv_to_color(sample[:,3:5],part['texture']).astype(float)/255.
        col=col[:,:3]*part['factor'][:3]
    else:col=np.broadcast_to(part['factor'][:3],(count,3)).copy()
    points.append(sample[:,:3]);colors.append(np.clip(col,0,1));normals.append(part['normals'][face]);product_flags.append(np.full(count,part['product']))
    radii.append(np.full(count,spacing*1.15))
    provenance.append({'node':part['node'],'area_m2':float(area),'samples':count,'product':part['product']})

means=np.concatenate(points).astype('float32')
norm=np.concatenate(normals).astype('float32')
colors=np.concatenate(colors).astype('float32')
product=np.concatenate(product_flags)
radii=np.concatenate(radii).astype('float32')
w=np.sqrt(np.maximum((1+norm[:,2])/2,1e-10))
quat=np.stack([w,-norm[:,1]/(2*w),norm[:,0]/(2*w),np.zeros_like(w)],1)
quat[norm[:,2]<-.9999]=[0,1,0,0]
quat/=np.linalg.norm(quat,axis=1,keepdims=True)
scales=np.stack([radii,radii,np.full_like(radii,.00015)],1)
source=np.load(W/'scene.npz')
outside=~((source['means']>=lo)&(source['means']<=hi)).all(1)
sh=np.zeros((len(means),source['sh'].shape[1],3),dtype='float32')
sh[:,0]=(colors-.5)/.28209479177387814
arrays={key:source[key].copy() for key in source.files}
new=dict(means=means,quats=quat,scales=scales,opacities=np.full(len(means),.99,dtype='float32'),sh=sh)
for key,value in new.items():arrays[key]=np.concatenate([source[key][outside],value])
np.savez_compressed(O/'scene.npz',**arrays)
np.savez_compressed(O/'corner_samples.npz',**new,product=product)
N=len(arrays['means']);degree=int(arrays['sh_degree'])
fields=[(n,'f4') for n in ['x','y','z','nx','ny','nz']+[f'f_dc_{i}' for i in range(3)]+[f'f_rest_{i}' for i in range(((degree+1)**2-1)*3)]+['opacity']+[f'scale_{i}' for i in range(3)]+[f'rot_{i}' for i in range(4)]]
vertices=np.empty(N,dtype=fields);opacity=np.clip(arrays['opacities'],1e-6,1-1e-6)
values=np.concatenate([arrays['means'],np.zeros((N,3)),arrays['sh'][:,0],arrays['sh'][:,1:].transpose(0,2,1).reshape(N,-1),np.log(opacity/(1-opacity))[:,None],np.log(arrays['scales']),arrays['quats']],axis=1)
for i,name in enumerate(vertices.dtype.names):vertices[name]=values[:,i]
PlyData([PlyElement.describe(vertices,'vertex')],text=False).write(O/'scene.ply')
report={'source':str(W/'scene.npz'),'reference_scene':str(R/'toaster_selected/test.glb'),'region':[lo.tolist(),hi.tolist()],'old_local_gaussians_removed':int((~outside).sum()),'surface_area_m2':float(total_area),'new_local_gaussians':len(means),'new_product_gaussians':int(product.sum()),'final_gaussians':N,'method':'Frozen exact clipped-triangle surface samples, original mesh UV colors, constant SH appearance; no photographic reconstruction claim','surface_max_error_m':0,'elapsed_seconds':time.perf_counter()-started,'parts':provenance}
(O/'construction.json').write_text(json.dumps(report,indent=2))
print('DENSE_CORNER_READY',json.dumps({k:v for k,v in report.items() if k!='parts'}),flush=True)
