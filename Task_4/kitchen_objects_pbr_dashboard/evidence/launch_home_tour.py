"""Start the private mesh tour while preserving the navigation and Gaussian services."""
from pathlib import Path
from urllib.request import urlopen
import json, os, signal, socket, subprocess, time

R = Path('/data/robotics/toshith/rxr_author/refined')
T = R / 'toaster_home_tour'
PYTHON = '/data/robotics/toshith/envs/kitchen3d/bin/python'
PID = R / 'dashboard_restore/pid'

def occupied(port):
    with socket.socket() as sock:
        return sock.connect_ex(('127.0.0.1', port)) == 0

def get(port, path):
    with urlopen('http://127.0.0.1:%d%s' % (port, path), timeout=15) as response:
        return json.load(response)

if not (T / 'home_pbr_items.glb').is_file():
    raise RuntimeError('Reviewed home GLB is missing')
if not occupied(8778) or not occupied(8779):
    subprocess.run([PYTHON, str(R / 'kitchen_all_upgrade/launch_dashboards.py')], check=True, cwd=R)
before = get(8778, '/state')
ready = False
if occupied(8774):
    try:
        ready = get(8774, '/tour-info').get('revision') == 'kitchen_objects_pbr_v1'
    except Exception:
        pass
    if not ready:
        pid = int(PID.read_text())
        proc = Path('/proc/%d/cmdline' % pid)
        argv = proc.read_bytes().split(b'\0')
        allowed = [R / 'kitchen_all_upgrade/all_dashboard.py', R / 'dashboard_restore/full_editor_proxy.py', T / 'items_dashboard.py', T / 'home_tour_dashboard.py']
        if not any(str(script).encode() in argv for script in allowed):
            raise RuntimeError('Port 8774 is not owned by the known private dashboard; leaving it untouched')
        os.kill(pid, signal.SIGTERM)
        deadline = time.monotonic() + 10
        while occupied(8774) and time.monotonic() < deadline:
            time.sleep(.1)
        if occupied(8774):
            raise RuntimeError('Prior private presentation did not stop')

if not ready:
    with (T / 'active.log').open('a') as log:
        process = subprocess.Popen([PYTHON, '-u', str(T / 'items_dashboard.py')], cwd=R,
            env=dict(os.environ, KITCHEN_DASH_PORT='8774'), stdin=subprocess.DEVNULL,
            stdout=log, stderr=log, start_new_session=True)
    PID.write_text(str(process.pid))
    (T / 'active.pid').write_text(str(process.pid))
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        try:
            ready = get(8774, '/tour-info').get('revision') == 'kitchen_objects_pbr_v1'
            if ready: break
        except Exception:
            pass
        time.sleep(.2)
    if not ready:
        raise RuntimeError('Home tour did not become ready; see toaster_home_tour/active.log')

after = get(8778, '/state')
publication = {'revision': 'kitchen_objects_pbr_v1', 'port': 8774, 'url': 'http://localhost:8767/',
    'scene': str(T / 'home_pbr_items.glb'), 'toaster_original_parts': 11, 'item_views': 22,
    'camera_before': before, 'camera_after': after,
    'navigation_process_restarted': False, 'gaussian_process_restarted': False,
    'shared_files_modified': False}
(T / 'publication.json').write_text(json.dumps(publication, indent=2))
print('KITCHEN_ITEMS_TOUR_ACTIVE http://localhost:8767/ (remote 8774)', flush=True)
