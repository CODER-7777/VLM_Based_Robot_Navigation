"""Final visual repairs on reviewed fixed geometry; private checkpoint only."""
from pathlib import Path
import sys,json,struct,numpy as np,trimesh,cv2
from PIL import Image
R=Path('/data/robotics/toshith/rxr_author/refined');W=R/'kitchen_all_upgrade';S=R/'split_visuals';sys.path.insert(0,str(R));sys.path.insert(0,str(S/'vendor'))
import kitchen_obj as K
from plyfile import PlyData,PlyElement
C0=.28209479177387814;rng=np.random.default_rng(905);construction=json.loads((W/'construction.json').read_text());offset=construction['old_retained'];names=construction['part_names'];sample=np.load(W/'surface_samples.npz');raw=np.load(W/'scene_refined_before_visual_selection.npz');arrays={k:raw[k].copy() for k in raw.files};old=np.load(S/'scene.npz');remove=np.zeros(len(arrays['means']),bool)
ids=[i for i,n in enumerate(names) if n.startswith(('Kitchen_frogs_v3_','Kitchen_wall_all_'))];remove[offset+np.flatnonzero(np.isin(sample['part'],ids))]=True
q=arrays['means'][:offset];remove[:offset]|=(q[:,0]>6.45)&(q[:,0]<7.25)&(q[:,1]>-2.90)&(q[:,1]<-2.23)&(q[:,2]>.90)&(q[:,2]<1.18)
groups=[]
def group(p,n,color,spacing=.0016,sh=None):
 N=len(p);w=np.sqrt(np.maximum((1+n[:,2])/2,1e-10));quat=np.stack([w,-n[:,1]/(2*w),n[:,0]/(2*w),np.zeros(N)],1);quat[n[:,2]<-.9999]=[0,1,0,0];quat/=np.linalg.norm(quat,axis=1)[:,None]
 if sh is None:
  sh=np.zeros((N,arrays['sh'].shape[1],3),np.float32);sh[:,0]=(color-.5)/C0
 return dict(means=p.astype('float32'),quats=quat.astype('float32'),scales=np.tile([spacing*1.23,spacing*1.23,.00015],(N,1)).astype('float32'),opacities=np.full(N,.99,np.float32),sh=sh.astype('float32'))
# Phone source geometry is fitted at physical support height. Only its visible
# front-facing surfaces receive actual telephone controls from the photograph.
fit=json.loads((R/'kitchen/objects/phone_v4/fit.json').read_text());scene=trimesh.load(fit['glb'],force='scene');C=np.array([[1,0,0],[0,0,1],[0,-1,0.]])
ph=fit['views'][0];mask=np.array(Image.open(W/'phone_target.png'))>0;photo=K.photo(ph).astype(float)/255;phone_count=0;phone_supported=0
for node in scene.graph.nodes_geometry:
 transform,key=scene.graph[node];mesh=scene.geometry[key];v=trimesh.transform_points(mesh.vertices,transform)@C;tri=v[mesh.faces];cross=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);area=np.linalg.norm(cross,axis=1)/2;valid=area>1e-12;tri=tri[valid];ns=cross[valid]/(2*area[valid,None]);area=area[valid];N=max(20,int(area.sum()/.0013**2));face=rng.choice(len(area),N,p=area/area.sum());a=np.sqrt(rng.random(N));b=rng.random(N);weights=np.stack([1-a,a*(1-b),a*b],1);p=(tri[face]*weights[:,:,None]).sum(1);n=ns[face];colors=np.tile([.34,.36,.37],(N,1));mat=getattr(mesh.visual,'material',None);uv=getattr(mesh.visual,'uv',None);texture=getattr(mat,'baseColorTexture',None);factor=getattr(mat,'baseColorFactor',None)
 if factor is not None:
  f=np.array(factor)[:3];f=f/255 if f.max()>1 else f;colors[:]=f
 if uv is not None and texture is not None:
  uvs=(uv[mesh.faces[valid][face]]*weights[:,:,None]).sum(1);colors=trimesh.visual.color.uv_to_color(uvs,texture)[:,:3]/255
 u,vv,z=K.project(ph,p).T;x=np.clip(u.astype(int),0,1279);y=np.clip(vv.astype(int),0,1023);direction=K.CAMS[ph]['c2w'][:3,3]-p;direction/=np.linalg.norm(direction,axis=1)[:,None];good=(z>.1)&(u>0)&(u<1279)&(vv>0)&(vv<1023)&mask[y,x]&((n*direction).sum(1)>.10);colors[good]=.97*photo[y[good],x[good]]+.03*colors[good];groups.append(group(p,n,np.clip(colors,0,1),.0013));phone_count+=N;phone_supported+=int(good.sum())
# Retain the decorative frog reconstruction rather than claiming a generic
# parametric statue is the exact original. Move the sparse scan slightly inward
# so the repaired backsplash cannot slice its back-facing splats.
p=old['means'];ph='f7a060bfa1164b5e9c5cca04284f6d6b_i1_4.jpg';mask=np.array(Image.open(W/'masks/frogs.png'))>0;mask=cv2.dilate(mask.astype('uint8'),np.ones((7,7),np.uint8)).astype(bool);u,v,z=K.project(ph,p).T;x=np.clip(u.astype(int),0,1279);y=np.clip(v.astype(int),0,1023);keep=(z>.1)&(u>0)&(u<1279)&(v>0)&(v<1023)&mask[y,x]&(p[:,0]>6.55)&(p[:,0]<7.20)&(p[:,1]>-5.52)&(p[:,1]<-5.0)&(p[:,2]>.925)&(p[:,2]<1.36)&(old['opacities']>.05);keep&=(p[:,0]<6.708)|(p[:,0]>6.925)|(p[:,2]>1.085)
g={k:old[k][keep].copy() for k in ['means','quats','scales','opacities','sh']};g['means'][:,0]=np.minimum(g['means'][:,0],7.087);g['means'][:,1]=np.maximum(g['means'][:,1],-5.430);g['means'][:,2]=np.maximum(g['means'][:,2],.932);groups.append(g);frog_count=int(keep.sum())
# Close the seam above the original short replacement strips. Entire replacement
# wall surfaces share the regenerated photo atlas and remain physically planar.
walls=json.loads((W/'wall_materials.json').read_text())
for wall in walls:
 axis=wall['axis'];fixed=wall['fixed'];lo,hi=wall['horizontal'];bottom,top=wall['vertical'];spacing=.0035;h=np.arange(lo+spacing/2,hi,spacing);z=np.arange(bottom+spacing/2,top,spacing);xx,zz=np.meshgrid(h,z);p=np.c_[xx.ravel(),np.full(xx.size,fixed),zz.ravel()] if axis==0 else np.c_[np.full(xx.size,fixed),xx.ravel(),zz.ravel()];uv=np.c_[(xx.ravel()-lo)/(hi-lo),(zz.ravel()-bottom)/(top-bottom)];texture=Image.open(wall['texture']).convert('RGB');colors=trimesh.visual.color.uv_to_color(uv,texture)[:,:3]/255;groups.append(group(p,np.tile(wall['normal'],(len(p),1)),colors,spacing))
for k in ['means','quats','scales','opacities','sh']:arrays[k]=np.concatenate([arrays[k][~remove]]+[g[k] for g in groups])
np.savez_compressed(W/'scene_refined.npz',**arrays);N=len(arrays['means']);degree=int(arrays['sh_degree']);fields=[(n,'f4') for n in ['x','y','z','nx','ny','nz']+[f'f_dc_{i}' for i in range(3)]+[f'f_rest_{i}' for i in range(((degree+1)**2-1)*3)]+['opacity']+[f'scale_{i}' for i in range(3)]+[f'rot_{i}' for i in range(4)]];vertices=np.empty(N,dtype=fields);op=np.clip(arrays['opacities'],1e-6,1-1e-6);values=np.concatenate([arrays['means'],np.zeros((N,3)),arrays['sh'][:,0],arrays['sh'][:,1:].transpose(0,2,1).reshape(N,-1),np.log(op/(1-op))[:,None],np.log(arrays['scales']),arrays['quats']],1)
for i,name in enumerate(vertices.dtype.names):vertices[name]=values[:,i]
PlyData([PlyElement.describe(vertices,'vertex')],text=False).write(W/'scene_refined.ply')
result={'phone':{'method':'Photo-fitted fixed desk-phone product, visible controls projected from the actual photo','surface_samples':phone_count,'photo_supported_samples':phone_supported,'fit':fit['name'],'limitation':'Silhouette and hidden sides remain approximate; fixed photographic appearance.'},'frogs':{'method':'Prior photo-trained decorative reconstruction retained with bounded wall/support correction','samples':frog_count,'limitation':'Sparse reconstruction remains imperfect; proxy and visual shape are approximate.'},'walls':{'top_m':1.40,'method':'Extended physically planar photo-textured backsplash closes the visible seam; hidden tiles use approximate infill'},'final_gaussians':N};(W/'visual_selection.json').write_text(json.dumps(result,indent=2));construction['final_gaussians']=N;construction['visual_selection']=result;(W/'construction.json').write_text(json.dumps(construction,indent=2));print('FINAL_VISUALS_READY',result,flush=True)
def matrix(node):
 if 'matrix' in node:return np.array(node['matrix']).reshape(4,4).T
 t=np.array(node.get('translation',[0,0,0.]));q=np.array(node.get('rotation',[0,0,0,1.]));x,y,z,w=q
 rotq=np.array([[1-2*y*y-2*z*z,2*x*y-2*z*w,2*x*z+2*y*w],[2*x*y+2*z*w,1-2*x*x-2*z*z,2*y*z-2*x*w],[2*x*z-2*y*w,2*y*z+2*x*w,1-2*x*x-2*y*y]])
 m=np.eye(4);m[:3,:3]=rotq@np.diag(node.get('scale',[1,1,1.]));m[:3,3]=t;return m
def patch_glb(path,dst,worldT,only_jug):
 b=Path(path).read_bytes();magic,version,total=struct.unpack('<III',b[:12]);n,kind=struct.unpack('<II',b[12:20]);data=json.loads(b[20:20+n]);remainder=b[20+n:];nodes=data['nodes'];parents={child:i for i,node in enumerate(nodes) for child in node.get('children',[])};cache={}
 def globalm(i):
  if i not in cache:cache[i]=(globalm(parents[i]) if i in parents else np.eye(4))@matrix(nodes[i])
  return cache[i]
 matches=[i for i,node in enumerate(nodes) if 'mesh' in node and (not only_jug or node.get('name','').startswith('Kitchen_wall_all_'))]
 assert matches
 for i in matches:
  parent=globalm(parents[i]) if i in parents else np.eye(4);localm=np.linalg.inv(parent)@worldT@globalm(i);node=nodes[i]
  for key in ['translation','rotation','scale']:node.pop(key,None)
  node['matrix']=localm.T.ravel().tolist()
  if only_jug:pass
 js=json.dumps(data,separators=(',',':')).encode();js+=b' '*((-len(js))%4);payload=struct.pack('<III',magic,version,12+8+len(js)+len(remainder))+struct.pack('<II',len(js),0x4e4f534a)+js+remainder;Path(dst).write_bytes(payload)

T=np.eye(4);T[2,2]=(1.40-.932)/(1.27-.932);T[2,3]=.932*(1-T[2,2])
for file in ['test.glb','test_pbr.glb']:patch_glb(W/file,W/file,T,True)
(W/'wall_assembly.json').write_text(json.dumps(walls,indent=2))
