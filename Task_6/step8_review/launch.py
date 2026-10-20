#!/usr/bin/env python3
"""Deploy or reconnect the Task 6 Step 8 review desk. Existing services are preserved."""
from __future__ import annotations
import argparse
import io
import json
import os
from pathlib import Path
import shlex
import socket
import subprocess
import tarfile
from urllib.request import urlopen

HERE=Path(__file__).resolve().parent
HOST=os.environ.get('TASK6_SIM_HOST','guest-isl@172.26.186.222')
REMOTE='/home/guest-isl/rishabh/task6_step8_review'
SSH=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=12',HOST]

def remote(code):
    return subprocess.run([*SSH,shlex.join(['python3','-c',code])],check=True,capture_output=True,text=True).stdout

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--deploy',action='store_true');p.add_argument('--restart',action='store_true',help='Restart only this dashboard’s own service');p.add_argument('--port',type=int,default=8896);p.add_argument('--open',action='store_true');args=p.parse_args()
    runtime=HERE/'.runtime';runtime.mkdir(exist_ok=True)
    if args.deploy:
        if not (HERE/'assets/calculator.glb').exists():
            raise SystemExit('Build the five models first: python3 build_props.py (requires trimesh locally).')
        buffer=io.BytesIO()
        with tarfile.open(fileobj=buffer,mode='w:gz') as tf:
            for name in ['model.py','server.py','simulator.py','index.html','app.js','style.css','assets']:
                tf.add(HERE/name,arcname=name)
        subprocess.run([*SSH,f'mkdir -p {shlex.quote(REMOTE)} && tar -xzf - -C {shlex.quote(REMOTE)}'],input=buffer.getvalue(),check=True)
    cfg=repr(json.dumps(dict(root=REMOTE,port=8896,gpu=os.environ.get('TASK6_GPU','3'),restart=args.restart)))
    result=remote('''import json,os,signal,socket,subprocess,time
from pathlib import Path
c=json.loads(CONFIG);root=Path(c['root'])
if c['restart'] and (root/'service.pid').exists():
 pid=int((root/'service.pid').read_text());proc=Path('/proc')/str(pid)
 if proc.exists():
  if str(root/'server.py') not in (proc/'cmdline').read_bytes().decode():raise SystemExit('PID belongs to another process; preserved')
  os.kill(pid,signal.SIGTERM)
  for _ in range(30):
   try:socket.create_connection(('127.0.0.1',c['port']),timeout=.1).close()
   except OSError:break
   time.sleep(.1)
try:socket.create_connection(('127.0.0.1',c['port']),timeout=1).close()
except OSError:
 env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES=c['gpu'],OMP_NUM_THREADS='2',PYTHONDONTWRITEBYTECODE='1',MAGNUM_LOG='quiet',HABITAT_SIM_LOG='quiet',LD_PRELOAD='/usr/lib/x86_64-linux-gnu/libGLX_nvidia.so.0:/usr/lib/x86_64-linux-gnu/libEGL.so.1')
 with (root/'service.log').open('ab') as log:
  proc=subprocess.Popen(['/home/guest-isl/rishabh/bench/envs/streamvln/bin/python','-u','-B',str(root/'server.py'),'--source','/data/robotics/toshith/rxr_author/levels/house_first','--navigation','--port',str(c['port'])],cwd=root,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
 (root/'service.pid').write_text(str(proc.pid))
print((root/'.runtime/author_key').read_text() if (root/'.runtime/author_key').exists() else '')
'''.replace('CONFIG',cfg))
    key=result.strip()
    if not key:
        key=remote(f"from pathlib import Path; print((Path({REMOTE!r})/'.runtime/author_key').read_text())").strip()
    (runtime/'remote_author_key').write_text(key);(runtime/'remote_author_key').chmod(0o600)
    try:
        with urlopen(f'http://127.0.0.1:{args.port}/api/health',timeout=2) as r:
            if json.load(r).get('service')!='task6-step8-review':raise RuntimeError('Local port belongs to another application')
    except OSError:
        cmd=['ssh','-NT','-o','BatchMode=yes','-o','ExitOnForwardFailure=yes','-o','ServerAliveInterval=30','-L',f'127.0.0.1:{args.port}:127.0.0.1:8896',HOST]
        with (runtime/'tunnel.log').open('ab') as log:
            proc=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
        (runtime/'tunnel.pid').write_text(str(proc.pid))
    url=f'http://127.0.0.1:{args.port}/review?key={key}'
    print('Reviewer:',url);print(f'Props: http://127.0.0.1:{args.port}/props');print(f'Blind: http://127.0.0.1:{args.port}/blind');print(f'Naturalness: http://127.0.0.1:{args.port}/naturalness')
    if args.open:subprocess.Popen(['xdg-open',url],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)

if __name__=='__main__':main()
