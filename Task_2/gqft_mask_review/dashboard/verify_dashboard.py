"""Exercise the offline dashboard in an isolated Chrome profile; no GPU/model work."""
import base64
import json
from pathlib import Path
import subprocess
import tempfile
import time
import urllib.request

from browser_cdp import CDP

HERE = Path(__file__).resolve().parent


def main():
    profile = Path(tempfile.mkdtemp(prefix='gqft-dashboard-browser-', dir='/tmp'))
    page = HERE.parent/'dashboard.html'
    log = (HERE/'browser.log').open('wb')
    proc = subprocess.Popen(['google-chrome', '--headless', '--no-sandbox', '--disable-gpu',
        '--disable-dev-shm-usage', '--disable-background-networking', '--disable-extensions',
        '--no-first-run', '--no-default-browser-check', '--remote-debugging-port=0',
        '--user-data-dir='+str(profile), '--window-size=1720,1120', page.as_uri()], stdout=log, stderr=log)
    client = None
    try:
        for _ in range(120):
            try:
                port = int((profile/'DevToolsActivePort').read_text().splitlines()[0])
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/json', timeout=1) as response:
                    tabs = json.load(response)
                tab = next(tab for tab in tabs if tab.get('type') == 'page' and 'dashboard.html' in tab.get('url', ''))
                client = CDP(tab['webSocketDebuggerUrl'])
                break
            except (OSError, ValueError, StopIteration):
                time.sleep(.1)
        assert client, 'Browser did not start'
        client.sock.settimeout(120)
        for _ in range(120):
            if client.evaluate('!!window.gqftDashboard?.ready'):
                break
            time.sleep(.1)
        result = client.evaluate('''(async()=>{
const ui=window.gqftDashboard,s=ui.state,D=ui.data,checks=[];
const ok=(condition,message)=>{if(!condition)throw Error(message);checks.push(message)};
const event=(id,type)=>document.getElementById(id).dispatchEvent(new Event(type,{bubbles:true}));
const select=(id,value)=>{document.getElementById(id).value=value;event(id,'change')};
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
ok(ui.ready,'All twelve embedded source images loaded offline');
ok(Object.keys(D.legs).length===4,'Four episode-629 legs available');
ok(document.querySelector('#model-a').options.length===5,'All five real checkpoint choices available');
ok(document.querySelector('#metric-grid').textContent.includes('6.50'),'Default leg-0 combined score matches saved predictions');
ok(document.querySelector('#overlay-a').toDataURL().length>20000,'Camera overlay contains rendered image and trajectories');
document.querySelector('[data-leg="2"]').click();
ok(s.leg==='2'&&document.querySelector('#window-description').textContent.includes('140–164'),'Leg switch updates window and data');
select('model-b','yaw_local_only');
ok(document.querySelector('#metric-grid').textContent.includes('2.82'),'Model B switch updates saved ground-error score');
document.getElementById('swap').click();
ok(s.a==='yaw_local_only'&&s.b==='pretrained_yaw','Model swap updates both selections');
document.getElementById('pose').value='8';event('pose','input');
ok(s.pose===8&&document.getElementById('pose-label').textContent==='Pose 8 / 24','Pose slider updates shared overlay cursor');
document.getElementById('play').click();await sleep(480);document.getElementById('play').click();
ok(s.pose>8&&!s.playing,'Play advances saved poses and pauses');
const before=s.showGT;document.getElementById('show-gt').click();
ok(s.showGT!==before,'Ground-truth visibility control works');
document.getElementById('show-future').click();ok(!s.showFuture,'Full-path visibility control works');
document.getElementById('fit-paths').click();ok(s.viewport&&s.viewport.zoom>1,'Fit-paths updates common camera viewport');
document.getElementById('reset').click();ok(s.pose===24&&s.viewport===null&&s.showGT&&s.showFuture,'Reset restores shared comparison view');
select('error-metric','pixel');ok(document.querySelector('#error-chart').textContent.includes('projected error'),'Error chart switches to pixel error');
document.querySelector('[data-arm="reference"]').click();ok(!s.visible.has('reference'),'Chart model visibility toggles');
document.querySelector('#metrics-table tbody tr[data-model="masked_only"]').click();ok(s.b==='masked_only','Scorecard row selects comparison model');
document.querySelector('[data-sort="endpoint_ground_error_m"]').click();ok(s.sort==='endpoint_ground_error_m','Scorecard sorting works');
document.getElementById('notes').value='Browser verification observation';event('notes','input');
ui.setLeg('3');ui.setLeg('2');ok(document.getElementById('notes').value==='Browser verification observation','Observations persist separately for each leg');
document.getElementById('notes').value='';event('notes','input');
document.getElementById('tab-attention').click();ok(s.tab==='attention'&&!document.getElementById('view-attention').hidden,'Attention tab opens');
for(const leg of ['0','2','3','4']){
 ui.setLeg(leg);
 for(const arm of Object.keys(D.provenance.checkpoints)){
  select('model-b',arm);
  for(const pair of ['0','12','23']){
   select('attention-pair',pair);
   for(const layer of ['attention_weights','feature_reliability','ground_prior_coverage','feature_valid_coverage'])select('attention-layer',layer);
  }
 }
}
ok(ui.errors.length===0,'All leg/model/pair/map attention combinations render without exceptions');
select('model-a','pretrained_yaw');select('model-b','masked_yaw_local');select('attention-layer','feature_reliability');
ok(document.getElementById('attention-foot-a').textContent.includes('no stored mask prior'),'Unmasked checkpoint does not invent a reliability map');
select('attention-layer','attention_weights');
document.getElementById('heat-opacity').value='40';event('heat-opacity','input');ok(s.opacity===.4,'Attention opacity slider works');
document.getElementById('tab-validation').click();select('validation-history','24');
ok(document.querySelector('#validation-table tbody').textContent.includes(D.validation.yaw_local_only.histories.find(r=>r.history===24).ade_px.toFixed(3)),'Fixed-history validation uses preserved numeric results');
ok(document.querySelector('#validation-table tbody').textContent.includes('None passed'),'Failed history gates remain visible');
for(const history of ['4','8','12','16','20','24','30'])select('validation-history',history);
ok(s.history===30&&document.querySelectorAll('#training-chart svg path').length===4,'All validation histories and four training curves render');
const originalCreate=URL.createObjectURL,originalClick=HTMLAnchorElement.prototype.click;
let lastBlob=null,lastName=null;
URL.createObjectURL=blob=>{lastBlob=blob;return 'blob:verification'};
HTMLAnchorElement.prototype.click=function(){lastName=this.download};
document.getElementById('export-csv').click();
ok((await lastBlob.text()).split('\\n').length===21&&lastName.endsWith('.csv'),'Metrics export includes all twenty leg/model rows');
document.getElementById('download-data').dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true}));
const exported=JSON.parse(await lastBlob.text());ok(Object.keys(exported.predictions).length===5&&exported.leg===s.leg,'Leg export includes predictions and selected-leg identity');
URL.createObjectURL=originalCreate;HTMLAnchorElement.prototype.click=originalClick;
ui.setLeg('0');select('model-a','pretrained_yaw');select('model-b','masked_yaw_local');select('validation-history','24');
ui.setTab('compare');select('error-metric','ground');document.getElementById('reset').click();
ok(ui.errors.length===0,'No JavaScript runtime errors during interaction checks');
return {checks,errors:ui.errors,desktop:{width:innerWidth,scrollWidth:document.documentElement.scrollWidth},offline_file_url:location.protocol==='file:'};
})()''')
        assert result['desktop']['scrollWidth'] <= result['desktop']['width']+2, result['desktop']
        for tab in ('compare', 'attention', 'validation'):
            client.evaluate(f"window.gqftDashboard.setTab('{tab}')")
            time.sleep(.15)
            shot = client.call('Page.captureScreenshot', {'format': 'png', 'captureBeyondViewport': False})
            (HERE/f'preview_{tab}.png').write_bytes(base64.b64decode(shot['data']))
        client.call('Emulation.setDeviceMetricsOverride', {'width': 430, 'height': 932, 'deviceScaleFactor': 1, 'mobile': True})
        client.evaluate("window.gqftDashboard.setTab('compare')")
        time.sleep(.3)
        mobile = client.evaluate("({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,errors:window.gqftDashboard.errors})")
        assert mobile['scrollWidth'] <= mobile['width']+2, mobile
        assert not mobile['errors'], mobile
        result['mobile'] = mobile
        shot = client.call('Page.captureScreenshot', {'format': 'png', 'captureBeyondViewport': False})
        (HERE/'preview_mobile.png').write_bytes(base64.b64decode(shot['data']))
        (HERE/'verification.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps(result, indent=2))
    finally:
        if client:
            client.sock.close()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        log.close()


if __name__ == '__main__':
    main()
