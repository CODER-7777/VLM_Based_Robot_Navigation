"""Smoke-test all initial views and clean images; this is not a human walkthrough."""
import io
import json
from pathlib import Path
from urllib.request import Request,urlopen
from PIL import Image

HERE=Path(__file__).resolve().parent
key=(HERE/'.runtime/remote_author_key').read_text().strip()
base='http://127.0.0.1:8896'

def get(path,data=None,image=False):
    req=Request(base+path,data=json.dumps(data).encode() if data is not None else None,headers={'Cookie':'step8_author='+key,'Content-Type':'application/json'})
    with urlopen(req,timeout=120) as r:
        content=r.read()
        if image:
            im=Image.open(io.BytesIO(content));im.load();assert im.width>=512 and im.height>=480
            return dict(width=im.width,height=im.height)
        return json.loads(content)

catalog=get('/api/catalog?mode=review');props=get('/api/props')
assert len(props['props'])==5 and all(p['support_ray_hit'] for p in props['props'])
photos=set();initial_views=0
for case in catalog['cases']:
    detail=get('/api/case?mode=review&id='+case['id'])
    session=get('/api/nav/start',dict(case_id=case['id'],mode='review'))
    get('/api/nav/act',dict(token=session['token'],action='none'),image=True);initial_views+=1
    photos.update(m['photo'] for m in detail['memories'] if m['photo'])
    if detail['image']:photos.add(detail['image'])
for name in sorted(photos):get('/assets/'+name,image=True)
blind=get('/api/nav/start',dict(case_id=catalog['cases'][0]['id'],mode='blind'))
req=Request(base+'/api/nav/act',data=json.dumps(dict(token=blind['token'],action='a',overlays=True)).encode(),headers={'Content-Type':'application/json'})
with urlopen(req,timeout=30) as r:
    state=json.loads(r.headers['X-Review-State']);assert set(state)=={'steps','recording'} and not state['recording'];r.read()
result=dict(passed=True,initial_views=initial_views,clean_photos=len(photos),props_on_detected_supports=5,blind_navigation_redacted=True,human_walkthroughs_performed=False)
(HERE/'.runtime/live_checks.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
