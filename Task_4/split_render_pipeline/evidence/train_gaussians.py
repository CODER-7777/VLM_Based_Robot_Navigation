"""Train a fixed-geometry SH Gaussian appearance baseline and report validation.

Geometry stays anchored to the scan/repaired assets; this pass does not claim
to reconstruct unseen surfaces or solve the room geometry from scratch.
"""
import os,sys,json,time,math
from pathlib import Path
W=Path('/data/robotics/toshith/rxr_author/refined/split_visuals')
sys.path.insert(0,str(W/'vendor'))
os.environ.setdefault('TORCH_EXTENSIONS_DIR',str(W/'torch_extensions'))
import numpy as np
import torch
from PIL import Image
from gsplat import rasterization
from plyfile import PlyData,PlyElement
torch.manual_seed(42)
device='cuda';degree=2;C0=.28209479177387814
data=np.load(W/'data/initial_points.npz');N=len(data['means'])
anchors=torch.as_tensor(data['means'],device=device)
means=torch.nn.Parameter(anchors.clone())
normals=torch.as_tensor(data['normals'],device=device)
w=torch.sqrt(torch.clamp((1+normals[:,2])/2,min=1e-8))
quats=torch.stack([w,-normals[:,1]/(2*w),normals[:,0]/(2*w),torch.zeros_like(w)],1)
negative=normals[:,2]<-.9999;quats[negative]=torch.tensor([0.,1.,0.,0.],device=device)
quats=torch.nn.Parameter(torch.nn.functional.normalize(quats,dim=1))
# Densely sampled product points need smaller splats than the coarse room scan.
obj=((means>=torch.tensor([4.425,-5.34,.928],device=device))&(means<=torch.tensor([4.615,-5.04,1.131],device=device))).all(1)
initial_scales=torch.full((N,3),.0048,device=device);initial_scales[:,2]=.0012;initial_scales[obj,:2]=.0028
log_scales=torch.nn.Parameter(torch.log(initial_scales))
sh=torch.zeros((N,(degree+1)**2,3),device=device)
sh[:,0]=(torch.as_tensor(data['colors'],device=device)-.5)/C0
sh=torch.nn.Parameter(sh)
logits=torch.nn.Parameter(torch.full((N,),math.log(.75/.25),device=device))
optim=torch.optim.Adam([{'params':[sh],'lr':.02},{'params':[logits],'lr':.012},{'params':[means],'lr':.00012},{'params':[log_scales],'lr':.003},{'params':[quats],'lr':.0008}])
records=json.loads((W/'data/cameras.json').read_text());views=[]
for record in records:
 image=np.asarray(Image.open(W/'data/photos'/record['name']).convert('RGB'),dtype=np.float32)/255.
 mask=np.load(W/'data/photos'/(record['name']+'.mask.npy')).astype(np.float32)
 teacher=np.asarray(Image.open(W/'data/teacher'/(record['name']+'.png')).convert('RGBA'),dtype=np.float32)/255.
 alpha=teacher[...,3:4]
 image=image*(1-alpha)+teacher[...,:3]*alpha
 mask=np.maximum(mask,alpha[...,0])
 c2w=np.asarray(record['c2w_raw_gl'])@np.diag([1.,-1.,-1.,1.])
 depth=np.load(W/'data/photos'/(record['name']+'.depth.npy')).astype(np.float32)
 depth_mask=(depth>.1)&(mask>.5)&(alpha[...,0]<.01)
 views.append((record,torch.as_tensor(image,device=device),torch.as_tensor(mask[...,None],device=device),torch.as_tensor(np.linalg.inv(c2w)[None],dtype=torch.float32,device=device),torch.as_tensor(np.asarray(record['K'])[None],dtype=torch.float32,device=device),torch.as_tensor(depth,device=device),torch.as_tensor(depth_mask,device=device)))
train=[v for v in views if v[0]['split']=='train'];val=[v for v in views if v[0]['split']=='val']
assert train and val
def render(view):
 record,_,_,matrix,K,_,_=view
 rgb,alpha,_=rasterization(means,quats,torch.exp(log_scales),torch.sigmoid(logits),sh,matrix,K,record['width'],record['height'],sh_degree=degree,render_mode='RGB+ED',packed=True,near_plane=.05,far_plane=12.)
 return rgb[0],alpha[0]
started=time.perf_counter();losses=[]
for step in range(4500):
 view=train[int(torch.randint(len(train),(1,)))]
 prediction,alpha=render(view)
 target,mask=view[1:3]
 loss=((prediction[...,:3]-target).abs()*mask).sum()/(mask.sum()*3+1e-6)
 # A little SH regularization keeps novel-view colors from becoming extreme.
 loss=loss+1e-5*sh[:,1:].square().mean()
 depth,depth_mask=view[5:7]
 if depth_mask.any():loss=loss+.10*(torch.log(prediction[...,3][depth_mask].clamp_min(.05))-torch.log(depth[depth_mask])).abs().mean()
 loss=loss+.002*((means-anchors)/.03).square().mean()
 loss.backward();optim.step();optim.zero_grad(set_to_none=True)
 with torch.no_grad():
  delta=(means-anchors).clamp(-.04,.04);delta[obj]=delta[obj].clamp(-.001,.001);means.copy_(anchors+delta)
  log_scales.clamp_(math.log(.0007),math.log(.025))
  quats.copy_(torch.nn.functional.normalize(quats,dim=1))
 if step%100==0:
  value=float(loss.detach());losses.append({'step':step,'loss':value,'elapsed_s':time.perf_counter()-started});print('TRAIN',losses[-1],flush=True)
 # Gradual decay improves fine texture convergence without moving geometry.
 if step in [2200,3600]:
  for group in optim.param_groups:group['lr']*=.4
torch.cuda.synchronize()
metrics=[];(W/'validation').mkdir(exist_ok=True)
with torch.inference_mode():
 for index,view in enumerate(val):
  prediction,alpha=render(view);target,mask=view[1:3]
  mse=float(((prediction[...,:3]-target).square()*mask).sum()/(mask.sum()*3+1e-6))
  metrics.append({'photo':view[0]['name'],'masked_psnr_db':-10*math.log10(max(mse,1e-10)),'evaluation_mask_fraction':float(mask.mean()),'coverage_alpha_gt_half':float((alpha>.5).float().mean())})
  im=np.clip(prediction[...,:3].cpu().numpy()*255,0,255).astype(np.uint8)
  Image.fromarray(im).save(W/'validation'/('view%d.jpg'%index),quality=95)
  Image.fromarray((target.cpu().numpy()*255).astype(np.uint8)).save(W/'validation'/('target%d.jpg'%index),quality=95)
 # Benchmark CUDA rasterization separately from JPEG/network/physics time.
 for _ in range(10):render(train[0])
 begin=torch.cuda.Event(enable_timing=True);end=torch.cuda.Event(enable_timing=True);begin.record()
 for _ in range(50):render(train[0])
 end.record();torch.cuda.synchronize();gpu_ms=begin.elapsed_time(end)/50
arrays={'means':means.detach().cpu().numpy(),'quats':quats.detach().cpu().numpy(),'scales':torch.exp(log_scales).detach().cpu().numpy(),'opacities':torch.sigmoid(logits).detach().cpu().numpy(),'sh':sh.detach().cpu().numpy(),'sh_degree':np.array(degree)}
np.savez_compressed(W/'scene.npz',**arrays)
# Standard 3DGS PLY: log scale, logit opacity, wxyz rotation, channel-major SH.
fields=[(n,'f4') for n in ['x','y','z','nx','ny','nz']+[f'f_dc_{i}' for i in range(3)]+[f'f_rest_{i}' for i in range(((degree+1)**2-1)*3)]+['opacity']+[f'scale_{i}' for i in range(3)]+[f'rot_{i}' for i in range(4)]]
vertices=np.empty(N,dtype=fields)
values=np.concatenate([arrays['means'],np.zeros((N,3)),arrays['sh'][:,0],arrays['sh'][:,1:].transpose(0,2,1).reshape(N,-1),logits.detach().cpu().numpy()[:,None],np.log(arrays['scales']),arrays['quats']],axis=1)
for i,n in enumerate(vertices.dtype.names):vertices[n]=values[:,i]
PlyData([PlyElement.describe(vertices,'vertex')],text=False).write(W/'scene.ply')
result={'model':'Experimental RGB-D and photo-trained Gaussian baseline with bounded geometry refinement','iterations':4500,'gaussians':N,'sh_degree':degree,'training_seconds':time.perf_counter()-started,'resolution':[640,512],'cuda_raster_rgb_expected_depth_ms':gpu_ms,'cuda_raster_fps':1000/gpu_ms,'validation':metrics,'loss_history':losses,'limitations':['Measured depth available for only some training views; cached scan depth used elsewhere.','Geometry refinement limited to 4 cm, selected toaster centers limited to 1 mm.','Kitchen coverage only; unseen regions and scan geometry errors may remain.','Gaussian expected optical depth is opacity-weighted; low-alpha pixels must be invalidated.','SH approximates view-dependent metal appearance; it is not a relightable BRDF.','Performance excludes HTTP, JPEG encoding, physics and scene loading.']}
(W/'training.json').write_text(json.dumps(result,indent=2));print('TRAINING_FINISHED',json.dumps(result),flush=True)
