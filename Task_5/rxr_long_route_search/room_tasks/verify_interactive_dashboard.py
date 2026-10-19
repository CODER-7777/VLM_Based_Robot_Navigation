"""Exercise the real browser and isolated review service; no media recording."""
import base64
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[1]/'level3_manual_collector_v2'))
from browser_cdp import CDP


def main():
    profile=tempfile.mkdtemp(prefix='rxr-review-chrome-',dir='/tmp')
    log=(ROOT/'dashboard_browser.log').open('wb')
    proc=subprocess.Popen(['google-chrome','--headless','--no-sandbox','--disable-gpu','--disable-dev-shm-usage',
        '--user-data-dir='+profile,'--remote-debugging-port=8897','--window-size=1720,1120',
        'http://127.0.0.1:8890/room_tasks/review.html'],stdout=log,stderr=log)
    try:
        client=None
        for _ in range(100):
            try:
                tabs=json.load(urllib.request.urlopen('http://127.0.0.1:8897/json',timeout=1))
                tab=next(t for t in tabs if t.get('type')=='page' and 'review.html' in t.get('url',''))
                client=CDP(tab['webSocketDebuggerUrl']);break
            except Exception:time.sleep(.15)
        assert client,'Browser did not start'
        client.sock.settimeout(180)
        for _ in range(100):
            try:
                if client.evaluate("document.readyState==='complete' && !!window.rxrReview"):break
            except RuntimeError:pass
            time.sleep(.1)
        result=client.evaluate('''(async()=>{
const checks=[],assert=(v,m)=>{if(!v)throw Error(m);checks.push(m)},pause=ms=>new Promise(r=>setTimeout(r,ms));
async function until(test){for(let i=0;i<900;i++){if(test())return;await pause(100)}throw Error('Scene operation timed out')}
await until(()=>window.rxrReview?.state.connected&&!window.rxrReview.state.busy);
const ui=window.rxrReview,s=ui.state;
assert(s.catalog.routes.length===28,'All 28 original source routes available');
assert(s.catalog.routes.filter(r=>r.schoolbag_selected).length===12,'All 12 user-selected school-bag cases preserved');
assert(s.catalog.routes.reduce((n,r)=>n+r.variants.length-1,0)===123,'All 123 authored variants available under their source routes');
assert(document.querySelectorAll('.instance-card').length===28,'Instance list renders all 28 source routes');
assert(document.querySelector('#scene-image').naturalWidth===768,'Real rendered first-person frame loads');
const heading=s.packet.heading_degrees;
document.getElementById('viewport').dispatchEvent(new KeyboardEvent('keydown',{key:'a',bubbles:true}));
document.getElementById('viewport').dispatchEvent(new KeyboardEvent('keyup',{key:'a',bubbles:true}));
await until(()=>!s.busy&&s.packet.heading_degrees!==heading);
assert(Math.abs(s.packet.heading_degrees-heading)>1,'A key turns the real inspection camera');
const frame=s.packet.frame;await ui.act('forward');
assert(s.packet.frame>frame&&Number.isFinite(s.packet.walked_m),'W action uses the navmesh movement service');
await ui.jump('pickup');assert(s.packet.message.includes('sink'),'Pickup jump inspects the actual sink props');
await ui.jump('nora');assert(s.packet.nearest_room===26,'Nora jump reaches the proposed bedroom');
await ui.seek(4);assert(s.packet.route_step===4,'Trajectory step slider endpoint updates the actual camera');
document.querySelector('[data-filter="schoolbag"]').click();assert(document.querySelectorAll('.instance-card').length===12,'School-bag filter shows 12 instances');
document.querySelector('[data-filter="nora-strong"]').click();assert(document.querySelectorAll('.instance-card').length===2,'Stronger Nora filter shows 2 instances');
document.querySelector('[data-filter="toiletries"]').click();assert(document.querySelectorAll('.instance-card').length===8,'Toiletries filter shows all 8 source candidates');
document.querySelector('[data-filter="all"]').click();
ui.setView('map');assert(document.querySelector('#large-map svg circle[data-step]'),'Large map shows clickable waypoints');
ui.setView('photos');await until(()=>[...document.querySelectorAll('#photo-grid img')].every(i=>i.complete&&i.naturalWidth>0));
assert(document.querySelectorAll('#photo-grid img').length===4,'All four original source-goal views load');
ui.setView('walk');
const source= s.catalog.routes.find(r=>r.path_id===11513);
assert(await ui.selectRoute(source.id,'original'),'Switch to a Nora candidate in a different scene');
assert(s.packet.scan===source.scan&&s.packet.route_steps===source.variants[0].path.length,'Switched scene returns its own route and first-person frame');
const bag=s.catalog.routes.find(r=>r.index===4);
assert(await ui.selectRoute(bag.id,'original'),'Switch to school-bag scene 04');
await ui.jump('prop:bag_brown_sofa');assert(s.packet.message.includes('brown'),'Brown-seat bag inspection is available');
await ui.jump('prop:bag_pink_sofa');assert(s.packet.message.includes('pink'),'Pink-seat bag inspection is available');
const prepared=s.catalog.routes.find(r=>r.path_id===5721);
assert(await ui.selectRoute(prepared.id,prepared.default_variant),'Restore the prepared combined instance');
await ui.jump('pickup');assert(s.errors.length===0,'No interface or API errors during browser checks');
return {checks,route_id:s.route.id,variant_id:s.variant.id,frame:s.packet.frame,counts:s.catalog.counts,
 viewport:{width:innerWidth,height:innerHeight,scrollWidth:document.documentElement.scrollWidth}};
})()''')
        (ROOT/'dashboard_browser_verification.json').write_text(json.dumps(result,indent=2))
        screenshot=client.call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False})
        (ROOT/'dashboard_desktop.png').write_bytes(base64.b64decode(screenshot['data']))
        client.call('Emulation.setDeviceMetricsOverride',dict(width=430,height=932,deviceScaleFactor=1,mobile=True))
        mobile=client.evaluate('''(async()=>{await new Promise(r=>setTimeout(r,200));document.getElementById('instances-toggle').click();return {width:innerWidth,scrollWidth:document.documentElement.scrollWidth,instance_list_open:document.getElementById('sidebar').classList.contains('open')}})()''')
        assert mobile['scrollWidth']<=mobile['width']+2,mobile
        result['mobile']=mobile;(ROOT/'dashboard_browser_verification.json').write_text(json.dumps(result,indent=2))
        print(json.dumps(result,indent=2))
    finally:
        proc.terminate()
        try:proc.wait(timeout=8)
        except subprocess.TimeoutExpired:proc.kill()
        log.close()


if __name__=='__main__':main()
