import os,sys,json,time
from pathlib import Path
R=Path('/data/robotics/toshith/rxr_author/refined/split_visuals')
sys.path.insert(0,str(R/'vendor'))
os.environ.setdefault('TORCH_EXTENSIONS_DIR',str(R/'torch_extensions'))
import torch
from gsplat import rasterization
device='cuda'
means=torch.tensor([[0.,0.,2.]],device=device)
quats=torch.tensor([[1.,0.,0.,0.]],device=device)
scales=torch.full((1,3),.1,device=device)
opacities=torch.tensor([.95],device=device)
colors=torch.tensor([[1.,0.,0.]],device=device)
K=torch.tensor([[[100.,0.,32.],[0.,100.,32.],[0.,0.,1.]]],device=device)
view=torch.eye(4,device=device)[None]
start=time.perf_counter()
out,alpha,_=rasterization(means,quats,scales,opacities,colors,view,K,64,64,render_mode='RGB+ED')
torch.cuda.synchronize()
assert out.shape==(1,64,64,4)
assert abs(float(out[0,32,32,3])-2.)<1e-4
assert float(out[0,32,32,0])>.8
(R/'gsplat_smoke.json').write_text(json.dumps({'gsplat_version':__import__('gsplat').__version__,'shape':list(out.shape),'center_depth_m':float(out[0,32,32,3]),'first_call_including_compile_s':time.perf_counter()-start},indent=2))
print('GSPLAT_RGBD_SMOKE_PASSED',out.shape,flush=True)
