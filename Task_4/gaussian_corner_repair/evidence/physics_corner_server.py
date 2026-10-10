"""Sensorless Habitat/Bullet process. All displayed pixels come from gsplat.

Navigation uses the proxy NavMesh. This prototype keeps the scene static;
dynamic object edits and articulated doors are not yet synchronized to splats.
"""
import os,json,math,time,threading,queue,io,base64
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.request import Request,urlopen
from urllib.parse import urlsplit,parse_qs
import numpy as np
import quaternion
import habitat_sim
W=Path('/data/robotics/toshith/rxr_author/refined/split_visuals')
C=np.array([[1.,0,0],[0,0,1],[0,-1,0]])
config=habitat_sim.SimulatorConfiguration();config.scene_id=str(W/'proxy.glb');config.enable_physics=True;config.create_renderer=False
agent_config=habitat_sim.agent.AgentConfiguration();agent_config.sensor_specifications=[]
sim=habitat_sim.Simulator(habitat_sim.Configuration(config,[agent_config]))
settings=habitat_sim.NavMeshSettings();settings.set_defaults();settings.agent_radius=.18;settings.agent_height=1.5
if not sim.recompute_navmesh(sim.pathfinder,settings,include_static_objects=True):raise RuntimeError('Proxy NavMesh build failed')
sim.pathfinder.save_nav_mesh(str(W/'proxy.navmesh'))
placement=json.loads((W.parent/'toaster_selected/placement.json').read_text());source=np.array(placement['camera']['c2w'])
start_raw=source[:3,3].copy();start_raw[2]=.05
start=np.asarray(sim.pathfinder.snap_point(C@start_raw),dtype=np.float32)
assert np.isfinite(start).all(), 'Kitchen start is not navigable on proxy'
assert np.linalg.norm((start-C@start_raw)[[0,2]])<.35,'Proxy start moved too far from kitchen'
start_state=habitat_sim.AgentState();start_state.position=start;start_state.rotation=quaternion.from_rotation_matrix(C@source[:3,:3])
sim.get_agent(0).set_state(start_state,reset_sensors=True)
camera_height=float(source[2,3]-start[1])
frame_id=0;packet={};jobs=queue.Queue();last_motion=0.
def publish():
 global packet
 state=sim.get_agent(0).get_state()
 pos=np.asarray(state.position,float)+[0,camera_height,0]
 rotation=quaternion.as_rotation_matrix(state.rotation)
 c2w=np.eye(4);c2w[:3,:3]=C.T@rotation;c2w[:3,3]=C.T@pos
 packet={'frame_id':frame_id,'width':800,'height':640,'K':[[placement['camera']['K'][0]*800/1280,0,placement['camera']['K'][2]*800/1280],[0,placement['camera']['K'][1]*640/1024,placement['camera']['K'][3]*640/1024],[0,0,1]],'c2w_raw_gl':c2w.tolist(),'coordinate_frame':'raw MP3D Z-up metres','agent_position_habitat':np.asarray(state.position).tolist(),'camera_position_habitat':pos.tolist(),'last_motion_m':last_motion}
publish()
# Check the frame bridge against the exact calibrated camera at startup.
frame_error=float(np.abs(np.asarray(packet['c2w_raw_gl'])-source).max())
assert frame_error<1e-5,(frame_error,'Camera frame conversion mismatch')
# Measure individual navigation/physics query throughput; never call it RGB FPS.
count=2000;forward=quaternion.rotate_vectors(start_state.rotation,np.array([0.,0.,-.02]));forward[1]=0
begin=time.perf_counter()
for _ in range(count):sim.pathfinder.try_step(start,start+forward)
nav_ms=(time.perf_counter()-begin)*1000/count
begin=time.perf_counter()
for _ in range(500):sim.step_physics(1/60)
bullet_ms=(time.perf_counter()-begin)*1000/500
# A long movement toward the kitchen counter must stop before passing its wall.
requested=start+forward/np.linalg.norm(forward)*2
stopped=np.asarray(sim.pathfinder.try_step(start,requested),dtype=np.float32)
blocked=float(np.linalg.norm(stopped-start))<1.8
assert blocked,'Collision proxy did not stop the kitchen counter/wall probe'
metrics={'proxy':str(W/'proxy.glb'),'habitat_renderer_created':False,'visual_sensors':0,'enable_physics':True,'navmesh_loaded':sim.pathfinder.is_loaded,'navmesh_area_m2':sim.pathfinder.navigable_area,'start_position_habitat':start.tolist(),'camera_transform_max_error':frame_error,'navmesh_try_step_mean_ms':nav_ms,'navmesh_queries_per_second':1000/nav_ms,'bullet_empty_world_step_mean_ms':bullet_ms,'counter_wall_probe_blocked':blocked,'counter_wall_probe_distance_m':float(np.linalg.norm(stopped-start)),'limitations':['Static proxy; dynamic objects and articulated edits are not synchronized to Gaussians.','NavMesh collision constrains the navigation agent; it is not a simulated articulated robot body.','Bullet benchmark is empty dynamic-world stepping, not a robot contact workload.','Navigation/physics throughput is separate from rendered RGB-D frame throughput.']}
(W/os.environ.get('PHYSICS_VALIDATION_FILE','physics_validation.json')).write_text(json.dumps(metrics,indent=2));print('SPLIT_PHYSICS_READY',json.dumps(metrics),flush=True)
# Restore the current private demo pose when replacing its UI process.
resume_path=W/'resume_pose.json'
if resume_path.exists():
 try:
  resume=json.loads(resume_path.read_text())
  state=sim.get_agent(0).get_state()
  position=np.asarray(resume['agent_position_habitat'],dtype=np.float32)
  snapped=np.asarray(sim.pathfinder.snap_point(position),dtype=np.float32)
  if not np.isfinite(snapped).all() or np.linalg.norm(snapped-position)>.08:raise ValueError('Saved pose is outside the new NavMesh')
  state.position=snapped
  state.rotation=quaternion.from_rotation_matrix(C@np.asarray(resume['c2w_raw_gl'])[:3,:3])
  sim.get_agent(0).set_state(state,reset_sensors=True)
  frame_id=int(resume['frame_id'])+1;publish()
  print('PRESERVED_CAMERA_POSE',frame_id,flush=True)
 except Exception as exc:print('RESUME_POSE_SKIPPED',str(exc),flush=True)
HTML='''<!doctype html><html><head><meta charset="utf-8"><title>Separate physics and Gaussian visuals — kitchen prototype</title><style>body{background:#153c2c;color:white;font:16px sans-serif;margin:24px}a{color:#bbf7d0}.views{display:flex;gap:12px;flex-wrap:wrap}img{width:600px;max-width:100%;height:auto}button{padding:12px;margin:4px;cursor:pointer}pre{white-space:pre-wrap}</style></head><body><a href="http://localhost:8767/">Full repaired-object editor</a><h1>Repaired kitchen corner — RGB and depth</h1><p>The toaster corner has been rebuilt with dense surface geometry and refined appearance. Other areas remain experimental. Movement uses a separate invisible collision model.</p><p>Use W/S/A/D to navigate; arrow up/down to tilt the camera. Press R or Reference view to return to the calibrated kitchen photo. The server preserves your camera when this page is refreshed.</p><p><a href="http://localhost:8767/comparisons">All repaired-object comparisons</a> · <a href="http://localhost:8767/product-viewer">Inspect the original metallic toaster model</a> · <a href="/corner-comparisons">Gaussian before / after and additional angles</a></p><div><button onclick="act('reference')">Reference view</button><button onclick="act('left')">Turn left</button><button onclick="act('forward')">Forward</button><button onclick="act('backward')">Backward</button><button onclick="act('right')">Turn right</button><button onclick="act('up')">Look up</button><button onclick="act('down')">Look down</button></div><div class="views"><div><p>Gaussian RGB</p><img id="rgb"></div><div><p>Optical depth: 0.3 m red → 3.5 m blue; invalid black</p><img id="depth"></div></div><p><a id="download" href="/depth.npz">Download this pose's metric depth, validity, alpha and camera calibration</a></p><pre id="status"></pre><details><summary>Measured performance and limitations</summary><pre id="metrics"></pre></details><script>let busy=false;async function update(state){document.getElementById('rgb').src='/frame.jpg?frame_id='+state.frame_id;document.getElementById('depth').src='/depth.png?frame_id='+state.frame_id;document.getElementById('download').href='/depth.npz?frame_id='+state.frame_id;document.getElementById('status').textContent='Frame '+state.frame_id+' · move '+state.last_motion_m.toFixed(3)+' m · camera '+JSON.stringify(state.camera_position_habitat);}async function act(action){if(busy)return;busy=true;try{let r=await fetch('/action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action})});let s=await r.json();if(!r.ok)throw Error(s.error);await update(s);}catch(e){document.getElementById('status').textContent=String(e);}finally{busy=false;}}document.addEventListener('keydown',e=>{const m={w:'forward',s:'backward',a:'left',d:'right',ArrowUp:'up',ArrowDown:'down',r:'reference'};if(m[e.key]){e.preventDefault();act(m[e.key]);}});fetch('/state').then(r=>r.json()).then(update);fetch('/metrics').then(r=>r.json()).then(m=>document.getElementById('metrics').textContent=JSON.stringify(m,null,2));</script></body></html>'''
def get_render(snapshot):
 req=Request('http://127.0.0.1:8779/render',data=json.dumps(snapshot).encode(),headers={'Content-Type':'application/json'})
 with urlopen(req,timeout=60) as response:return json.load(response)
class Handler(BaseHTTPRequestHandler):
 def send(self,status,ctype,data):
  self.send_response(status);self.send_header('Content-Type',ctype);self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data)
 def send_json(self,status,data):self.send(status,'application/json',json.dumps(data).encode())
 def do_GET(self):
  path=urlsplit(self.path);snapshot=packet
  try:
   if path.path=='/':self.send(200,'text/html; charset=utf-8',HTML.encode())
   elif path.path=='/corner-comparisons':
    content='<!doctype html><html><head><meta charset="utf-8"><title>Gaussian corner repair comparisons</title><style>body{background:#153c2c;color:white;font:16px sans-serif;margin:24px}a{color:#bbf7d0}img{max-width:100%;height:auto;display:block;margin:16px 0}</style></head><body><a href="/">Back to RGB-D navigation</a><h1>Toaster corner: previous / repaired Gaussian scene</h1><p>Dense samples follow the fitted toaster and repaired wall/counter surfaces. Countertop colors use available photographs; toaster appearance uses original PBR-material renders. These saved comparisons do not imply that other rooms have been repaired.</p>'
    for index,title in enumerate(['Calibrated reference','Saved user viewing angle','Additional angle 1','Additional angle 2','Close-up']):content+='<h2>'+title+'</h2><img src="/corner-preview/'+str(index)+'.jpg">'
    self.send(200,'text/html; charset=utf-8',(content+'</body></html>').encode())
   elif path.path.startswith('/corner-preview/'):
    name=path.path.rsplit('/',1)[-1]
    if name not in ['0.jpg','1.jpg','2.jpg','3.jpg','4.jpg']:self.send_json(404,{'error':'Not found'});return
    self.send(200,'image/jpeg',(W/'corner_v2/previews'/('comparison'+name)).read_bytes())
   elif path.path=='/state':self.send_json(200,snapshot)
   elif path.path=='/metrics':self.send_json(200,{'physics':metrics,'visuals':json.loads((W/'training.json').read_text()),'corner_repair':json.loads((W/'corner_v2/appearance.json').read_text())})
   elif path.path in ['/frame.jpg','/depth.png','/depth.npz']:
    frame=parse_qs(path.query).get('frame_id',[str(snapshot['frame_id'])])[0]
    if int(frame)!=snapshot['frame_id']:self.send_json(409,{'error':'Pose advanced; request the current frame again'});return
    result=get_render(snapshot)
    key,ctype={'/frame.jpg':('rgb_jpeg','image/jpeg'),'/depth.png':('depth_png','image/png'),'/depth.npz':('depth_npz','application/octet-stream')}[path.path]
    self.send(200,ctype,base64.b64decode(result[key]))
   elif path.path=='/render-info':
    result=get_render(snapshot);self.send_json(200,{k:v for k,v in result.items() if k not in ['rgb_jpeg','depth_png','depth_npz']})
   else:self.send_json(404,{'error':'Not found'})
  except Exception as exc:self.send_json(503,{'error':str(exc)})
 def do_POST(self):
  if self.path!='/action':self.send_json(404,{'error':'Not found'});return
  try:
   length=int(self.headers.get('Content-Length','0'))
   if length>4096:raise ValueError('Request too large')
   action=json.loads(self.rfile.read(length)).get('action')
   if action not in ['forward','backward','left','right','up','down','reference']:raise ValueError('Unknown action')
   event=threading.Event();job={'action':action,'event':event};jobs.put(job)
   if not event.wait(15):raise TimeoutError('Physics owner thread timed out')
   if 'error' in job:raise RuntimeError(job['error'])
   self.send_json(200,job['result'])
  except Exception as exc:self.send_json(400,{'error':str(exc)})
server=ThreadingHTTPServer(('127.0.0.1',int(os.environ.get('PHYSICS_DEMO_PORT','8778'))),Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
while True:
 try:job=jobs.get(timeout=.5)
 except queue.Empty:continue
 try:
  state=sim.get_agent(0).get_state();action=job['action'];last_motion=0.
  if action in ['forward','backward']:
   direction=quaternion.rotate_vectors(state.rotation,np.array([0.,0.,-1.]));direction[1]=0;direction/=np.linalg.norm(direction)
   target=np.asarray(state.position)+direction*(.2 if action=='forward' else -.2)
   actual=np.asarray(sim.pathfinder.try_step(state.position,target),dtype=np.float32);last_motion=float(np.linalg.norm(actual-state.position));state.position=actual
  elif action=='reference':
   state.position=start.copy();state.rotation=quaternion.from_rotation_matrix(C@source[:3,:3])
  elif action in ['left','right']:
   state.rotation=quaternion.from_rotation_vector([0,math.radians(10 if action=='left' else -10),0])*state.rotation
  else:state.rotation=state.rotation*quaternion.from_rotation_vector([math.radians(5 if action=='up' else -5),0,0])
  sim.get_agent(0).set_state(state,reset_sensors=True);sim.step_physics(1/60);frame_id+=1;publish();job['result']=packet
 except Exception as exc:job['error']=str(exc)
 finally:job['event'].set()
