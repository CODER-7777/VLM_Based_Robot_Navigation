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
 state=js("window.homeTour ? {...window.homeTour,status:document.getElementById('status')?.textContent} : {}")
 if i%15==0:print('LOAD',i,state.get('status'),flush=True)
 if state.get('error'):raise RuntimeError(state['error'])
 if state.get('ready'):break
else:raise RuntimeError('Scene did not load')
result=js("""(async()=>{const THREE=await import('three');const p=await fetch('/tour-assets/reference_camera.json').then(r=>r.json());const m=new THREE.Matrix4().set(...p.camera.c2w.flat());m.premultiply(new THREE.Matrix4().set(1,0,0,0,0,0,1,0,0,-1,0,0,0,0,0,1));window.homeTour.ready=false;window.homeTour.mode='walk';const camera=window.homeTourCamera;m.decompose(camera.position,camera.quaternion,new THREE.Vector3());const [fx,fy,cx,cy]=p.camera.K,n=camera.near,f=camera.far;camera.projectionMatrix.makePerspective(-cx/fx*n,(1280-cx)/fx*n,cy/fy*n,-(1024-cy)/fy*n,n,f);camera.projectionMatrixInverse.copy(camera.projectionMatrix).invert();window.homeTourRenderer.setPixelRatio(1);window.homeTourRenderer.setSize(1280,1024,false);await new Promise(r=>setTimeout(r,150));window.homeTourRenderer.render(window.homeTourScene,camera);return {parts:window.homeTour.toasterParts,pbr:window.homeTour.originalPbr,pose:p.camera,canvas:window.homeTourRenderer.domElement.toDataURL('image/png')};})()""")
(ROOT/'images/pbr_reference.png').write_bytes(base64.b64decode(result.pop('canvas').split(',',1)[1]))
(ROOT/'evidence/pbr_reference_camera.json').write_text(json.dumps(result,indent=2))
assert result['parts']==11 and result['pbr'] and not errors
print('PBR_REFERENCE_CAPTURED',flush=True)
call('Page.close');sock.close()
