"""Render five matched 360 views from the already verified private browser tab."""
from pathlib import Path
from urllib.request import urlopen,Request
import sys,json,base64,time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/'kitchen_panorama_compare'))
from capture_panoramas import DevTools,DEBUG
URL='http://localhost:8769'
if __name__=='__main__':
    with urlopen(URL+'/config.json') as r:cfg=json.load(r)
    with urlopen('http://localhost:8772/tour-info') as r:live=json.load(r)
    assert cfg['source_sha256']==live['validation']['scene_sha256']
    with urlopen(DEBUG+'/json/list') as r:tab=next(t for t in json.load(r) if 'localhost:8772/home-tour' in t.get('url',''))
    b=DevTools(tab=tab);b.call('Page.bringToFront');assert b.js('homeTour.ready')
    with urlopen('http://localhost:8772/tour-info') as r:preview=json.load(r)
    assert preview['validation']['scene_sha256']==cfg['source_sha256']
    for view in cfg['views']:
        for index,packet in enumerate(view['capture_packets']):
            png=b.js('homeTour.capturePhoto('+json.dumps(packet)+')')
            data=base64.b64decode(png.split(',',1)[1])
            with urlopen(Request(URL+'/capture/'+view['id']+'/'+str(index),data=data,headers={'Content-Type':'image/png'}),timeout=60) as r:assert r.status==200
            print('FACE',view['id'],index,flush=True)
        with urlopen(Request(URL+'/assemble/'+view['id'],data=b'{}',headers={'Content-Type':'application/json'}),timeout=120) as r:assert r.status==200
        with urlopen(URL+'/images/'+view['id']+'_after.jpg') as r:
            out=ROOT/'evidence/panoramas';out.mkdir(exist_ok=True);(out/(view['id']+'_after.jpg')).write_bytes(r.read())
        print('PANORAMA',view['id'],flush=True)
    assert not b.errors,b.errors
    report={'status':'captured; visual review pending','revision':cfg['revision'],'scene_sha256':cfg['source_sha256'],'views':[v['id'] for v in cfg['views']],'faces':30,'size':cfg['panorama_size'],'navigation_actions_sent':False,'browser_errors':b.errors,'captured_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
    (ROOT/'evidence/panorama_review.json').write_text(json.dumps(report,indent=2))
