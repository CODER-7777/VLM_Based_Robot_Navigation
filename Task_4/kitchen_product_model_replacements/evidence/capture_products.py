"""Read-only Chrome verification via DevTools. Uses no browser dependencies."""
from urllib.request import Request,urlopen
from urllib.parse import urlsplit,quote
from pathlib import Path
import socket,os,struct,json,base64,time,io
from PIL import Image
ROOT=Path(__file__).resolve().parent.parent
with urlopen('http://127.0.0.1:9238/json/list') as r:tabs=json.load(r)
previous=next((t for t in tabs if t.get('url')=='http://127.0.0.1:8784/home-tour'),None)
if previous:tab=previous
else:
 with urlopen(Request('http://127.0.0.1:9238/json/new?about:blank',method='PUT')) as r:tab=json.load(r)
u=urlsplit(tab['webSocketDebuggerUrl']);sock=socket.create_connection((u.hostname,u.port));sock.settimeout(180);key=base64.b64encode(os.urandom(16)).decode();sock.sendall(('GET '+u.path+' HTTP/1.1\r\nHost: '+u.netloc+'\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: '+key+'\r\nSec-WebSocket-Version: 13\r\nOrigin: http://localhost:9238\r\n\r\n').encode());header=b''
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
catalog=json.loads((ROOT/'evidence/catalog.json').read_text())['items']
call('Page.enable');call('Runtime.enable');call('Emulation.setDeviceMetricsOverride',{'width':1400,'height':1120,'deviceScaleFactor':1,'mobile':False})
if not previous:call('Page.navigate',{'url':'http://127.0.0.1:8784/home-tour'})
for i in range(900):
 time.sleep(1)
 state=js("window.homeTour ? {ready:window.homeTour.ready,error:window.homeTour.error,status:document.getElementById('status')?.textContent} : {}")
 if i%15==0:print('LOAD',i,state.get('status'),flush=True)
 if state.get('error'):raise RuntimeError(state['error'])
 if state.get('ready'):break
else:raise RuntimeError('Latest kitchen scene did not load')
report={'scene':js("({toasterParts:window.homeTour.toasterParts,originalPbr:window.homeTour.originalPbr,items:window.homeTour.items})"),'photos':[],'room_views':[]}
assert report['scene']['originalPbr'] and report['scene']['toasterParts']==11
for item in catalog:
 diagnostics=report['scene']['items'][item['id']]
 assert diagnostics['parts']==item['mesh_parts'],(item['id'],diagnostics)
 if diagnostics['bounds']:
  error=abs(diagnostics['bounds']['min'][1]-item['counter_z'])
  assert error<1e-5,(item['id'],error)
assert abs(report['scene']['items']['blue_jug']['bounds']['max'][1]-report['scene']['items']['blue_jug']['bounds']['min'][1]-.051)<1e-5
assert report['scene']['items']['phone']['parts']==22
photos={item['photo']:item['camera'] for item in catalog}
for filename,camera in photos.items():
 packet=json.loads(json.dumps(camera));packet['width']=1280;packet['height']=1024
 for row in [0,1]:packet['K'][row]=[value*1.6 for value in packet['K'][row]]
 canvas=js('window.homeTour.capturePhoto('+json.dumps(packet)+')')
 output=ROOT/'images'/('photo_'+filename)
 Image.open(io.BytesIO(base64.b64decode(canvas.split(',',1)[1]))).convert('RGB').save(output,quality=94)
 report['photos'].append({'photo':filename,'capture':str(output),'camera':packet})
 print('PHOTO_CAPTURED',filename,flush=True)
js('window.homeTour.resumeInspection()')
for item in catalog:
 assert js('window.homeTour.focusObject('+json.dumps(item['id'])+')')
 js('window.homeTourRenderer.render(window.homeTourScene,window.homeTourCamera)')
 time.sleep(.2)
 result=js("({id:window.homeTour.selectedObject,mode:window.homeTour.mode,camera:window.homeTourCamera.position.toArray(),target:window.homeTourCamera.getWorldDirection(new window.homeTourCamera.position.constructor()).toArray(),canvas:window.homeTourRenderer.domElement.toDataURL('image/png')})")
 Image.open(io.BytesIO(base64.b64decode(result.pop('canvas').split(',',1)[1]))).convert('RGB').save(ROOT/'images'/('room_'+item['id']+'.jpg'),quality=92)
 assert result['mode']=='inspect' and result['id']==item['id']
 report['room_views'].append(result)
 print('ROOM_CAPTURED',item['id'],flush=True)
report['js_exceptions']=errors
(ROOT/'evidence/scene_browser_review.json').write_text(json.dumps(report,indent=2))
assert not errors,errors
print('ALL_ITEM_SCENE_VERIFIED',len(catalog),len(photos),flush=True)
sock.close()
