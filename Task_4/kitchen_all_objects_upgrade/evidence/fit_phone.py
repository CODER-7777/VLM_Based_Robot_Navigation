"""Fixed physically sized scan, fitted by photo silhouette with support constraints."""
from pathlib import Path
import sys,json,numpy as np,trimesh,cv2
from scipy.optimize import minimize
from PIL import Image
R=Path('/data/robotics/toshith/rxr_author/refined');W=R/'kitchen_all_upgrade';sys.path.insert(0,str(R))
import kitchen_obj as K
from product_fit import FastSil
from frames import RAW_TO_GLTF as C
s=trimesh.load(W/'phone_canonical.glb',force='mesh',process=False);v=np.asarray(s.vertices)@C;faces=np.asarray(s.faces)
v*=.295/.32;v-=np.r_[(v[:,:2].min(0)+v[:,:2].max(0))/2,v[:,2].min()]
photo='1eae5d4a0c0146c2b884d6b96d9b0e16_i2_3.jpg';box=[227,213,491,496]
mask=np.array(Image.open(W/'phone_target.png'))>0 if (W/'phone_target.png').exists() else K.sam_mask(photo,box);Image.fromarray((mask*255).astype('uint8')).save(W/'phone_target.png')
target=cv2.resize(mask.astype('uint8'),(320,256),interpolation=cv2.INTER_NEAREST).astype(bool);sil=FastSil([photo],[target]);sil.set_faces(faces)
base=np.array([6.80,-2.472,.929])
def transform(p):
 angle=np.radians(p[0]);c,sn=np.cos(angle),np.sin(angle);rot=np.array([[c,-sn,0],[sn,c,0],[0,0,1.]])
 return v@rot.T+base+[p[1],p[2],0]
def score(p):
 pts=transform(p)
 if pts[:,0].min()<6.48 or pts[:,0].max()>7.075 or pts[:,1].min()<-2.67 or pts[:,1].max()>-2.25:return 1+np.linalg.norm(p[1:])
 return -float(sil.ious(pts)[0])
best=None
for angle in range(0,360,15):
 p=[angle,0,0];val=score(p)
 if best is None or val<best[0]:best=(val,p)
result=minimize(score,best[1],method='Powell',bounds=[(best[1][0]-20,best[1][0]+20),(-.035,.035),(-.045,.045)],options={'maxiter':45,'xtol':.0005,'ftol':.0001})
pts=transform(result.x);base+=np.r_[result.x[1:],0]
s.vertices=pts@C.T
# Vertex colors from exactly the newly fitted visible surface, not scan depth.
cam=K.CAMS[photo];uv=K.project(photo,pts);u,zv,z=uv.T
x=np.clip(u.astype(int),0,1279);y=np.clip(zv.astype(int),0,1023)
col=np.tile([112.,119.,121.,255.],(len(pts),1))
valid=(z>.1)&(u>=0)&(u<1280)&(zv>=0)&(zv<1024)&mask[y,x]
# Grey plastics are preserved in hidden surfaces; only foreground photo pixels
# can add the keypad, LCD and handwritten labels.
source=K.photo(photo)[y,x].astype(float)
col[valid,:3]=source[valid]
s.visual=trimesh.visual.ColorVisuals(s,vertex_colors=col.astype('uint8'))
O=R/'kitchen/objects/phone_v3';O.mkdir(exist_ok=True);s.export(O/'world_display.glb')
raw=s.copy();raw.vertices=pts;raw.export(O/'world.ply')
old=json.loads((R/'kitchen/objects/phone_v2/fit.json').read_text());from shapely.geometry import MultiPoint,Polygon
hull=MultiPoint(pts[:,:2]).convex_hull.union(Polygon(old['delete_polygon'])).convex_hull
old.update(name='phone_v3',glb=str(O/'world_display.glb'),world_mesh=str(O/'world.ply'),base=base.tolist(),height=float(np.ptp(pts[:,2])),pose={'yaw_deg':float(result.x[0]),'fixed_max_source_dimension_m':.295},score=-float(result.fun),delete_polygon=np.asarray(hull.exterior.coords)[:-1].tolist(),product={'uid':'ede86b7cc9804f39a9fcafd263873ee0','name':'OFFICE TELEPHONE','author':'Aquateknica','license':'CC-BY-4.0','url':'https://sketchfab.com/3d-models/office-telephone-ede86b7cc9804f39a9fcafd263873ee0'},appearance_note='Author scan is untextured; visible color from kitchen photo and grey plastic fallback. Shape similar, not exact original phone.',photo_vertex_fraction=float(valid.mean()))
(O/'fit.json').write_text(json.dumps(old,indent=2));(W/'phone_placement.json').write_text(json.dumps({'fit':str(O/'fit.json'),'bounds':raw.bounds.tolist(),'photo_iou':-float(result.fun),'yaw_deg':float(result.x[0]),'color_coverage':float(valid.mean())},indent=2));print('PHONE_READY',old['pose'],raw.bounds.tolist(),-float(result.fun),flush=True)
