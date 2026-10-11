"""Actual browser verification: mesh switching and split view preserve one camera."""
from pathlib import Path
from urllib.request import urlopen,Request
import json,sys,time,base64
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/'kitchen_panorama_compare'))
from capture_panoramas import DevTools, DEBUG
URL='http://localhost:8772'

def unchanged(a,b):
    return a['frame']==b['frame'] and a['mode']==b['mode'] and all(abs(x-y)<1e-7 for key in ['position','quaternion'] for x,y in zip(a[key],b[key]))

def snapshot(browser):
    return browser.js('({position:homeTourCamera.position.toArray(),quaternion:homeTourCamera.quaternion.toArray(),frame:homeTour.frame,mode:homeTour.mode})')

if __name__=='__main__':
    output=ROOT/'evidence';output.mkdir(exist_ok=True)
    with urlopen(URL+'/state') as r:nav_before=json.load(r)
    with urlopen(DEBUG+'/json/list') as response:tabs=json.load(response)
    tab=next((t for t in tabs if t.get('url')==URL+'/home-tour'),None)
    b=DevTools(tab=tab);b.call('Page.enable');b.call('Runtime.enable')
    b.call('Emulation.setDeviceMetricsOverride',{'width':1100,'height':850,'deviceScaleFactor':1,'mobile':False})
    if tab is None:b.call('Page.navigate',{'url':URL+'/home-tour'})
    for n in range(600):
        time.sleep(1)
        state=b.js('window.homeTour?{ready:homeTour.ready,error:homeTour.error}:{}')
        if n%15==0:print('LOAD_AFTER',n,state,flush=True)
        assert not state.get('error'),state
        if state.get('ready'):break
    assert state.get('ready')
    b.js('document.getElementById("walk").click()');time.sleep(.3)
    initial=snapshot(b)
    print('LOADING_BEFORE_MESH',flush=True)
    assert b.js('homeTour.setVersion("before")')
    assert unchanged(snapshot(b),initial),('camera moved',snapshot(b),initial)
    data=b.call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False})['data'];(output/'before_tour.png').write_bytes(base64.b64decode(data))
    for version in ['after','compare']:
        assert b.js('homeTour.setVersion('+json.dumps(version)+')')
        assert unchanged(snapshot(b),initial),version
        state=b.js('({version:homeTour.version,beforeReady:homeTour.beforeReady,mode:homeTour.mode,toasterParts:homeTour.toasterParts,originalPbr:homeTour.originalPbr})')
        assert state['version']==version and state['beforeReady'] and state['toasterParts']==11 and state['originalPbr']
        print('VERSION_PASSED',version,flush=True)
    data=b.call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False})['data'];(output/'comparison_tour.png').write_bytes(base64.b64decode(data))
    for obj in ['toaster','blue_jug','phone','glass_kettle','phone_dock']:
        assert b.js('homeTour.focusObject('+json.dumps(obj)+')')
        time.sleep(.5)
        start=snapshot(b)
        for v in ['before','after','compare']:
            assert b.js('homeTour.setVersion('+json.dumps(v)+')')
            assert unchanged(snapshot(b),start),('inspection camera moved',obj,v)
        if obj=='toaster':
            data=b.call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False})['data'];(output/(obj+'_compare.png')).write_bytes(base64.b64decode(data))
        print('INSPECTION_PASSED',obj,flush=True)
    # Restore the local browser camera to the existing walking pose; no /action call.
    b.js('document.getElementById("walk").click()');time.sleep(.5)
    assert b.js('homeTour.mode')=='walk'
    with urlopen(Request(URL+'/before-home-scene.glb',headers={'Range':'bytes=0-11'})) as r:
        assert r.status==206 and r.read()[:4]==b'glTF'
    with urlopen(URL+'/before-scene-info') as r:source=json.load(r)
    with urlopen(URL+'/state') as r:nav_after=json.load(r)
    assert not b.errors,b.errors
    report={'status':'passed','versions':['before','after','compare'],'same_camera_on_every_switch':True,
        'split_view_uses_one_camera':True,'object_inspection_checked':['toaster','blue_jug','phone','glass_kettle','phone_dock'],
        'baseline':source,'browser_errors':b.errors,'navigation_actions_sent':False,
        'navigation_state_unchanged_during_verification':nav_before==nav_after,
        'navigation_note':'Other user sessions can change the existing walking state; this verifier sends no actions.',
        'room_scene_modified':False,'verified_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
    (output/'verification.json').write_text(json.dumps(report,indent=2));print('HOME_TOUR_BROWSER_PASSED',flush=True)
