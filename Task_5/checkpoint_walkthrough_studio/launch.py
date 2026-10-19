"""Launch this standalone studio and its independent Habitat camera."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shlex
import socket
import subprocess
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / '.runtime'
HOST = os.environ.get('TASK5_SIM_HOST', 'guest-isl@172.26.186.222')
REMOTE = '/tmp/checkpoint_walkthrough_studio_20261016_v2'
REMOTE_PYTHON = '/home/guest-isl/rishabh/bench/envs/navila/bin/python'
URL = 'http://127.0.0.1:8900/'
SOCKET = 'checkpoint-walkthrough-studio'
UNIT = 'checkpoint-walkthrough-studio-tmux.service'
SSH = ['/usr/bin/ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8']


def alive(port):
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=.5):
            return True
    except OSError:
        return False


def identity():
    try:
        with urlopen(URL + 'api/health', timeout=2) as res:
            return json.load(res).get('app') == 'checkpoint-walkthrough-studio'
    except (OSError, ValueError):
        return False


def remote():
    # Upload only this application's source; never touch a V1/V2 service or session.
    code = '''import socket
from pathlib import Path
try:
 s=socket.create_connection(('127.0.0.1',8914),timeout=1);s.close();print('listening')
except OSError:
 Path(REMOTE).mkdir(parents=True,exist_ok=True);print('missing')
'''.replace('REMOTE', repr(REMOTE))
    check = subprocess.run(SSH + [HOST, shlex.join(['/usr/bin/python3', '-c', code])], capture_output=True, text=True, timeout=15, check=True)
    if check.stdout.strip() == 'listening':
        return
    subprocess.run(['/usr/bin/scp', '-q', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8',
                    str(ROOT / 'tools/scene_service.py'), str(ROOT / 'renderer_catalog.json'), HOST + ':' + REMOTE + '/'], check=True, timeout=25)
    start = '''import os,socket,subprocess
from pathlib import Path
base=Path(REMOTE)
try:
 s=socket.create_connection(('127.0.0.1',8914),timeout=1);s.close()
except OSError:
 env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES='0',OMP_NUM_THREADS='2',PYTHONDONTWRITEBYTECODE='1')
 with (base/'renderer.log').open('ab') as log:
  p=subprocess.Popen([REMOTE_INTERPRETER,'-u','-B',str(base/'scene_service.py'),'--catalog',str(base/'renderer_catalog.json'),'--port','8914'],cwd=base,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
 print('Independent renderer PID',p.pid)
'''.replace('REMOTE_INTERPRETER', repr(REMOTE_PYTHON)).replace('REMOTE', repr(REMOTE))
    result = subprocess.run(SSH + [HOST, shlex.join(['/usr/bin/python3', '-c', start])], text=True, capture_output=True, check=True, timeout=15)
    print(result.stdout.strip(), flush=True)


def worker():
    RUNTIME.mkdir(exist_ok=True)
    children = {}
    remote_check = -100
    commands = {
        'web': (8900, ['/usr/bin/python3', '-u', '-B', str(ROOT / 'server.py')]),
        'tunnel': (8912, SSH + ['-NT', '-o', 'ExitOnForwardFailure=yes', '-o', 'ServerAliveInterval=20',
                              '-o', 'ServerAliveCountMax=3', '-L', '127.0.0.1:8912:127.0.0.1:8914', HOST]),
    }
    try:
        while True:
            for role, (port, command) in commands.items():
                child = children.get(role)
                if not alive(port) and (child is None or child.poll() is not None):
                    with (RUNTIME / (role + '.log')).open('ab') as log:
                        children[role] = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=log)
            if time.monotonic() - remote_check > 40:
                remote_check = time.monotonic()
                try:
                    remote()
                except (OSError, subprocess.SubprocessError) as error:
                    print('Simulator connection pending:', error, flush=True)
            time.sleep(5)
    finally:
        for p in children.values():
            if p.poll() is None:
                p.terminate()


def tmux(*args, check=True):
    return subprocess.run(['/usr/bin/tmux', '-L', SOCKET, *args], capture_output=True, text=True, check=check)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--no-open', action='store_true')
    ap.add_argument('--status', action='store_true')
    ap.add_argument('--refresh', action='store_true', help='Reload only this app’s supervisor after a source update')
    ap.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = ap.parse_args()
    if args.worker:
        return worker()
    if args.status:
        print(('LIVE ' if identity() else 'STOPPED ') + URL)
        return
    RUNTIME.mkdir(exist_ok=True)
    if alive(8900) and not identity():
        raise SystemExit('Port 8900 belongs to another app; it was preserved.')
    if tmux('show-options', '-g', check=False).returncode:
        state = subprocess.run(['systemctl', '--user', 'show', UNIT, '--property=LoadState', '--value'], text=True, capture_output=True)
        if state.returncode == 0:
            if state.stdout.strip() == 'not-found':
                subprocess.run(['systemd-run', '--user', '--unit=' + UNIT, '--description=Checkpoint walkthrough studio supervisor',
                                '--property=Restart=on-failure', '/usr/bin/tmux', '-D', '-L', SOCKET], check=True)
            else:
                subprocess.run(['systemctl', '--user', 'start', UNIT], check=True)
            for _ in range(50):
                if tmux('show-options', '-g', check=False).returncode == 0:
                    break
                time.sleep(.1)
        else:
            tmux('new-session', '-d', '-s', 'anchor', 'sleep 86400')
            tmux('set-option', '-g', 'exit-empty', 'off')
    if args.refresh and tmux('has-session', '-t', '=studio', check=False).returncode == 0:
        tmux('send-keys', '-t', 'studio:0.0', 'C-c')
        for _ in range(100):
            if tmux('has-session', '-t', '=studio', check=False).returncode:
                break
            time.sleep(.1)
        if tmux('has-session', '-t', '=studio', check=False).returncode == 0:
            raise SystemExit('Supervisor is stopping; wait and run the launcher again.')
    if tmux('has-session', '-t', '=studio', check=False).returncode:
        command = shlex.join(['/usr/bin/python3', '-u', '-B', str(ROOT / 'launch.py'), '--worker'])
        tmux('new-session', '-d', '-s', 'studio', '-c', str(ROOT), command)
    for _ in range(50):
        if identity():
            break
        time.sleep(.1)
    if not identity():
        raise SystemExit('Server is starting. Inspect ' + str(RUNTIME / 'web.log'))
    print('LIVE ' + URL + '\nLocal recordings: ' + str(ROOT / 'sessions'))
    if not args.no_open and (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')):
        with (RUNTIME / 'browser.log').open('ab') as log:
            subprocess.Popen(['xdg-open', URL], stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)


if __name__ == '__main__':
    main()
