from pathlib import Path
from urllib.request import urlopen,Request
import json,struct
base='http://127.0.0.1:8767';report={'url':base,'pages':[],'models':[],'images':[]}
def read(path,headers=None):
 with urlopen(Request(base+path,headers=headers or {}),timeout=20) as r:return r.status,dict(r.headers),r.read()
status,h,b=read('/tour-info');info=json.loads(b);assert info['revision']=='kitchen_objects_pbr_v1';assert len(info['items'])==22
for path in ['/','/home-tour','/kitchen-room?object=phone','/models','/gaussian','/comparisons','/legacy-editor']:
 status,h,b=read(path);assert status==200,(path,status);report['pages'].append({'path':path,'status':status,'bytes':len(b)})
for item in info['items']:
 for key in ['real_image','render_image','room_image']:
  path='/tour-assets/comparison/items/'+item[key];status,h,b=read(path);assert b[:2]==b'\xff\xd8',(item['id'],key);report['images'].append({'path':path,'status':status,'bytes':len(b)})
 for part in range(len(item['fit_paths'])):
  status,h,b=read('/item-model.glb?object='+item['id']+'&part='+str(part),{'Range':'bytes=0-19'});assert status==206 and b[:4]==b'glTF',(item['id'],part,status);report['models'].append({'id':item['id'],'part':part,'bytes':int(h['Content-Range'].split('/')[-1])})
 status,h,b=read('/item-viewer?object='+item['id']);assert b'<model-viewer' in b,item['id']
status,h,b=read('/home-scene.glb',{'Range':'bytes=0-19'});assert status==206 and b[:4]==b'glTF';scene_bytes=int(h['Content-Range'].split('/')[-1]);assert scene_bytes==struct.unpack('<III',b[:12])[2]
report.update(revision=info['revision'],items=len(info['items']),scene_bytes=scene_bytes)
Path(__file__).with_name('published_http_verification.json').write_text(json.dumps(report,indent=2));print('PUBLISHED_OK',len(report['images']),'images',len(report['models']),'models',len(report['pages']),'pages')
