from pathlib import Path
from urllib.request import urlopen
import os,json,subprocess,socket,signal,time
R=Path('/data/robotics/toshith/rxr_author/refined');W=R/'kitchen_all_upgrade';S=R/'split_visuals'
# Stop only our previous review renderer, never the active dashboard renderer.
pidpath=W/'candidate.pid'
if pidpath.exists():
 pid=int(pidpath.read_text());p=Path('/proc/%d/cmdline'%pid)
 if p.exists():
  if str(W/'visual_candidate.py').encode() not in p.read_bytes():raise RuntimeError('Candidate PID mismatch')
  os.kill(pid,signal.SIGTERM)
  for i in range(40):
   with socket.socket() as sock:busy=sock.connect_ex(('127.0.0.1',8781))==0
   if not busy:break
   time.sleep(.1)
env=dict(os.environ,CUDA_VISIBLE_DEVICES='4',PATH='/data/robotics/toshith/envs/kitchen3d/bin:'+os.environ['PATH'],CUDA_HOME='/data/robotics/toshith/envs/kitchen3d',TORCH_EXTENSIONS_DIR=str(S/'torch_extensions'),TORCH_CUDA_ARCH_LIST='8.6+PTX',CC='/usr/bin/gcc-9',CXX='/usr/bin/g++-9',MAX_JOBS='4')
with (W/'candidate.log').open('a') as log:p=subprocess.Popen(['/data/robotics/toshith/envs/kitchen3d/bin/python','-u',str(W/'visual_candidate.py')],cwd=S,env=env,stdout=log,stderr=log,start_new_session=True,stdin=subprocess.DEVNULL)
pidpath.write_text(str(p.pid));print('REFINED_CANDIDATE_STARTED',p.pid)
