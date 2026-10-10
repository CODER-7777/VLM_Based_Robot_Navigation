from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlencode
from concurrent.futures import ThreadPoolExecutor
import json,zipfile,io,hashlib
O=Path(__file__).resolve().parents[1]
rows=json.loads((O/'evidence/candidates.json').read_text())
uids=['ede86b7cc9804f39a9fcafd263873ee0','0a09b18567594cac9ad165fda5d7e17b','33168c1e12784aaea08ed4e727665884']
uids += [r['uid'] for r in rows if r['uid'].startswith('3ee32fff')]
def download(uid):
 out=O/'source'/uid;out.mkdir(exist_ok=True)
 url=f'https://mirror.traines.eu/sketchfab-backup/{uid[:2]}/{uid}.zip'
 try:
  if not (out/'archive.zip').exists():
   with urlopen(Request(url,headers={'User-Agent':'KitchenRepairResearch/1.0'}),timeout=90) as r:(out/'archive.zip').write_bytes(r.read())
  z=zipfile.ZipFile(out/'archive.zip');meta={}
  for n in z.namelist():
   if n.endswith('.json') and '.m.' in n:meta=json.loads(z.read(n))
  lic=(meta.get('license') or {}).get('label','')
  if not lic and 'license.txt' in z.namelist():
   license_text=z.read('license.txt').decode()
   if 'CC-BY-4.0' in license_text:lic='CC Attribution'
   elif 'CC0' in license_text:lic='CC0 Public Domain'
  if lic not in ['CC Attribution','CC0 Public Domain','CC Attribution-ShareAlike']:raise ValueError('Archive licence cannot be verified '+lic)
  if not meta:meta=next((r for r in rows if r['uid']==uid),{})
  (out/'metadata.json').write_text(json.dumps(meta,indent=2))
  dest=out/'extracted';dest.mkdir(exist_ok=True)
  archives=[zipfile.ZipFile(io.BytesIO(z.read(n))) for n in z.namelist() if n.endswith('.zip')]
  if not archives:archives=[z]
  for inner in archives:
   for entry in inner.infolist():
    path=(dest/entry.filename).resolve()
    if not path.is_relative_to(dest.resolve()):raise ValueError('Unsafe archive path')
   inner.extractall(dest)
  result={'uid':uid,'url':url,'license':lic,'author':meta.get('author') or meta.get('user',{}).get('displayName'),'name':meta.get('name'),'sha256':hashlib.sha256((out/'archive.zip').read_bytes()).hexdigest(),'files':[str(p.relative_to(out)) for p in out.rglob('*') if p.is_file()]}
 except Exception as e:result={'uid':uid,'error':str(e)}
 print(json.dumps(result),flush=True);return result
with ThreadPoolExecutor(max_workers=3) as p:results=list(p.map(download,uids))
(O/'evidence/downloads.json').write_text(json.dumps(results,indent=2))
terms=['blue pitcher','milk jug','ceramic creamer','ceramic canister','storage jar clamp']
def search(t):
 try:
  u='https://api.sketchfab.com/v3/search?'+urlencode({'type':'models','q':t,'downloadable':'true','count':20})
  with urlopen(u,timeout=30) as r:return {'term':t,'models':json.load(r).get('results',[])}
 except Exception as e:return {'term':t,'error':str(e)}
with ThreadPoolExecutor(max_workers=3) as p:more=list(p.map(search,terms))
(O/'evidence/focused_search.json').write_text(json.dumps(more,indent=2))
for r in more:
 print(r['term'],[(m['uid'],m['name']) for m in r.get('models',[])[:8]],flush=True)
