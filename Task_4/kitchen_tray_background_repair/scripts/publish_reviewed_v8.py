"""Publish reviewed personal v8 room and panorama; preserve navigation state."""
from pathlib import Path
from urllib.request import urlopen
import os,signal,socket,subprocess,time,json,shutil

ROOT=Path('/data/robotics/toshith/vivekananda/kitchen_tray_background_repair')
PREVIOUS=Path('/data/robotics/toshith/vivekananda/kitchen_appliance_refinement_20261011')
PY='/data/robotics/toshith/envs/kitchen3d/bin/python'

def get(port,path):
    with urlopen(f'http://127.0.0.1:{port}{path}',timeout=30) as r:return json.load(r)
def start(script,port,logpath,extra=None):
    with socket.socket() as s:assert s.connect_ex(('127.0.0.1',port))!=0,f'Port {port} still occupied'
    env=dict(os.environ,KITCHEN_DASH_PORT=str(port),KITCHEN_PANORAMA_PORT=str(port),PYTHONDONTWRITEBYTECODE='1');env.update(extra or {})
    with logpath.open('a') as log:
        p=subprocess.Popen([PY,'-u',str(script)],cwd=script.parent,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
    return p
def wait_for(port,path,predicate):
    for _ in range(120):
        try:
            data=get(port,path)
            if predicate(data):return data
        except Exception:pass
        time.sleep(.25)
    raise RuntimeError(f'No healthy response on {port}{path}')
def assert_owned(pid,script):
    argv=Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')
    assert str(script).encode() in argv,(pid,argv)

if __name__=='__main__':
    revision='kitchen_workspace_v8_tray_20261011'
    artifact=json.loads((ROOT/'evidence/artifact_verification.json').read_text())
    browser=json.loads((ROOT/'evidence/browser_review.json').read_text())
    tour=json.loads((ROOT/'evidence/verification.json').read_text())
    pano=json.loads((ROOT/'evidence/panorama_review.json').read_text())
    panobrowser=json.loads((ROOT/'evidence/panorama_browser/verification.json').read_text())
    assert artifact['status']=='local artifact checks passed' and browser['status']=='passed'
    assert tour['status']=='passed' and tour['same_camera_on_every_switch'] and tour['split_view_uses_one_camera']
    assert pano['status']=='passed' and pano['faces']==30
    assert panobrowser['status']=='passed' and panobrowser['scene_sha256']==artifact['scene_sha256']
    assert artifact['revision']==browser['revision']==pano['revision']==panobrowser['revision']==revision
    assert artifact['scene_sha256']==browser['scene_sha256']==tour['scene_sha256']==pano['scene_sha256']==panobrowser['scene_sha256']
    nav_before=get(8778,'/state');old=get(8774,'/tour-info')
    assert old['workspace']==str(PREVIOUS) and old['revision']=='kitchen_workspace_v7_20261011',old
    olddash=int((PREVIOUS/'dashboard.pid').read_text());assert_owned(olddash,PREVIOUS/'products_dashboard.py')
    oldpano=int((PREVIOUS/'panoramas/server.pid').read_text());assert_owned(oldpano,PREVIOUS/'panoramas/panorama_server.py')
    assert get(8786,'/config.json')['source_sha256']==json.loads((PREVIOUS/'panoramas/config.json').read_text())['source_sha256']
    (ROOT/'previous_publication.json').write_text(json.dumps({'dashboard_pid':olddash,'dashboard':old,'panorama_pid':oldpano},indent=2))
    backup=ROOT/'web_backup_prepublication'
    if backup.exists():shutil.rmtree(backup)
    shutil.copytree(ROOT/'web',backup)
    os.kill(olddash,signal.SIGTERM)
    for _ in range(120):
        with socket.socket() as s:free=s.connect_ex(('127.0.0.1',8774))!=0
        if free:break
        time.sleep(.1)
    assert free
    proc=start(ROOT/'products_dashboard.py',8774,ROOT/'logs/dashboard.log')
    (ROOT/'dashboard.pid').write_text(str(proc.pid))
    info=wait_for(8774,'/tour-info',lambda d:d.get('workspace')==str(ROOT) and d.get('revision')==revision)
    assert info['validation']['scene_sha256']==artifact['scene_sha256']
    nav_mid=get(8778,'/state')
    assert nav_mid==nav_before,'Navigation state changed during dashboard switch'
    os.kill(oldpano,signal.SIGTERM)
    for _ in range(120):
        with socket.socket() as s:free=s.connect_ex(('127.0.0.1',8786))!=0
        if free:break
        time.sleep(.1)
    assert free
    pp=start(ROOT/'panoramas/panorama_server.py',8786,ROOT/'panoramas/logs/http.log')
    (ROOT/'panoramas/server.pid').write_text(str(pp.pid))
    pinfo=wait_for(8786,'/config.json',lambda d:d.get('revision')==revision and d.get('ready') is True)
    assert pinfo['source_sha256']==artifact['scene_sha256']
    nav_after=get(8778,'/state');assert nav_after==nav_before
    report={'status':'published','revision':revision,'dashboard_pid':proc.pid,'dashboard_port':8774,
            'panorama_pid':pp.pid,'panorama_port':8786,'scene_sha256':artifact['scene_sha256'],
            'same_camera_glb_comparison':'passed','five_position_panoramas':'passed',
            'navigation_state_preserved':True,'navigation_actions_sent':False,
            'replaced_dashboard_pid':olddash,'replaced_panorama_pid':oldpano,
            'workspace':str(ROOT)}
    (ROOT/'publication_status.json').write_text(json.dumps(report,indent=2))
    print(report,flush=True)
