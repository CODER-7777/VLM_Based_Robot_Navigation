"""Publish the reviewed personal dashboard; preserve unrelated services."""
from pathlib import Path
from urllib.request import urlopen
import sys,json,socket,os,signal,time,subprocess
ROOT=Path(__file__).resolve().parents[1];OLD=ROOT.parent/'kitchen_repair_20261011'
sys.path.insert(0,str(ROOT/'scripts'));import glb_tools as gt
PY='/data/robotics/toshith/envs/kitchen3d/bin/python'
def get(port,path):
    with urlopen(f'http://127.0.0.1:{port}{path}',timeout=20) as r:return json.load(r)
if __name__=='__main__':
    rev=json.loads((ROOT/'evidence/browser_review.json').read_text());audit=json.loads((ROOT/'evidence/artifact_verification.json').read_text())
    assert rev['status']=='passed' and audit['status']=='local artifact checks passed'
    assert rev['scene_sha256']==audit['scene_sha256']==gt.sha(ROOT/'home_pbr_products.glb')
    assert rev['calibrated_photo_captures']==23 and rev['room_model_routes_checked']==30
    before=get(8778,'/state');info=get(8774,'/tour-info')
    assert info['workspace']==str(OLD) and info['revision']=='kitchen_workspace_v6_20261011',info
    pid=int((OLD/'dashboard.pid').read_text());cmd=Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')
    assert str(OLD/'products_dashboard.py').encode() in cmd,cmd
    (ROOT/'previous_publication.json').write_text(json.dumps({'pid':pid,'info':info},indent=2))
    os.kill(pid,signal.SIGTERM)
    for _ in range(100):
        with socket.socket() as sock:free=sock.connect_ex(('127.0.0.1',8774))!=0
        if free:break
        time.sleep(.1)
    assert free,'Old presentation process did not release its port'
    env=dict(os.environ,KITCHEN_DASH_PORT='8774',PYTHONDONTWRITEBYTECODE='1')
    with (ROOT/'logs/dashboard.log').open('a') as log:
        process=subprocess.Popen([PY,'-u',str(ROOT/'products_dashboard.py')],cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
    (ROOT/'dashboard.pid').write_text(str(process.pid))
    for _ in range(100):
        assert process.poll() is None,'Published presentation process stopped'
        try:
            info=get(8774,'/tour-info')
            if info.get('workspace')==str(ROOT):break
        except Exception:pass
        time.sleep(.2)
    assert info['validation']['scene_sha256']==rev['scene_sha256'] and info['workspace']==str(ROOT)
    after=get(8778,'/state')
    report={'status':'published','pid':process.pid,'port':8774,'revision':info['revision'],'scene_sha256':rev['scene_sha256'],'workspace':str(ROOT),'navigation_process_restarted':False,'gaussian_process_restarted':False,'navigation_state_preserved':before==after,'replaced_personal_presentation_pid':pid}
    (ROOT/'publication_status.json').write_text(json.dumps(report,indent=2));print(report,flush=True)
