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

call('Page.enable');call('Runtime.enable');call('Emulation.setDeviceMetricsOverride',{'width':1500,'height':1050,'deviceScaleFactor':1,'mobile':False})
call('Page.navigate',{'url':'http://127.0.0.1:8767/?object=range_kettle'})
for i in range(100):
 time.sleep(.2)
 if js("document.getElementById('item-picker')?.options.length===22 && [...document.querySelectorAll('.compare img')].every(im=>im.complete&&im.naturalWidth>0)"):break
else:raise RuntimeError('Published comparisons did not load')
rows=json.loads((ROOT/'evidence/catalog.json').read_text())['items'];checks=[]
for row in rows:
 slug=row['id'];js("(()=>{const p=document.getElementById('item-picker');p.value="+json.dumps(slug)+";p.dispatchEvent(new Event('change'));})()")
 for i in range(100):
  time.sleep(.1)
  if js("[...document.querySelectorAll('.compare img')].every(im=>im.complete&&im.naturalWidth>0)"):break
 else:raise RuntimeError('Comparison images failed: '+slug)
 state=js("({selected:document.getElementById('item-picker').value,images:document.querySelectorAll('.compare img').length,room:document.getElementById('room-link').getAttribute('href'),model:document.getElementById('model-link').getAttribute('href'),roomHidden:document.getElementById('room').hidden})")
 assert state['selected']==slug and state['images']==3 and state['room'].endswith(slug) and state['model'].endswith(slug);checks.append(state)
js("(()=>{const p=document.getElementById('item-picker');p.value='range_kettle';p.dispatchEvent(new Event('change'));})()");time.sleep(.5)
shot=call('Page.captureScreenshot',{'format':'jpeg','quality':94})['data'];(ROOT/'images/published_dashboard.jpg').write_bytes(base64.b64decode(shot));assert not errors,errors
(ROOT/'evidence/published_comparison_browser_review.json').write_text(json.dumps({'items':checks,'exceptions':errors},indent=2));call('Page.close');sock.close();print('PUBLISHED_COMPARISONS_VERIFIED',len(checks),'items; three real/earlier/current panels and correct room/model links')
