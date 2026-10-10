import bpy,bmesh,json
from pathlib import Path
from mathutils import Vector
W=Path('/data/robotics/toshith/rxr_author/refined/toaster_wall_repair')
def apply():
 spec=json.load(open(W/'patch_spec.json'));deleted=0
 scan=[o for o in bpy.data.objects if o.type=='MESH' and not o.name.startswith('Kitchen_') and not o.hide_get()]
 for low,high in spec['delete_boxes']:
  lo=Vector(low);hi=Vector(high)
  for o in scan:
   ws=[o.matrix_world@Vector(c) for c in o.bound_box]
   if any(min(w[a] for w in ws)>hi[a] or max(w[a] for w in ws)<lo[a] for a in range(3)):continue
   bm=bmesh.new();bm.from_mesh(o.data);M=o.matrix_world;inv=M.inverted()
   for ax in range(3):
    for value in [lo[ax],hi[ax]]:
     p=Vector((0,0,0));p[ax]=value;n=Vector((0,0,0));n[ax]=1
     bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=inv@p,plane_no=M.to_3x3().transposed()@n,clear_inner=False,clear_outer=False)
   kill=[]
   for f in bm.faces:
    p=M@f.calc_center_median()
    if all(lo[a]-1e-6<=p[a]<=hi[a]+1e-6 for a in range(3)):kill.append(f)
   deleted+=len(kill)
   if kill:bmesh.ops.delete(bm,geom=kill,context='FACES')
   bm.to_mesh(o.data);o.data.update();bm.free()
 before=set(bpy.data.objects);imgs=set(bpy.data.images)
 for i,im in enumerate(bpy.data.images):
  if im.name.startswith('Image'):im.name='Wall_hold_'+str(i)
 bpy.ops.import_scene.gltf(filepath=str(W/'wall_patch.glb'))
 for i,im in enumerate(set(bpy.data.images)-imgs):im.name='WallPatch_'+str(i)
 for o in set(bpy.data.objects)-before:o.name='WallRepair_'+o.name
 (W/'geometry_result.json').write_text(json.dumps({'scan_faces_removed':deleted,'surfaces_added':len(spec['surfaces']),'patch_spec':str(W/'patch_spec.json')},indent=2))
 print('WALL_REPAIR',deleted,'scan faces removed',flush=True)
