"""Private presentation layer for the repaired kitchen; earlier editor preserved."""
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.request import Request,urlopen
from urllib.parse import urlsplit,parse_qs,quote
from urllib.error import HTTPError
import json,os,base64,html,re
R=Path('/data/robotics/toshith/rxr_author/refined');W=R/'kitchen_all_upgrade';P=W/'previews';S=R/'split_visuals'
STYLE='body{background:#153c2c;color:#fff;font:16px sans-serif;margin:24px}a{color:#bbf7d0}button,select{padding:10px;margin:4px;cursor:pointer}img{max-width:100%;height:auto}section{margin:24px 0}model-viewer{width:100%;height:70vh;background:#ddd}.views{display:flex;gap:16px;flex-wrap:wrap}.views img{width:650px}pre{white-space:pre-wrap}'
def page(title,body,script=''):
 return ('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+title+'</title><style>'+STYLE+'</style>'+script+'</head><body>'+body+'</body></html>').encode()
def fits():
 out={}
 for entry in json.loads((W/'manifest.json').read_text()):
  if isinstance(entry,str):
   p=Path(entry);p=p if p.is_absolute() else R/p;fit=json.loads(p.read_text());out[fit['name']]=fit
 out['toaster_corner']={'name':'toaster_corner','glb':str(R/'kitchen/objects/toaster_v4/toaster_corner_pbr.glb'),'product':{'name':'Hamilton Beach Toaster Standing on Counter Slab','author':'AtTheSpeedOf','license':'CC-BY-4.0','url':'https://sketchfab.com/3d-models/toaster-0d39352a32404ce7b71b8ac020844949'}}
 return out
class Handler(BaseHTTPRequestHandler):
 def send(self,status,ctype,data):
  self.send_response(status);self.send_header('Content-Type',ctype);self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data)
 def upstream(self,port,path,body=None):
  req=Request('http://127.0.0.1:%d'%port+path,data=body,headers={'Content-Type':self.headers.get('Content-Type','application/json')})
  try:
   with urlopen(req,timeout=90) as r:self.send(r.status,r.headers.get('Content-Type','application/octet-stream'),r.read())
  except HTTPError as e:self.send(e.code,e.headers.get('Content-Type','application/json'),e.read())
 def do_GET(self):
  path=urlsplit(self.path);query=parse_qs(path.query)
  try:
   if path.path=='/':
    body='''<h1>Repaired kitchen — all objects</h1><p><a href="/comparisons">Real photo | previous | updated comparisons for every item</a> · <a href="/models">Rotate repaired models and inspect their finishes</a> · <a href="/product-viewer?object=toaster_corner" style="font-weight:bold;color:#4ade80">⭐ Toaster on Counter Top (PBR Lustre)</a> · <a href="http://localhost:8778/">Separate physics / Gaussian RGB-D</a> · <a href="/legacy-editor">Earlier full route editor</a></p><p>The counter stone is matched from the real photographs. The blue miniature creamer, caddy, bottles, knife blocks, tea and coffee objects use dense fixed surfaces. The phone uses a fixed product mesh fitted to its photograph; the stronger photo-trained frog visuals are retained alongside separate fitted proxies. Hidden surfaces and exact product details remain approximate.</p><p>Use W/S/A/D and arrow up/down to navigate. R returns to the reference view. Your live camera is preserved when this page refreshes.</p><div><button onclick="act('reference')">Reference view</button><button onclick="act('left')">Left</button><button onclick="act('forward')">Forward</button><button onclick="act('backward')">Backward</button><button onclick="act('right')">Right</button><button onclick="act('up')">Look up</button><button onclick="act('down')">Look down</button></div><div class="views"><div><p>Updated Gaussian RGB</p><img id="rgb" alt="Live repaired kitchen"></div><div><p>Optical depth — near red, far blue; invalid black</p><img id="depth" alt="Metric optical depth"></div></div><p><a id="download" href="/depth.npz">Download depth, alpha, validity and camera calibration</a></p><pre id="status"></pre><h2>Inspect specific items</h2><p><a href="/comparisons#blue_jug">Vase / blue jug</a> · <a href="/comparisons#phone">Telephone</a> · <a href="/comparisons#canister_l">Canisters</a> · <a href="/comparisons#caddy">Caddy</a> · <a href="/comparisons#frogs">Frogs</a> · <a href="/comparisons#grinder">Grinder</a></p><script>let busy=false;async function update(s){document.getElementById('rgb').src='/frame.jpg?frame_id='+s.frame_id;document.getElementById('depth').src='/depth.png?frame_id='+s.frame_id;document.getElementById('download').href='/depth.npz?frame_id='+s.frame_id;document.getElementById('status').textContent='Frame '+s.frame_id+' · camera '+JSON.stringify(s.camera_position_habitat);}async function act(action){if(busy)return;busy=true;try{const r=await fetch('/action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action})});const s=await r.json();if(!r.ok)throw Error(s.error);update(s);}catch(e){document.getElementById('status').textContent=String(e);}finally{busy=false;}}document.addEventListener('keydown',e=>{const actions={w:'forward',s:'backward',a:'left',d:'right',ArrowUp:'up',ArrowDown:'down',r:'reference'};if(actions[e.key]){e.preventDefault();act(actions[e.key]);}});fetch('/state').then(r=>r.json()).then(update);</script>'''
    self.send(200,'text/html; charset=utf-8',page('All kitchen repairs',body))
   elif path.path in ['/comparisons','/corner-comparisons']:
    rows=json.loads((P/'gaussian_index.json').read_text());by={r['name']:r for r in rows};order=['toaster','canister_l','canister_r','soap_bottle','soap_dish','soap_pump','hot_tap','air_gap','bottles','caddy','frogs','knife_block','knife_block_round','blue_jug','paper_towel','phone','grinder','range_kettle','tea_tray','glass_kettle','frother','coffee_machine','coffee_can']
    body='<a href="/">Back to live kitchen</a> · <a href="/models">Inspect models</a> · <a href="/legacy-comparisons">Earlier mesh comparison panels</a><h1>Real photo | previous Gaussian | updated kitchen</h1><p>Black areas in the previous prep-counter views were absent from that earlier corner-only Gaussian checkpoint. The updated kitchen covers these counters, but the untouched background can still have gaps.</p><p>Same calibrated camera for each comparison. The phone uses a photo-fitted product mesh with photographed controls. The frogs retain their sparse prior visual reconstruction, moved inward from the wall; they still need a closer model. The blue jug is fitted as a small 5.1 cm creamer. Photo-projected colors and fixed surfaces improve stability, but several shapes and unseen surfaces remain approximate.</p><p>'+ ' · '.join('<a href="#'+n+'">'+n.replace('_',' ')+'</a>' for n in ['blue_jug','phone','caddy','frogs','grinder','canister_l'])+'</p>'
    for n in order:
     if n not in by:continue
     row=by[n];body+='<section id="'+n+'"><h2>'+n.replace('_',' ').title()+'</h2><img src="/all-preview/'+row['comparison']+'" loading="lazy" alt="'+n+' comparison"></section>'
    body+='<h2>Additional viewpoints</h2>'
    for name in ['sink_run','jug_and_caddy','phone','prep','island']:body+='<h3>'+name.replace('_',' ')+'</h3><img src="/all-preview/novel_'+name+'.jpg" loading="lazy">'
    self.send(200,'text/html; charset=utf-8',page('All repaired-object comparisons',body))
   elif path.path=='/models':
    body='<a href="/">Back to kitchen</a><h1>Repaired model and material previews</h1><p>Drag to rotate each object under studio lighting. The Gaussian scene uses fixed kitchen appearance; the GLBs retain material parameters and fitted geometry.</p><ul>'
    body+='<li style="margin-bottom:10px"><a href="/product-viewer?object=toaster_corner" style="font-size:17px;font-weight:bold;color:#4ade80">⭐ Toaster Standing on Counter Top (In-Place PBR Lustre)</a></li>'
    body+='<li style="margin-bottom:10px"><a href="/product-viewer?object=toaster_v4" style="font-weight:bold;color:#60a5fa">🔍 Isolated Toaster Model (Hamilton Beach PBR)</a></li>'
    for name,fit in fits().items():
     if name.startswith(('counter_','sink_')) or name in ['toaster_corner','toaster_v4']:continue
     body+='<li><a href="/product-viewer?object='+quote(name)+'">'+html.escape(name)+'</a></li>'
    self.send(200,'text/html; charset=utf-8',page('Model previews',body+'</ul>'))
   elif path.path=='/product-viewer':
    name=query.get('object',['toaster_v4'])[0];fit=fits().get(name)
    if not fit:raise ValueError('Unknown model')
    credit=fit.get('product',{});src='/object.glb?object='+quote(name);display=re.sub(r'_v[0-9]+$','',name).replace('_',' ').title()
    extra_banner=''
    if name=='toaster_v4':
     extra_banner='<p style="background:#1e3a5f;padding:12px;border-radius:8px"><b>Want to see it on the counter?</b> <a href="/product-viewer?object=toaster_corner" style="color:#4ade80;font-weight:bold;text-decoration:underline">👉 Click here to inspect the toaster sitting directly on the counter slab with full PBR metallic lustre</a></p>'
    elif name=='toaster_corner':
     display='Toaster In-Place on Counter Slab (PBR Lustre)'
     extra_banner='<p style="background:#14532d;padding:12px;border-radius:8px"><b>In-place PBR view:</b> The toaster sits directly on the counter slab (z=0.929 m) next to the ceramic canister with full metallic reflections, roughness, normal maps, slots, and dials preserved under studio lighting. <a href="/product-viewer?object=toaster_v4" style="color:#93c5fd;margin-left:12px">View isolated model</a></p>'
    orbit = '220deg 60deg 1.1m' if name=='toaster_corner' else '210deg 30deg 110%'
    body='<a href="/models">All models</a> · <a href="/comparisons">Photo comparisons</a><h1>'+html.escape(display)+'</h1>'+extra_banner+'<p>Drag to rotate; scroll to zoom. Studio illumination helps inspect the material finish. Shapes and photo-derived textures may differ from the exact photographed product.</p><model-viewer src="'+src+'" camera-controls camera-orbit="'+orbit+'" environment-image="neutral" exposure="1" shadow-intensity="1" alt="'+html.escape(name)+'"></model-viewer><p><a href="'+src+'" download>Download GLB</a></p>'
    if credit:body+='<p>Source: <a href="'+html.escape(credit.get('url',''))+'">'+html.escape(credit.get('name',''))+'</a> by '+html.escape(credit.get('author',''))+' · '+html.escape({'by':'CC-BY', 'by-sa':'CC-BY-SA', 'cc0':'CC0'}.get(credit.get('license',''),credit.get('license','')))+'</p>'
    self.send(200,'text/html; charset=utf-8',page('Material preview '+name,body,'<script type="module" src="/model-viewer.min.js"></script>'))
   elif path.path=='/object.glb':
    name=query.get('object',['toaster_v4'])[0];fit=fits().get(name)
    if not fit:raise ValueError('Unknown model')
    p=Path(fit['glb']);p=p if p.is_absolute() else R/p
    if name=='toaster_v4':p=R/'kitchen/objects/toaster_v4/product_pbr.glb'
    elif name=='toaster_corner':p=R/'kitchen/objects/toaster_v4/toaster_corner_pbr.glb'
    self.send(200,'model/gltf-binary',p.read_bytes())
   elif path.path=='/model-viewer.min.js':self.send(200,'text/javascript',(R/'toaster_selected/dashboard/model-viewer.min.js').read_bytes())
   elif path.path.startswith('/all-preview/'):
    name=path.path.rsplit('/',1)[-1]
    if Path(name).name!=name or not name.endswith('.jpg'):raise ValueError('Invalid image')
    self.send(200,'image/jpeg',(P/name).read_bytes())
   elif path.path=='/legacy-comparisons':
    body='<a href="/comparisons">Latest Gaussian comparisons</a><h1>Earlier mesh repairs</h1>'
    for i in range(1,4):body+='<img src="/legacy-preview/'+str(i)+'.jpg">'
    self.send(200,'text/html; charset=utf-8',page('Earlier comparisons',body))
   elif path.path.startswith('/legacy-preview/'):
    n=path.path.rsplit('/',1)[-1]
    if n not in ['1.jpg','2.jpg','3.jpg']:raise ValueError('Unknown panel')
    self.send(200,'image/jpeg',(R/'agentA_resume/previews'/('agentA_resume_compare'+n)).read_bytes())
   elif path.path=='/legacy-editor':
    with urlopen('http://127.0.0.1:8776/',timeout=30) as r:content=r.read().decode()
    content=content.replace('"/','"/legacy/').replace("'/","'/legacy/")
    self.send(200,'text/html; charset=utf-8',content.encode())
   elif path.path.startswith('/legacy/'):self.upstream(8776,self.path[len('/legacy'):])
   elif path.path=='/scene-info':
    data={'scene_glb':str(W/'test.glb'),'visual_checkpoint':str(W/'scene_refined.npz'),'revision':'all_kitchen_v3','fits':list(fits()),'construction':json.loads((W/'construction.json').read_text()),'shared_files_modified':False};self.send(200,'application/json',json.dumps(data).encode())
   elif path.path in ['/state','/frame.jpg','/depth.png','/depth.npz','/metrics','/render-info']:self.upstream(8778,self.path)
   else:self.send(404,'text/plain',b'Not found')
  except Exception as e:self.send(503,'application/json',json.dumps({'error':str(e)}).encode())
 def do_POST(self):
  length=int(self.headers.get('Content-Length','0'))
  if length>1048576:self.send(400,'text/plain',b'Request too large');return
  body=self.rfile.read(length)
  if self.path=='/action':self.upstream(8778,self.path,body)
  elif self.path.startswith('/legacy/'):self.upstream(8776,self.path[len('/legacy'):],body)
  else:self.send(404,'text/plain',b'Not found')
ThreadingHTTPServer(('127.0.0.1',int(os.environ.get('KITCHEN_DASH_PORT','8774'))),Handler).serve_forever()
