import os, sys
os.environ['MP3D_W']='1280'
sys.path.insert(0,'/data/robotics/toshith/rxr_author/refined')
import numpy as np
from PIL import Image,ImageDraw
from mp3d_cams import load_conf,make_sim,render,photo
from pathlib import Path
R=Path('/data/robotics/toshith/rxr_author/refined');W=R/'toaster_selected';P=W/'previews';P.mkdir(exist_ok=True)
cam=next(c for c in load_conf() if c['color']=='58348305b0f84dd8b161aaf2d5b945ef_i2_4.jpg')
def look(eye,target):
 eye=np.array(eye,float);f=np.array(target)-eye;f/=np.linalg.norm(f);r=np.cross(f,[0,0,1.]);r/=np.linalg.norm(r);u=np.cross(r,f);m=np.eye(4);m[:3,:3]=np.stack([r,u,-f],axis=1);m[:3,3]=eye;return {'c2w':m}
imgs=[Image.fromarray(photo(cam))];novel=[]
for g in [R/'toaster_wall_repair/test.glb',W/'test.glb']:
 s=make_sim(str(g));imgs.append(Image.fromarray(render(s,cam)))
 if g.parent==W:
  for eye in [[4.9,-4.5,1.42],[4.75,-4.65,1.23],[4.82,-5.08,1.36]]:
   novel.append(Image.fromarray(render(s,look(eye,[4.52,-5.19,1.03]))))
 s.close()
crop=(500,0,1100,480);panel=Image.new('RGB',(1800,510),'#153c2c');d=ImageDraw.Draw(panel)
for i,(im,label) in enumerate(zip(imgs,['Real photograph','Previous toaster + repaired wall','Selected AtTheSpeedOf model'])):
 d.text((i*600+8,8),label,fill='white');panel.paste(im.crop(crop),(i*600,30))
panel.save(P/'toaster_comparison.jpg',quality=95)
full=Image.new('RGB',(2560,1024));full.paste(imgs[0],(0,0));full.paste(imgs[2],(1280,0));full.save(P/'toaster_full_scene.jpg',quality=93)
nov=Image.new('RGB',(3840,1024))
for i,im in enumerate(novel):nov.paste(im,(1280*i,0))
nov.save(P/'toaster_novel_views.jpg',quality=93)
print('SELECTED_TOASTER_PREVIEWS_COMPLETE',flush=True)
