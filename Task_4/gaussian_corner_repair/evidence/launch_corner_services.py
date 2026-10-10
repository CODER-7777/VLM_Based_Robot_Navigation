"""Start or publish this private corner repair, preserving the live camera.

Existing earlier editor sessions and shared scene files are never touched.
--activate requires reviewed comparison evidence before publishing a checkpoint.
"""
from pathlib import Path
from urllib.request import urlopen
import argparse,json,os,signal,socket,subprocess,time,shutil
W=Path('/data/robotics/toshith/rxr_author/refined/split_visuals');O=W/'corner_v2'
parser=argparse.ArgumentParser();parser.add_argument('--activate',action='store_true');args=parser.parse_args()
def occupied(port):
 with socket.socket() as s:return s.connect_ex(('127.0.0.1',port))==0
def stop(name,allowed):
 path=W/(name+'.pid')
 if not path.exists():raise RuntimeError('Missing private PID for '+name)
 pid=int(path.read_text());cmd=Path(f'/proc/{pid}/cmdline').read_bytes()
 if not any(str(W/script).encode() in cmd for script in allowed):raise RuntimeError('PID does not belong to the private '+name+' service')
 os.kill(pid,signal.SIGTERM)
 for _ in range(30):
  if not Path(f'/proc/{pid}').exists():break
  time.sleep(.1)
 print('Stopped private',name,pid,flush=True)
def start(name,port,python,script,extra):
 if occupied(port):print(name,'already running; preserved',flush=True);return
 env=dict(os.environ,CUDA_VISIBLE_DEVICES='4',MAGNUM_LOG='quiet',HABITAT_SIM_LOG='quiet',**extra)
 with (W/(name+'.log')).open('a') as log:
  p=subprocess.Popen([python,'-u',str(W/script)],cwd=str(W),env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
 (W/(name+'.pid')).write_text(str(p.pid));print('Started',name,p.pid,flush=True)
if args.activate:
 approval=json.loads((O/'review.json').read_text())
 if not approval.get('accepted'):raise RuntimeError('Candidate has not passed image review')
 if occupied(8778):
  with urlopen('http://127.0.0.1:8778/state',timeout=10) as r:pose=json.load(r)
  (W/'resume_pose.json').write_text(json.dumps(pose,indent=2))
 for suffix in ['npz','ply']:
  current=W/('scene.'+suffix);backup=W/('scene_before_dense_corner.'+suffix)
  if not backup.exists():shutil.copy2(current,backup)
  temp=W/('scene_publishing.'+suffix);shutil.copy2(O/('scene_refined.'+suffix),temp);os.replace(temp,current)
 if occupied(8781):
  pid=int((O/'candidate.pid').read_text())
  if str(W/'visual_candidate.py').encode() not in Path(f'/proc/{pid}/cmdline').read_bytes():raise RuntimeError('Candidate PID mismatch')
  os.kill(pid,signal.SIGTERM)
 if occupied(8779):stop('visual',['visual_server.py','visual_corner_server.py'])
 if occupied(8778):stop('physics',['physics_server.py','physics_corner_server.py'])
 (W/'active_visual.json').write_text(json.dumps({'revision':'surface_anchored_corner_v2','construction':json.loads((O/'construction.json').read_text()),'appearance':json.loads((O/'appearance.json').read_text()),'review':approval},indent=2))
extra={'PATH':'/data/robotics/toshith/envs/kitchen3d/bin:'+os.environ.get('PATH',''),'CUDA_HOME':'/data/robotics/toshith/envs/kitchen3d','TORCH_EXTENSIONS_DIR':str(W/'torch_extensions'),'TORCH_CUDA_ARCH_LIST':'8.6+PTX','CC':'/usr/bin/gcc-9','CXX':'/usr/bin/g++-9','MAX_JOBS':'4'}
start('visual',8779,'/data/robotics/toshith/envs/kitchen3d/bin/python','visual_corner_server.py',extra)
start('physics',8778,'/home/guest-isl/rishabh/VLA-paper/.navida-env/bin/python','physics_corner_server.py',{})
