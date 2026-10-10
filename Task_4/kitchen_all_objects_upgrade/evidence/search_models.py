"""Inspect public downloadable model metadata and artist preview thumbnails."""
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlencode
import concurrent.futures,json,io
from PIL import Image,ImageDraw
O=Path(__file__).resolve().parents[1];(O/'source').mkdir(exist_ok=True)
terms=['ceramic pitcher','jug','office telephone','coffee grinder','canister jar','knife block','wood basket','frog statue']
def search(term):
 url='https://api.sketchfab.com/v3/search?'+urlencode({'type':'models','q':term,'downloadable':'true','count':24})
 try:
  with urlopen(Request(url,headers={'User-Agent':'KitchenRepairResearch/1.0'}),timeout=30) as r:data=json.load(r)
  return {'term':term,'url':url,'models':data.get('results',[])}
 except Exception as e:return {'term':term,'url':url,'error':str(e),'models':[]}
cache=O/'evidence/search_results.json'
if cache.exists():results=json.loads(cache.read_text())
else:
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(search,terms))
(O/'evidence/search_results.json').write_text(json.dumps(results,indent=2))
selected=[]
for row in results:
 usable=[]
 for model in row['models']:
  tags=[t.get('name','').lower() for t in model.get('tags',[])]
  lic=model.get('license',{}) or {}
  if 'noai' in tags or lic.get('label') not in ['CC Attribution','CC0 Public Domain','CC Attribution-ShareAlike']:continue
  usable.append(model)
 selected.extend((row['term'],m) for m in usable[:8])
 print(row['term'],'results',len(row['models']),'CC usable',len(usable),'error',row.get('error'),flush=True)
def thumb(item):
 term,m=item;images=m.get('thumbnails',{}).get('images',[])
 if not images:return item,None
 target=min(images,key=lambda x:abs(x.get('width',0)-480))
 try:
  with urlopen(target['url'],timeout=20) as r:raw=r.read()
  path=O/'source'/(m['uid']+'.jpg');path.write_bytes(raw)
  return item,Image.open(io.BytesIO(raw)).convert('RGB')
 except Exception:return item,None
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:thumbnails=list(pool.map(thumb,selected))
canvas=Image.new('RGB',(1200,max(1,(len(thumbnails)+3)//4)*260),'#153c2c');draw=ImageDraw.Draw(canvas)
index=[]
for i,((term,m),im) in enumerate(thumbnails):
 x=(i%4)*300;y=(i//4)*260
 if im:im.thumbnail((290,195));canvas.paste(im,(x+(300-im.width)//2,y+55))
 draw.text((x+4,y+3),term+' '+m['uid'][:8],fill='white');draw.text((x+4,y+22),m.get('name','')[:38],fill='white')
 index.append({'term':term,'uid':m['uid'],'name':m.get('name'),'license':m.get('license'),'author':m.get('user',{}).get('displayName'),'url':m.get('viewerUrl'),'faces':m.get('faceCount'),'tags':m.get('tags',[])})
(O/'evidence/candidates.json').write_text(json.dumps(index,indent=2));canvas.save(O/'images/model_candidates.jpg',quality=93)
print('Saved',len(index),'candidate previews',flush=True)
