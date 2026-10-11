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

rows=json.loads((ROOT/'objects/replacement_inventory.json').read_text());report=[]
call('Page.enable');call('Runtime.enable');call('Emulation.setDeviceMetricsOverride',{'width':1500,'height':1000,'deviceScaleFactor':1,'mobile':False})
for row in rows:
 slug=row['id'];call('Page.navigate',{'url':'http://127.0.0.1:8768/?object='+slug})
 for i in range(120):
  time.sleep(.25)
  if js("document.querySelector('model-viewer')?.loaded===true"):break
 else:raise RuntimeError('Saved model did not load: '+slug)
 result=js("({loaded:document.querySelector('model-viewer').loaded,dimensions:document.querySelector('model-viewer').getDimensions(),materials:document.querySelector('model-viewer').model.materials.map(m=>({name:m.name,metallic:m.pbrMetallicRoughness.metallicFactor,roughness:m.pbrMetallicRoughness.roughnessFactor})),images:[...document.querySelectorAll('img')].every(im=>im.complete&&im.naturalWidth>0)})")
 assert result['images'] and result['loaded']
 result['object']=slug;report.append(result)
 image=call('Page.captureScreenshot',{'format':'jpeg','quality':90})['data'];(ROOT/'images'/('saved_view_'+slug+'.jpg')).write_bytes(base64.b64decode(image))
 js("document.querySelector('model-viewer').cameraOrbit='120deg 65deg auto'");time.sleep(.2)
 print('SAVED_MODEL_VERIFIED',slug,flush=True)
(ROOT/'evidence/saved_model_browser_review.json').write_text(json.dumps({'objects':report,'exceptions':errors},indent=2));assert not errors,errors
call('Page.close');sock.close();print('TEN_SAVED_MODEL_VIEWERS_VERIFIED',flush=True)
