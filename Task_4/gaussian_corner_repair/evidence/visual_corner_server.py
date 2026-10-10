"""Independent CUDA visual process. No Habitat or Bullet imports."""
import os,sys,json,time,io,base64,threading,hashlib,traceback
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
W=Path('/data/robotics/toshith/rxr_author/refined/split_visuals')
sys.path.insert(0,str(W/'vendor'))
os.environ.setdefault('TORCH_EXTENSIONS_DIR',str(W/'torch_extensions'))
import numpy as np
import torch
import cv2
from PIL import Image
from gsplat import rasterization
data=np.load(W/'scene.npz');device='cuda'
parameters={n:torch.as_tensor(data[n],device=device) for n in ['means','quats','scales','opacities']}
parameters['colors']=torch.as_tensor(data['sh'],device=device)
degree=int(data['sh_degree'])
lock=threading.Lock();cached_key=None;cached_result=None
def image_bytes(array,kind='PNG'):
 out=io.BytesIO();Image.fromarray(array).save(out,format=kind,**({'quality':93} if kind=='JPEG' else {}));return out.getvalue()
@torch.inference_mode()
def render(packet):
 global cached_key,cached_result
 key=hashlib.sha256(json.dumps(packet,sort_keys=True).encode()).hexdigest()
 with lock:
  if key==cached_key:return cached_result
  width,height=int(packet['width']),int(packet['height'])
  if not (16<=width<=1280 and 16<=height<=1024):raise ValueError('Unsupported render dimensions')
  c2w=np.asarray(packet['c2w_raw_gl'],dtype=np.float64)
  K=np.asarray(packet['K'],dtype=np.float64)
  if c2w.shape!=(4,4) or K.shape!=(3,3) or not np.isfinite(c2w).all() or not np.isfinite(K).all():raise ValueError('Invalid camera matrices')
  if abs(np.linalg.det(c2w[:3,:3])-1)>1e-3:raise ValueError('Camera rotation must be rigid')
  # OpenGL camera (-Z forward,+Y up) -> OpenCV camera (+Z forward,+Y down).
  view=np.linalg.inv(c2w@np.diag([1.,-1.,-1.,1.]))
  matrix=torch.tensor(view[None],dtype=torch.float32,device=device)
  intrinsics=torch.tensor(K[None],dtype=torch.float32,device=device)
  begin=torch.cuda.Event(enable_timing=True);end=torch.cuda.Event(enable_timing=True)
  begin.record()
  colors,alphas,_=rasterization(**parameters,viewmats=matrix,Ks=intrinsics,width=width,height=height,sh_degree=degree,render_mode='RGB+ED',near_plane=.05,far_plane=12.,packed=True)
  end.record();torch.cuda.synchronize();kernel_ms=begin.elapsed_time(end)
  rgba=colors[0].cpu().numpy();alpha=alphas[0,...,0].cpu().numpy()
  rgb=np.clip(rgba[...,:3]*255,0,255).astype(np.uint8)
  depth=rgba[...,3].astype(np.float32)
  valid=(alpha>=.5)&np.isfinite(depth)&(depth>.05)&(depth<12)
  depth[~valid]=np.nan
  display=np.nan_to_num(depth,nan=0)
  display=np.clip((1-(display-.3)/3.2)*255,0,255).astype(np.uint8)
  depth_rgb=cv2.applyColorMap(display,cv2.COLORMAP_TURBO)[...,::-1];depth_rgb[~valid]=0
  payload=io.BytesIO()
  np.savez_compressed(payload,depth_m=depth,valid=valid,alpha=alpha.astype(np.float32),K=K,c2w_raw_gl=c2w,frame_id=np.array(packet['frame_id']),depth_definition=np.array('Gaussian expected optical-axis Z depth, metres; invalid below alpha 0.5'))
  result={'frame_id':packet['frame_id'],'rgb_jpeg':base64.b64encode(image_bytes(rgb,'JPEG')).decode(),'depth_png':base64.b64encode(image_bytes(depth_rgb)).decode(),'depth_npz':base64.b64encode(payload.getvalue()).decode(),'cuda_raster_ms':kernel_ms,'valid_depth_fraction':float(valid.mean()),'width':width,'height':height,'depth_definition':'Expected optical-axis Z in metres; opacity-weighted, not a guaranteed first surface hit','camera':packet}
  cached_key=key;cached_result=result;return result
class Handler(BaseHTTPRequestHandler):
 def send(self,status,payload):
  data=json.dumps(payload).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
 def do_GET(self):
  if self.path=='/health':self.send(200,{'ready':True,'process':'independent_gsplat_cuda','gaussians':len(data['means']),'training':json.loads((W/'training.json').read_text()),'visual_revision':'surface_anchored_corner_v2'})
  else:self.send(404,{'error':'Not found'})
 def do_POST(self):
  if self.path!='/render':self.send(404,{'error':'Not found'});return
  try:
   length=int(self.headers.get('Content-Length','0'))
   if length>65536:raise ValueError('Camera packet too large')
   packet=json.loads(self.rfile.read(length));self.send(200,render(packet))
  except Exception as exc:
   traceback.print_exc();self.send(400,{'error':str(exc)})
# CUDA loading and the first kernel invocation are startup work. Warm before
# exposing the HTTP service, so the first browser frame is not a compile probe.
warm=next(r for r in json.loads((W/'data/cameras.json').read_text()) if r['name']=='58348305b0f84dd8b161aaf2d5b945ef_i2_4.jpg')
ready=False
for attempt in range(3):
 try:
  render(dict(warm,frame_id='startup_%d'%attempt));ready=True
 except Exception:
  traceback.print_exc()
  if attempt==2:raise
if not ready:raise RuntimeError('CUDA renderer warm-up failed')
print('GSPLAT_VISUAL_SERVER_READY',8779,flush=True)
ThreadingHTTPServer(('127.0.0.1',8779),Handler).serve_forever()
