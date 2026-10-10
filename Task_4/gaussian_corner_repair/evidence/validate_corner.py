"""Compare optical depth with repaired-mesh ray hits at five fixed poses.

This verifies consistency with the repaired mesh, not measured scene truth.
"""
from pathlib import Path
import json,sys
import numpy as np
import trimesh
R=Path('/data/robotics/toshith/rxr_author/refined');W=R/'split_visuals';O=W/'corner_v2'
sys.path.insert(0,str(W/'vendor'))
meta=json.loads((O/'construction.json').read_text());lo,hi=np.array(meta['region'])
scene=trimesh.load(R/'toaster_selected/test.glb',force='scene');parts=[]
for node in scene.graph.nodes_geometry:
 transform,key=scene.graph[node];mesh=scene.geometry[key]
 vertices=trimesh.transform_points(mesh.vertices,transform)
 if np.any(vertices.max(0)<lo) or np.any(vertices.min(0)>hi):continue
 tri=vertices[mesh.faces];keep=((tri.max(1)>=lo)&(tri.min(1)<=hi)).all(1)
 if keep.any():parts.append(trimesh.Trimesh(vertices,mesh.faces[keep],process=False))
reference=trimesh.util.concatenate(parts);reference.remove_unreferenced_vertices()
records=json.loads((O/'comparison.json').read_text());rng=np.random.default_rng(42);results=[]
for i,record in enumerate(records):
 cam=record['camera'];width,height=cam['width'],cam['height'];K=np.array(cam['K']);c2w=np.array(cam['c2w_raw_gl'])
 selection=rng.choice(width*height,size=min(10000,width*height),replace=False)
 y,x=np.divmod(selection,width)
 local_rays=np.stack([(x+.5-K[0,2])/K[0,0],-(y+.5-K[1,2])/K[1,1],np.full(len(x),-1.)],1)
 rays=local_rays@c2w[:3,:3].T;origins=np.broadcast_to(c2w[:3,3],rays.shape)
 hits,ray_ids,_=reference.ray.intersects_location(origins,rays,multiple_hits=False)
 inside=((hits>=lo-.001)&(hits<=hi+.001)).all(1)
 hits=hits[inside];ray_ids=ray_ids[inside]
 expected=-((hits-c2w[:3,3])@c2w[:3,:3])[:,2]
 comparison={}
 for suffix in ['before','after']:
  dep=np.load(O/'previews'/('view%d_%s_depth.npz'%(i,suffix)))
  actual=dep['depth_m'][y[ray_ids],x[ray_ids]]
  valid=np.isfinite(actual)
  # Foreground outside the clipped reference may legitimately occlude it.
  # Report this separately rather than silently treating it as depth accuracy.
  delta=np.abs(actual[valid]-expected[valid])
  comparison[suffix]={'sampled_reference_hits':len(expected),'finite_depth_fraction_on_reference':float(valid.mean()),'median_depth_absolute_error_to_mesh_m':float(np.median(delta)),'p90_depth_absolute_error_to_mesh_m':float(np.percentile(delta,90)),'cuda_raster_ms':record[suffix]['cuda_raster_ms'],'image_valid_depth_fraction':record[suffix]['valid_depth_fraction']}
 result={'view':i,'camera_frame_id':cam['frame_id'],**comparison};results.append(result);print('MESH_DEPTH_CHECK',json.dumps(result),flush=True)
arrays=np.load(O/'scene_refined.npz');samples=np.load(O/'corner_samples.npz')
offset=len(arrays['means'])-len(samples['means']);product=arrays['means'][offset:][samples['product']]
fit=json.loads((R/'kitchen/objects/toaster_v4/fit.json').read_text())
report={'views':results,'product_min_mean_z_m':float(product[:,2].min()),'counter_surface_z_m':.929,'product_support_height_error_m':float(abs(product[:,2].min()-.929)),'geometry_changed_by_appearance_fit':not np.array_equal(arrays['means'][offset:],samples['means']),'reference_triangles':len(reference.faces),'limits':['Depth errors are relative to the repaired mesh, not an independent sensor measurement.','The cropped mesh reference omits some foreground occluders outside the repaired corner.','Valid depth coverage is not a photorealism or accuracy score.']}
assert report['product_support_height_error_m']<1e-5
assert not report['geometry_changed_by_appearance_fit']
assert all(r['after']['finite_depth_fraction_on_reference']>.97 for r in results)
(O/'geometry_validation.json').write_text(json.dumps(report,indent=2));print('GEOMETRY_VALIDATION_READY',flush=True)
