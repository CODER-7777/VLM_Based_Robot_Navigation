import os,sys,json
os.environ['MP3D_W']='1280';sys.path.insert(0,'/data/robotics/toshith/rxr_author/refined')
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from mp3d_cams import load_conf,make_sim,render,photo
R=Path('/data/robotics/toshith/rxr_author/refined');O=R/'kitchen_all_upgrade';P=O/'previews';P.mkdir(exist_ok=True)
cams={c['color']:c for c in load_conf()};items={}
for l in (R/'kitchen/kitchen_items.txt').read_text().splitlines():
 t=l.split()
 if len(t)==6:
  try:items[t[0]]=(t[1],list(map(int,t[2:])))
  except ValueError:pass
items.update(frogs=('f7a060bfa1164b5e9c5cca04284f6d6b_i1_4.jpg',[485,650,880,960]),paper_towel=('f7a060bfa1164b5e9c5cca04284f6d6b_i2_4.jpg',[925,0,1120,260]))
images={}
for label,g in [('previous',R/'toaster_selected/test.glb'),('updated',O/'test.glb')]:
 sim=make_sim(str(g))
 for ph in set(v[0] for v in items.values()):
  image=Image.fromarray(render(sim,cams[ph]));images[(label,ph)]=image;image.save(P/(label+'_'+ph))
 sim.close()
rows=[]
for name,(ph,b) in items.items():
 x0,y0,x1,y1=b;b=(max(0,x0-45),max(0,y0-45),min(1280,x1+45),min(1024,y1+45));ims=[Image.fromarray(photo(cams[ph]))]+[images[(l,ph)] for l in ['previous','updated']]
 h=260;w=round((b[2]-b[0])*h/(b[3]-b[1]));row=Image.new('RGB',(w*3,h+25),'#153c2c');d=ImageDraw.Draw(row)
 for i,(im,l) in enumerate(zip(ims,['Real photo','Previous mesh','Updated mesh'])):row.paste(im.crop(b).resize((w,h)),(w*i,25));d.text((w*i+5,5),l,fill='white')
 row.save(P/('mesh_'+name+'.jpg'),quality=94);rows.append({'name':name,'photo':ph,'box':b,'comparison':'mesh_'+name+'.jpg'})
(P/'mesh_index.json').write_text(json.dumps(rows,indent=2));print('ALL_MESH_PREVIEWS_READY',len(rows),flush=True)
