"""Verify real panorama controls, downloads and source provenance."""
from capture_panoramas import DevTools, ROOT, PANORAMA
from urllib.request import urlopen
from PIL import Image
import base64, io, json, time

def config():
    with urlopen(PANORAMA+'/config.json',timeout=30) as r:return json.load(r)

if __name__ == '__main__':
    for n in range(1200):
        c=config()
        if c['ready']:break
        if n%30==0:print('WAITING_FOR_CAPTURE',n,flush=True)
        time.sleep(1)
    assert c['ready']
    browser=DevTools();browser.call('Page.enable');browser.call('Runtime.enable')
    browser.call('Emulation.setDeviceMetricsOverride',{'width':1560,'height':1000,'deviceScaleFactor':1,'mobile':False})
    browser.call('Page.navigate',{'url':PANORAMA+'/'})
    for n in range(120):
        time.sleep(.5)
        if browser.js('Boolean(window.panorama?.ready)'):break
    assert browser.js('Boolean(window.panorama?.ready)')
    output=ROOT/'panorama_browser_evidence';output.mkdir(exist_ok=True)
    rows=[]
    for view in c['views']:
        browser.js('panorama.choose('+json.dumps(view['id'])+')')
        state=browser.js('({ready:panorama.ready,error:panorama.error,view:panorama.view,selection:document.getElementById("position").value,panels:panorama.panels.map(p=>({size:[p.texture.image.width,p.texture.image.height],quaternion:p.camera.quaternion.toArray(),fov:p.camera.fov,programs:p.renderer.info.programs.length}))})')
        assert state['ready'] and not state['error'] and state['selection']==view['id']
        assert all(p['size']==[4096,2048] and p['programs']>0 for p in state['panels'])
        assert state['panels'][0]['quaternion']==state['panels'][1]['quaternion']
        downloads=[]
        for suffix in ['before','after','comparison']:
            with urlopen(PANORAMA+'/images/'+view['id']+'_'+suffix+'.jpg',timeout=60) as r:data=r.read();assert r.status==200
            image=Image.open(io.BytesIO(data));expected=(4096,4216) if suffix=='comparison' else (4096,2048)
            assert image.size==expected
            downloads.append({'name':view['id']+'_'+suffix+'.jpg','bytes':len(data),'dimensions':list(image.size)})
        screen=browser.call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False})['data']
        (output/(view['id']+'_viewer.png')).write_bytes(base64.b64decode(screen))
        rows.append({'id':view['id'],'state':state,'downloads':downloads})
        print('PANORAMA_VERIFIED',view['id'],flush=True)
    browser.js('panorama.choose("sink")')
    before=browser.js('panorama.panels.map(p=>p.camera.quaternion.toArray())')
    box=browser.js('(()=>{const r=panorama.panels[0].element.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()')
    browser.call('Input.dispatchMouseEvent',{'type':'mousePressed',**box,'button':'left','buttons':1,'clickCount':1})
    browser.call('Input.dispatchMouseEvent',{'type':'mouseMoved','x':box['x']+90,'y':box['y']+30,'button':'left','buttons':1})
    browser.call('Input.dispatchMouseEvent',{'type':'mouseReleased','x':box['x']+90,'y':box['y']+30,'button':'left','buttons':0,'clickCount':1})
    after=browser.js('panorama.panels.map(p=>p.camera.quaternion.toArray())')
    assert before[0]!=after[0] and after[0]==after[1]
    browser.call('Input.dispatchMouseEvent',{'type':'mouseWheel',**box,'deltaX':0,'deltaY':120})
    time.sleep(.2)
    fov=browser.js('panorama.panels.map(p=>p.camera.fov)');assert fov==[104,104],fov
    browser.js('document.getElementById("reset").click()')
    assert browser.js('panorama.orientation.fov')==100
    catalog=json.loads((ROOT/'v6_browser_evidence/catalog.json').read_text())
    covered={i for view in c['views'] for i in view['objects']}
    missing=sorted({i['id'] for i in catalog['items']}-covered);assert not missing,missing
    assert not browser.errors,browser.errors
    report={'status':'passed','revision':c['revision'],'scene_sha256':c['source_sha256'],
        'views':rows,'linked_drag_passed':True,'linked_wheel_zoom_passed':True,'reset_passed':True,
        'photo_comparison_objects_covered':len(catalog['items']),'missing_photo_objects':missing,
        'browser_errors':browser.errors,'navigation_actions_sent':False,
        'before_representation':'Original dataset photographic skyboxes; untouched mesh unavailable',
        'after_representation':'Actual published PBR room browser captures',
        'verified_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
    (output/'verification.json').write_text(json.dumps(report,indent=2))
    print('PANORAMA_BROWSER_PASSED',flush=True)
