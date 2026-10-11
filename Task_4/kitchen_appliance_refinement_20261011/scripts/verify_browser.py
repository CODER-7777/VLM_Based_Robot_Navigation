"""Capture actual Three.js room output, inspect exported materials and model routes."""
from pathlib import Path
from urllib.request import urlopen,Request
import sys,json,time,base64
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/'kitchen_panorama_compare'))
from capture_panoramas import DevTools,DEBUG
URL='http://localhost:8772'

def get(path):
    with urlopen(URL+path,timeout=60) as r:return r.read()

if __name__=='__main__':
    out=ROOT/'evidence/browser';out.mkdir(parents=True,exist_ok=True)
    cat=json.loads(get('/tour-assets/comparison/items/catalog.json'));info=json.loads(get('/tour-info'))
    with urlopen(DEBUG+'/json/list') as r:tabs=json.load(r)
    current_tab=next((t for t in tabs if t.get('url')==URL+'/kitchen-room?object=tea_tray'),None)
    for tab in tabs:
        if tab.get('type')=='page' and tab.get('url')!='about:blank' and tab!=current_tab:
            with urlopen(DEBUG+'/json/close/'+tab['id']) as r:r.read()
    b=DevTools(tab=current_tab);b.call('Page.enable');b.call('Runtime.enable')
    b.call('Emulation.setDeviceMetricsOverride',{'width':1050,'height':900,'deviceScaleFactor':1,'mobile':False})
    if current_tab is None:b.call('Page.navigate',{'url':URL+'/kitchen-room?object=tea_tray'})
    for n in range(600):
        time.sleep(1);state=b.js('window.homeTour?{ready:homeTour.ready,error:homeTour.error,toasterParts:homeTour.toasterParts,originalPbr:homeTour.originalPbr}:{}')
        if n%15==0:print('LOAD',n,state,flush=True)
        assert not state.get('error'),state
        if state.get('ready'):break
    assert state.get('ready') and state['toasterParts']==11 and state['originalPbr']
    rows=[]
    for name in ['tea_tray','frother','coffee_machine']:
        item=next(x for x in cat['items'] if x['id']==name)
        assert b.js('homeTour.focusObject('+json.dumps(name)+')')
        time.sleep(.5)
        snap=b.call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False})['data'];(out/(name+'_room.png')).write_bytes(base64.b64decode(snap))
        data=b.js('homeTour.capturePhoto('+json.dumps(item['camera'])+')');(out/(name+'_full.png')).write_bytes(base64.b64decode(data.split(',',1)[1]))
        (out/(name+'_real.jpg')).write_bytes(get('/tour-assets/comparison/items/'+item['real_image']))
        current=Image.open(out/(name+'_full.png')).convert('RGB').crop(item['crop']);current.save(out/(name+'_current.jpg'))
        before=Image.open(ROOT.parent/'kitchen_panorama_compare/v6_browser_evidence'/(name+'_full.png')).crop(item['crop'])
        real=Image.open(out/(name+'_real.jpg'));sheet=Image.new('RGB',(1050,370),(24,49,39));d=ImageDraw.Draw(sheet)
        for index,(title,image) in enumerate([('Real photograph',real),('Earlier v6 room',before),('Repaired v7 room',current)]):
            image=image.copy();image.thumbnail((340,330));sheet.paste(image,(index*350+(340-image.width)//2,30+(330-image.height)//2));d.text((index*350+5,8),title,fill='white')
        sheet.save(out/(name+'_comparison.jpg'))
        with urlopen(Request(URL+'/item-model.glb?object='+name,headers={'Range':'bytes=0-11'})) as r:assert r.status==206 and r.read()[:4]==b'glTF'
        rows.append({'id':name,'calibrated_camera_capture':True,'room_inspection':True,'model_route':True})
        print('CAPTURED',name,flush=True)
    materials=b.js('(()=>{let a=[];homeTourScene.traverse(o=>{if(o.isMesh&&o.name.includes("tea_tray_v7")){for(let m of (Array.isArray(o.material)?o.material:[o.material]))a.push({name:o.name,material:m.name,map:!!m.map,roughnessMap:!!m.roughnessMap,vertices:o.geometry.attributes.position.count});}});return a;})()')
    assert any(x['map'] and x['roughnessMap'] for x in materials),materials
    assert any('Sugar_jar' in x['name'] and x['vertices']>10000 for x in materials),materials
    for item in cat['items']:
        name=item['id']
        if name not in ['tea_tray','frother','coffee_machine']:
            data=b.js('homeTour.capturePhoto('+json.dumps(item['camera'])+')')
            (out/(name+'_full.png')).write_bytes(base64.b64decode(data.split(',',1)[1]))
            Image.open(out/(name+'_full.png')).convert('RGB').crop(item['crop']).save(out/(name+'_current.jpg'),quality=95,subsampling=0)
        prior=ROOT.parent/'kitchen_panorama_compare/v6_browser_evidence'/(name+'_full.png')
        Image.open(prior).convert('RGB').crop(item['crop']).save(out/(name+'_before.jpg'),quality=95,subsampling=0)
        print('PANEL_READY',name,flush=True)
    for item in cat['room_items']:
        assert b.js('homeTour.items['+json.dumps(item['id'])+']?.parts>0')
        with urlopen(Request(URL+'/item-model.glb?object='+item['id'],headers={'Range':'bytes=0-11'})) as r:assert r.status==206 and r.read()[:4]==b'glTF'
    assert not b.errors,b.errors
    report={'status':'captured; visual review pending','scene_sha256':info['validation']['scene_sha256'],'revision':info['revision'],'items':rows,'calibrated_photo_captures':len(cat['items']),'room_model_routes_checked':len(cat['room_items']),'tea_materials_in_actual_browser':materials,'browser_errors':b.errors,'toaster':state,'navigation_actions_sent':False,'before_after_ui_retained':True}
    (ROOT/'evidence/browser_review.json').write_text(json.dumps(report,indent=2));print('BROWSER_CAPTURE_COMPLETE',flush=True)
