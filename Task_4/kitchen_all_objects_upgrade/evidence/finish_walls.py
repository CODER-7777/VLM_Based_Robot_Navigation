"""Photo tile grain for hidden regions; update only embedded private wall images."""
from pathlib import Path
import json,struct,cv2,numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt
W=Path('/data/robotics/toshith/rxr_author/refined/kitchen_all_upgrade');rows=json.loads((W/'wall_materials.json').read_text());report=[]
for row in rows:
 p=Path(row['texture']);atlas=np.asarray(Image.open(p).convert('RGB'),float)/255;mask=np.asarray(Image.open(W/(row['name']+'_observed.png')))>0
 lum=atlas.mean(-1);sat=atlas.max(-1)-atlas.min(-1);clean=mask&(lum>.25)&(lum<.85)&(sat>.045)
 dt=distance_transform_edt(clean);y,x=np.unravel_index(dt.argmax(),dt.shape);radius=max(4,min(35,int(dt.max()*.75)));patch=atlas[max(0,y-radius):y+radius,max(0,x-radius):x+radius]
 h,w=mask.shape;spacing=round(w/(row['horizontal'][1]-row['horizontal'][0])*.1524);tile=cv2.resize(patch,(spacing-2,spacing-2),interpolation=cv2.INTER_CUBIC)
 cell=np.full((spacing,spacing,3),np.median(atlas[mask],axis=0)*1.13);cell[2:,2:]=tile
 # Estimate grid phase from the actual visible grout in the photographs.
 white=lum-sat*.75;horizontal=np.sum(white*mask,0)/np.maximum(mask.sum(0),1);vertical=np.sum(white*mask,1)/np.maximum(mask.sum(1),1)
 px=max(range(spacing),key=lambda a:horizontal[a::spacing].mean());py=max(range(spacing),key=lambda a:vertical[a::spacing].mean())
 yy,xx=np.mgrid[:h,:w];synth=cell[(yy-py)%spacing,(xx-px)%spacing];blend=np.clip(distance_transform_edt(~mask)/10,0,1)
 atlas=atlas*(1-blend[...,None])+synth*blend[...,None];Image.fromarray(np.clip(atlas*255,0,255).astype('uint8')).save(p)
 report.append({'wall':row['name'],'source_patch_center_px':[int(x),int(y)],'patch_radius_px':radius,'infill':'photographed warm ceramic grain, approximate six-inch grid; observed pixels preserved','observed_fraction':float(mask.mean())})
# Append replacement image bytes so existing geometry buffer offsets stay intact.
for file in ['test.glb','test_pbr.glb']:
 p=W/file;raw=p.read_bytes();magic,ver,total=struct.unpack('<III',raw[:12]);length,typ=struct.unpack('<II',raw[12:20]);data=json.loads(raw[20:20+length]);start=20+length;blen,btyp=struct.unpack('<II',raw[start:start+8]);binary=bytearray(raw[start+8:start+8+blen]);found=[]
 for image in data.get('images',[]):
  name=image.get('name','');row=next((r for r in rows if Path(r['texture']).stem in name),None)
  if not row:continue
  payload=Path(row['texture']).read_bytes();offset=len(binary);binary.extend(payload);binary.extend(b'\0'*((-len(binary))%4));idx=len(data['bufferViews']);data['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':len(payload)});image['bufferView']=idx;image['mimeType']='image/png';image.pop('uri',None);found.append(name)
 if len(found)!=3:raise RuntimeError('Wall embedded-image match failed '+str(found))
 data['buffers'][0]['byteLength']=len(binary);js=json.dumps(data,separators=(',',':')).encode();js+=b' '*((-len(js))%4);out=struct.pack('<III',magic,ver,12+8+len(js)+8+len(binary))+struct.pack('<II',len(js),0x4e4f534a)+js+struct.pack('<II',len(binary),0x004e4942)+binary;temp=W/(file+'.tmp');temp.write_bytes(out);temp.replace(p);print('WALL_IMAGES_UPDATED',file,found,flush=True)
(W/'wall_infill.json').write_text(json.dumps(report,indent=2))
