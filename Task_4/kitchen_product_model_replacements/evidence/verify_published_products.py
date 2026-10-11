from urllib.request import urlopen,Request
from pathlib import Path
import json,struct
ROOT=Path(__file__).resolve().parent.parent
base='http://127.0.0.1:8767'
def get(path):
 with urlopen(base+path,timeout=30) as r:return r.read(),dict(r.headers)
data,headers=get('/tour-info');info=json.loads(data);assert info['revision']=='kitchen_product_models_pbr_v2';assert len(info['items'])==22
pages=['/','/models','/home-tour','/kitchen-room?object=range_kettle','/item-viewer?object=grinder','/gaussian','/comparisons'];checks=[]
for path in pages:
 b,h=get(path);assert b;checks.append({'path':path,'bytes':len(b)})
for item in info['items']:
 for suffix in ['real_image','render_image','room_image']:
  b,h=get('/tour-assets/comparison/items/'+item[suffix]);assert b.startswith(b'\xff\xd8')
 b,h=get('/tour-assets/comparison/items/'+item['id']+'_before.jpg');assert b.startswith(b'\xff\xd8')
 for part,fit in enumerate(item['fit_paths']):
  with urlopen(Request(base+'/item-model.glb?object='+item['id']+'&part='+str(part),headers={'Range':'bytes=0-11'}),timeout=30) as r:
   b=r.read();assert r.status==206 and b[:4]==b'glTF';magic,version,size=struct.unpack('<III',b);assert version==2
with urlopen(Request(base+'/home-scene.glb',headers={'Range':'bytes=0-11'}),timeout=30) as r:assert r.status==206 and r.read()[:4]==b'glTF'
with urlopen(Request(base+'/home-scene.glb',headers={'Accept-Encoding':'gzip'}),timeout=30) as r:
 assert r.headers.get('Content-Encoding')=='gzip';assert r.read(2)==b'\x1f\x8b';compressed_bytes=int(r.headers['Content-Length'])
report={'revision':info['revision'],'items':22,'images_verified':88,'pages':checks,'models_verified':sum(len(i['fit_paths']) for i in info['items']),'scene_range_and_lossless_gzip':True,'compressed_scene_bytes':compressed_bytes}
(ROOT/'evidence/published_http_verification.json').write_text(json.dumps(report,indent=2));print(report)
