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
call('Page.enable');call('Runtime.enable');call('Emulation.setDeviceMetricsOverride',{'width':1400,'height':1050,'deviceScaleFactor':1,'mobile':False})
call('Page.navigate',{'url':'http://127.0.0.1:8767/'})
for i in range(80):
 time.sleep(.25)
 ready=js("document.readyState==='complete' && [...document.querySelectorAll('.compare img')].length===2 && [...document.querySelectorAll('.compare img')].every(im=>im.complete&&im.naturalWidth===600)")
 if ready:break
assert ready,'Comparison images did not load'
report={'comparison':js("({title:document.title,headings:[...document.querySelectorAll('h2')].map(e=>e.textContent),images:[...document.querySelectorAll('.compare img')].map(im=>({src:im.src,width:im.naturalWidth,height:im.naturalHeight})),roomInitiallyHidden:document.getElementById('room').hidden,roomInitiallyUnloaded:!document.getElementById('room').getAttribute('src')})")}
assert report['comparison']['roomInitiallyHidden'] and report['comparison']['roomInitiallyUnloaded']
shot=call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False});(ROOT/'images/comparison_first.png').write_bytes(base64.b64decode(shot['data']))
js("document.getElementById('show-room').click()")
for i in range(240):
 time.sleep(1)
 state=js("(()=>{const f=document.getElementById('room');return f.contentWindow?.homeTour ? {...f.contentWindow.homeTour,status:f.contentDocument?.getElementById('status')?.textContent,title:f.contentDocument?.title,src:f.getAttribute('src'),visible:!f.hidden} : {};})()")
 if i%15==0:print('ROOM',i,state.get('status'),flush=True)
 if state.get('error'):raise RuntimeError(state['error'])
 if state.get('ready'):break
else:raise RuntimeError('Kitchen room did not load')
assert state['mode']=='inspect' and state['toasterParts']==11 and state['originalPbr'] and state['visible'],state
assert state['title']=='Toaster in the kitchen',state
assert abs(state['toasterBounds']['min'][1]-.929)<.001
report['room']=state
js("document.getElementById('room').scrollIntoView({block:'start'})")
time.sleep(1)
shot=call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False});(ROOT/'images/embedded_kitchen.png').write_bytes(base64.b64decode(shot['data']))
report['js_exceptions']=errors
(ROOT/'evidence/comparison_room_verification.json').write_text(json.dumps(report,indent=2))
assert not errors,errors
print('COMPARISON_THEN_ROOM_VERIFIED',report,flush=True)
call('Page.close');sock.close()
