"""Verify the collected solver review is self-contained and opens offline."""
import base64
import csv
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request

LAB=Path(__file__).resolve().parent
ROOT=LAB/'SOLVER_REVIEW'
sys.path.insert(0,str(LAB/'dashboard'))
from browser_cdp import CDP


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[]
    def handle_starttag(self,tag,attrs):
        for key,value in attrs:
            if value and key in {'href','src'}:self.links.append(value)


def main():
    copied=json.loads((ROOT/'SOURCE_COPY_MANIFEST.json').read_text())
    assert all(sha(ROOT/r['file'])==r['sha256'] for r in copied)
    manifest=json.loads((ROOT/'PACKAGE_SHA256.json').read_text())
    assert all(sha(ROOT/p)==digest for p,digest in manifest.items())
    checked=0
    for p in [ROOT/'START_HERE.html',ROOT/'index.html',*sorted((ROOT/'data').rglob('index.html')),ROOT/'data/motion_fixes_20261112/comparison.html']:
        if 'dashboard_revisions' in p.parts:continue
        parser=Links();parser.feed(p.read_text())
        for link in parser.links:
            u=urllib.parse.urlparse(link)
            if u.scheme or not u.path:continue
            target=(p.parent/urllib.parse.unquote(u.path)).resolve()
            assert target.is_relative_to(ROOT.resolve()),(p,link,'Leaves dedicated folder')
            assert target.exists(),(p,link,'Missing file')
            checked+=1
    trajectory_count=0
    for name in ['trained_episode_overlays/20261111T220751Z_gpu4/all_episodes_20261111T223221Z',
                 'motion_fixes_20261112/original_rgb_center','motion_fixes_20261112/height_corrected_center']:
        r=ROOT/'data'/name;v=json.loads((r/'render_verification.json').read_text())
        actual=sum(1 for p in r.glob('ep*/**/*.png'))
        assert actual==v['png_images'],(r,actual,v['png_images'])
        trajectory_count+=actual
    assert trajectory_count==1830
    profile=Path(tempfile.mkdtemp(prefix='gqft-solver-review-',dir='/tmp'))
    log=(ROOT/'review_browser.log').open('wb')
    proc=subprocess.Popen(['google-chrome','--headless','--no-sandbox','--disable-gpu',
        '--disable-dev-shm-usage','--disable-background-networking','--disable-extensions',
        '--no-first-run','--no-default-browser-check','--remote-debugging-port=0',
        '--user-data-dir='+str(profile),'--window-size=1600,1100',(ROOT/'START_HERE.html').as_uri()],stdout=log,stderr=log)
    client=None
    try:
        for _ in range(100):
            try:
                port=int((profile/'DevToolsActivePort').read_text().splitlines()[0])
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/json',timeout=1) as f:tabs=json.load(f)
                tab=next(t for t in tabs if t.get('type')=='page' and 'START_HERE.html' in t.get('url',''))
                client=CDP(tab['webSocketDebuggerUrl']);break
            except (OSError,ValueError,StopIteration):time.sleep(.1)
        assert client,'Browser did not start'
        checks=client.evaluate('''(async()=>{const pause=ms=>new Promise(r=>setTimeout(r,ms));
for(const im of document.images)im.loading='eager';
for(let i=0;i<100&&[...document.images].some(im=>!im.complete);i++)await pause(30);
return {offline:location.protocol==='file:',title:document.title,images:[...document.images].every(im=>im.complete&&im.naturalWidth>0),imageCount:document.images.length,width:innerWidth,scroll:document.documentElement.scrollWidth};})()''')
        assert checks['offline'] and checks['images'] and checks['imageCount']==9,checks
        assert checks['scroll']<=checks['width']+2
        shot=client.call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False})
        (ROOT/'review_preview_desktop.png').write_bytes(base64.b64decode(shot['data']))
        client.call('Emulation.setDeviceMetricsOverride',{'width':430,'height':932,'deviceScaleFactor':1,'mobile':True})
        time.sleep(.1)
        mobile=client.evaluate('({width:innerWidth,scroll:document.documentElement.scrollWidth})')
        assert mobile['scroll']<=mobile['width']+2
        shot=client.call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False})
        (ROOT/'review_preview_mobile.png').write_bytes(base64.b64decode(shot['data']))
        client.call('Page.navigate',{'url':(ROOT/'data/motion_fixes_20261112/comparison.html').as_uri()})
        for _ in range(100):
            if client.evaluate('!!window.COMPARISON_STATE'):break
            time.sleep(.1)
        experiments=client.evaluate('''(async()=>{const pause=ms=>new Promise(r=>setTimeout(r,ms));
const first=window.COMPARISON_STATE.experiment;
location.hash='height';await pause(100);
for(let i=0;i<100&&[...document.querySelectorAll('#views img')].some(im=>!im.complete);i++)await pause(30);
return {defaultExperiment:first,heightExperiment:window.COMPARISON_STATE.experiment,images:[...document.querySelectorAll('#views img')].every(im=>im.complete&&im.naturalWidth===640),heightRows:document.getElementById('cohort').rows.length,errors:window.__comparisonErrors};})()''')
        assert experiments=={'defaultExperiment':'original','heightExperiment':'height','images':True,'heightRows':5,'errors':[]},experiments
        result={'passed':True,'source_copies_hash_checked':len(copied),'package_hashes_checked':len(manifest),
                'internal_links_checked':checked,'trajectory_pngs':trajectory_count,'home':checks,'mobile':mobile,
                'portable_dashboard':experiments,'scope':'Copied artifacts,links and offline UI; no new inference or training'}
        (ROOT/'VERIFICATION.json').write_text(json.dumps(result,indent=2)+'\n')
    finally:
        if client:client.sock.close()
        proc.terminate()
        try:proc.wait(timeout=5)
        except subprocess.TimeoutExpired:proc.kill();proc.wait()
        log.close()
    inventory=[]
    for p in sorted(ROOT.rglob('*')):
        if p.is_file() and 'plot_cache' not in p.relative_to(ROOT).parts and p.name not in {'ALL_FILES.csv','PNGS.csv','PACKAGE_SHA256.json'}:
            inventory.append({'file':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)})
    for name,rows in [('ALL_FILES.csv',inventory),('PNGS.csv',[x for x in inventory if x['file'].endswith('.png')])]:
        with (ROOT/name).open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    (ROOT/'PACKAGE_SHA256.json').write_text(json.dumps({x['file']:x['sha256'] for x in inventory},indent=2)+'\n')
    print(json.dumps({'passed':True,'source_files':len(copied),'trajectory_pngs':trajectory_count,
                      'checked_internal_links':checked,'portable_dashboard':experiments},indent=2))


if __name__=='__main__':main()
