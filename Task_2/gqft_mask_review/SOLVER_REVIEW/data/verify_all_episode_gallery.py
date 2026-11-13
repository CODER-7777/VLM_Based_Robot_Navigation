"""Validate full-episode PNG coverage, saved metrics and the offline gallery UI."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.request

import numpy as np
from PIL import Image

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'dashboard'))
from browser_cdp import CDP


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--allow-partial',action='store_true')
    args=parser.parse_args();root=args.run.resolve()
    manifest=json.loads((root/'manifest.json').read_text())
    checks={};segments=0;legs=0
    for ep in manifest['episodes']:
        record=json.loads((root/ep['data']).read_text())
        assert len(record['segments'])==ep['legs']+1
        for s in record['segments']:
            segments+=1;legs+=s['id']!='full';folder=root/f"ep{ep['episode']}"/s['id']
            n=s['pairs']+1
            assert len(s['reference']['ground_m'])==n
            for arm,p in s['predictions'].items():
                assert len(p['ground_m'])==n and len(p['uv_px'])==n
                error=np.linalg.norm(np.asarray(p['ground_m'])-s['reference']['ground_m'],axis=1)
                assert np.isfinite(error).all()
                assert abs(error[1:].mean()-p['metrics']['mean_ground_error_m'])<1e-10
                assert np.max(np.abs(error*100-p['metrics']['ground_error_cm']))<1e-8
                with Image.open(folder/(arm+'_overlay.png')) as im:
                    assert im.size==(640,650)
                    im.verify()
            for name in ['comparison.png','ground_paths.png']:
                with Image.open(folder/name) as im:im.verify()
    checks['metrics_recomputed_from_saved_paths']=True
    checks['all_rendered_pngs_decode']=True
    checks['all_expected_episodes']=len(manifest['episodes'])==manifest['expected_episode_count']
    checks['all_expected_legs']=legs==manifest['expected_leg_count']
    if (root/'input_provenance.json').exists():
        inputs=json.loads((root/'input_provenance.json').read_text())
        assert all(hashlib.sha256((root/path).read_bytes()).hexdigest()==digest
                   for path,digest in inputs['files'].items())
        checks['downloaded_keyframes_predictions_and_raw_poses_match_server_hashes']=True
    profile=Path(tempfile.mkdtemp(prefix='gqft-all-episodes-browser-',dir='/tmp'))
    log=(root/'browser.log').open('wb')
    proc=subprocess.Popen(['google-chrome','--headless','--no-sandbox','--disable-gpu',
        '--disable-dev-shm-usage','--disable-background-networking','--disable-extensions',
        '--no-first-run','--no-default-browser-check','--remote-debugging-port=0',
        '--user-data-dir='+str(profile),'--window-size=1600,1100',(root/'index.html').as_uri()],stdout=log,stderr=log)
    client=None
    try:
        for _ in range(100):
            try:
                port=int((profile/'DevToolsActivePort').read_text().splitlines()[0])
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/json',timeout=1) as response:tabs=json.load(response)
                tab=next(t for t in tabs if t.get('type')=='page' and 'index.html' in t.get('url',''))
                client=CDP(tab['webSocketDebuggerUrl']);break
            except (OSError,ValueError,StopIteration):time.sleep(.1)
        assert client,'Browser did not start'
        client.call('Page.addScriptToEvaluateOnNewDocument',{'source':"window.__galleryErrors=[];addEventListener('error',e=>window.__galleryErrors.push(e.message));"})
        client.call('Page.reload')
        for _ in range(100):
            if client.evaluate('!!window.GQFT_GALLERY'):break
            time.sleep(.1)
        result=client.evaluate('''(async()=>{
const checks=[],ok=(x,m)=>{if(!x)throw Error(m);checks.push(m)},$=id=>document.getElementById(id);
const set=(id,value)=>{$(id).value=value;$(id).dispatchEvent(new Event('change'))};
const pause=ms=>new Promise(r=>setTimeout(r,ms));
ok(location.protocol==='file:','Gallery opens as a local offline file');
ok($('episode').options.length===window.EPISODE_DATA.manifest.episodes.length,'All completed episode choices available');
await pause(150);ok($('view').toDataURL().length>20000,'Camera canvas includes photo and paths');
let count=0;
for(const e of window.EPISODE_DATA.manifest.episodes){
 set('episode',String(e.episode));ok($('segment').options.length===e.legs+1,'Full episode and all legs selectable: '+e.episode);
 for(const s of window.EPISODE_DATA.episodes[String(e.episode)].segments){
  set('segment',s.id);$('ground-view').click();$('frame').value=String(Math.floor(s.pairs/2));$('frame').dispatchEvent(new Event('input'));
  if(window.GQFT_GALLERY.state.frame!==Math.floor(s.pairs/2))throw Error('Slider mismatch');
  $('camera-view').click();count++;
 }
}
ok(count===Object.values(window.EPISODE_DATA.episodes).reduce((n,e)=>n+e.segments.length,0),'Every full recording and leg renders in both coordinate views');
set('episode',String(window.EPISODE_DATA.manifest.episodes[0].episode));set('segment','leg00');await pause(80);
const box=document.querySelector('[data-model="solver_residual"]');box.click();ok(!window.GQFT_GALLERY.state.selected.includes('solver_residual'),'Model isolation toggles paths');box.click();
$('frame').value='0';$('frame').dispatchEvent(new Event('input'));$('play').click();await pause(250);$('play').click();ok(window.GQFT_GALLERY.state.frame>0,'Playback advances recorded positions');
$('zoom-in').click();$('zoom-out').click();$('reset').click();ok(true,'Zoom and reset controls execute');
ok($('comparison').getAttribute('href').endsWith('comparison.png'),'Comparison PNG link matches selection');
ok($('ground-image').getAttribute('href').endsWith('ground_paths.png'),'Metric plot link matches selection');
ok($('individuals').children.length===3,'Three individual checkpoint overlays linked');
ok(window.__galleryErrors.length===0,'No JavaScript errors');
$('frame').value=$('frame').max;$('frame').dispatchEvent(new Event('input'));
return {checks,errors:window.__galleryErrors,views_tested:count,width:innerWidth,scrollWidth:document.documentElement.scrollWidth};
})()''')
        assert result['scrollWidth']<=result['width']+2
        screenshot=client.call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False})
        (root/'gallery_preview_desktop.png').write_bytes(base64.b64decode(screenshot['data']))
        client.call('Emulation.setDeviceMetricsOverride',{'width':430,'height':932,'deviceScaleFactor':1,'mobile':True})
        time.sleep(.2)
        mobile=client.evaluate('({width:innerWidth,scrollWidth:document.documentElement.scrollWidth})')
        assert mobile['scrollWidth']<=mobile['width']+2,mobile
        screenshot=client.call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False})
        (root/'gallery_preview_mobile.png').write_bytes(base64.b64decode(screenshot['data']))
        checks['browser_interaction_checks']=result
        checks['mobile_no_horizontal_overflow']=True
    finally:
        if client:client.sock.close()
        proc.terminate()
        try:proc.wait(timeout=5)
        except subprocess.TimeoutExpired:proc.kill();proc.wait()
        log.close()
    verification={'checks':checks,'episodes':len(manifest['episodes']),'legs':legs,'segments':segments,
                  'scope':'Offline PNG/data/UI checks; no inference or training'}
    (root/'verification.json').write_text(json.dumps(verification,indent=2)+'\n')
    print(json.dumps(verification,indent=2))
    if not args.allow_partial and (not checks['all_expected_episodes'] or not checks['all_expected_legs']):
        raise SystemExit('Gallery is valid but full episode coverage is still pending')


if __name__=='__main__':main()
