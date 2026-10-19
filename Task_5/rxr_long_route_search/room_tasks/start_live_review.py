"""Keep only this review's local server and SSH tunnel alive outside the chat PTY."""
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parent
RUN=ROOT/'dashboard_runtime';RUN.mkdir(exist_ok=True)
FORWARD='127.0.0.1:8892:127.0.0.1:8894'
HOST='guest-isl@172.26.186.222'


def occupied(port):
    with socket.socket() as s:return s.connect_ex(('127.0.0.1',port))==0


def owned_processes():
    servers=[];tunnels=[]
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit() or int(proc.name)==os.getpid():continue
        try:
            argv=[a.decode() for a in (proc/'cmdline').read_bytes().split(b'\0') if a]
            if not argv:continue
            cwd=(proc/'cwd').resolve()
            if Path(argv[0]).name.startswith('python') and '--port' in argv:
                port=argv[argv.index('--port')+1]
                if port in ('8890','8891') and any((cwd/a).resolve()==ROOT/'dashboard_server.py' for a in argv[1:] if a.endswith('dashboard_server.py')):
                    servers.append(int(proc.name))
            if Path(argv[0]).name=='ssh' and '-N' in argv and FORWARD in argv and HOST in argv:tunnels.append(int(proc.name))
        except (OSError,UnicodeError,IndexError):continue
    return servers,tunnels


def start(argv,log_name):
    with (RUN/log_name).open('ab') as log:
        return subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,cwd=ROOT)


def main():
    saved=RUN/'processes.json'
    if saved.exists():
        try:
            record=json.loads(saved.read_text())
            if all(Path('/proc',str(record[k])).exists() for k in ('server_pid','tunnel_pid')):
                with urlopen('http://127.0.0.1:8890/room_tasks/api/health',timeout=3) as r:
                    if r.status==200:print('ALREADY LIVE http://127.0.0.1:8890/room_tasks/review.html');return
        except (OSError,ValueError,KeyError):pass
    servers,tunnels=owned_processes()
    # Touch only the explicit review commands, never Task_4 or data collectors.
    for pid in servers+tunnels:
        try:os.kill(pid,signal.SIGTERM)
        except ProcessLookupError:pass
    deadline=time.monotonic()+5
    while any(occupied(p) for p in (8890,8892)) and time.monotonic()<deadline:time.sleep(.1)
    if occupied(8890) or occupied(8892):raise RuntimeError('A required port remains occupied; no unrelated process was stopped.')
    tunnel=start(['ssh','-N','-o','BatchMode=yes','-o','ConnectTimeout=12','-o','ExitOnForwardFailure=yes',
        '-o','ServerAliveInterval=20','-o','ServerAliveCountMax=3','-L',FORWARD,HOST],'tunnel.log')
    server=start([sys.executable,'-u','-B',str(ROOT/'dashboard_server.py'),'--port','8890'],'server.log')
    deadline=time.monotonic()+18
    while time.monotonic()<deadline:
        try:
            with urlopen('http://127.0.0.1:8890/room_tasks/api/health',timeout=2) as response:
                health=json.load(response)
                if response.status==200 and 'physical_gpu' in health:break
        except OSError:time.sleep(.2)
    else:raise RuntimeError('Review did not become ready; inspect dashboard_runtime logs.')
    record=dict(server_pid=server.pid,tunnel_pid=tunnel.pid,url='http://127.0.0.1:8890/room_tasks/review.html',
                remote_service='/tmp/rxr_review_dashboard_20261015',health=health)
    saved.write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))


if __name__=='__main__':main()
