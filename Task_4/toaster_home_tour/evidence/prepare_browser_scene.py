"""Browser copy of full kitchen/house. Geometry and toaster maps are preserved.
Repack binary buffer views and encode background photographic colour images
as JPEG; retain all non-colour/data maps and the toaster's original bytes.
"""
from pathlib import Path
import json,struct,io,hashlib
from PIL import Image
R=Path('/data/robotics/toshith/rxr_author/refined');W=R/'toaster_home_tour';W.mkdir(exist_ok=True);src=R/'kitchen_all_upgrade/test_pbr.glb';b=src.read_bytes();n=struct.unpack('<I',b[12:16])[0];d=json.loads(b[20:20+n]);start=20+n;blen=struct.unpack('<I',b[start:start+4])[0];binary=b[start+8:start+8+blen]
protected=set();color=set();data_maps=set();toaster_mats=set()
for node in d['nodes']:
 if 'mesh' in node and node.get('name','').startswith('Kitchen_toaster_v4_'):
  for prim in d['meshes'][node['mesh']]['primitives']:toaster_mats.add(prim['material'])
for mid,mat in enumerate(d.get('materials',[])):
 pbr=mat.get('pbrMetallicRoughness',{})
 for name,entry in [('baseColorTexture',pbr.get('baseColorTexture')),('metallicRoughnessTexture',pbr.get('metallicRoughnessTexture')),('normalTexture',mat.get('normalTexture')),('occlusionTexture',mat.get('occlusionTexture'))]:
  if not entry:continue
  image=d['textures'][entry['index']]['source']
  (color if name=='baseColorTexture' else data_maps).add(image)
  if mid in toaster_mats:protected.add(image)
changes={};textures=[]
for iid,im in enumerate(d['images']):
 if 'bufferView' not in im:continue
 vid=im['bufferView'];v=d['bufferViews'][vid];payload=binary[v.get('byteOffset',0):v.get('byteOffset',0)+v['byteLength']]
 if iid in protected:
  textures.append({'image':iid,'name':im.get('name'),'sha256':hashlib.sha256(payload).hexdigest(),'bytes':len(payload),'preserved':True});continue
 if iid not in color or iid in data_maps:continue
 try:
  image=Image.open(io.BytesIO(payload));image.load()
  if image.mode in ['RGBA','LA'] and image.getextrema()[-1][0]<255:continue
  out=io.BytesIO();image.convert('RGB').save(out,format='JPEG',quality=94,optimize=True);new=out.getvalue()
  if len(new)<len(payload)*.90:changes[vid]=new;im['mimeType']='image/jpeg'
 except Exception:continue
rebuilt=bytearray();cache={}
for vid,v in enumerate(d['bufferViews']):
 original=binary[v.get('byteOffset',0):v.get('byteOffset',0)+v['byteLength']];payload=changes.get(vid,original);key=hashlib.sha256(payload).digest()
 if key in cache:offset=cache[key]
 else:
  offset=len(rebuilt);rebuilt.extend(payload);rebuilt.extend(b'\0'*((-len(rebuilt))%4));cache[key]=offset
 v['buffer']=0;v['byteOffset']=offset;v['byteLength']=len(payload)
d['buffers']=[{'byteLength':len(rebuilt)}];js=json.dumps(d,separators=(',',':')).encode();js+=b' '*((-len(js))%4);out=struct.pack('<III',0x46546c67,2,12+8+len(js)+8+len(rebuilt))+struct.pack('<II',len(js),0x4e4f534a)+js+struct.pack('<II',len(rebuilt),0x004e4942)+rebuilt;temp=W/'home_pbr.tmp';temp.write_bytes(out);temp.replace(W/'home_pbr.glb')
report={'source':str(src),'browser_glb':str(W/'home_pbr.glb'),'source_bytes':len(b),'browser_bytes':len(out),'geometry_changed':False,'image_resolution_changed':False,'background_color_images_jpeg94':len(changes),'toaster_original_images':textures,'toaster_parts':len([n for n in d['nodes'] if 'mesh' in n and n.get('name','').startswith('Kitchen_toaster_v4_')]),'coordinate_frame':'raw MP3D Z-up metres; browser root uses raw-to-Y-up rotation','notes':'Photographic colour atlases are JPEG-compressed for browser transfer; original toaster PBR textures and all geometry buffer bytes are retained.'};(W/'browser_scene.json').write_text(json.dumps(report,indent=2));print('BROWSER_SCENE_READY',report['source_bytes'],report['browser_bytes'],'toaster parts',report['toaster_parts'],flush=True)
