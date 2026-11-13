"""Exercise offline intervention selection and real image loading in Chrome."""
import base64
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'dashboard'))
from browser_cdp import CDP


def main():
    profile=Path(tempfile.mkdtemp(prefix='gqft-motion-comparison-',dir='/tmp'))
    log=(ROOT/'comparison_browser.log').open('wb')
    process=subprocess.Popen(['google-chrome','--headless','--no-sandbox','--disable-gpu',
        '--disable-dev-shm-usage','--disable-background-networking','--disable-extensions',
        '--no-first-run','--no-default-browser-check','--remote-debugging-port=0',
        '--user-data-dir='+str(profile),'--window-size=1600,1100',(ROOT/'comparison.html').as_uri()],stdout=log,stderr=log)
    client=None
    try:
        for _ in range(100):
            try:
                port=int((profile/'DevToolsActivePort').read_text().splitlines()[0])
                with urllib.request.urlopen('http://127.0.0.1:%d/json'%port,timeout=1) as response:tabs=json.load(response)
                tab=next(t for t in tabs if t.get('type')=='page' and 'comparison.html' in t.get('url',''))
                client=CDP(tab['webSocketDebuggerUrl']);break
            except (OSError,ValueError,StopIteration):time.sleep(.1)
        assert client,'Browser did not start'
        for _ in range(100):
            if client.evaluate('!!window.COMPARISON_STATE'):break
            time.sleep(.1)
        result=client.evaluate('''(async()=>{
const $=id=>document.getElementById(id),pause=ms=>new Promise(r=>setTimeout(r,ms)),checks=[];
const ok=(v,m)=>{if(!v)throw Error(m);checks.push(m)},set=(id,v)=>{$(id).value=v;$(id).dispatchEvent(new Event('change'))};
ok(location.protocol==='file:','Comparison runs as an offline local file');
ok($('episode').options.length===10,'All ten diagnostic episodes selectable');
ok(window.COMPARISON_STATE.experiment==='original','Original-RGB experiment is the default');
let states=0;
for(const experiment of ['original','height']){
set('experiment',experiment);await pause(40);
ok(window.COMPARISON_STATE.experiment===experiment,'Experiment selection: '+experiment);
const expected=experiment==='height'?['center','height']:['original','center'];
ok(JSON.stringify([...document.querySelectorAll('#views .view')].map(v=>v.dataset.run))===JSON.stringify(expected),'Only the selected experiment conditions are displayed: '+experiment);
for(const ep of [...$('episode').options].map(o=>o.value)){
 set('episode',ep);set('segment','full');
 for(const model of [...$('model').options].map(o=>o.value)){
  set('model',model);
  for(let i=0;i<50&&[...document.querySelectorAll('#views img')].some(im=>!im.complete);i++)await pause(30);
  ok([...document.querySelectorAll('#views img')].every(im=>im.complete&&im.naturalWidth===640),'PNG overlays load: '+ep+' / '+model);
  ok($('cohort').rows.length===(experiment==='height'?5:10),'Separate cohort retained: '+experiment+' / '+ep+' / '+model);
  ok($('cohort-head').children.length===3,'Only the selected experiment has table columns');
  states++;
 }
}
}
set('episode','837');ok($('views').textContent.includes('Not rerendered'),'Uncertain-height episode is explicit');
set('episode','629');set('model','solver_learned_weights');set('segment','leg00');
await pause(100);ok($('views').querySelectorAll('img').length===2,'Height experiment compares only original-center and reconstructed-center');
ok($('experiment-note').textContent.includes('Model height and sensor mount remain 1.2 m'),'Height experiment explains the unchanged camera calibration');
ok($('experiment-note').textContent.includes('scores stay separate'),'Height experiment keeps scores separate');
location.hash='original';await pause(40);
ok(window.COMPARISON_STATE.experiment==='original'&&!$('views').querySelector('[data-run="height"]'),'Returning to the default removes reconstructed-height results');
location.hash='height';await pause(40);
ok(window.COMPARISON_STATE.experiment==='height','Direct height-experiment link selects the separate view');
ok(window.__comparisonErrors.length===0,'No JavaScript or image load errors');
return {checks,selection_states:states,errors:window.__comparisonErrors};
})()''')
        desktop=client.evaluate('({width:innerWidth,scroll:document.documentElement.scrollWidth})')
        assert desktop['scroll']<=desktop['width']+2
        shot=client.call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False})
        (ROOT/'comparison_preview_desktop.png').write_bytes(base64.b64decode(shot['data']))
        client.call('Emulation.setDeviceMetricsOverride',{'width':430,'height':932,'deviceScaleFactor':1,'mobile':True})
        time.sleep(.1)
        mobile=client.evaluate('({width:innerWidth,scroll:document.documentElement.scrollWidth})')
        assert mobile['scroll']<=mobile['width']+2
        result.update(desktop=desktop,mobile=mobile,passed=True)
        (ROOT/'comparison_verification.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({'passed':True,'selection_states':result['selection_states'],'checks':len(result['checks'])}))
    finally:
        if client:client.sock.close()
        process.terminate()
        try:process.wait(timeout=5)
        except subprocess.TimeoutExpired:process.kill();process.wait()
        log.close()


if __name__=='__main__':main()
