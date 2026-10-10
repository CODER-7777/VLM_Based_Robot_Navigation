from pathlib import Path
import sys,json,struct,numpy as np,trimesh,cv2
from scipy.optimize import minimize
from PIL import Image
R=Path('/data/robotics/toshith/rxr_author/refined');W=R/'kitchen_all_upgrade';sys.path.insert(0,str(R))
import kitchen_obj as K
from product_fit import FastSil
oldfit=json.loads((R/'kitchen/objects/phone_v3/fit.json').read_text());base=np.array(oldfit['base']);raw=trimesh.load(oldfit['world_mesh'],process=False);local=raw.vertices-base;ph=oldfit['views'][0]
mask=np.asarray(Image.open(W/'phone_target.png'))>0;target=cv2.resize(mask.astype('uint8'),(320,256),interpolation=cv2.INTER_NEAREST).astype(bool);sil=FastSil([ph],[target]);sil.set_faces(raw.faces)
def transform(p):
 scale,dx,dy,angle=p;a=np.radians(angle);c,s=np.cos(a),np.sin(a);rot=np.array([[c,-s,0],[s,c,0],[0,0,1.]])
 return local@rot.T*scale+base+[dx,dy,0]
def score(p):
 pts=transform(p)
 if pts[:,0].min()<6.47 or pts[:,0].max()>7.080 or pts[:,1].min()<-2.658 or pts[:,1].max()>-2.251:return 1.+abs(p[1])+abs(p[2])
 return -float(sil.ious(pts)[0])
starts=[]
for scale in [.85,1.,1.10]:
 for dx in [0,.06,.12]:
  for dy in [-.04,0,.04]:
   for angle in [-30,0,30]:
    p=[scale,dx,dy,angle];starts.append((score(p),p))
start=min(starts,key=lambda x:x[0]);result=minimize(score,start[1],method='Powell',bounds=[(.80,1.15),(-.07,.18),(-.09,.09),(-65,65)],options={'maxiter':45,'xtol':.0005,'ftol':.0001});parameters=result.x
if result.fun>start[0]:parameters=np.array(start[1]);final=-start[0]
else:final=-float(result.fun)
points=transform(parameters);scale,dx,dy,angle=parameters;a=np.radians(angle);c,s=np.cos(a),np.sin(a);rot=np.array([[c,-s,0],[s,c,0],[0,0,1.]]);T=np.eye(4);T[:3,:3]=rot*scale;T[:3,3]=base+[dx,dy,0]-rot@base*scale
out=R/'kitchen/objects/phone_v4';out.mkdir(exist_ok=True);raw.vertices=points;raw.export(out/'world.ply')
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
 matches=[i for i,node in enumerate(nodes) if 'mesh' in node and (not only_jug or node.get('name','').startswith('Kitchen_phone_v3_'))]
 assert matches
 for i in matches:
  parent=globalm(parents[i]) if i in parents else np.eye(4);localm=np.linalg.inv(parent)@worldT@globalm(i);node=nodes[i]
  for key in ['translation','rotation','scale']:node.pop(key,None)
  node['matrix']=localm.T.ravel().tolist()
  if only_jug:node['name']=node.get('name','').replace('phone_v3','phone_v4')
 js=json.dumps(data,separators=(',',':')).encode();js+=b' '*((-len(js))%4);payload=struct.pack('<III',magic,version,12+8+len(js)+len(remainder))+struct.pack('<II',len(js),0x4e4f534a)+js+remainder;Path(dst).write_bytes(payload)

C=np.eye(4);C[:3,:3]=np.array([[1,0,0],[0,0,1],[0,-1,0.]])
patch_glb(oldfit['glb'],out/'world_pbr.glb',C@T@C.T,False)
for file in ['test.glb','test_pbr.glb']:patch_glb(W/file,W/file,T,True)
fit=oldfit.copy();fit.update(name='phone_v4',glb=str(out/'world_pbr.glb'),world_mesh=str(out/'world.ply'),base=(base+[dx,dy,0]).tolist(),height=float(np.ptp(points[:,2])),photo_iou=final,realism_notes='Original free desk-phone product with constrained photo fit; controls photographed onto visible fixed surfaces, unseen sides approximate.');(out/'fit.json').write_text(json.dumps(fit,indent=2));manifest=json.loads((W/'manifest.json').read_text());manifest=[str(out/'fit.json') if isinstance(e,str) and '/phone_v3/' in e else e for e in manifest];(W/'manifest.json').write_text(json.dumps(manifest,indent=2))
result={'height_m':fit['height'],'parameters':parameters.tolist(),'primary_photo_iou':final,'bounds':raw.bounds.tolist(),'transform':T.tolist(),'fit':str(out/'fit.json')};(W/'phone_final_fit.json').write_text(json.dumps(result,indent=2));print('PHONE_FINAL_FIT_READY',result,flush=True)
