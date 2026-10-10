"""Detach the private dashboard tunnel so a cancelled tool turn does not close it."""
from pathlib import Path
from urllib.request import urlopen
import os, socket, subprocess, time, shutil

destination = os.environ.get('ISL_DESTINATION', 'guest-isl@172.26.186.222')
log_path = Path('/tmp/toaster-home-tour-tunnel.log')
pid_path = Path('/tmp/toaster-home-tour-tunnel.pid')

def occupied(port):
    with socket.socket() as sock:
        return sock.connect_ex(('127.0.0.1', port)) == 0

pairs = [(8767, 8774), (8778, 8778), (8776, 8776)]
forward = []
for local, remote in pairs:
    if not occupied(local):
        forward.extend(['-L', '127.0.0.1:%d:127.0.0.1:%d' % (local, remote)])

if forward:
    command = ['ssh', '-N', '-o', 'ExitOnForwardFailure=yes', '-o', 'ConnectTimeout=15',
               '-o', 'ServerAliveInterval=30', '-o', 'ServerAliveCountMax=3',
               '-o', 'BatchMode=yes', *forward, destination]
    service = None
    probe = subprocess.run(['systemctl', '--user', 'is-system-running'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) if shutil.which('systemctl') else None
    if shutil.which('systemd-run') and probe and probe.returncode == 0:
        # The user manager owns this process, so cancelling a Codex turn cannot
        # terminate the SSH forwarding along with the tool's child processes.
        service = 'isl-kitchen-dashboard-tunnel-%d' % int(time.time())
        service_command = ['systemd-run', '--user', '--quiet', '--collect',
            '--unit=' + service, '--property=Restart=on-failure', '--property=RestartSec=5s']
        if os.environ.get('SSH_AUTH_SOCK'):
            service_command.append('--setenv=SSH_AUTH_SOCK=' + os.environ['SSH_AUTH_SOCK'])
        subprocess.run([*service_command, '--', *command], check=True)
        (Path(__file__).resolve().parent / 'active_tunnel_service.txt').write_text(service + '\n')
    else:
        with log_path.open('a') as log:
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log,
                                       stderr=subprocess.STDOUT, start_new_session=True)
        pid_path.write_text(str(process.pid))
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if not service and process.poll() is not None:
            raise RuntimeError('SSH tunnel exited; see ' + str(log_path))
        if all(occupied(local) for local, _ in pairs):
            break
        time.sleep(.2)
    else:
        raise RuntimeError('Tunnel did not become ready; see ' + str(log_path))

with urlopen('http://127.0.0.1:8767/', timeout=10) as response:
    page = response.read()
    if response.status != 200 or not any(title in page for title in [b'Toaster', b'Kitchen objects']):
        raise RuntimeError('Local port 8767 does not show the expected kitchen dashboard')

print('LIVE comparison: http://localhost:8767/')
print('Focused kitchen: http://localhost:8767/kitchen-room')
print('Models: http://localhost:8767/models')
print('Tunnel runs in the background; this terminal can be closed.')
