"""Photo silhouette fit at exact support height; update only the jug transform.
Keep all other scene nodes and Gaussian positions bit-for-bit unchanged.
"""
from pathlib import Path
import sys,json,struct,numpy as np,trimesh,cv2
from scipy.optimize import minimize
from PIL import Image
R=Path('/data/robotics/toshith/rxr_author/refined');W=R/'kitchen_all_upgrade';sys.path.insert(0,str(R));sys.path.insert(0,str(R/'split_visuals/vendor'))
import kitchen_obj as K
from product_fit import FastSil
from plyfile import PlyData,PlyElement
oldfit=json.loads((R/'kitchen/objects/blue_jug_v3/fit.json').read_text());base=np.array(oldfit['base']);raw=trimesh.load(oldfit['world_mesh'],process=False);vertices=np.asarray(raw.vertices);local=vertices-base;ph=oldfit['views'][0]
mask=np.asarray(Image.open(W/'masks/blue_jug.png'))>0;photo=K.photo(ph).astype(float)/255
mask&=(photo[:,:,2]>photo[:,:,0]*1.08)&(photo[:,:,2]>photo[:,:,1]*.85)&(photo.mean(2)<.60)
Image.fromarray((mask*255).astype('uint8')).save(W/'jug_target.png');target=cv2.resize(mask.astype('uint8'),(320,256),interpolation=cv2.INTER_NEAREST).astype(bool);sil=FastSil([ph],[target]);sil.set_faces(raw.faces)
def transform(p):
 scale,dx,dy,angle=p;a=np.radians(angle);c,s=np.cos(a),np.sin(a);rot=np.array([[c,-s,0],[s,c,0],[0,0,1.]])
 return local@rot.T*scale+base+[dx,dy,0]
def score(p):
 points=transform(p)
 if points[:,0].min()<6.47 or points[:,0].max()>7.084 or points[:,1].min()<-4.78 or points[:,1].max()>-4.355:return 1.+abs(p[1])+abs(p[2])
 return -float(sil.ious(points)[0])
starts=[]
for scale in [.6,.75,.9,1.0]:
 for dx in [-.04,0,.04]:
  for dy in [-.04,0,.02]:
   p=[scale,dx,dy,0.];starts.append((score(p),p))
start=min(starts,key=lambda x:x[0]);result=minimize(score,start[1],method='Powell',bounds=[(.55,1.1),(-.085,.045),(-.08,.08),(-25,25)],options={'maxiter':60,'xtol':.0002,'ftol':.0001});parameters=result.x
if result.fun>start[0]:parameters=np.array(start[1]);final=-start[0]
else:final=-float(result.fun)
points=transform(parameters);scale,dx,dy,angle=parameters;a=np.radians(angle);c,s=np.cos(a),np.sin(a);rot=np.array([[c,-s,0],[s,c,0],[0,0,1.]]);T=np.eye(4);T[:3,:3]=rot*scale;T[:3,3]=base+[dx,dy,0]-rot@base*scale
assert abs(points[:,2].min()-.929)<1e-5
newbase=base+[dx,dy,0];out=R/'kitchen/objects/blue_jug_v4';out.mkdir(exist_ok=True)
raw.vertices=points;raw.export(out/'world.ply')
# Apply a world transform to selected glTF mesh nodes without touching buffers.
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
 matches=[i for i,node in enumerate(nodes) if 'mesh' in node and (not only_jug or node.get('name','').startswith('Kitchen_blue_jug_v3_'))]
 assert matches
 for i in matches:
  parent=globalm(parents[i]) if i in parents else np.eye(4);localm=np.linalg.inv(parent)@worldT@globalm(i);node=nodes[i]
  for key in ['translation','rotation','scale']:node.pop(key,None)
  node['matrix']=localm.T.ravel().tolist()
  if only_jug:node['name']=node.get('name','').replace('blue_jug_v3','blue_jug_v4')
 js=json.dumps(data,separators=(',',':')).encode();js+=b' '*((-len(js))%4);payload=struct.pack('<III',magic,version,12+8+len(js)+len(remainder))+struct.pack('<II',len(js),0x4e4f534a)+js+remainder;Path(dst).write_bytes(payload)
C=np.eye(4);C[:3,:3]=np.array([[1,0,0],[0,0,1],[0,-1,0.]])
patch_glb(oldfit['glb'],out/'world_pbr.glb',C@T@C.T,False)
for file in ['test.glb','test_pbr.glb']:patch_glb(W/file,W/file,T,True)
fit=oldfit.copy();fit.update(name='blue_jug_v4',glb=str(out/'world_pbr.glb'),world_mesh=str(out/'world.ply'),base=newbase.tolist(),height=float(np.ptp(points[:,2])),photo_iou=final,geometry_changed=True,realism_notes='Physically sized miniature creamer, photo silhouette fit; generic unseen opening and handle.');(out/'fit.json').write_text(json.dumps(fit,indent=2));manifest=json.loads((W/'manifest.json').read_text());manifest=[str(out/'fit.json') if isinstance(e,str) and '/blue_jug_v3/' in e else e for e in manifest];(W/'manifest.json').write_text(json.dumps(manifest,indent=2))
# Transform the corresponding frozen samples with the identical matrix.
construction=json.loads((W/'construction.json').read_text());sample=np.load(W/'surface_samples.npz');samples={k:sample[k].copy() for k in sample.files};parts=construction['part_names'];partids=[i for i,n in enumerate(parts) if 'Kitchen_blue_jug_v3_' in n];ids=np.flatnonzero(np.isin(samples['part'],partids));offset=construction['old_retained'];gids=offset+ids
rawnp=np.load(W/'scene_refined.npz');arrays={k:rawnp[k].copy() for k in rawnp.files};arrays['means'][gids]=arrays['means'][gids]@T[:3,:3].T+T[:3,3];samples['means'][ids]=arrays['means'][gids];normals=samples['normals'][ids]@rot.T;samples['normals'][ids]=normals;arrays['scales'][gids]*=scale;samples['scales'][ids]*=scale
ww=np.sqrt(np.maximum((1+normals[:,2])/2,1e-10));quat=np.stack([ww,-normals[:,1]/(2*ww),normals[:,0]/(2*ww),np.zeros(len(ww))],1);quat[normals[:,2]<-.9999]=[0,1,0,0];quat/=np.linalg.norm(quat,axis=1)[:,None];arrays['quats'][gids]=quat;samples['quats'][ids]=quat
# At the now fitted surface, restore the photo's real cobalt glaze highlights.
p=arrays['means'][gids];uv=K.project(ph,p);u,v,z=uv.T;x=np.clip(u.astype(int),0,1279);y=np.clip(v.astype(int),0,1023);direction=K.CAMS[ph]['c2w'][:3,3]-p;direction/=np.linalg.norm(direction,axis=1)[:,None];good=(z>.1)&(u>0)&(u<1279)&(v>0)&(v<1023)&mask[y,x]&((normals*direction).sum(1)>.2);C0=.28209479177387814;col=arrays['sh'][gids,0]*C0+.5;col[good]=.88*photo[y[good],x[good]]+.12*col[good];arrays['sh'][gids,0]=(col-.5)/C0;arrays['sh'][gids[good],1:]*=.3
np.savez_compressed(W/'scene_refined.npz',**arrays);np.savez_compressed(W/'surface_samples.npz',**samples)
for i in partids:parts[i]=parts[i].replace('blue_jug_v3','blue_jug_v4');construction['parts'][i]['node']=parts[i]
construction['jug_final_fit']={'height_m':fit['height'],'parameters':parameters.tolist(),'primary_photo_iou':final,'photographic_surface_fraction':float(good.mean()),'bounds':raw.bounds.tolist(),'transform':T.tolist()};(W/'construction.json').write_text(json.dumps(construction,indent=2));(W/'jug_final_fit.json').write_text(json.dumps(construction['jug_final_fit'],indent=2))
N=len(arrays['means']);degree=int(arrays['sh_degree']);fields=[(n,'f4') for n in ['x','y','z','nx','ny','nz']+[f'f_dc_{i}' for i in range(3)]+[f'f_rest_{i}' for i in range(((degree+1)**2-1)*3)]+['opacity']+[f'scale_{i}' for i in range(3)]+[f'rot_{i}' for i in range(4)]];vv=np.empty(N,dtype=fields);op=np.clip(arrays['opacities'],1e-6,1-1e-6);values=np.concatenate([arrays['means'],np.zeros((N,3)),arrays['sh'][:,0],arrays['sh'][:,1:].transpose(0,2,1).reshape(N,-1),np.log(op/(1-op))[:,None],np.log(arrays['scales']),arrays['quats']],1)
for i,name in enumerate(vv.dtype.names):vv[name]=values[:,i]
PlyData([PlyElement.describe(vv,'vertex')],text=False).write(W/'scene_refined.ply');print('JUG_PHOTO_FIT_READY',fit['height'],final,raw.bounds.tolist(),flush=True)
