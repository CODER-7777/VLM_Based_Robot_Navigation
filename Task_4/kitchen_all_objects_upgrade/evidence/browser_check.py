"""Read-only Chrome verification via DevTools. Uses no browser dependencies."""
from urllib.request import Request,urlopen
from urllib.parse import urlsplit,quote
from pathlib import Path
import socket,os,struct,json,base64,time
ROOT=Path(__file__).resolve().parent.parent
with urlopen(Request('http://127.0.0.1:9237/json/new?about:blank',method='PUT')) as r:tab=json.load(r)
u=urlsplit(tab['webSocketDebuggerUrl']);sock=socket.create_connection((u.hostname,u.port));sock.settimeout(40);key=base64.b64encode(os.urandom(16)).decode();sock.sendall(('GET '+u.path+' HTTP/1.1\r\nHost: '+u.netloc+'\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: '+key+'\r\nSec-WebSocket-Version: 13\r\nOrigin: http://localhost:9237\r\n\r\n').encode());header=b''
while not header.endswith(b'\r\n\r\n'):header+=sock.recv(1)
assert header.split(b' ')[1]==b'101',header
seq=0;errors=[]
def exact(n):
 out=b''
 while len(out)<n:
  data=sock.recv(n-len(out))
  if not data:raise RuntimeError('DevTools disconnected')
  out+=data
 return out
def recv():
 h=exact(2);size=h[1]&127
 if size==126:size=struct.unpack('!H',exact(2))[0]
 if size==127:size=struct.unpack('!Q',exact(8))[0]
 mask=exact(4) if h[1]&128 else None;data=exact(size)
 if mask:data=bytes(v^mask[i%4] for i,v in enumerate(data))
 if h[0]&15==8:raise RuntimeError('DevTools closed')
 return json.loads(data)
def call(method,params={}):
 global seq
 seq+=1;data=json.dumps({'id':seq,'method':method,'params':params}).encode();mask=os.urandom(4);n=len(data);header=bytes([0x81,0x80|n]) if n<126 else bytes([0x81,0x80|126])+struct.pack('!H',n);sock.sendall(header+mask+bytes(v^mask[i%4] for i,v in enumerate(data)))
 while True:
  r=recv()
  if r.get('method')=='Runtime.exceptionThrown':errors.append(r['params'])
  if r.get('id')==seq:
   if 'error' in r:raise RuntimeError(r['error'])
   return r.get('result',{})
def js(expr):return call('Runtime.evaluate',{'expression':expr,'returnByValue':True,'awaitPromise':True}).get('result',{}).get('value')
call('Page.enable');call('Runtime.enable');call('Emulation.setDeviceMetricsOverride',{'width':1400,'height':1050,'deviceScaleFactor':1,'mobile':False});report={}
for name,path in [('live','/'),('comparisons','/comparisons'),('phone_model','/product-viewer?object=phone_v4'),('jug_model','/product-viewer?object=blue_jug_v4')]:
 call('Page.navigate',{'url':'http://127.0.0.1:8767'+path})
 for i in range(80):
  time.sleep(.25)
  ready=js("document.readyState==='complete' && (document.querySelector('model-viewer') ? document.querySelector('model-viewer').loaded===true : [...document.querySelectorAll('img')].filter(x=>x.loading!=='lazy').every(x=>x.complete&&x.naturalWidth>0))")
  if ready:break
 if name=='comparisons':
  js("(async()=>{for(const im of document.images){im.loading='eager';}await Promise.all([...document.images].map(im=>im.complete?Promise.resolve():new Promise(r=>{im.onload=r;im.onerror=r;})));return true;})()")
 result=js("({title:document.title,images:[...document.images].map(x=>({src:x.src,loaded:x.complete&&x.naturalWidth>0})),status:document.getElementById('status')?.textContent,modelLoaded:document.querySelector('model-viewer')?.loaded,modelError:document.querySelector('model-viewer')?.getAttribute('error')})")
 result['ready']=ready;report[name]=result
 shot=call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False});(ROOT/'images/browser'/(name+'.png')).write_bytes(base64.b64decode(shot['data']))
report['js_exceptions']=errors;(ROOT/'evidence/browser_verification.json').write_text(json.dumps(report,indent=2));assert not errors,errors
assert all(im['loaded'] for name in ['live','comparisons'] for im in report[name]['images']);assert report['phone_model'].get('modelLoaded') and report['jug_model'].get('modelLoaded');print('BROWSER_VERIFIED',[(k,v.get('ready')) for k,v in report.items() if isinstance(v,dict)])
call('Page.close');sock.close()
