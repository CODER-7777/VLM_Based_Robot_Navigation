"""Exercise the actual saved workspace room through a dedicated Chromium tab."""
from capture_panoramas import DevTools, ROOT
from urllib.request import Request, urlopen
from pathlib import Path
import base64, json, time

URL = 'http://127.0.0.1:8770'
OUT = ROOT / 'v6_browser_evidence'

def get(path):
    with urlopen(URL + path, timeout=60) as response:
        return response.read()

if __name__ == '__main__':
    OUT.mkdir(exist_ok=True)
    catalog = json.loads(get('/tour-assets/comparison/items/catalog.json'))
    (OUT / 'catalog.json').write_text(json.dumps(catalog, indent=2))
    info = json.loads(get('/tour-info'))
    browser = DevTools()
    browser.call('Page.enable'); browser.call('Runtime.enable')
    browser.call('Emulation.setDeviceMetricsOverride', {'width':1100, 'height':1000, 'deviceScaleFactor':1, 'mobile':False})
    browser.call('Page.navigate', {'url': URL + '/kitchen-room?object=toaster'})
    for n in range(600):
        time.sleep(1)
        state = browser.js('window.homeTour ? {ready:homeTour.ready,error:homeTour.error,toasterParts:homeTour.toasterParts,originalPbr:homeTour.originalPbr} : {}')
        if n % 15 == 0: print('LOAD', n, state, flush=True)
        assert not state.get('error'), state
        if state.get('ready'): break
    assert state.get('ready') and state['toasterParts'] == 11 and state['originalPbr'], state
    rows = []
    for item in catalog['room_items']:
        result = browser.js('({focused:homeTour.focusObject('+json.dumps(item['id'])+'),parts:homeTour.items['+json.dumps(item['id'])+']})')
        assert result['focused'] and result['parts']['parts'] > 0
        with urlopen(Request(URL+'/item-model.glb?object='+item['id'], headers={'Range':'bytes=0-11'}),timeout=60) as response:
            header = response.read(12)
            assert header[:4] == b'glTF' and response.status == 206
        rows.append({'id':item['id'], 'parts':result['parts'], 'inspection':True, 'model_download_header_valid':True})
    print('ROOM_AND_MODELS', len(rows), flush=True)
    for item in catalog['items']:
        data = browser.js('homeTour.capturePhoto('+json.dumps(item['camera'])+')')
        (OUT / (item['id']+'_full.png')).write_bytes(base64.b64decode(data.split(',',1)[1]))
        (OUT / item['real_image']).write_bytes(get('/tour-assets/comparison/items/'+item['real_image']))
        print('PHOTO_CAPTURE', item['id'], flush=True)
    browser.call('Page.navigate', {'url':URL+'/'})
    for n in range(60):
        time.sleep(1)
        if browser.js('document.getElementById("item-picker")?.options.length') == len(catalog['items']): break
    comparison_rows=[]
    for item in catalog['items']:
        browser.js('(()=>{const p=document.getElementById("item-picker");p.value='+json.dumps(item['id'])+';p.dispatchEvent(new Event("change",{bubbles:true}));})()')
        for n in range(60):
            time.sleep(.25)
            images = browser.js('Array.from(document.querySelectorAll(".compare img")).map(i=>({src:i.src,ready:i.complete&&i.naturalWidth>0}))')
            if len(images)>=3 and all(i['ready'] for i in images):break
        assert len(images)>=3 and all(i['ready'] for i in images), (item['id'],images)
        comparison_rows.append({'id':item['id'],'images':images})
        if item.get('updated_in_revision'):
            data=browser.call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False})['data']
            (OUT/(item['id']+'_dashboard.png')).write_bytes(base64.b64decode(data))
    report={'status':'captured; visual review pending','revision':info['revision'],
        'scene_sha256':info['validation']['scene_sha256'], 'browser_errors':browser.errors,
        'scene_state':state,'room_selections':rows,'comparisons':comparison_rows,
        'calibrated_photo_captures':len(catalog['items']),'navigation_actions_sent':False,
        'browser':'Chromium CDP / SwiftShader','capture_time_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
    assert not browser.errors, browser.errors
    (OUT/'browser_review.json').write_text(json.dumps(report,indent=2))
    print('BROWSER_VERIFICATION_CAPTURED',flush=True)
