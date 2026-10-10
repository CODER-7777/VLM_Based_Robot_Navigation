import json,sys,math,copy
from pathlib import Path
import numpy as np,trimesh
from PIL import Image
from shapely.geometry import MultiPoint,Polygon
R=Path('/data/robotics/toshith/rxr_author/refined');W=R/'toaster_upgrade';O=R/'kitchen/objects/toaster_v3';O.mkdir(exist_ok=True)
sys.path.insert(0,str(R))
import kitchen_obj as K
from frames import RAW_TO_GLTF as C
uid='bc62dbead31f4a3293f4e17df6f342f7'
src=W/'candidates'/(uid+'.glb');scene=trimesh.load(src,force='scene')
nodes=[]
for node in scene.graph.nodes_geometry:
 M,key=scene.graph[node];m=scene.geometry[key].copy();m.apply_transform(M);nodes.append((node,m))
allv=np.vstack([np.asarray(m.vertices)@C for _,m in nodes]);lo=allv.min(0);hi=allv.max(0);center=(lo+hi)/2;center[2]=lo[2]
ph='58348305b0f84dd8b161aaf2d5b945ef_i2_4.jpg'
base=np.array([4.52,-5.19,.929]);delta=K.CAMS[ph]['c2w'][:3,3]-base;yaw=math.atan2(delta[1],delta[0]);co,si=np.cos(yaw),np.sin(yaw);rot=np.array([[co,-si,0],[si,co,0],[0,0,1]])
scale=.20/(hi[2]-lo[2]);result=trimesh.Scene();raw=[]
for node,m in nodes:
 v=(np.asarray(m.vertices)@C-center)*scale
 v[:,1]*=.88
 normal=np.asarray(m.face_normals)@C
 # Preserve a polished front/top with a black side housing, as in the reference photograph.
 subsets=[(np.ones(len(m.faces),bool),'steel')]
 if node.startswith(('FEET','CASE.001')):subsets=[(np.ones(len(m.faces),bool),'plastic')]
 elif node.startswith('CASE_'):
  fc=v[m.faces].mean(1);side=(np.abs(normal[:,1])>.66)&(fc[:,2]<.175)&(fc[:,0]<.102)
  subsets=[(~side,'steel'),(side,'plastic')]
 elif node.startswith(('Text.','BAGEL','Name_text','KNOB.000','cutter')):subsets=[(np.ones(len(m.faces),bool),'ink')]
 elif node.startswith(('LEDS','INDIC,GLASS')):subsets=[(np.ones(len(m.faces),bool),'indicator')]
 for mask,kind in subsets:
  if not mask.any():continue
  part=trimesh.Trimesh(v@rot.T+base,m.faces[mask],process=False);part.remove_unreferenced_vertices();raw.append(part.copy())
  g=part.copy();g.vertices=np.asarray(g.vertices)@C.T
  rgb={'steel':[190,192,193,255],'plastic':[14,16,18,255],'ink':[28,31,32,255],'indicator':[74,29,12,255]}[kind]
  mat=trimesh.visual.material.PBRMaterial(name=kind,baseColorFactor=rgb,metallicFactor=.98 if kind=='steel' else 0,roughnessFactor=.18 if kind=='steel' else .32)
  g.visual=trimesh.visual.TextureVisuals(material=mat);result.add_geometry(g,geom_name=node+'_'+kind)
# Close the downloaded shell with physically meaningful dark toasting chambers.
# Coordinates here are toaster-local metres: X depth, Y width, Z height.
def add_internal(part,label,kind):
 part.apply_transform(np.block([[rot,base[:,None]],[np.zeros((1,3)),np.ones((1,1))]]));raw.append(part.copy())
 g=part.copy();g.vertices=np.asarray(g.vertices)@C.T
 rgb=[100,103,105,255] if kind=='steel' else [5,5,5,255]
 mat=trimesh.visual.material.PBRMaterial(name=kind,baseColorFactor=rgb,metallicFactor=.98 if kind=='steel' else 0,roughnessFactor=.28 if kind=='steel' else .7)
 g.visual=trimesh.visual.TextureVisuals(material=mat);result.add_geometry(g,geom_name=label)
def internal_box(label,extent,position,kind='plastic'):
 part=trimesh.creation.box(extents=extent);part.apply_translation(position);add_internal(part,label,kind)
internal_box('chamber_floor',[.232,.150,.004],[0,0,.074])
for x in [-.115,.115]:internal_box('chamber_end_'+str(x),[.003,.150,.112],[x,0,.129])
for y in [-.074,.074,0]:internal_box('chamber_wall_'+str(y),[.232,.003,.112],[0,y,.129])
# Recessed steel top plate leaves two approximately 3 cm bread slots.
for y in [-.0615,.0615]:internal_box('top_edge_'+str(y),[.232,.027,.0015],[0,y,.1855],'steel')
internal_box('top_center',[.232,.035,.0015],[0,0,.1855],'steel')
for x in [-.109,.109]:internal_box('top_end_'+str(x),[.014,.150,.0015],[x,0,.1855],'steel')
for y in [-.058,-.014,.014,.058]:
 for z in [.136,.157,.178]:
  part=trimesh.creation.cylinder(radius=.00065,height=.216,sections=8)
  part.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[0,1,0]));part.apply_translation([0,y,z]);add_internal(part,'bread_guide_'+str(y)+'_'+str(z),'steel')
mesh=trimesh.util.concatenate(raw)
# Fit within the same cabinet/counter constraints as the accepted placement.
shift=max(0,4.425-mesh.bounds[0,0]);base[0]+=shift
if shift:
 mesh.apply_translation([shift,0,0])
 for m in result.geometry.values():m.vertices[:,0]+=shift
mesh.export(O/'world.ply');result.export(O/'world_pbr.glb')
old=json.load(open(R/'kitchen/objects/toaster_v2/fit.json'));hull=MultiPoint(mesh.vertices[:,:2]).convex_hull.buffer(.006).union(Polygon(old['delete_polygon'])).convex_hull
meta=next(v for v in json.load(open(W/'toaster_candidates.json')) if v['uid']==uid)
fit=dict(old,name='toaster_v3',glb=str(O/'world_baked.glb'),world_mesh=str(O/'world.ply'),base=base.tolist(),height=.20,matrix=np.eye(4).tolist(),pose={'yaw_deg':math.degrees(yaw),'scale':scale,'width_factor':.88,'up':'+Y'},product={'uid':uid,'name':meta['name'],'author':meta['user']['displayName'],'license':meta['license'],'url':meta['viewerUrl'],'glb':str(src)},realism_notes='Cuisinart geometry adapted to the photographed polished-steel/black finish. CC BY-NC asset; original controls/profile remain approximate.',delete_mode='centroid',protect_backsplash=True)
fit['delete_aabb']=[np.minimum(mesh.bounds[0]-[.006,.006,0],old['delete_aabb'][0]).tolist(),np.maximum(mesh.bounds[1]+.006,old['delete_aabb'][1]).tolist()];fit['delete_polygon']=np.asarray(hull.exterior.coords)[:-1].tolist()
fit.pop('score',None);fit['materials']=['steel','plastic','ink','indicator'];fit['pbr_glb']=str(O/'world_pbr_textured.glb');fit['finish_method']='Photo-derived environment reflections baked for Habitat; true metallic PBR variant retained'
json.dump(fit,open(O/'fit.json','w'),indent=2)
print('PLACED',base,'dimensions',mesh.extents,'yaw',math.degrees(yaw),flush=True)
# Reconstruct a lighting panorama from the real source panorama's calibrated perspective views.
cams=[v for name,v in K.CAMS.items() if name.startswith(ph.split('_')[0])]
w,h=2048,1024;u,v=np.meshgrid((np.arange(w)+.5)/w,(np.arange(h)+.5)/h)
lon=(u-.5)*2*np.pi;lat=(.5-v)*np.pi
D=np.stack([np.cos(lat)*np.cos(lon),np.cos(lat)*np.sin(lon),np.sin(lat)],-1).reshape(-1,3)
out=np.zeros((len(D),3),np.float32);weight=np.zeros(len(D),np.float32)
for cam in cams:
 q=D@cam['c2w'][:3,:3];z=-q[:,2];fx,fy,cx,cy=cam['K'];px=fx*q[:,0]/np.maximum(z,1e-6)+cx;py=cy-fy*q[:,1]/np.maximum(z,1e-6)
 ok=(z>0)&(px>=0)&(px<1279)&(py>=0)&(py<1023);ids=np.flatnonzero(ok);p=K.photo(cam['color']);ww=z[ids]**8
 out[ids]+=p[py[ids].astype(int),px[ids].astype(int)]*ww[:,None];weight[ids]+=ww
out=np.clip(out/np.maximum(weight[:,None],1e-6),0,255).astype(np.uint8);out[weight==0]=[120,118,112]
Image.fromarray(out.reshape(h,w,3)).save(W/'kitchen_environment.jpg',quality=97)
json.dump({'photo':ph,'base':base.tolist(),'camera':{'c2w':K.CAMS[ph]['c2w'].tolist(),'K':K.CAMS[ph]['K']},'dims':mesh.extents.tolist(),'panorama_views':len(cams)},open(W/'placement.json','w'),indent=2)
print('PANORAMA',len(cams),'coverage',float((weight>0).mean()),flush=True)
