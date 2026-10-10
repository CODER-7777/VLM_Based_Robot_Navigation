"""Publish the reviewed private all-object repair; preserve user camera/editor."""
from pathlib import Path
from urllib.request import urlopen,Request
import argparse,json,os,signal,socket,subprocess,time,shutil
R=Path('/data/robotics/toshith/rxr_author/refined');W=R/'kitchen_all_upgrade';S=R/'split_visuals';PYTHON='/data/robotics/toshith/envs/kitchen3d/bin/python'
parser=argparse.ArgumentParser();parser.add_argument('--activate',action='store_true');args=parser.parse_args()
def occupied(port):
 with socket.socket() as sock:return sock.connect_ex(('127.0.0.1',port))==0
def fetch(port,path):
 with urlopen('http://127.0.0.1:%d'%port+path,timeout=15) as r:return json.load(r)
def stop(pidpath,allowed):
 if not pidpath.exists():raise RuntimeError('Missing owned service PID: '+str(pidpath))
 pid=int(pidpath.read_text());proc=Path('/proc/%d/cmdline'%pid)
 if not proc.exists():return
 argv=proc.read_bytes().split(b'\0')
 if not any(str(script).encode() in argv for script in allowed):raise RuntimeError('Owned service PID mismatch: '+str(pidpath))
 os.kill(pid,signal.SIGTERM)
 for _ in range(50):
  if not proc.exists():break
  time.sleep(.1)
 print('Stopped owned service',pidpath.name,pid,flush=True)
def start(pidpath,script,extra):
 env=dict(os.environ,CUDA_VISIBLE_DEVICES='4',MAGNUM_LOG='quiet',HABITAT_SIM_LOG='quiet',**extra)
 with pidpath.with_suffix('.log').open('a') as log:p=subprocess.Popen([PYTHON,'-u',str(script)],cwd=R,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
 pidpath.write_text(str(p.pid));print('Started private service',script.name,p.pid,flush=True)
def ready(port,path,limit=60):
 end=time.monotonic()+limit
 while time.monotonic()<end:
  try:return fetch(port,path)
  except Exception:time.sleep(.3)
 raise RuntimeError('Service did not become ready: '+str(port))
cuda={'PATH':str(Path(PYTHON).parent)+':'+os.environ['PATH'],'CUDA_HOME':str(Path(PYTHON).parent.parent),'TORCH_EXTENSIONS_DIR':str(S/'torch_extensions'),'TORCH_CUDA_ARCH_LIST':'8.6+PTX','CC':'/usr/bin/gcc-9','CXX':'/usr/bin/g++-9','MAX_JOBS':'4'}
habitat={'PYTHONNOUSERSITE':'1','PYTHONPATH':':'.join([str(W/'vendor'),'/home/guest-isl/rishabh/habitat-sim-v0.2.4/build/lib.linux-x86_64-cpython-310','/home/guest-isl/rishabh/habitat-sim-v0.2.4/build/deps/magnum-bindings/src/python'])}
if args.activate:
 review=json.loads((W/'review.json').read_text());validation=json.loads((W/'validation.json').read_text());audit=(W/'audit_final.log').read_text()
 if not review.get('accepted') or not validation['all_gaussian_parameters_finite'] or 'AUDIT objects 33 issues 0' not in audit:raise RuntimeError('Candidate review/audit is incomplete')
 before=fetch(8778,'/state') if occupied(8778) else None
 if before:(S/'resume_pose.json').write_text(json.dumps(before,indent=2))
 for suffix in ['npz','ply']:
  active=S/('scene.'+suffix);backup=S/('scene_before_all_kitchen.'+suffix)
  if active.exists() and not backup.exists():shutil.copy2(active,backup)
  temp=S/('scene_all_publishing.'+suffix);shutil.copy2(W/('scene_refined.'+suffix),temp);os.replace(temp,active)
 if occupied(8779):stop(S/'visual.pid',[S/'visual_corner_server.py',S/'visual_server.py',W/'visual_all_server.py'])
 start(S/'visual.pid',W/'visual_all_server.py',cuda);health=ready(8779,'/health')
 if health.get('revision')!='all_kitchen_v3' or health['gaussians']!=validation['gaussians']:raise RuntimeError('Incorrect visual checkpoint')
 if occupied(8778):
  before=fetch(8778,'/state');(S/'resume_pose.json').write_text(json.dumps(before,indent=2));stop(S/'physics.pid',[S/'physics_corner_server.py',S/'physics_server.py',W/'physics_all_server.py'])
 start(S/'physics.pid',W/'physics_all_server.py',habitat);after=ready(8778,'/state')
 if before:
  import numpy as np
  if np.max(np.abs(np.array(before['c2w_raw_gl'])-np.array(after['c2w_raw_gl'])))>1e-4:raise RuntimeError('Camera pose was not preserved')
 # Replace just the private presentation wrapper. The earlier editor on 8776
 # retains its process, scene, current pose and all advanced controls.
 if occupied(8774):stop(R/'dashboard_restore/pid',[R/'dashboard_restore/full_editor_proxy.py',W/'all_dashboard.py'])
 start(R/'dashboard_restore/pid',W/'all_dashboard.py',{'KITCHEN_DASH_PORT':'8774'});info=ready(8774,'/scene-info')
 publication={'revision':'all_kitchen_v3','scene_glb':info['scene_glb'],'visual_checkpoint':str(W/'scene_refined.npz'),'health':health,'camera_before':before,'camera_after':after,'prior_editor_preserved':occupied(8776),'shared_files_modified':False,'review':review,'backups':[str(S/'scene_before_all_kitchen.npz'),str(S/'scene_before_all_kitchen.ply')]}
 (W/'publication.json').write_text(json.dumps(publication,indent=2));(S/'active_visual.json').write_text(json.dumps(publication,indent=2));print('ALL_KITCHEN_PUBLISHED',health,flush=True)
else:
 if not occupied(8779):start(S/'visual.pid',W/'visual_all_server.py',cuda);ready(8779,'/health')
 if not occupied(8778):start(S/'physics.pid',W/'physics_all_server.py',habitat);ready(8778,'/state')
 if not occupied(8774):start(R/'dashboard_restore/pid',W/'all_dashboard.py',{'KITCHEN_DASH_PORT':'8774'});ready(8774,'/scene-info')
