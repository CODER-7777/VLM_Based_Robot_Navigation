"""Save actual old/new CUDA outputs at identical calibrated and user poses."""
import json,base64,io,time
from pathlib import Path
from urllib.request import Request,urlopen
import numpy as np
from PIL import Image, ImageDraw
W=Path('/data/robotics/toshith/rxr_author/refined/split_visuals')
O=W/'corner_v2';(O/'previews').mkdir(exist_ok=True)
def get(port,path):
 with urlopen(f'http://127.0.0.1:{port}'+path,timeout=60) as r:return json.load(r)
def render(port,camera):
 with urlopen(Request(f'http://127.0.0.1:{port}/render',data=json.dumps(camera).encode(),headers={'Content-Type':'application/json'}),timeout=120) as r:return json.load(r)
current=get(8778,'/state')
(O/'user_pose_before.json').write_text(json.dumps(current,indent=2))
records=json.loads((W/'data/cameras.json').read_text())
reference=next(r for r in records if r['name']=='58348305b0f84dd8b161aaf2d5b945ef_i2_4.jpg')
cameras=[dict(reference,frame_id='comparison_reference'),dict(current,frame_id='comparison_user')]
def look(eye,target):
 eye=np.array(eye,float);f=np.array(target)-eye;f/=np.linalg.norm(f);r=np.cross(f,[0,0,1]);r/=np.linalg.norm(r);u=np.cross(r,f)
 m=np.eye(4);m[:3,:3]=np.stack([r,u,-f],axis=1);m[:3,3]=eye
 return m.tolist()
for i,eye in enumerate([[4.90,-4.50,1.42],[4.75,-4.65,1.23],[4.82,-5.08,1.36]]):
 cameras.append(dict(reference,c2w_raw_gl=look(eye,[4.52,-5.19,1.03]),frame_id='comparison_novel%d'%i))
report=[]
for i,camera in enumerate(cameras):
 results=[render(port,camera) for port in [8779,8781]]
 panel=Image.new('RGB',(camera['width']*2,camera['height']+30),'#153c2c');draw=ImageDraw.Draw(panel)
 for j,(result,label) in enumerate(zip(results,['Previous Gaussian scene','Dense surface-anchored corner'])):
  image=Image.open(io.BytesIO(base64.b64decode(result['rgb_jpeg'])))
  panel.paste(image,(j*camera['width'],30));draw.text((j*camera['width']+8,8),label,fill='white')
  (O/'previews'/('view%d_%s.jpg'%(i,['before','after'][j]))).write_bytes(base64.b64decode(result['rgb_jpeg']))
  (O/'previews'/('view%d_%s_depth.npz'%(i,['before','after'][j]))).write_bytes(base64.b64decode(result['depth_npz']))
 panel.save(O/'previews'/('comparison%d.jpg'%i),quality=95)
 report.append({'camera':camera,'before':{k:v for k,v in results[0].items() if k not in ['rgb_jpeg','depth_png','depth_npz']},'after':{k:v for k,v in results[1].items() if k not in ['rgb_jpeg','depth_png','depth_npz']}})
 print('COMPARE_VIEW',i,'coverage',[r['valid_depth_fraction'] for r in results],flush=True)
(O/'comparison.json').write_text(json.dumps(report,indent=2))
print('COMPARISONS_READY',flush=True)
