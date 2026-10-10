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

import sys
base=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:8784'
items=json.loads((ROOT/'evidence/catalog.json').read_text())['items']
call('Page.enable');call('Runtime.enable');call('Emulation.setDeviceMetricsOverride',{'width':1400,'height':1050,'deviceScaleFactor':1,'mobile':False})
call('Page.navigate',{'url':base+'/?object=phone'})
def wait(expr,seconds=20):
 deadline=time.monotonic()+seconds
 while time.monotonic()<deadline:
  result=js(expr)
  if result:return result
  time.sleep(.25)
 raise RuntimeError('Browser condition timed out: '+expr)
wait("document.querySelector('#item-picker')?.options.length===22")
report={'base':base,'comparisons':[]}
assert js("document.getElementById('room').hidden && !document.getElementById('room').getAttribute('src')")
for item in items:
 js("(()=>{const p=document.getElementById('item-picker');p.value="+json.dumps(item['id'])+";p.dispatchEvent(new Event('change'));})()")
 wait("[...document.querySelectorAll('.compare img')].every(im=>im.complete&&im.naturalWidth>0) && document.querySelector('#render-image').src.includes("+json.dumps(item['id']+'_pbr.jpg')+")")
 report['comparisons'].append(js("({selected:document.getElementById('item-picker').value,images:[...document.querySelectorAll('.compare img')].map(im=>({width:im.naturalWidth,height:im.naturalHeight}))})"))
js("(()=>{const p=document.getElementById('item-picker');p.value='phone';p.dispatchEvent(new Event('change'));document.getElementById('show-room').click();})()")
for i in range(300):
 time.sleep(1)
 state=js("(()=>{const s=document.getElementById('room').contentWindow?.homeTour;return s?{ready:s.ready,error:s.error,selected:s.selectedObject,mode:s.mode}:{};})()")
 if i%15==0:print('EMBEDDED_ROOM',i,state,flush=True)
 if state.get('error'):raise RuntimeError(state['error'])
 if state.get('ready'):break
else:raise RuntimeError('Embedded room did not load')
assert state['mode']=='inspect' and state['selected']=='phone',state
report['room_switches']=[]
for item in items:
 js("(()=>{const p=document.getElementById('item-picker');p.value="+json.dumps(item['id'])+";p.dispatchEvent(new Event('change'));})()")
 state=wait("(()=>{const s=document.getElementById('room').contentWindow?.homeTour;return s?.ready&&s.selectedObject==="+json.dumps(item['id'])+"&&s.mode==='inspect'?{id:s.selectedObject,originalPbr:s.originalPbr,parts:s.items[s.selectedObject].parts}:false;})()")
 report['room_switches'].append(state)
js("(()=>{const w=document.getElementById('room').contentWindow;w.homeTour.focusObject('blue_jug');})()")
assert wait("document.getElementById('item-picker').value==='blue_jug'")
js("document.getElementById('room').scrollIntoView({block:'start'})")
time.sleep(.5)
shot=call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False});(ROOT/'images/live_embedded_jug.png').write_bytes(base64.b64decode(shot['data']))
js("window.scrollTo(0,0)")
time.sleep(.3)
shot=call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False});(ROOT/'images/live_comparison.png').write_bytes(base64.b64decode(shot['data']))
report['exceptions']=errors
assert not errors,errors
(ROOT/'evidence/dashboard_browser_review.json').write_text(json.dumps(report,indent=2))
print('ALL_COMPARISONS_AND_EMBEDDED_ROOM_VERIFIED',len(items),flush=True)
call('Page.close');sock.close()
