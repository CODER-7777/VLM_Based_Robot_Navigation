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
call('Page.navigate',{'url':'http://127.0.0.1:8767/home-tour'})
for i in range(240):
 time.sleep(1)
 result=js("window.homeTour ? JSON.parse(JSON.stringify(window.homeTour)) : {loading:document.getElementById('status')?.textContent}")
 if i%10==0:print('LOAD',i,result,flush=True)
 if result and result.get('error'):raise RuntimeError(result['error'])
 if result and result.get('ready'):break
else:raise RuntimeError('Home scene loading timed out')
time.sleep(2)
report={'walk':result}
shot=call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False});(ROOT/'images/home_walk.png').write_bytes(base64.b64decode(shot['data']))
js("document.getElementById('inspect').click()")
time.sleep(2)
report['inspect']=js("({...window.homeTour,camera:window.homeTourCamera.position.toArray(),render:window.homeTourRenderer.info.render})")
shot=call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False});(ROOT/'images/toaster_in_home.png').write_bytes(base64.b64decode(shot['data']))
rect=js("(()=>{const b=document.querySelector('canvas').getBoundingClientRect();return {x:b.x+b.width*.5,y:b.y+b.height*.5};})()")
x,y=rect['x'],rect['y']
call('Input.dispatchMouseEvent',{'type':'mousePressed','x':x,'y':y,'button':'left','buttons':1,'clickCount':1})
for step in range(1,11):
 call('Input.dispatchMouseEvent',{'type':'mouseMoved','x':x+step*14,'y':y+step*2,'button':'left','buttons':1});time.sleep(.06)
call('Input.dispatchMouseEvent',{'type':'mouseReleased','x':x+140,'y':y+20,'button':'left','buttons':0,'clickCount':1});time.sleep(2)
report['orbit']=js("({...window.homeTour,camera:window.homeTourCamera.position.toArray()})")
shot=call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False});(ROOT/'images/toaster_orbit.png').write_bytes(base64.b64decode(shot['data']))
js("document.getElementById('walk').click()")
time.sleep(1)
report['walk_resume']=js("({...window.homeTour,camera:window.homeTourCamera.position.toArray()})")
report['js_exceptions']=errors
(ROOT/'evidence/browser_verification.json').write_text(json.dumps(report,indent=2))
assert report['walk']['toasterParts']==11 and report['walk']['originalPbr']
assert abs(report['walk']['toasterBounds']['min'][1]-.929)<.001,report['walk']['toasterBounds']
assert report['inspect']['camera']!=report['orbit']['camera'],'Orbit did not move camera'
assert report['walk_resume']['mode']=='walk'
assert not errors,errors
print('PBR_HOME_TOUR_VERIFIED',report,flush=True)
call('Page.close');sock.close()
