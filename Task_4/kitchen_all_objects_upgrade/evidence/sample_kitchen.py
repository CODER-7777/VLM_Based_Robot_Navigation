"""Dense fixed surfaces for all repaired kitchen props and their supports.
True-to-geometry geometry; approximate photographic environment highlights.
Never claim these fixed-light splats are a relightable physical material.
"""
from pathlib import Path
import sys,json,time,numpy as np,trimesh
from PIL import Image
from scipy.spatial import cKDTree
R=Path('/data/robotics/toshith/rxr_author/refined');O=R/'kitchen_all_upgrade';W=R/'split_visuals';sys.path.insert(0,str(W/'vendor'))
from plyfile import PlyData,PlyElement
source=np.load(W/'scene.npz');arrays={k:source[k].copy() for k in source.files};s=trimesh.load(O/'test.glb',force='scene');pbr=trimesh.load(O/'test_pbr.glb',force='scene')
# A union of work regions, sampled once per triangle; retain the rest of the home.
regions=[(np.array([4.25,-5.50,.900]),np.array([7.15,-2.20,1.74])),(np.array([1.15,-5.00,.910]),np.array([2.32,-1.86,1.78])),(np.array([3.70,-3.82,.918]),np.array([4.249999,-1.97,1.02])),(np.array([4.25,-2.199999,.918]),np.array([5.54,-1.97,1.02]))]
inside=lambda pts:np.logical_or.reduce([((pts>=a)&(pts<=b)).all(-1) for a,b in regions])
def clip(poly,axis,edge,positive):
 out=[]
 for i,b in enumerate(poly):
  a=poly[i-1];aa=a[axis]>=edge if positive else a[axis]<=edge;bb=b[axis]>=edge if positive else b[axis]<=edge
  if aa!=bb:out.append(a+(b-a)*((edge-a[axis])/(b[axis]-a[axis])))
  if bb:out.append(b)
 return out
rng=np.random.default_rng(2345);groups=[];report=[];partnames=[]
old=arrays['means'];outside=~inside(old)
phone_retained=(old[:,0]>6.59)&(old[:,0]<7.025)&(old[:,1]>-2.659)&(old[:,1]<-2.25)&(old[:,2]>.931)&(old[:,2]<1.105)
old_colors=source['sh'][:,0]*.28209479177387814+.5
phone_retained&=(old[:,2]>.945)|(old_colors.mean(1)<.50)
outside|=phone_retained
old_toaster=inside(old)&(old[:,0]>4.42)&(old[:,0]<4.62)&(old[:,1]>-5.35)&(old[:,1]<-5.02)&(old[:,2]>.9295)&(old[:,2]<1.131)
toastertree=cKDTree(old[old_toaster]);toastersh=arrays['sh'][old_toaster]
# Real kitchen photographic environment, not measured HDR radiance.
env=np.asarray(Image.open(R/'toaster_upgrade/kitchen_environment.jpg').convert('RGB'),float)/255
# Low-pass environment makes highlights broad enough for degree-2 SH.
from scipy.ndimage import gaussian_filter
env=gaussian_filter(env,sigma=(4,4,0));C0=.28209479177387814
viewdirs=np.array([[x,y,z] for x in [-1,0,1] for y in [-1,0,1] for z in [-1,0,1] if x*x+y*y+z*z>0],float);viewdirs/=np.linalg.norm(viewdirs,axis=1)[:,None]
def basis(d):
 x,y,z=d.T
 return np.stack([np.full_like(x,C0),-.4886025119029199*y,.4886025119029199*z,-.4886025119029199*x,1.0925484305920792*x*y,-1.0925484305920792*y*z,.31539156525252005*(3*z*z-1),-1.0925484305920792*x*z,.5462742152960396*(x*x-y*y)],-1)
# gsplat evaluates appearance on camera-to-point direction.
projector=np.linalg.pinv(basis(-viewdirs))
start=time.time()
for node in s.graph.nodes_geometry:
 if 'Kitchen_phone_v3_' in node:continue
 transform,key=s.graph[node];mesh=s.geometry[key];vertices=trimesh.transform_points(mesh.vertices,transform)
 if not any(np.all(vertices.max(0)>=a)&np.all(vertices.min(0)<=b) for a,b in regions):continue
 triangles=vertices[mesh.faces];uv=getattr(mesh.visual,'uv',None);vertexcolor=None
 if mesh.visual.kind=='vertex':vertexcolor=np.asarray(mesh.visual.vertex_colors)/255
 elif hasattr(mesh.visual,'vertex_attributes') and 'color' in mesh.visual.vertex_attributes:vertexcolor=np.asarray(mesh.visual.vertex_attributes['color'])
 mat=getattr(mesh.visual,'material',None);texture=getattr(mat,'baseColorTexture',None)
 if texture is None:texture=getattr(mat,'image',None)
 factor=getattr(mat,'baseColorFactor',None);factor=np.array([255]*4 if factor is None else factor,float);factor/=255 if factor.max()>1 else 1
 if texture is not None:texture=texture.convert('RGBA')
 clipped=[];faceids=[]
 for lo,hi in regions:
  chosen=((triangles.max(1)>=lo)&(triangles.min(1)<=hi)).all(1)
  for fidx in np.flatnonzero(chosen):
   face=mesh.faces[fidx];poly=[np.r_[vertices[v],uv[v] if uv is not None else [0,0],vertexcolor[v][:3] if vertexcolor is not None else factor[:3]] for v in face]
   for axis in range(3):
    poly=clip(poly,axis,lo[axis],True)
    if len(poly)<3:break
    poly=clip(poly,axis,hi[axis],False)
    if len(poly)<3:break
   if len(poly)<3:continue
   for j in range(1,len(poly)-1):clipped.append([poly[0],poly[j],poly[j+1]]);faceids.append(fidx)
 if not clipped:continue
 tri=np.array(clipped);ns=np.cross(tri[:,1,:3]-tri[:,0,:3],tri[:,2,:3]-tri[:,0,:3]);area=np.linalg.norm(ns,axis=1)/2;good=area>1e-11;tri=tri[good];ns=ns[good]/(area[good,None]*2);area=area[good];faceids=np.array(faceids)[good]
 isprop=node.startswith('Kitchen_') and not node.startswith(('Kitchen_counter','Kitchen_sink','Kitchen_rangetop','Kitchen_wall'))
 counter=node.startswith('Kitchen_counter_') and node.endswith('_top')
 spacing=.0016 if isprop else (.0027 if counter else .004)
 n=max(20,int(np.ceil(area.sum()/spacing**2)));face=rng.choice(len(area),size=n,p=area/area.sum());a=np.sqrt(rng.random(n));b=rng.random(n);weights=np.stack([1-a,a*(1-b),a*b],1);sample=(tri[face]*weights[:,:,None]).sum(1);pts=sample[:,:3]
 normals=ns[face]
 if isprop:
  # Interpolate artist vertex normals on curved product surfaces. Flat edges stay flat.
  vn=mesh.vertex_normals[mesh.faces[faceids[face]]];vn=vn@np.linalg.inv(transform[:3,:3]);normals=(vn*weights[:,:,None]).sum(1);normals/=np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-8)
 colors=sample[:,5:8]
 if texture is not None:colors=trimesh.visual.color.uv_to_color(sample[:,3:5],texture)[:,:3].astype(float)/255*factor[:3]
 colors=np.clip(colors,0,1)
 sh=np.zeros((n,arrays['sh'].shape[1],3),dtype='float32');sh[:,0]=(colors-.5)/C0
 if isprop and 'toaster_v4' not in node:
  tag=str(node).lower();spec=.055;rough=.6;metal=False
  if any(t in tag for t in ['chrome','steel','rim','faucet','hot_tap','air_gap','button']):spec=.28;rough=.23;metal=True
  if any(t in tag for t in ['jug','canister','ceramic','tea_tray']):spec=.14;rough=.17;metal=False
  if any(t in tag for t in ['wood','caddy','basket','knife_block','towel','bottle','frog']):spec=.045;rough=.5;metal=False
  if 'phone' in tag:spec=.035;rough=.4
  # Fixed broad-light environment reflection. Geometry never moves during appearance fitting.
  for begin in range(0,n,35000):
   nn=normals[begin:begin+35000];cc=colors[begin:begin+35000];vv=viewdirs[:,None,:]
   nd=(nn[None]*vv).sum(-1);ref=2*nd[...,None]*nn[None]-vv
   u=(np.arctan2(ref[...,1],ref[...,0])/(2*np.pi)+.5)*(env.shape[1]-1);v=(.5-np.arcsin(np.clip(ref[...,2],-1,1))/np.pi)*(env.shape[0]-1)
   radiance=env[np.clip(v.astype(int),0,env.shape[0]-1),np.clip(u.astype(int),0,env.shape[1]-1)]
   # Broad neutral window reflection models clipped bright kitchen lighting.
   light=np.array([.4,.1,.91]);window=np.clip((ref*light).sum(-1),0,1)**(5+10*(1-rough))
   fresnel=.04+.20*(1-np.clip(nd,0,1))**5
   highlight=radiance*spec*(1+fresnel[...,None])+window[...,None]*spec*.6
   diffuse=cc[None]*(.93+.07*np.maximum(nn[:,2],0))[None,:,None]
   target=np.clip(diffuse+highlight,0,1)
   coeff=np.einsum('av,vnc->nac',projector,target-.5)
   # Keep photo-matched median tones and soften exaggerated highlights.
   coeff[:,0]=np.clip(coeff[:,0],-.5/C0,.5/C0)
   sh[begin:begin+len(nn),:9]=coeff
 if 'toaster_v4' in node:
  d,index=toastertree.query(pts,k=1);sh=toastersh[index].copy();sh[d>.0035,0]=(colors[d>.0035]-.5)/C0
 # Stable planar tangents; 0.15mm normal thickness prevents halos.
 w=np.sqrt(np.maximum((1+normals[:,2])/2,1e-10));quat=np.stack([w,-normals[:,1]/(2*w),normals[:,0]/(2*w),np.zeros(n)],1);quat[normals[:,2]<-.9999]=[0,1,0,0];quat/=np.linalg.norm(quat,axis=1,keepdims=True)
 row={'node':str(node),'area_m2':float(area.sum()),'samples':n,'prop':isprop,'counter':counter};report.append(row);partnames.append(str(node))
 groups.append({'means':pts.astype('float32'),'quats':quat.astype('float32'),'scales':np.tile([spacing*1.22,spacing*1.22,.00015],(n,1)).astype('float32'),'opacities':np.full(n,.99,dtype='float32'),'sh':sh,'normals':normals.astype('float32'),'part':np.full(n,len(partnames)-1,dtype='int32')})
 if isprop or counter:print('SAMPLED',str(node),n,flush=True)
new={k:np.concatenate([g[k] for g in groups]) for k in groups[0]};offset=int(outside.sum());N=offset+len(new['means'])
# Soft contact darkening uses actual low mesh vertices on each support slab.
props=[]
for entry in json.loads((O/'manifest.json').read_text()):
 if not isinstance(entry,str):continue
 f=json.loads(Path(entry).read_text());name=f['name']
 if name.startswith(('counter_','sink_')) or name=='rangetop':continue
 mm=trimesh.load(f['world_mesh'],force='mesh');vv=np.asarray(mm.vertices);bot=vv[:,2].min();low=vv[vv[:,2]<bot+.018]
 if len(low)>10000:low=low[::max(1,len(low)//10000)]
 props.append((name,bot,cKDTree(low[:,:2])))
for part,row in enumerate(report):
 if not row['counter']:continue
 ids=np.flatnonzero(new['part']==part);p=new['means'][ids];occlusion=np.zeros(len(ids))
 for name,z,tree in props:
  if abs(z-float(np.median(p[:,2])))>.025:continue
  d=tree.query(p[:,:2],k=1)[0];occlusion=np.maximum(occlusion,.25*np.exp(-d/.017))
 rgb=new['sh'][ids,0]*C0+.5;rgb*=1-occlusion[:,None];new['sh'][ids,0]=(rgb-.5)/C0
for k in ['means','quats','scales','opacities','sh']:arrays[k]=np.concatenate([source[k][outside],new[k]])
np.savez_compressed(O/'scene.npz',**arrays);np.savez_compressed(O/'surface_samples.npz',**new)
fields=[(n,'f4') for n in ['x','y','z','nx','ny','nz']+[f'f_dc_{i}' for i in range(3)]+[f'f_rest_{i}' for i in range((arrays['sh'].shape[1]-1)*3)]+['opacity']+[f'scale_{i}' for i in range(3)]+[f'rot_{i}' for i in range(4)]]
vertices=np.empty(N,dtype=fields);op=np.clip(arrays['opacities'],1e-6,1-1e-6);vals=np.concatenate([arrays['means'],np.zeros((N,3)),arrays['sh'][:,0],arrays['sh'][:,1:].transpose(0,2,1).reshape(N,-1),np.log(op/(1-op))[:,None],np.log(arrays['scales']),arrays['quats']],1)
for i,name in enumerate(vertices.dtype.names):vertices[name]=vals[:,i]
PlyData([PlyElement.describe(vertices,'vertex')],text=False).write(O/'scene.ply')
(O/'construction.json').write_text(json.dumps({'final_gaussians':N,'removed':int((~outside).sum()),'new_fixed_samples':len(new['means']),'old_retained':offset,'parts':report,'part_names':partnames,'regions':[[a.tolist(),b.tolist()] for a,b in regions],'appearance':'Photo UV colors plus approximate environment reflection SH; fixed geometry; separate PBR export for relighting','phone_existing_visual_retained':int(phone_retained.sum()),'elapsed_s':time.time()-start},indent=2));print('ALL_KITCHEN_SPLATS_READY',N,flush=True)
