from pathlib import Path
import json,numpy as np,trimesh
p=Path('rxr_long_route_search/environment_04/revision_02');probe=p/'probe';rng=np.random.default_rng(71)
cams={c['object_id']:c for c in json.load(open(probe/'close_camera_poses.json'))}
rois={'bag_brown_sofa':{'seat':[178,233,236,277],'back':[229,212,270,238]},'bag_pink_sofa':{'seat':[240,277,282,294],'back':[273,218,306,252]}}
planes={}
for oid,regions in rois.items():
 result={}
 for kind,box in regions.items():
  c=cams[oid];filename=oid+'_empty_close_depth.npy'
  if oid=='bag_brown_sofa':
   name='brown_overhead' if kind=='seat' else 'brown_other_side';c=next(v for v in json.load(open(probe/'extra_camera_poses.json')) if v['name']==name);filename=name+'_depth.npy'
  d=np.load(probe/filename);h,w=d.shape;yy,xx=np.indices(d.shape);local=np.stack([(xx+.5-w/2)*d/(w/2),-(yy+.5-h/2)*d/(w/2),-d],axis=-1);T=np.array(c['camera_to_world']);world=local@T[:3,:3].T+T[:3,3]
  x0,y0,x1,y1=box;pts=world[y0:y1,x0:x1].reshape(-1,3);pts=pts[np.isfinite(pts).all(axis=1)];best=None
  for _ in range(600):
   a,b,cc=pts[rng.choice(len(pts),3,replace=False)];n=np.cross(b-a,cc-a);length=np.linalg.norm(n)
   if length<1e-8:continue
   n/=length
   if kind=='seat' and abs(n[1])<.94:continue
   if kind=='back' and abs(n[1])>.65:continue
   off=-n@a;mask=abs(pts@n+off)<.006
   if best is None or mask.sum()>best.sum():best=mask
  assert best is not None
  clean=pts[best];center=clean.mean(axis=0);_,_,vh=np.linalg.svd(clean-center,full_matrices=False);n=vh[-1]
  if (kind=='seat' and n[1]<0) or (kind=='back' and (np.array(c['eye'])-center)@n<0):n=-n
  result[kind]={'normal':n.tolist(),'offset':float(-n@center),'center':center.tolist(),'inliers':int(best.sum()),'roi_xyxy':box,'rms_m':float(np.sqrt(np.mean(((clean-center)@n)**2)))}
 planes[oid]=result
print(json.dumps(planes,indent=2));(p/'surface_planes.json').write_text(json.dumps(planes,indent=2)+'\n')
# Bake source node transforms, rotate the bag front to +Z, remove the scan's
# black display ring and dangling underside fragments, and normalize to 42 cm.
s=trimesh.load(p/'assets/wv_backpack_photogrammetry.glb',force='scene');target=trimesh.Scene();cut=-0.8
R=trimesh.transformations.rotation_matrix(np.pi/2,[0,1,0]);allv=[];kept=[];removed=0
for node in s.graph.nodes_geometry:
 tf,k=s.graph[node];mesh=s.geometry[k].copy();mesh.apply_transform(tf)
 mask=np.all(mesh.vertices[mesh.faces,1]>=cut,axis=1);removed+=int((~mask).sum());mesh.update_faces(mask);mesh.remove_unreferenced_vertices()
 if len(mesh.faces)==0:continue
 mesh.apply_transform(R);kept.append((node,mesh));allv.append(mesh.vertices)
v=np.concatenate(allv);lo=v.min(axis=0);hi=v.max(axis=0);scale=.40/(hi[1]-lo[1]);origin=np.array([(lo[0]+hi[0])/2,lo[1],(lo[2]+hi[2])/2])
for node,mesh in kept:
 mesh.vertices=(mesh.vertices-origin)*scale;target.add_geometry(mesh,node_name=node,geom_name=node)
normalized=p/'assets/canvas_backpack_baked_clean_40cm.glb';normalized.write_bytes(target.export(file_type='glb'))
verts=np.concatenate([m.vertices for m in target.geometry.values()]);np.save(p/'assets/normalized_vertices.npy',verts)
request=json.load(open(p/'placement_request.json'));request['asset']='assets/canvas_backpack_baked_clean_40cm.glb';request['asset_height_m']=.40;request['lighting']='baked';request['source_model']='WV_ArtDev / SmallpolyArt Backpack Photogrammetry, CC BY 4.0';
contact={}
for item in request['placements']:
 pp=planes[item['object_id']];ns=np.array(pp['seat']['normal']);nb=np.array(pp['back']['normal']);yaw=np.arctan2(nb[0],nb[2]);tangent=np.cross(ns,nb);tangent/=np.linalg.norm(tangent);back_up=np.cross(nb,tangent);back_up/=np.linalg.norm(back_up);rot=np.column_stack([tangent,back_up,nb]);tilt=np.arccos(np.clip(back_up[1],-1,1));rv=verts@rot.T;hint=np.array(pp['seat']['center']);A=np.stack([ns,nb,tangent]);rhs=np.array([.001-pp['seat']['offset']-np.quantile(rv@ns,.02),.002-pp['back']['offset']-np.quantile(rv@nb,.02),tangent@hint]);translation=np.linalg.solve(A,rhs);matrix=np.eye(4);matrix[:3,:3]=rot;q=trimesh.transformations.quaternion_from_matrix(matrix)
 item['yaw_degrees']=float(np.rad2deg(yaw));item['lean_back_degrees']=float(np.rad2deg(tilt));item['rotation_xyzw']=[float(q[1]),float(q[2]),float(q[3]),float(q[0])];item['translation_world']=translation.tolist();item['support_world']=hint.tolist();item['placement_method']='Actual mesh body fitted to measured seat/backrest planes with 2% soft-contact allowance for loose strap tips; Bag back aligned to measured backrest plane, with lateral roll matched to cushion/back intersection.'
 gaps={key:float(np.min((rv+translation)@np.array(pp[key]['normal'])+pp[key]['offset'])) for key in ['seat','back']};contact[item['object_id']]={'minimum_clearances_m':gaps,'bulk_contact_quantile':.02,'note':'Soft-contact placement: 2% of thin/stray surface samples may enter the reconstructed cushion; no rigid-body settling claimed.','translation':translation.tolist(),'yaw_degrees':item['yaw_degrees'],'lean_back_degrees':float(np.rad2deg(tilt))}
request['status']='revision 2 fitted geometry; pending preview validation';(p/'placement_request.json').write_text(json.dumps(request,indent=2)+'\n');(p/'contact_checks.json').write_text(json.dumps(contact,indent=2)+'\n');(p/'assets/cleanup_report.json').write_text(json.dumps({'source':'wv_backpack_photogrammetry.glb','source_triangles':303347,'removed_triangles':removed,'retained_triangles':sum(len(m.faces) for m in target.geometry.values()),'cut_source_y':cut,'height_m':.40,'front_direction':'+Z','modifications':'Removed display ring/underside scan artifacts, baked node transforms, normalized Y-up and scale; no texture replacement or invented details.'},indent=2)+'\n');print('CONTACTS',json.dumps(contact,indent=2));print('cleaned extents',target.extents)
