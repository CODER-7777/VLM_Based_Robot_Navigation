"""Read-only Chrome verification via DevTools. Uses no browser dependencies."""
from urllib.request import Request,urlopen
from urllib.parse import urlsplit,quote
from pathlib import Path
import socket,os,struct,json,base64,time
ROOT=Path(__file__).resolve().parent.parent
with urlopen(Request('http://127.0.0.1:9238/json/new?about:blank',method='PUT')) as r:tab=json.load(r)
u=urlsplit(tab['webSocketDebuggerUrl']);sock=socket.create_connection((u.hostname,u.port));sock.settimeout(40);key=base64.b64encode(os.urandom(16)).decode();sock.sendall(('GET '+u.path+' HTTP/1.1\r\nHost: '+u.netloc+'\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: '+key+'\r\nSec-WebSocket-Version: 13\r\nOrigin: http://localhost:9238\r\n\r\n').encode());header=b''
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

call('Page.enable');call('Runtime.enable');call('Emulation.setDeviceMetricsOverride',{'width':1400,'height':1050,'deviceScaleFactor':1,'mobile':False})
call('Page.navigate',{'url':'http://127.0.0.1:8767/'})
for i in range(80):
 time.sleep(.25)
 if js("document.getElementById('item-picker')?.options.length===22 && [...document.querySelectorAll('.compare img')].every(im=>im.complete&&im.naturalWidth>0)"):break
else:raise RuntimeError('Published comparison did not load')
report={'comparison':js("({title:document.title,items:document.getElementById('item-picker').options.length,initiallyHidden:document.getElementById('room').hidden})"),'models':[]}
assert report['comparison']['initiallyHidden']
for name in ['blue_jug','phone','range_kettle','toaster','coffee_machine']:
 call('Page.navigate',{'url':'http://127.0.0.1:8767/item-viewer?object='+name})
 for i in range(120):
  time.sleep(.5)
  ready=js("document.querySelector('model-viewer')?.loaded===true")
  if ready:break
 else:raise RuntimeError('Model viewer failed for '+name)
 result=js("({title:document.title,loaded:document.querySelector('model-viewer').loaded,src:document.querySelector('model-viewer').src})")
 report['models'].append(result);print('LIVE_MODEL_LOADED',name,flush=True)
report['exceptions']=errors
assert not errors,errors
(ROOT/'evidence/published_browser_verification.json').write_text(json.dumps(report,indent=2))
call('Page.close');sock.close()
print('PUBLISHED_BROWSER_VERIFIED',flush=True)
