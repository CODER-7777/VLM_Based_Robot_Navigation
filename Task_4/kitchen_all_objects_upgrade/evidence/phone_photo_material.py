"""Correct the standalone and stage phone's old partial keypad decal.
Geometry is unchanged. Front surfaces use the calibrated kitchen photo;
masked or unseen parts remain neutral dark plastic.
"""
from pathlib import Path
import sys,json,struct,copy,shutil,numpy as np,trimesh
from PIL import Image
R=Path('/data/robotics/toshith/rxr_author/refined');W=R/'kitchen_all_upgrade';O=R/'kitchen/objects/phone_v4';sys.path.insert(0,str(R));import kitchen_obj as K
fit=json.loads((O/'fit.json').read_text());src=O/'world_pbr_before_photo_material.glb'
if not src.exists():shutil.copy2(fit['glb'],src)
s=trimesh.load(src,force='scene');C=np.array([[1,0,0],[0,0,1],[0,-1,0.]])
ph=fit['views'][0];photo=K.photo(ph).copy();mask=np.array(Image.open(W/'phone_target.png'))>0;photo[~mask]=[60,65,67];texture=Image.fromarray(photo);out=trimesh.Scene();rawout=trimesh.Scene();count=0
for node in s.graph.nodes_geometry:
 t,key=s.graph[node];m=s.geometry[key];p=trimesh.transform_points(m.vertices,t)@C;tri=p[m.faces];n=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);n/=np.maximum(np.linalg.norm(n,axis=1)[:,None],1e-10);direction=K.CAMS[ph]['c2w'][:3,3]-tri.mean(1);direction/=np.maximum(np.linalg.norm(direction,axis=1)[:,None],1e-10);front=(n*direction).sum(1)>.05;u,v,z=K.project(ph,p).T;uv=np.c_[u/1280,1-v/1024]
 for visible,faces in [(True,m.faces[front]),(False,m.faces[~front])]:
  if not len(faces):continue
  mesh=trimesh.Trimesh(vertices=p@C.T,faces=faces,process=False)
  mat=trimesh.visual.material.PBRMaterial(name='Phone_photo_plastic' if visible else 'Phone_hidden_plastic',baseColorTexture=texture if visible else None,baseColorFactor=[255,255,255,255] if visible else [38,43,46,255],metallicFactor=0.,roughnessFactor=.48)
  mesh.visual=trimesh.visual.texture.TextureVisuals(uv=uv,material=mat);name='Kitchen_phone_v4_photo_'+str(count);out.add_geometry(mesh,node_name=name,geom_name=name);meshraw=mesh.copy();meshraw.vertices=p;rawout.add_geometry(meshraw,node_name=name,geom_name=name);count+=1
out.export(O/'world_pbr.glb');rawout.export(W/'phone_stage_raw.glb')
# Append the new asset's binary ranges and index tables to each private stage.
# Clear only old phone mesh nodes; all other geometry and buffers remain intact.
def unpack(path):
 b=Path(path).read_bytes();length=struct.unpack('<I',b[12:16])[0];d=json.loads(b[20:20+length]);start=20+length;blen=struct.unpack('<I',b[start:start+4])[0];return d,bytearray(b[start+8:start+8+blen])
asset,assetbin=unpack(W/'phone_stage_raw.glb')
for filename in ['test.glb','test_pbr.glb']:
 data,binary=unpack(W/filename);base=len(binary);binary.extend(assetbin);binary.extend(b'\0'*((-len(binary))%4));tables=['bufferViews','accessors','images','samplers','textures','materials','meshes','nodes'];offset={k:len(data.get(k,[])) for k in tables};a=copy.deepcopy(asset)
 for v in a.get('bufferViews',[]):v['buffer']=0;v['byteOffset']=v.get('byteOffset',0)+base
 for v in a.get('accessors',[]):
  if 'bufferView' in v:v['bufferView']+=offset['bufferViews']
 for v in a.get('images',[]):
  if 'bufferView' in v:v['bufferView']+=offset['bufferViews']
 for v in a.get('textures',[]):
  if 'source' in v:v['source']+=offset['images']
  if 'sampler' in v:v['sampler']+=offset['samplers']
 def material(v):
  if isinstance(v,dict):
   for k,value in v.items():
    if k.endswith('Texture') and isinstance(value,dict) and 'index' in value:value['index']+=offset['textures']
    else:material(value)
  elif isinstance(v,list):
   for value in v:material(value)
 for v in a.get('materials',[]):material(v)
 for mesh in a.get('meshes',[]):
  for p in mesh['primitives']:
   p['attributes']={k:i+offset['accessors'] for k,i in p['attributes'].items()}
   if 'indices' in p:p['indices']+=offset['accessors']
   if 'material' in p:p['material']+=offset['materials']
 for n in a.get('nodes',[]):
  if 'mesh' in n:n['mesh']+=offset['meshes']
  if 'children' in n:n['children']=[i+offset['nodes'] for i in n['children']]
 cleared=0
 for n in data['nodes']:
  if 'mesh' in n and n.get('name','').startswith('Kitchen_phone_v4_'):n.pop('mesh');cleared+=1
 assert cleared>0
 for key in tables:data.setdefault(key,[]).extend(a.get(key,[]))
 roots=a['scenes'][a.get('scene',0)]['nodes'];data['scenes'][data.get('scene',0)]['nodes'].extend(i+offset['nodes'] for i in roots);data['buffers'][0]['byteLength']=len(binary);js=json.dumps(data,separators=(',',':')).encode();js+=b' '*((-len(js))%4);payload=struct.pack('<III',0x46546c67,2,12+8+len(js)+8+len(binary))+struct.pack('<II',len(js),0x4e4f534a)+js+struct.pack('<II',len(binary),0x004e4942)+binary;tmp=W/(filename+'.phone.tmp');tmp.write_bytes(payload);tmp.replace(W/filename);print('PHONE_MATERIAL_STAGE_UPDATED',filename,cleared,count,flush=True)
fit['appearance_note']='Calibrated photo UV projection on visible front faces; neutral dark plastic on hidden surfaces. Geometry unchanged. Photograph includes fixed lighting.';(O/'fit.json').write_text(json.dumps(fit,indent=2));(W/'phone_material.json').write_text(json.dumps({'fit':str(O/'fit.json'),'mesh_parts':count,'geometry_changed':False,'photo':ph,'method':fit['appearance_note']},indent=2))
