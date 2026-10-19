"""Activate the tested V2 update only when no recording/export is active."""
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time
import urllib.request

ROOT = Path('/home/guest-isl/rishabh/bench/experiments/level3_manual_collector_v2')
PYTHON = '/home/guest-isl/rishabh/bench/envs/navila/bin/python'
BASE = 'http://127.0.0.1:8878'
OLD_PID = 3490951


def api(path, data=None):
    request=urllib.request.Request(BASE+path,data=None if data is None else json.dumps(data).encode(),
        headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=8) as response:return json.load(response)


def launch():
    env=dict(os.environ,CUDA_VISIBLE_DEVICES='0',HABITAT_SIM_LOG='quiet',MAGNUM_LOG='quiet')
    with (ROOT/'server_environment.log').open('ab') as log:
        return subprocess.Popen([PYTHON,'-B',str(ROOT/'collector.py'),'--port','8878'],cwd=ROOT,
            env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)


def ready(process):
    for _ in range(120):
        if process.poll() is not None:raise RuntimeError('Updated collector exited; see server_environment.log')
        try:return api('/api/state')
        except Exception:time.sleep(.5)
    raise RuntimeError('Updated collector did not start in time')


state=api('/api/state')
assert not state['active'], 'A human recording is active. The server was not restarted.'
assert not state.get('processing'), 'MP4 exports are active. The server was not restarted.'
cmdline=Path('/proc')/str(OLD_PID)/'cmdline'
assert str(ROOT/'collector.py').encode() in cmdline.read_bytes(), 'Unexpected PID; do not stop it'
saved_session=state['session_id'] if state['finished'] else None
os.kill(OLD_PID,signal.SIGTERM)
for _ in range(40):
    try:api('/api/state');time.sleep(.1)
    except Exception:break
process=launch()
try:
    ready(process)
    environments=api('/api/environments')
    assert len(environments)==4 and sum(len(e['episodes']) for e in environments)==10
    if saved_session:api('/api/load',{'session_id':saved_session})
except Exception:
    if process.poll() is None:
        process.terminate();process.wait(timeout=15)
    shutil.copyfile(ROOT/'collector_before_environment_selection.py',ROOT/'collector.py')
    previous=launch();ready(previous)
    if saved_session:api('/api/load',{'session_id':saved_session})
    raise
report={'live':True,'port':8878,'pid':process.pid,'environment_count':4,'episode_count':10,
    'restored_completed_session':saved_session,'original_dashboard_restarted':False,'human_recordings_modified':False}
(ROOT/'environment_deployment.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
