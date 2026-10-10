from pathlib import Path
import json,numpy as np,trimesh
from shapely.geometry import MultiPoint,Polygon
from scipy.spatial import cKDTree
R=Path('/data/robotics/toshith/rxr_author/refined');W=R/'kitchen_all_upgrade';spec=json.loads((R/'kitchen/counters_spec.json').read_text())['counters'];surfaces=[(c['name'],Polygon(c['polygon']),c['z']+.002) for c in spec];surfaces.append(('rangetop',Polygon([(6.405,-3.995),(7.114,-3.995),(7.114,-3.081),(6.405,-3.081)]),.991))
rows=[]
for entry in json.loads((W/'manifest.json').read_text()):
 if not isinstance(entry,str):continue
 fit=json.loads(Path(entry).read_text());name=fit['name']
 if name.startswith(('counter_','sink_')) or name=='rangetop':continue
 points=np.asarray(trimesh.load(fit['world_mesh'],process=False).vertices);hull=MultiPoint(points[:,:2]).convex_hull;bot=float(points[:,2].min());below=[(n,p,z) for n,p,z in surfaces if p.contains(hull.centroid) and z<=bot+.03];surf=max(below,key=lambda e:e[2]) if below else None
 rows.append({'name':name,'bottom_z':bot,'support':surf[0] if surf else None,'support_z':surf[2] if surf else None,'base_gap_mm':(bot-surf[2])*1000 if surf else None,'bounds':np.array([points.min(0),points.max(0)]).tolist(),'counter_fraction':float(hull.intersection(surf[1]).area/max(hull.area,1e-9)) if surf else None})
raw=np.load(W/'scene_refined.npz');assert all(np.isfinite(raw[k]).all() for k in ['means','quats','scales','opacities','sh']);assert (raw['scales']>0).all();assert ((raw['opacities']>0)&(raw['opacities']<=1)).all()
report={'props':rows,'prop_count':len(rows),'gaussians':len(raw['means']),'all_gaussian_parameters_finite':True,'geometry':'fixed mesh-surface samples; photo changes affect appearance only except the explicitly fitted miniature jug','phone_visual':'photo-fitted physical desk-phone product with photo-grounded controls', 'frog_visual':'sparse prior visual reconstruction with bounded support/wall correction','audit_log':str(W/'audit.log'),'limits':['Some object silhouettes and unseen surfaces remain approximate.','Hidden counter/backsplash material uses photographic infill.','Specular Gaussian colors are a fixed-light approximation; original toaster PBR remains separate.','Depth is opacity-weighted expected optical-axis depth, not an independent physical depth measurement.']};(W/'validation.json').write_text(json.dumps(report,indent=2));print('VALIDATED',len(rows),'props',report['gaussians'],'finite Gaussians',flush=True)
