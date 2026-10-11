from pathlib import Path
import json,struct,copy,io
from PIL import Image
ROOT=Path(__file__).resolve().parent.parent

def read(path):
 with path.open('rb') as f:
  f.read(12);n,k=struct.unpack('<II',f.read(8));g=json.loads(f.read(n));n,k=struct.unpack('<II',f.read(8));return g,f.read(n)
def add(g,data,blob,mime,name):
 data.extend(b'\0'*((-len(data))%4));offset=len(data);data.extend(blob);view=len(g['bufferViews']);g['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':len(blob)});image=len(g['images']);g['images'].append({'name':name,'mimeType':mime,'bufferView':view});sampler=len(g.setdefault('samplers',[]));g['samplers'].append({'magFilter':9729,'minFilter':9987,'wrapS':10497,'wrapT':10497});texture=len(g['textures']);g['textures'].append({'source':image,'sampler':sampler});return texture
def write(path,g,data):
 g['buffers']=[{'byteLength':len(data)}];encoded=json.dumps(g,separators=(',',':')).encode();encoded+=b' '*((-len(encoded))%4);data.extend(b'\0'*((-len(data))%4));size=12+8+len(encoded)+8+len(data)
 with path.open('wb') as f:f.write(struct.pack('<III',0x46546c67,2,size));f.write(struct.pack('<II',len(encoded),0x4e4f534a));f.write(encoded);f.write(struct.pack('<II',len(data),0x004e4942));f.write(data)
old,oldbin=read(ROOT/'current/grinder_old.glb');oldmat=next(m for m in old['materials'] if 'Wood' in m.get('name',''));tex=oldmat['pbrMetallicRoughness']['baseColorTexture']['index'];img=old['images'][old['textures'][tex]['source']];view=old['bufferViews'][img['bufferView']];start=view.get('byteOffset',0);photo=oldbin[start:start+view['byteLength']];photo_path=ROOT/'images/grinder_drawer_photo.png';photo_path.write_bytes(photo)
wood=Image.open(ROOT/'images/native_texture_1.png').convert('RGB');wood=wood.resize((1024,1024),Image.Resampling.LANCZOS);wood.save(ROOT/'images/grinder_grain.jpg',quality=96);blob=(ROOT/'images/grinder_grain.jpg').read_bytes()
for filename in ['product_pbr.glb','world_pbr.glb']:
 path=ROOT/'objects/grinder_v5'/filename;g,b=read(path);data=bytearray(b);woodtex=add(g,data,blob,'image/jpeg','Licensed_wood_grain_tile')
 for m in g['materials']:
  if m.get('name')=='Dark_stained_real_wood':m['pbrMetallicRoughness']['baseColorTexture']={'index':woodtex};m['pbrMetallicRoughness']['baseColorFactor']=[.045,.045,.045,1];m['pbrMetallicRoughness']['roughnessFactor']=.35
 phototex=add(g,data,photo,img['mimeType'],'Retained_drawer_photo');m=copy.deepcopy(oldmat);m['name']='Labelled_grinder_drawer_photo';m['pbrMetallicRoughness']['baseColorTexture']={'index':phototex};matindex=len(g['materials']);g['materials'].append(m)
 for node in g['nodes']:
  if node.get('name','').endswith('Kitchen_grinder_v3_4') and 'mesh' in node:
   for prim in g['meshes'][node['mesh']]['primitives']:prim['material']=matindex
 write(path,g,data)
print('Corrected grinder texture tile, retained the existing drawer photograph; geometry unchanged')
