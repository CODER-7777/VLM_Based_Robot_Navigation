"""Evaluate displayed/clipped RGB after local cleanup, including held-out views."""
import json,io,base64,math,time
from pathlib import Path
from urllib.request import Request,urlopen
import numpy as np
from PIL import Image,ImageDraw
W=Path('/data/robotics/toshith/rxr_author/refined/split_visuals');P=W/'final_previews';P.mkdir(exist_ok=True)
records=json.loads((W/'data/cameras.json').read_text())
chosen=[next(r for r in records if r['name']=='58348305b0f84dd8b161aaf2d5b945ef_i2_4.jpg')]+[r for r in records if r['split']=='val']
report=[]
for index,record in enumerate(chosen):
 packet=dict(record,frame_id='evaluation_%d'%index)
 request=Request('http://127.0.0.1:8779/render',data=json.dumps(packet).encode(),headers={'Content-Type':'application/json'})
 with urlopen(request,timeout=60) as response:result=json.load(response)
 rgb=np.asarray(Image.open(io.BytesIO(base64.b64decode(result['rgb_jpeg']))),dtype=np.float32)/255.
 target=np.asarray(Image.open(W/'data/photos'/record['name']),dtype=np.float32)/255.
 teacher=np.asarray(Image.open(W/'data/teacher'/(record['name']+'.png')),dtype=np.float32)/255.;alpha=teacher[...,3:4]
 target=target*(1-alpha)+teacher[...,:3]*alpha
 mask=np.maximum(np.load(W/'data/photos'/(record['name']+'.mask.npy')),alpha[...,0])
 mse=float(((rgb-target)**2*mask[...,None]).sum()/(mask.sum()*3+1e-8))
 depth=np.load(io.BytesIO(base64.b64decode(result['depth_npz'])))
 measured=np.load(W/'data/photos'/(record['name']+'.depth.npy'))
 valid=(measured>.1)&depth['valid']&(mask>.5)&(alpha[...,0]<.01)
 errors=np.abs(depth['depth_m'][valid]-measured[valid])
 report.append({'photo':record['name'],'split':record['split'],'displayed_rgb_masked_psnr_db':-10*math.log10(max(mse,1e-10)),'evaluation_mask_fraction':float(mask.mean()),'valid_depth_fraction':result['valid_depth_fraction'],'measured_depth_evaluation_pixels':int(valid.sum()),'median_depth_absolute_error_m':float(np.median(errors)) if len(errors) else None,'mean_depth_absolute_error_m':float(np.mean(errors)) if len(errors) else None,'cuda_raster_ms':result['cuda_raster_ms']})
 panel=Image.new('RGB',(record['width']*2,record['height']+30),'#153c2c');draw=ImageDraw.Draw(panel)
 draw.text((8,8),'Photo + PBR replacement target',fill='white');draw.text((record['width']+8,8),'Experimental cleaned Gaussian output',fill='white')
 panel.paste(Image.fromarray(np.clip(target*255,0,255).astype(np.uint8)),(0,30));panel.paste(Image.fromarray(np.clip(rgb*255,0,255).astype(np.uint8)),(record['width'],30));panel.save(P/('view%d.jpg'%index),quality=95)
(W/'final_evaluation.json').write_text(json.dumps({'rgb_metric':'Displayed 8-bit JPEG RGB, clipped to [0,1]; masked to modeled region and synthetic selected-toaster target','views':report,'quality_gate':'Experimental only: held-out quality and visible artifacts require further reconstruction work'},indent=2));print(json.dumps(report,indent=2))
