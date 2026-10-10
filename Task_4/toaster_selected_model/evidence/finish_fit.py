"""Create a private manifest and audit script for the selected toaster."""
import json
from pathlib import Path
import numpy as np
import trimesh
from shapely.geometry import MultiPoint, Polygon
R = Path('/data/robotics/toshith/rxr_author/refined')
W = R / 'toaster_selected'
O = R / 'kitchen/objects/toaster_v4'
old = json.loads((R / 'kitchen/objects/toaster_v3/fit.json').read_text())
placement = json.loads((W / 'placement.json').read_text())
mesh = trimesh.load(O / 'world.ply', process=False)
hull = MultiPoint(mesh.vertices[:, :2]).convex_hull.buffer(.006).union(Polygon(old['delete_polygon'])).convex_hull
fit = dict(old, name='toaster_v4', glb=str(O / 'world_baked.glb'), pbr_glb=str(O / 'world_pbr.glb'), product_pbr_glb=str(O / 'product_pbr.glb'), world_mesh=str(O / 'world.ply'), base=placement['base'], height=.20, matrix=np.eye(4).tolist(), pose={'yaw_deg':placement['yaw_deg'],'scale':placement['uniform_scale'],'up':'+Y','uniform_scale':True}, product={'uid':'0d39352a32404ce7b71b8ac020844949','name':'toaster','author':'AtTheSpeedOf','license':'CC-BY-4.0','url':'https://sketchfab.com/3d-models/toaster-0d39352a32404ce7b71b8ac020844949','source':'https://mirror.traines.eu/sketchfab-backup/0d/0d39352a32404ce7b71b8ac020844949.zip','credit':'toaster by AtTheSpeedOf, CC BY 4.0; scaled and positioned; separate kitchen reflection bake.'}, materials=['Original base color, metallic/roughness and tangent normal maps'], realism_notes='Selected CC-BY model retains original geometry and PBR textures. Its Hamilton Beach markings/control arrangement differ from the Black & Decker photo. Habitat variant uses fixed photo-environment reflections; true PBR export retained.', finish_method='Original PBR material retained; separate camera-conditioned Cycles combined bake for matte Habitat stage')
fit['delete_aabb']=[np.minimum(mesh.bounds[0]-[.006,.006,0],old['delete_aabb'][0]).tolist(),np.maximum(mesh.bounds[1]+.006,old['delete_aabb'][1]).tolist()]
fit['delete_polygon']=np.asarray(hull.exterior.coords)[:-1].tolist()
(O / 'fit.json').write_text(json.dumps(fit,indent=2))
manifest=json.loads((R / 'toaster_wall_repair/manifest.json').read_text())
manifest=[str(O / 'fit.json') if isinstance(e,str) and '/toaster_v3/' in e else e for e in manifest]
(W / 'manifest.json').write_text(json.dumps(manifest,indent=2))
s=(R / 'toaster_wall_repair/audit.py').read_text().replace("W=R/'toaster_wall_repair'","W=R/'toaster_selected'")
(W / 'audit.py').write_text(s)
print('SELECTED_FIT_READY',fit['base'],mesh.extents,flush=True)
