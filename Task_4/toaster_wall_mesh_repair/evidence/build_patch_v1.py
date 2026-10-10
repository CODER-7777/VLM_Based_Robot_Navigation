from pathlib import Path
import sys,json,numpy as np,trimesh,cv2
from PIL import Image
sys.path.insert(0,'/data/robotics/toshith/rxr_author/refined')
import kitchen_obj as K
R=Path('/data/robotics/toshith/rxr_author/refined');W=R/'toaster_wall_repair';W.mkdir(exist_ok=True)
C=np.array([[1,0,0],[0,0,1],[0,-1,0]],float)
# The visible tile surface is aligned with the finished counter/cabinet boundary.
patches=[('tiled_return',np.array([4.405,-5.44,.929]),np.array([4.405,-4.80,1.435]),(1,2),np.array([1,0,0])),('backsplash',np.array([4.405,-5.44,.929]),np.array([4.95,-5.44,1.435]),(0,2),np.array([0,1,0])),('return_end',np.array([4.375,-4.80,.929]),np.array([4.405,-4.80,1.435]),(0,2),np.array([0,1,0]))]
scene=trimesh.Scene();report=[];allmesh=[]
# Restrict colour sources to the calibrated nearby panorama; distant views are occluded by the tall cabinet.
photos=[ph for ph in K.CAMS if ph.startswith('58348305b0f84dd8b161aaf2d5b945ef_')]
for name,lo,hi,axes,normal in patches:
 a,b=axes;ww=max(96,round((hi[a]-lo[a])*1200));hh=round((hi[b]-lo[b])*1200)
 U,V=np.meshgrid((np.arange(ww)+.5)/ww,(np.arange(hh)+.5)/hh)
 P=np.tile(lo,(ww*hh,1));P[:,a]=lo[a]+U.ravel()*(hi[a]-lo[a]);P[:,b]=hi[b]-V.ravel()*(hi[b]-lo[b])
 acc=np.zeros((len(P),3));weight=np.zeros(len(P));used=[]
 for ph in photos:
  cam=K.CAMS[ph];uv=K.project(ph,P);u,v,d=uv.T
  dp=Path(K.PHOTOS)/'undistorted_depth_images'/ph.replace('_i','_d').replace('.jpg','.png')
  if not dp.exists():continue
  raw=np.asarray(Image.open(dp));dh,dw=raw.shape;depth=raw[np.clip((v*dh/1024).astype(int),0,dh-1),np.clip((u*dw/1280).astype(int),0,dw-1)]/4000
  direction=cam['c2w'][:3,3]-P;direction/=np.linalg.norm(direction,axis=1,keepdims=True);cos=direction@normal
  ok=(u>=0)&(u<1279)&(v>=0)&(v<1023)&(d>.1)&(depth>0)&(depth>=d-.018)&(depth<=d+(.25 if name=='tiled_return' else .065))&(cos>.06)
  # Exclude the original toaster explicitly, as its chrome can give invalid depth returns.
  if ph.endswith('_i2_4.jpg'):ok&=~((u>620)&(u<850)&(v>70)&(v<400))
  if ok.sum()<20:continue
  image=K.photo(ph);col=cv2.remap(image,u.astype(np.float32).reshape(hh,ww),v.astype(np.float32).reshape(hh,ww),cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE).reshape(-1,3)
  wt=ok*cos**2/np.maximum(d,.2)**2;acc+=col*wt[:,None];weight+=wt;used.append(ph)
 valid=weight>0;tex=np.clip(acc/np.maximum(weight[:,None],1e-9),0,255).astype(np.uint8).reshape(hh,ww,3);seen=valid.reshape(hh,ww)
 Image.fromarray(tex).save(W/(name+'_observed.png'));Image.fromarray((seen*255).astype(np.uint8)).save(W/(name+'_visibility.png'))
 # Hidden tile areas use repeats of observed tile at the approximate measured tile pitch.
 filled=seen.copy();pitch=.20
 offsets=sorted([(dy,dz) for dy in range(-3,4) for dz in range(-3,4) if dy or dz],key=lambda q:q[0]**2+q[1]**2)
 for dy,dz in offsets:
  dx=round(dy*pitch/(hi[a]-lo[a])*ww);dr=round(dz*pitch/(hi[b]-lo[b])*hh)
  if abs(dx)>=ww or abs(dr)>=hh:continue
  ry,rx=np.indices((hh,ww));sy=ry+dr;sx=rx+dx;inside=(sy>=0)&(sy<hh)&(sx>=0)&(sx<ww);sy=np.clip(sy,0,hh-1);sx=np.clip(sx,0,ww-1)
  take=(~filled)&inside&seen[sy,sx];tex[take]=tex[sy[take],sx[take]];filled[take]=True
 if not seen.any():
  # Narrow end trim is hidden/grazing; sample the clean tile colour from its photographed neighbouring return.
  prev=np.asarray(Image.open(W/'tiled_return.png'));tex[:]=np.median(prev.reshape(-1,3),axis=0)
 elif not filled.all():tex=cv2.inpaint(tex,(~filled).astype(np.uint8),5,cv2.INPAINT_TELEA)
 Image.fromarray(tex).save(W/(name+'.png'))
 corners=np.tile(lo,(4,1));corners[1,a]=hi[a];corners[2,[a,b]]=hi[[a,b]];corners[3,b]=hi[b]
 mesh=trimesh.Trimesh(corners,[[0,1,2],[0,2,3]],process=False)
 if np.dot(mesh.face_normals[0],normal)<0:mesh.faces=mesh.faces[:,::-1]
 allmesh.append(mesh.copy());g=mesh.copy();g.vertices=np.asarray(g.vertices)@C.T
 g.visual=trimesh.visual.TextureVisuals(uv=[[0,0],[1,0],[1,1],[0,1]],material=trimesh.visual.material.PBRMaterial(name=name,baseColorTexture=Image.fromarray(tex),metallicFactor=0,roughnessFactor=1,doubleSided=True));scene.add_geometry(g,geom_name=name)
 report.append({'surface':name,'lo':lo.tolist(),'hi':hi.tolist(),'observed_fraction':float(seen.mean()),'repeated_fraction':float((filled&~seen).mean()),'photos':used})
scene.export(W/'wall_patch.glb');trimesh.util.concatenate(allmesh).export(W/'wall_patch.ply')
spec={'surfaces':report,'delete_boxes':[[[4.25,-5.51,.931],[4.455,-4.795,1.435]],[[4.405,-5.53,.931],[4.95,-5.35,1.435]]],'reference_toaster':'User identifies Black & Decker 2-Slice Toaster, resembling T2030; installed mesh is a Cuisinart substitute.','texture_method':'Calibrated real RGB with depth rejection; hidden texels repeat observed tile at approximate 20 cm pitch, with residual inpainting. Not all tile pattern is directly observed.'}
json.dump(spec,open(W/'patch_spec.json','w'),indent=2);print(json.dumps(spec),flush=True)
