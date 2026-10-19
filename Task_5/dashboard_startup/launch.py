"""Start/reuse Task 5 dashboards in tmux and open them in the desktop browser."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import socket
import subprocess
import sys
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
RUNTIME = HERE / '.runtime'
SOCKET = 'task5-dashboards'
TMUX_UNIT = 'task5-dashboard-tmux.service'
HOST = os.environ.get('TASK5_SIM_HOST', 'guest-isl@172.26.186.222')
REMOTE_PYTHON = '/home/guest-isl/rishabh/bench/envs/navila/bin/python'
REVIEW_REMOTE = '/tmp/rxr_review_dashboard_20261015'

def tunnel(local_port, remote_port):
    return ['/usr/bin/ssh', '-NT', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
            '-o', 'ExitOnForwardFailure=yes', '-o', 'ServerAliveInterval=30',
            '-o', 'ServerAliveCountMax=3', '-L',
            f'127.0.0.1:{local_port}:127.0.0.1:{remote_port}', HOST]

TARGETS = {
    'voice-video': {
        'label': 'Voice and video collection', 'session': 'task5-voice-video',
        'url': 'http://localhost:8878/', 'probe': 'http://127.0.0.1:8878/api/state',
        'identity': 'session_id', 'components': [('tunnel', 8878, tunnel(8878, 8878))],
        'remote': ('/home/guest-isl/rishabh/bench/experiments/level3_manual_collector_v2',
                   'collector.py', ['--port', '8878'], 8878)},
    'original': {
        'label': 'Original collection dashboard', 'session': 'task5-original-collector',
        'url': 'http://localhost:8876/', 'probe': 'http://127.0.0.1:8876/api/state',
        'identity': 'session_id', 'components': [('tunnel', 8876, tunnel(8876, 8876))],
        'remote': ('/home/guest-isl/rishabh/bench/experiments/level3_manual_collector',
                   'collector.py', ['--port', '8876'], 8876)},
    'research': {
        'label': 'RxR trajectories and backpack models', 'session': 'task5-research',
        'url': 'http://127.0.0.1:8894/', 'probe': 'http://127.0.0.1:8894/data.json',
        'identity': 'selected_indices', 'components': [('web', 8894,
            ['/usr/bin/python3', '-u', '-B', str(ROOT/'rxr_long_route_search/model_research_20261015/dashboard/serve_dashboard.py'), '--port', '8894'])]},
    'trajectory-review': {
        'label': 'Interactive trajectory and room review', 'session': 'task5-trajectory-review',
        'url': 'http://127.0.0.1:8890/room_tasks/review.html',
        'probe': 'http://127.0.0.1:8890/room_tasks/api/health', 'identity': 'physical_gpu',
        'components': [('tunnel', 8892, tunnel(8892, 8894)),
            ('web', 8890, ['/usr/bin/python3', '-u', '-B',
             str(ROOT/'rxr_long_route_search/room_tasks/dashboard_server.py'),
             '--port', '8890', '--upstream', 'http://127.0.0.1:8892'])],
        'remote': (REVIEW_REMOTE, 'interactive_scene_service.py',
                   ['--catalog', REVIEW_REMOTE+'/dashboard_catalog.json', '--port', '8894'], 8894)},
}

def tmux(*args, check=True):
    return subprocess.run(['/usr/bin/tmux', '-L', SOCKET, *args], text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=check)

def listening(port):
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=.6):
            return True
    except OSError:
        return False

def healthy(target):
    try:
        with urlopen(target['probe'], timeout=2) as response:
            data = json.load(response)
            return response.status == 200 and isinstance(data, dict) and target['identity'] in data
    except (OSError, ValueError):
        return False

def ensure_tmux_server():
    if not shutil.which('tmux'):
        raise RuntimeError('tmux is required. Install it, then run this script again.')
    if tmux('show-options', '-g', check=False).returncode == 0:
        return
    # The managed server survives tool-session cleanup; each dashboard runs in a pane.
    state = subprocess.run(['systemctl', '--user', 'show', TMUX_UNIT,
                            '--property=LoadState', '--value'], text=True, capture_output=True)
    if state.returncode == 0:
        if state.stdout.strip() == 'not-found':
            subprocess.run(['systemd-run', '--user', '--unit='+TMUX_UNIT,
                            '--description=Task 5 dashboard tmux server',
                            '--property=Restart=on-failure', '--property=RestartSec=5',
                            '/usr/bin/tmux', '-D', '-L', SOCKET], check=True)
        else:
            subprocess.run(['systemctl', '--user', 'start', TMUX_UNIT], check=True)
        deadline = time.monotonic()+8
        while time.monotonic() < deadline:
            if tmux('show-options', '-g', check=False).returncode == 0:
                return
            time.sleep(.1)
        raise RuntimeError('Managed tmux did not start; inspect journalctl --user -u '+TMUX_UNIT)
    # Standard desktop fallback if no user service manager exists.
    command = 'exec '+shlex.join(['/usr/bin/python3', '-c', 'import time; time.sleep(86400)'])
    tmux('new-session', '-d', '-s', 'task5-server-anchor', command)
    tmux('set-option', '-g', 'exit-empty', 'off')

def ensure_session(name):
    session = TARGETS[name]['session']
    if tmux('has-session', '-t', '='+session, check=False).returncode == 0:
        print('Reusing tmux session:', session, flush=True)
        return
    command = 'exec '+shlex.join(['/usr/bin/python3', '-u', '-B', str(Path(__file__).resolve()), '--worker', name])
    result = tmux('new-session', '-d', '-s', session, '-c', str(ROOT), command, check=False)
    if result.returncode and tmux('has-session', '-t', '='+session, check=False).returncode:
        raise RuntimeError(result.stderr.strip())
    print('Started tmux session:', session, flush=True)

def ensure_remote(target):
    directory, script, args, port = target['remote']
    # Preserve any listening backend, including its active recording sample.
    # Missing remote source files are reported rather than re-uploaded.
    code = r'''import json,os,socket,subprocess
from pathlib import Path
cfg=json.loads(CONFIG)
try:
    sock=socket.create_connection(('127.0.0.1',cfg['port']),timeout=2)
except OSError:
    base=Path(cfg['directory']);script=base/cfg['script']
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():continue
        try:
            argv=[v.decode() for v in (proc/'cmdline').read_bytes().split(b'\0') if v]
            same=str(script) in argv or (cfg['script'] in argv and (proc/'cwd').resolve()==base.resolve())
            if same and '--port' in argv and argv[argv.index('--port')+1]==str(cfg['port']):
                print('Existing backend process is initializing; preserved PID',proc.name);raise SystemExit(0)
        except (OSError,UnicodeError,ValueError,IndexError):pass
    if not script.is_file():raise SystemExit('Remote application missing: '+str(script))
    env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES='0',OMP_NUM_THREADS='2',PYTHONDONTWRITEBYTECODE='1')
    with (base/'dashboard_startup.log').open('ab') as log:
        p=subprocess.Popen([cfg['python'],'-u','-B',str(script),*cfg['args']],cwd=base,
                           stdin=subprocess.DEVNULL,stdout=log,stderr=log,env=env,start_new_session=True)
    print('Started missing backend',cfg['port'],'PID',p.pid)
else:
    sock.close();print('Existing backend is listening on',cfg['port'],'(preserved)')
'''
    cfg = json.dumps(dict(directory=directory, script=script, args=args, port=port, python=REMOTE_PYTHON))
    code = code.replace('CONFIG', repr(cfg), 1)
    result = subprocess.run(['/usr/bin/ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                             HOST, shlex.join(['/usr/bin/python3', '-c', code])],
                            text=True, capture_output=True, timeout=25)
    if result.stdout.strip():
        print(result.stdout.strip(), flush=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or 'Could not check/start the remote backend')

def worker(name):
    target = TARGETS[name]
    RUNTIME.mkdir(exist_ok=True)
    children = {}
    previous = None
    remote_check = -100.
    print(target['label']+'\n'+target['url'], flush=True)
    print('Existing live processes are reused. Ctrl-b, then d detaches this pane.', flush=True)
    try:
        while True:
            for role, port, command in target['components']:
                child = children.get(role)
                if not listening(port) and (child is None or child.poll() is not None):
                    log_path = RUNTIME/(name+'-'+role+'.log')
                    with log_path.open('ab') as log:
                        children[role] = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                                                          stdout=log, stderr=log)
                    print('Started '+role+'; log: '+str(log_path), flush=True)
            ready = healthy(target)
            if not ready and 'remote' in target and time.monotonic()-remote_check >= 35:
                remote_check = time.monotonic()
                try:
                    ensure_remote(target)
                except (OSError, subprocess.SubprocessError, RuntimeError) as error:
                    print('Connection pending:', error, flush=True)
            if ready != previous:
                print(('LIVE: ' if ready else 'Waiting for: ')+target['url'], flush=True)
                previous = ready
            time.sleep(3 if not ready else 10)
    finally:
        for child in children.values():
            if child.poll() is None:
                child.terminate()

def open_browser(url):
    if not (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')):
        print('No desktop display found. Open this address in your browser: '+url)
        return
    opener = shutil.which('xdg-open')
    if not opener:
        print('xdg-open unavailable. Open: '+url)
        return
    with (RUNTIME/'browser.log').open('ab') as log:
        subprocess.Popen([opener, url], stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target', nargs='?', choices=['all', *TARGETS], default='all')
    parser.add_argument('--no-open', action='store_true', help='Start/reuse without opening browser tabs')
    parser.add_argument('--status', action='store_true', help='Read status without starting anything')
    parser.add_argument('--timeout', type=float, default=90, help='Maximum readiness wait in seconds')
    parser.add_argument('--worker', choices=TARGETS, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        worker(args.worker)
        return 0
    names = list(TARGETS) if args.target == 'all' else [args.target]
    RUNTIME.mkdir(exist_ok=True)
    if args.status:
        for name in names:
            target = TARGETS[name]
            print(('LIVE ' if healthy(target) else 'OFFLINE ')+target['label']+' — '+target['url'])
        return 0
    ensure_tmux_server()
    for name in names:
        ensure_session(name)
    pending = set(names)
    deadline = time.monotonic()+max(0, args.timeout)
    while pending and time.monotonic() < deadline:
        for name in list(pending):
            target = TARGETS[name]
            if healthy(target):
                print('LIVE '+target['label']+' — '+target['url'], flush=True)
                if not args.no_open:
                    open_browser(target['url'])
                pending.remove(name)
        if pending:
            time.sleep(.5)
    status = {name: dict(url=TARGETS[name]['url'], session=TARGETS[name]['session'], live=name not in pending) for name in names}
    (RUNTIME/'last_launch.json').write_text(json.dumps(status, indent=2)+'\n')
    for name in pending:
        print('Not ready yet: '+TARGETS[name]['label']+' — '+TARGETS[name]['url'], file=sys.stderr)
        print('Check VPN/SSH access; attach with: tmux -L '+SOCKET+' attach -t '+TARGETS[name]['session'], file=sys.stderr)
    return 1 if pending else 0

if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, subprocess.SubprocessError, RuntimeError) as error:
        print('Startup failed:', error, file=sys.stderr)
        raise SystemExit(1)
