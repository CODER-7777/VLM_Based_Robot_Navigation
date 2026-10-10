"""Read-only checks of the published dashboard, RGB/depth and model routes."""
from urllib.request import urlopen
from pathlib import Path
import json,io,numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parent.parent;BASE='http://127.0.0.1:8767'
def read(path):
 with urlopen(BASE+path,timeout=90) as r:return r.status,r.headers.get('Content-Type'),r.read()
def obj(path):return json.loads(read(path)[2])
info=obj('/scene-info');state=obj('/state');render=obj('/render-info');assert info['revision']=='all_kitchen_v3';assert not info['shared_files_modified'];assert render['frame_id']==state['frame_id'];assert len(info['fits'])==40
routes={}
for path in ['/','/comparisons','/models','/product-viewer?object=blue_jug_v4','/product-viewer?object=phone_v4','/legacy-editor','/legacy-comparisons']:
 status,ctype,data=read(path);assert status==200;routes[path]={'status':status,'bytes':len(data)}
for path,name in [('/frame.jpg','live_rgb.jpg'),('/depth.png','live_depth.png')]:
 data=read(path+'?frame_id='+str(state['frame_id']))[2];im=Image.open(io.BytesIO(data));assert im.size==(800,640);(ROOT/'images'/name).write_bytes(data)
data=read('/depth.npz?frame_id='+str(state['frame_id']))[2];d=np.load(io.BytesIO(data));assert d['depth_m'].shape==(640,800);assert np.isfinite(d['depth_m'][d['valid']]).all();assert np.isnan(d['depth_m'][~d['valid']]).all();assert np.allclose(d['K'],state['K']);assert np.allclose(d['c2w_raw_gl'],state['c2w_raw_gl']);(ROOT/'evidence'/'live_depth.npz').write_bytes(data)
# Verify both new key models are actual glTF binary assets, not an HTML error.
for name in ['toaster_v4','blue_jug_v4','phone_v4','caddy_v3','canister_l_v3','grinder_v3']:
 status,ctype,data=read('/object.glb?object='+name);assert status==200 and data[:4]==b'glTF';routes[name]={'status':status,'glb_bytes':len(data)}
report={'revision':info['revision'],'fits':len(info['fits']),'gaussians':info['construction']['final_gaussians'],'routes':routes,'state':state,'render_info':render,'depth_valid_fraction':float(d['valid'].mean()),'depth_median_m':float(np.nanmedian(d['depth_m'])),'shared_files_modified':False};(ROOT/'evidence'/'published_validation.json').write_text(json.dumps(report,indent=2));print('PUBLISHED_OK',report['revision'],report['gaussians'],'Gaussians',len(routes),'routes, metric depth valid',report['depth_valid_fraction'])
