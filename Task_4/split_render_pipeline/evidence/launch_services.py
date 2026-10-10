"""Start private services; optional visual-only reload preserves physics pose."""
from pathlib import Path
import argparse,os,socket,subprocess,signal,time
W=Path('/data/robotics/toshith/rxr_author/refined/split_visuals')
args=argparse.ArgumentParser();args.add_argument('--reload-visual',action='store_true');args=args.parse_args()
def occupied(port):
 with socket.socket() as sock:return sock.connect_ex(('127.0.0.1',port))==0
def start(name,port,python,extra):
 if occupied(port):print(name,'already running; preserved');return
 env=dict(os.environ,CUDA_VISIBLE_DEVICES='4',MAGNUM_LOG='quiet',HABITAT_SIM_LOG='quiet',**extra)
 with (W/(name+'.log')).open('w') as log:
  process=subprocess.Popen([python,'-u',str(W/(name+'_server.py'))],cwd=str(W),env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
 (W/(name+'.pid')).write_text(str(process.pid));print(name,'started',process.pid)
if args.reload_visual and occupied(8779):
 pid=int((W/'visual.pid').read_text())
 if str(W/'visual_server.py').encode() not in Path(f'/proc/{pid}/cmdline').read_bytes():raise RuntimeError('Visual PID does not match this private service')
 os.kill(pid,signal.SIGTERM);time.sleep(.3)
start('visual',8779,'/data/robotics/toshith/envs/kitchen3d/bin/python',{'PATH':'/data/robotics/toshith/envs/kitchen3d/bin:'+os.environ.get('PATH',''),'CUDA_HOME':'/data/robotics/toshith/envs/kitchen3d','TORCH_EXTENSIONS_DIR':str(W/'torch_extensions'),'TORCH_CUDA_ARCH_LIST':'8.6','CC':'/usr/bin/gcc-9','CXX':'/usr/bin/g++-9','MAX_JOBS':'4'})
start('physics',8778,'/home/guest-isl/rishabh/VLA-paper/.navida-env/bin/python',{})
